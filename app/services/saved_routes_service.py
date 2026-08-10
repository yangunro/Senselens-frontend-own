from sqlalchemy import text

from app.database import engine
from app.services.routes_service import create_route


DEMO_USER_EMAIL = "abdullah@example.com"

# Live routes are generated on the fly (Mapbox Directions API) and only ever
# live in an in-memory cache — they're never rows in "Route", so there was
# never a real RouteID to attach a SavedRoute to via the FK. "level" (the
# route's own low/medium/high crowd rating) is the closest thing to a route
# type available on a dynamic route; RouteType is a fixed 3-value Postgres
# enum, so it's mapped onto that rather than left to fail the insert.
LEVEL_TO_ROUTE_TYPE = {
    "low": "Low",
    "medium": "Balanced",
    "high": "Fast",
    "unknown": "Balanced",
}


def get_saved_routes():
    query = text("""
        SELECT
            sr."SavedRouteID",
            sr."Label",
            sr."SavedAt",

            r."RouteID",
            r."OriginLat",
            r."OriginLng",
            r."DestLat",
            r."DestLng",
            r."RouteType",
            r."DistanceM",
            r."EstDurationMin"

        FROM "SavedRoute" sr

        JOIN "User" u
            ON u."UserID" = sr."UserID"

        JOIN "Route" r
            ON r."RouteID" = sr."RouteID"

        WHERE u."Email" = :email

        ORDER BY sr."SavedAt" DESC;
    """)

    with engine.connect() as conn:
        rows = conn.execute(
            query,
            {"email": DEMO_USER_EMAIL},
        ).mappings().all()

    return [
        {
            "savedRouteId": str(row["SavedRouteID"]),
            "routeId": str(row["RouteID"]),
            "label": row["Label"],
            "savedAt": (
                row["SavedAt"].isoformat()
                if row["SavedAt"] is not None
                else None
            ),
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
        for row in rows
    ]


def save_route(label, origin, destination, level, distance_m, duration_min):
    # Persist a real Route row first — dynamic routes only exist in memory,
    # so there's nothing yet for SavedRoute's FK to point at.
    persisted_route = create_route(
        origin_lat=origin["lat"],
        origin_lng=origin["lng"],
        dest_lat=destination["lat"],
        dest_lng=destination["lng"],
        route_type=LEVEL_TO_ROUTE_TYPE.get(level, "Balanced"),
        distance_m=distance_m,
        est_duration_min=duration_min,
    )

    query = text("""
        INSERT INTO "SavedRoute"
        (
            "UserID",
            "RouteID",
            "Label",
            "SavedAt"
        )

        SELECT
            u."UserID",
            :route_id,
            :label,
            NOW()

        FROM "User" u

        WHERE u."Email" = :email

        RETURNING
            "SavedRouteID",
            "RouteID",
            "Label",
            "SavedAt";
    """)

    with engine.begin() as conn:
        row = conn.execute(
            query,
            {
                "route_id": persisted_route["routeId"],
                "label": label,
                "email": DEMO_USER_EMAIL,
            },
        ).mappings().first()

    if row is None:
        return None

    return {
        "savedRouteId": str(row["SavedRouteID"]),
        "routeId": str(row["RouteID"]),
        "label": row["Label"],
        "savedAt": (
            row["SavedAt"].isoformat()
            if row["SavedAt"] is not None
            else None
        ),
        "distanceM": persisted_route["distanceM"],
        "durationMin": persisted_route["durationMin"],
        "origin": persisted_route["origin"],
        "destination": persisted_route["destination"],
    }

def delete_saved_route(saved_route_id):
    query = text("""
        DELETE FROM "SavedRoute"
        WHERE "SavedRouteID" = :saved_route_id
        RETURNING
            "SavedRouteID",
            "RouteID",
            "Label";
    """)

    with engine.begin() as conn:
        row = conn.execute(
            query,
            {
                "saved_route_id": saved_route_id,
            },
        ).mappings().first()

    if row is None:
        return None

    return {
        "savedRouteId": str(row["SavedRouteID"]),
        "routeId": str(row["RouteID"]),
        "label": row["Label"],
    }