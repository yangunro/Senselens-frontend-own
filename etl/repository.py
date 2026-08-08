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

        ON CONFLICT ("SensorID", "DateTimeMinute")

        DO UPDATE SET
            "MinuteCount" = EXCLUDED."MinuteCount";
    """)

    with engine.begin() as conn:
        conn.execute(query, record)


def upsert_development(record):
    query = text("""
        INSERT INTO "DevelopmentSite_Status"
        (
            "PropertyID",
            "CLUE_SmallArea",
            "Status",
            "DevelopmentType",
            "Lat",
            "Lng"
        )
        VALUES
        (
            :PropertyID,
            :CLUE_SmallArea,
            :Status,
            :DevelopmentType,
            :Lat,
            :Lng
        )

        ON CONFLICT ("PropertyID")

        DO UPDATE SET
            "CLUE_SmallArea" = EXCLUDED."CLUE_SmallArea",
            "Status" = EXCLUDED."Status",
            "DevelopmentType" = EXCLUDED."DevelopmentType",
            "Lat" = EXCLUDED."Lat",
            "Lng" = EXCLUDED."Lng";
    """)

    with engine.begin() as conn:
        conn.execute(query, record)


def upsert_pedestrian_history(record):
    query = text("""
        INSERT INTO "PedestrianHourlyHistory"
        (
            "SensorID",
            "SensingDate",
            "HourDay",
            "HourlyCount"
        )
        VALUES
        (
            :SensorID,
            :SensingDate,
            :HourDay,
            :HourlyCount
        )

        ON CONFLICT ("SensorID", "SensingDate", "HourDay")

        DO UPDATE SET
            "HourlyCount" = EXCLUDED."HourlyCount";
    """)

    with engine.begin() as conn:
        conn.execute(query, record)


def get_latest_history_date():
    query = text("""
        SELECT MAX("SensingDate")
        FROM "PedestrianHourlyHistory";
    """)

    with engine.connect() as conn:
        result = conn.execute(query).scalar()

    return result


def get_checkpoint(dataset):
    query = text("""
        SELECT "LastSuccessfulDate"
        FROM "ETLCheckpoint"
        WHERE "Dataset" = :dataset;
    """)

    with engine.connect() as conn:
        result = conn.execute(
            query,
            {
                "dataset": dataset
            }
        ).scalar()

    return result


def update_checkpoint(dataset, day):
    query = text("""
        INSERT INTO "ETLCheckpoint"
        (
            "Dataset",
            "LastSuccessfulDate"
        )
        VALUES
        (
            :dataset,
            :day
        )

        ON CONFLICT ("Dataset")

        DO UPDATE SET
            "LastSuccessfulDate" = EXCLUDED."LastSuccessfulDate",
            "UpdatedAt" = NOW();
    """)

    with engine.begin() as conn:
        conn.execute(
            query,
            {
                "dataset": dataset,
                "day": day
            }
        )