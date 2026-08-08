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