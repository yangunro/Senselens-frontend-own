from sqlalchemy import text

from app.database import engine


DEMO_USER_EMAIL = "abdullah@example.com"


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


def save_route(route_id, label):
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
                "route_id": route_id,
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