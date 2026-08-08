from sqlalchemy import text

from app.database import engine


def get_cbd_status():
    query = text("""
        SELECT AVG("MinuteCount") AS average_count
        FROM "PedestrianCount"
        WHERE "DateTimeMinute" >= NOW() - INTERVAL '15 minutes';
    """)

    with engine.connect() as conn:
        average_count = conn.execute(query).scalar()

    if average_count is None:
        return {
            "level": "unknown",
            "label": "CBD activity unavailable",
            "note": "No recent pedestrian data is available."
        }

    if average_count < 20:
        level = "low"
        label = "CBD is QUIET now"
        note = "Pedestrian activity is currently low."

    elif average_count < 50:
        level = "moderate"
        label = "CBD is MODERATELY BUSY now"
        note = "Pedestrian activity is moderate."

    else:
        level = "high"
        label = "CBD is BUSY now"
        note = "Pedestrian activity is currently high."

    return {
        "level": level,
        "label": label,
        "note": note
    }