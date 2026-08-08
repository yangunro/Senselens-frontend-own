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