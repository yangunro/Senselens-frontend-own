from sqlalchemy import text

from app.database import engine
from app.services.dynamic_route_store import (
    get_dynamic_route,
    save_dynamic_routes,
)
from app.services.google_routes_service import get_google_routes
from app.services.forecast_service import build_pedestrian_forecast
from app.services.pedestrian_service import (
    get_latest_pedestrian_snapshot,
)
from app.services.construction_service import get_active_construction_sites
from app.services.lighting_service import get_lights_in_bounds
from app.services.refuges_service import get_refuges
from app.services.route_analysis_service import (
    analyse_route,
    decode_route,
    refuges_near_route,
    route_bounding_box,
)


DEFAULT_ORIGIN = {
    "lat": -37.8136,
    "lng": 144.9631,
}


def get_routes(
    destination=None,
    origin_lat=None,
    origin_lng=None,
    destination_lat=None,
    destination_lng=None,
    avoid_construction=False,
):
    """
    Generate live Google walking routes when a destination is supplied.
    Without a destination, preserve the existing stored-route API.
    """

    if destination:
        origin = {
            "lat": (
                origin_lat
                if origin_lat is not None
                else DEFAULT_ORIGIN["lat"]
            ),
            "lng": (
                origin_lng
                if origin_lng is not None
                else DEFAULT_ORIGIN["lng"]
            ),
        }
        destination_waypoint = (
            {
                "lat": destination_lat,
                "lng": destination_lng,
            }
            if (
                destination_lat is not None
                and destination_lng is not None
            )
            else destination
        )
        routes = get_google_routes(
            origin,
            destination_waypoint,
        )
        pedestrian_snapshot = get_latest_pedestrian_snapshot()

        # Construction/lighting are enhancements on top of route generation,
        # not the core feature — if either lookup fails for any reason (DB
        # hiccup, bad data), the route itself should still come back rather
        # than the whole request failing over an optional extra.
        try:
            construction_sites = get_active_construction_sites()
        except Exception as error:
            print(f"Construction site lookup failed, continuing without it: {error}")
            construction_sites = []

        # One lighting fetch covering every alternative, not one per route —
        # they all run through roughly the same area, and a DB round trip
        # per alternative would noticeably slow down route generation.
        light_candidates = []
        try:
            all_points = [decode_route(route.get("polyline")) for route in routes]
            boxes = [route_bounding_box(points) for points in all_points if points]
            if boxes:
                min_lat = min(box[0] for box in boxes)
                max_lat = max(box[1] for box in boxes)
                min_lng = min(box[2] for box in boxes)
                max_lng = max(box[3] for box in boxes)
                light_candidates = get_lights_in_bounds(
                    min_lat, max_lat, min_lng, max_lng
                )
        except Exception as error:
            print(f"Lighting lookup failed, continuing without it: {error}")
            light_candidates = []

        routes = [
            analyse_route(
                route,
                pedestrian_snapshot,
                construction_sites=construction_sites,
                light_candidates=light_candidates,
            )
            for route in routes
        ]
        routes.sort(
            key=lambda route: (
                # Only takes priority over crowd/duration when the user has
                # opted in via their "avoid construction zones" preference —
                # otherwise a route isn't penalised for something the rider
                # never asked to avoid.
                avoid_construction and route["hasActiveConstruction"],
                route["sensoryScore"] is None,
                (
                    route["sensoryScore"]
                    if route["sensoryScore"] is not None
                    else 101
                ),
                route["durationMinutes"],
            )
        )

        for index, route in enumerate(routes):
            is_recommended = index == 0
            has_score = route["sensoryScore"] is not None
            has_alternatives = len(routes) > 1
            route_name = {
                "low": "Lower-crowd walking route",
                "medium": "Moderate-crowd walking route",
                "high": "Higher-crowd walking route",
                "unknown": "Walking route",
            }[route["level"]]
            route.update({
                "tag": (
                    "RECOMMENDED FOR YOU"
                    if is_recommended and has_score and has_alternatives
                    else "ONLY AVAILABLE ROUTE"
                    if is_recommended and not has_alternatives
                    else "GOOGLE RECOMMENDED"
                    if is_recommended
                    else "ALTERNATIVE ROUTE"
                ),
                "name": f"{route_name} {index + 1}",
                "footnote": (
                    "Lowest measured crowd exposure"
                    if is_recommended and has_score and has_alternatives
                    else "Only available walking route"
                    if is_recommended and not has_alternatives
                    else "Google recommended route"
                    if is_recommended
                    else ""
                ),
                "recommended": is_recommended,
                "progress": 0,
                "transit": None,
                "alternativeId": None,
            })

        if routes:
            recommended_id = routes[0]["id"]
            for route in routes[1:]:
                route["alternativeId"] = recommended_id

        save_dynamic_routes(routes)

        return [
            {
                "id": route["id"],
                "tag": route["tag"],
                "level": route["level"],
                "levelLabel": route["levelLabel"],
                "name": route["name"],
                "description": route["description"],
                "duration": route["duration"],
                "durationMinutes": route["durationMinutes"],
                "footnote": route["footnote"],
                "recommended": route["recommended"],
                "sensoryScore": route["sensoryScore"],
                "matchedSensorCount": route["matchedSensorCount"],
                "pedestrianObservedAt": route["pedestrianObservedAt"],
                "hasActiveConstruction": route["hasActiveConstruction"],
                "constructionSitesNearby": route["constructionSitesNearby"],
                "averageLux": route["averageLux"],
                "lightingComfort": route["lightingComfort"],
                "factors": route["factors"],
                "transit": route["transit"],
            }
            for route in routes
        ]

    query = text("""
        SELECT
            "RouteID",
            "OriginLat",
            "OriginLng",
            "DestLat",
            "DestLng",
            "RouteType",
            "DistanceM",
            "EstDurationMin"
        FROM "Route"
        ORDER BY "EstDurationMin" ASC;
    """)

    with engine.connect() as conn:
        rows = conn.execute(query).mappings().all()

    routes = []

    for row in rows:
        routes.append({
            "routeId": str(row["RouteID"]),
            "routeType": row["RouteType"],
            "distanceM": row["DistanceM"],
            "durationMin": row["EstDurationMin"],
            "origin": {
                "lat": float(row["OriginLat"]),
                "lng": float(row["OriginLng"]),
            },
            "destination": {
                "lat": float(row["DestLat"]),
                "lng": float(row["DestLng"]),
            },
        })

    return routes


