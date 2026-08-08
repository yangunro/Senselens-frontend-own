from sqlalchemy import text
from app.database import engine


def upsert_sensor(sensor):
    query = text("""
        INSERT INTO "SensorLocation"
        (
            "SensorID",
            "SensorDescription",
            "Lat",
            "Lng",
            "Status",
            "InstallationDate"
        )
        VALUES
        (
            :SensorID,
            :SensorDescription,
            :Lat,
            :Lng,
            :Status,
            :InstallationDate
        )
        ON CONFLICT ("SensorID")
        DO UPDATE SET
            "SensorDescription" = EXCLUDED."SensorDescription",
            "Lat" = EXCLUDED."Lat",
            "Lng" = EXCLUDED."Lng",
            "Status" = EXCLUDED."Status",
            "InstallationDate" = EXCLUDED."InstallationDate";
    """)

    with engine.begin() as conn:
        conn.execute(query, sensor)

def upsert_pedestrian_count(record):
    query = text("""
        INSERT INTO "PedestrianCount"
        (
            "SensorID",
            "DateTimeMinute",
            "MinuteCount"
        )

        VALUES
        (
            :SensorID,
            :DateTimeMinute,
            :MinuteCount
        )

        ON CONFLICT ("SensorID","DateTimeMinute")

        DO UPDATE SET

            "MinuteCount" = EXCLUDED."MinuteCount";
    """)

    with engine.begin() as conn:
        conn.execute(query, record)