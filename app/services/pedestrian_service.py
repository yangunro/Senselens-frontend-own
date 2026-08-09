from sqlalchemy import text

from app.database import engine


LOW_AVERAGE_THRESHOLD = 10
HIGH_AVERAGE_THRESHOLD = 25


def get_latest_pedestrian_snapshot():
    """Return readings from the latest available minute in the database."""
    query = text("""
        WITH latest AS (
            SELECT MAX("DateTimeMinute") AS observed_at
            FROM "PedestrianCount"
        )
        SELECT
            pc."SensorID" AS sensor_id,
            pc."MinuteCount" AS minute_count,
            pc."DateTimeMinute" AS observed_at,
            sl."SensorDescription" AS sensor_name,
            sl."Lat" AS lat,
            sl."Lng" AS lng
        FROM "PedestrianCount" pc
        JOIN "SensorLocation" sl
            ON sl."SensorID" = pc."SensorID"
        CROSS JOIN latest
        WHERE pc."DateTimeMinute" = latest.observed_at
          AND sl."Status" = 'A'
        ORDER BY pc."MinuteCount" DESC;
    """)

    with engine.connect() as conn:
        rows = conn.execute(query).mappings().all()

    if not rows:
        return None

    counts = [int(row["minute_count"]) for row in rows]
    observed_at = rows[0]["observed_at"]

    return {
        "observedAt": observed_at.isoformat(),
        "sensorCount": len(rows),
        "totalCount": sum(counts),
        "averageCount": round(sum(counts) / len(counts), 2),
        "maximumCount": max(counts),
        "sensors": [
            {
                "sensorId": row["sensor_id"],
                "name": row["sensor_name"],
                "minuteCount": int(row["minute_count"]),
                "lat": float(row["lat"]),
                "lng": float(row["lng"]),
            }
            for row in rows
        ],
    }


def classify_cbd_status(snapshot):
    average_count = snapshot["averageCount"]

    if average_count < LOW_AVERAGE_THRESHOLD:
        return {
            "level": "low",
            "label": "CBD is RELATIVELY CALM now",
            "note": "Most reporting pedestrian sensors are showing lower activity.",
        }

    if average_count < HIGH_AVERAGE_THRESHOLD:
        return {
            "level": "moderate",
            "label": "CBD is MODERATELY BUSY now",
            "note": "Some areas are busy, so a calmer route may be more comfortable.",
        }

    return {
        "level": "high",
        "label": "CBD is VERY BUSY now",
        "note": "Pedestrian activity is elevated across reporting sensors.",
    }


def get_current_cbd_status():
    snapshot = get_latest_pedestrian_snapshot()

    if snapshot is None:
        return None

    return {
        **classify_cbd_status(snapshot),
        "observedAt": snapshot["observedAt"],
        "sensorCount": snapshot["sensorCount"],
        "averageCount": snapshot["averageCount"],
    }
