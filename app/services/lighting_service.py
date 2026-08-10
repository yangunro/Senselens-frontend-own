from sqlalchemy import text

from app.database import engine


# Degrees of lat/lng padding around a route's bounding box, roughly 300m at
# Melbourne's latitude — wide enough to catch every light within matching
# distance of the route, tight enough to keep the candidate set small.
# There are 12k+ streetlights citywide; filtering to the route's bounding
# box in SQL first (instead of distance-checking all of them in Python)
# keeps this fast.
BOUNDING_BOX_PADDING_DEGREES = 0.003


def get_lights_in_bounds(min_lat, max_lat, min_lng, max_lng):
    query = text("""
        SELECT
            "LightID",
            "Lat",
            "Lng",
            "LuxLabel"
        FROM "StreetLight_LuxLevel"
        WHERE "Lat" BETWEEN :min_lat AND :max_lat
          AND "Lng" BETWEEN :min_lng AND :max_lng
          AND "LuxLabel" IS NOT NULL;
    """)

    with engine.connect() as conn:
        rows = conn.execute(
            query,
            {
                "min_lat": min_lat - BOUNDING_BOX_PADDING_DEGREES,
                "max_lat": max_lat + BOUNDING_BOX_PADDING_DEGREES,
                "min_lng": min_lng - BOUNDING_BOX_PADDING_DEGREES,
                "max_lng": max_lng + BOUNDING_BOX_PADDING_DEGREES,
            },
        ).mappings().all()

    lights = []
    for row in rows:
        try:
            lux = float(row["LuxLabel"])
        except (TypeError, ValueError):
            continue

        lights.append({
            "lightId": row["LightID"],
            "lat": float(row["Lat"]),
            "lng": float(row["Lng"]),
            "lux": lux,
        })

    return lights