def get_route(route_id):
    dynamic_route = get_dynamic_route(route_id)

    if dynamic_route is not None:
        return {
            "name": dynamic_route["name"],
            "level": dynamic_route["level"],
            "levelLabel": dynamic_route["levelLabel"],
            "duration": dynamic_route["duration"],
            "durationMinutes": dynamic_route["durationMinutes"],
            "distance": dynamic_route["distance"],
            "distanceMeters": dynamic_route["distanceMeters"],
            "progress": dynamic_route["progress"],
            "factors": dynamic_route["factors"],
            "transit": dynamic_route["transit"],
            "alternativeId": dynamic_route["alternativeId"],
            "polyline": dynamic_route["polyline"],
            "steps": dynamic_route["steps"],
            "origin": dynamic_route["origin"],
            "destination": dynamic_route["destination"],
            "sensoryScore": dynamic_route["sensoryScore"],
            "matchedSensorCount": dynamic_route["matchedSensorCount"],
            "routeAverageCount": dynamic_route["routeAverageCount"],
            "pedestrianObservedAt": dynamic_route["pedestrianObservedAt"],
            "sensorRadiusM": dynamic_route["sensorRadiusM"],
            "nearbySensors": dynamic_route["nearbySensors"],
            "hasActiveConstruction": dynamic_route["hasActiveConstruction"],
            "constructionSitesNearby": dynamic_route["constructionSitesNearby"],
            "averageLux": dynamic_route["averageLux"],
            "lightingComfort": dynamic_route["lightingComfort"],
        }

    query = text("""
        SELECT
            "RouteID",
            "OriginLat",
            "OriginLng",
            "DestLat",
            "DestLng",
            "RouteType",
            "DistanceM",
            "EstDurationMin"
        FROM "Route"
        WHERE "RouteID" = :route_id;
    """)

    with engine.connect() as conn:
        row = conn.execute(
            query,
            {"route_id": route_id},
        ).mappings().first()

    if row is None:
        return None

    return {
        "routeId": str(row["RouteID"]),
        "routeType": row["RouteType"],
        "distanceM": row["DistanceM"],
        "durationMin": row["EstDurationMin"],
        "origin": {
            "lat": float(row["OriginLat"]),
            "lng": float(row["OriginLng"]),
        },
        "destination": {
            "lat": float(row["DestLat"]),
            "lng": float(row["DestLng"]),
        },
    }

