from sqlalchemy import text

from app.database import engine


def get_routes(destination=None):
    """
    Returns all routes currently stored in the database.

    The destination parameter is accepted for future compatibility
    but is not used yet because routes are not generated dynamically.
    """

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
    # Refuge locations are not yet spatially matched to routes.
    # Return an empty list rather than fabricating route/refuge matches.
    return []

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