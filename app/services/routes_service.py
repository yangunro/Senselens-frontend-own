from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app.database import engine
from app.services.dynamic_route_store import (
    get_dynamic_route,
    save_dynamic_routes,
)
from app.services.google_routes_service import get_google_routes
from app.services.pedestrian_service import (
    get_latest_pedestrian_snapshot,
)
from app.services.refuges_service import get_refuges
from app.services.route_analysis_service import (
    analyse_route,
    decode_route,
    refuges_near_route,
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
        routes = [
            analyse_route(route, pedestrian_snapshot)
            for route in routes
        ]
        routes.sort(
            key=lambda route: (
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
                "footnote": route["footnote"],
                "recommended": route["recommended"],
                "sensoryScore": route["sensoryScore"],
                "matchedSensorCount": route["matchedSensorCount"],
                "pedestrianObservedAt": route["pedestrianObservedAt"],
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
            "distance": dynamic_route["distance"],
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

def _forecast_from_history(dynamic_route):
    """
    Estimate whether the upcoming hour will be busier or quieter
    than usual for this route's nearby sensors, using real
    historical hourly counts (same hour-of-day, same day-of-week)
    from PedestrianHourlyHistory.

    This is a historical-pattern heuristic, not a machine-learning
    prediction. It compares each nearby sensor's typical count for
    the upcoming hour+weekday against that same sensor's own
    overall average, so it is calibrated per-location rather than
    against an unrelated scale.
    """

    nearby_sensors = dynamic_route.get("nearbySensors") or []

    if not nearby_sensors:
        return None

    sensor_ids = [sensor["sensorId"] for sensor in nearby_sensors]

    now = datetime.now(timezone.utc)
    target_time = now + timedelta(hours=1)
    target_hour = target_time.hour
    # Postgres EXTRACT(DOW): Sunday=0 .. Saturday=6.
    target_dow = target_time.isoweekday() % 7

    query = text("""
        SELECT
            "SensorID" AS sensor_id,
            AVG("HourlyCount") FILTER (
                WHERE "HourDay" = :target_hour
                  AND EXTRACT(DOW FROM "SensingDate") = :target_dow
            ) AS upcoming_hour_avg,
            AVG("HourlyCount") AS overall_avg
        FROM "PedestrianHourlyHistory"
        WHERE "SensorID" = ANY(:sensor_ids)
        GROUP BY "SensorID";
    """)

    with engine.connect() as conn:
        rows = conn.execute(
            query,
            {
                "sensor_ids": sensor_ids,
                "target_hour": target_hour,
                "target_dow": target_dow,
            },
        ).mappings().all()

    history_by_sensor = {row["sensor_id"]: row for row in rows}

    weighted_ratio_total = 0.0
    total_weight = 0.0
    matched_sensor_count = 0

    for sensor in nearby_sensors:
        history = history_by_sensor.get(sensor["sensorId"])

        if (
            history is None
            or history["upcoming_hour_avg"] is None
            or not history["overall_avg"]
        ):
            continue

        ratio = (
            float(history["upcoming_hour_avg"])
            / float(history["overall_avg"])
        )

        distance = sensor["distanceFromRouteM"]
        weight = 1 / (1 + distance / 50)

        weighted_ratio_total += ratio * weight
        total_weight += weight
        matched_sensor_count += 1

    if matched_sensor_count == 0 or total_weight == 0:
        return None

    forecast_ratio = weighted_ratio_total / total_weight

    if forecast_ratio < 0.85:
        level, level_label = "low", "LOW SENSORY"
    elif forecast_ratio < 1.25:
        level, level_label = "medium", "MEDIUM SENSORY"
    else:
        level, level_label = "high", "HIGH SENSORY"

    return {
        "routeId": str(dynamic_route["id"]),
        "sensoryIndicator": level_label,
        "level": level,
        "forecastRatio": round(forecast_ratio, 2),
        "matchedSensorCount": matched_sensor_count,
        "forecastFor": target_time.isoformat(),
        "basis": (
            f"Historical pedestrian counts for "
            f"{matched_sensor_count} nearby sensor(s) at this "
            "hour and day of week, compared to each sensor's own "
            "typical hourly average."
        ),
        "computedAt": now.isoformat(),
    }


def get_route_forecast(route_id):
    dynamic_route = get_dynamic_route(route_id)

    if dynamic_route is not None:
        return _forecast_from_history(dynamic_route)

    query = text("""
        SELECT
            "SensoryIndicator",
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
        row = conn.execute(
            query,
            {"route_id": route_id},
        ).mappings().first()

    if row is None:
        return None

    return {
        "routeId": str(route_id),
        "sensoryIndicator": row["SensoryIndicator"],
        "pedestrianDensityScore": (
            float(row["PedestrianDensityScore"])
            if row["PedestrianDensityScore"] is not None
            else None
        ),
        "constructionExposureScore": (
            float(row["ConstructionExposureScore"])
            if row["ConstructionExposureScore"] is not None
            else None
        ),
        "lightingComfortScore": (
            float(row["LightingComfortScore"])
            if row["LightingComfortScore"] is not None
            else None
        ),
        "computedAt": (
            row["ComputedAt"].isoformat()
            if row["ComputedAt"] is not None
            else None
        ),
    }

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