def get_route_alerts(route_id):
    dynamic_route = get_dynamic_route(route_id)

    if dynamic_route is not None:
        if (
            dynamic_route["sensoryScore"] is not None
            and dynamic_route["sensoryScore"] >= 65
        ):
            return [{
                "type": "crowd",
                "title": "HIGH CROWD EXPOSURE",
                "level": "high",
                "message": (
                    "This route passes reporting sensors with higher "
                    "current pedestrian activity."
                ),
                "observedAt": dynamic_route["pedestrianObservedAt"],
            }]

        return []

    alerts = []

    sensory_query = text("""
        SELECT
            "PedestrianDensityScore",
            "ConstructionExposureScore",
            "LightingComfortScore",
            "ComputedAt"
        FROM "SensoryScore"
        WHERE "RouteID" = :route_id
        ORDER BY "ComputedAt" DESC
        LIMIT 1;
    """)

    with engine.connect() as conn:
        sensory_score = conn.execute(
            sensory_query,
            {"route_id": route_id},
        ).mappings().first()

    if sensory_score:
        if (
            sensory_score["PedestrianDensityScore"] is not None
            and float(sensory_score["PedestrianDensityScore"]) >= 0.67
        ):
            alerts.append({
                "type": "crowd",
                "level": "high",
                "message": "High pedestrian activity detected on this route.",
                "observedAt": (
                    sensory_score["ComputedAt"].isoformat()
                    if sensory_score["ComputedAt"] is not None
                    else None
                ),
            })

        if (
            sensory_score["ConstructionExposureScore"] is not None
            and float(sensory_score["ConstructionExposureScore"]) >= 0.67
        ):
            alerts.append({
                "type": "construction",
                "level": "high",
                "message": "High construction exposure detected on this route.",
                "observedAt": (
                    sensory_score["ComputedAt"].isoformat()
                    if sensory_score["ComputedAt"] is not None
                    else None
                ),
            })

    transit_query = text("""
        SELECT
            "VehicleMode",
            "CongestionLevel",
            "OccupancyStatus",
            "OccupancyPct",
            "ObservedAt"
        FROM "TransitCongestionSignal"
        WHERE "RouteID" = :route_id
        ORDER BY "ObservedAt" DESC;
    """)

    with engine.connect() as conn:
        transit_signals = conn.execute(
            transit_query,
            {"route_id": route_id},
        ).mappings().all()

    for signal in transit_signals:
        alerts.append({
            "type": "transit",
            "vehicleMode": signal["VehicleMode"],
            "congestionLevel": signal["CongestionLevel"],
            "occupancyStatus": signal["OccupancyStatus"],
            "occupancyPct": signal["OccupancyPct"],
            "observedAt": (
                signal["ObservedAt"].isoformat()
                if signal["ObservedAt"] is not None
                else None
            ),
        })

    return alerts

def get_route_forecast(route_id):
    dynamic_route = get_dynamic_route(route_id)

    if dynamic_route is not None:
        return build_pedestrian_forecast(
            dynamic_route.get("nearbySensors", []),
            route_id=route_id,
            horizon_hours=3,
            data_as_of=dynamic_route.get("pedestrianObservedAt"),
        )

    query = text("""
        SELECT
            rs."SensorID" AS sensor_id,
            sl."SensorDescription" AS sensor_name,
            sl."Lat" AS lat,
            sl."Lng" AS lng,
            latest."DateTimeMinute" AS observed_at
        FROM "RouteSensor" rs
        JOIN "SensorLocation" sl
            ON sl."SensorID" = rs."SensorID"
        LEFT JOIN LATERAL (
            SELECT pc."DateTimeMinute"
            FROM "PedestrianCount" pc
            WHERE pc."SensorID" = rs."SensorID"
            ORDER BY pc."DateTimeMinute" DESC
            LIMIT 1
        ) latest ON TRUE
        WHERE rs."RouteID" = :route_id
          AND sl."Status" = 'A'
          AND sl."Lat" IS NOT NULL
          AND sl."Lng" IS NOT NULL
        ORDER BY rs."SequenceOrder", rs."SensorID";
    """)

    with engine.connect() as conn:
        rows = conn.execute(
            query,
            {"route_id": route_id},
        ).mappings().all()

    if not rows:
        return None

    observed_values = [
        row["observed_at"]
        for row in rows
        if row["observed_at"] is not None
    ]
    data_as_of = max(observed_values).isoformat() if observed_values else None

    return build_pedestrian_forecast(
        [
            {
                "sensorId": row["sensor_id"],
                "name": row["sensor_name"],
                "lat": float(row["lat"]),
                "lng": float(row["lng"]),
            }
            for row in rows
        ],
        route_id=route_id,
        horizon_hours=3,
        data_as_of=data_as_of,
    )

def get_route_quiet_spaces(route_id):
    dynamic_route = get_dynamic_route(route_id)

    if dynamic_route is not None:
        route_points = decode_route(dynamic_route.get("polyline"))
    else:
        stored_route = get_route(route_id)

        if stored_route is None:
            return []

        # Stored (legacy) routes have no path geometry, only
        # origin/destination points. Match against the straight
        # line between them rather than fabricating a real path.
        route_points = [
            stored_route["origin"],
            stored_route["destination"],
        ]

    if not route_points:
        return []

    refuges = get_refuges()
    nearby = refuges_near_route(route_points, refuges)

    return [
        {
            "refugeId": refuge["refugeId"],
            "name": refuge["name"],
            "category": refuge["category"],
            "lat": refuge["lat"],
            "lng": refuge["lng"],
            "quietScore": refuge["quietScore"],
            "distanceFromRouteM": refuge["distanceFromRouteM"],
        }
        for refuge in nearby
    ]


def create_route(
    origin_lat,
    origin_lng,
    dest_lat,
    dest_lng,
    route_type,
    distance_m,
    est_duration_min,
):
    query = text("""
        INSERT INTO "Route"
        (
            "OriginLat",
            "OriginLng",
            "DestLat",
            "DestLng",
            "RouteType",
            "DistanceM",
            "EstDurationMin"
        )
        VALUES
        (
            :origin_lat,
            :origin_lng,
            :dest_lat,
            :dest_lng,
            :route_type,
            :distance_m,
            :est_duration_min
        )
        RETURNING
            "RouteID",
            "OriginLat",
            "OriginLng",
            "DestLat",
            "DestLng",
            "RouteType",
            "DistanceM",
            "EstDurationMin";
    """)

    with engine.begin() as conn:
        row = conn.execute(
            query,
            {
                "origin_lat": origin_lat,
                "origin_lng": origin_lng,
                "dest_lat": dest_lat,
                "dest_lng": dest_lng,
                "route_type": route_type,
                "distance_m": distance_m,
                "est_duration_min": est_duration_min,
            },
        ).mappings().first()

    return {
        "routeId": str(row["RouteID"]),
        "routeType": row["RouteType"],
        "distanceM": row["DistanceM"],
        "durationMin": row["EstDurationMin"],
        "origin": {
            "lat": float(row["OriginLat"]),
            "lng": float(row["OriginLng"]),
        },
        "destination": {
            "lat": float(row["DestLat"]),
            "lng": float(row["DestLng"]),
        },
    }

def save_route_sensors(route_id, sensors):
    """
    Replace the pedestrian sensor associations for a route.

    sensors should be a list like:
    [
        {"sensorId": 1, "sequenceOrder": 1},
        {"sensorId": 12, "sequenceOrder": 2}
    ]
    """

    route_query = text("""
        SELECT "RouteID"
        FROM "Route"
        WHERE "RouteID" = :route_id;
    """)

    sensor_exists_query = text("""
        SELECT "SensorID"
        FROM "SensorLocation"
        WHERE "SensorID" = :sensor_id;
    """)

    delete_query = text("""
        DELETE FROM "RouteSensor"
        WHERE "RouteID" = :route_id;
    """)

    insert_query = text("""
        INSERT INTO "RouteSensor"
        (
            "RouteID",
            "SensorID",
            "SequenceOrder"
        )
        VALUES
        (
            :route_id,
            :sensor_id,
            :sequence_order
        );
    """)

    with engine.begin() as conn:
        route = conn.execute(
            route_query,
            {"route_id": route_id},
        ).first()

        if route is None:
            return {
                "success": False,
                "error": "route_not_found",
            }

        validated_sensors = []

        for sensor in sensors:
            sensor_id = sensor["sensorId"]

            existing_sensor = conn.execute(
                sensor_exists_query,
                {"sensor_id": sensor_id},
            ).first()

            if existing_sensor is None:
                return {
                    "success": False,
                    "error": "sensor_not_found",
                    "sensorId": sensor_id,
                }

            validated_sensors.append(sensor)

        # Replace existing associations only after
        # every supplied sensor has been validated.
        conn.execute(
            delete_query,
            {"route_id": route_id},
        )

        for sensor in validated_sensors:
            conn.execute(
                insert_query,
                {
                    "route_id": route_id,
                    "sensor_id": sensor["sensorId"],
                    "sequence_order": sensor["sequenceOrder"],
                },
            )

    return {
        "success": True,
        "routeId": str(route_id),
        "sensorCount": len(validated_sensors),
        "sensors": validated_sensors,
    }
