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

def bulk_upsert_pedestrian_history(records):
    """
    Bulk UPSERT historical pedestrian records
    in one database transaction.

    Expected keys:
        SensorID
        SensingDate
        HourDay
        HourlyCount
    """

    if not records:
        return 0

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
        conn.execute(query, records)

    return len(records)


def upsert_streetlight(record):
    query = text("""
        INSERT INTO "StreetLight_LuxLevel"
        (
            "LightID",
            "Lat",
            "Lng",
            "LuxLabel"
        )
        VALUES
        (
            :LightID,
            :Lat,
            :Lng,
            :LuxLabel
        )

        ON CONFLICT ("LightID")

        DO UPDATE SET
            "Lat" = EXCLUDED."Lat",
            "Lng" = EXCLUDED."Lng",
            "LuxLabel" = EXCLUDED."LuxLabel";
    """)

    with engine.begin() as conn:
        conn.execute(query, record)


def bulk_upsert_streetlights(records):
    if not records:
        return 0

    query = text("""
        INSERT INTO "StreetLight_LuxLevel"
        (
            "LightID",
            "Lat",
            "Lng",
            "LuxLabel"
        )
        VALUES
        (
            :LightID,
            :Lat,
            :Lng,
            :LuxLabel
        )

        ON CONFLICT ("LightID")

        DO UPDATE SET
            "Lat" = EXCLUDED."Lat",
            "Lng" = EXCLUDED."Lng",
            "LuxLabel" = EXCLUDED."LuxLabel";
    """)

    with engine.begin() as conn:
        conn.execute(query, records)

    return len(records)


def get_all_routes():
    query = text("""
        SELECT
            "RouteID",
            "OriginLat",
            "OriginLng",
            "DestLat",
            "DestLng"
        FROM "Route";
    """)

    with engine.connect() as conn:
        rows = conn.execute(query).mappings().all()

    return [dict(row) for row in rows]


def bulk_insert_transit_signals(records):
    if not records:
        return 0

    query = text("""
        INSERT INTO "TransitCongestionSignal"
        (
            "RouteID",
            "VehicleMode",
            "CongestionLevel",
            "OccupancyStatus",
            "OccupancyPct",
            "ObservedAt"
        )
        VALUES
        (
            :RouteID,
            :VehicleMode,
            :CongestionLevel,
            :OccupancyStatus,
            :OccupancyPct,
            :ObservedAt
        );
    """)

    with engine.begin() as conn:
        conn.execute(query, records)

    return len(records)


def refresh_refuge_locations(source_dataset, records):
    """
    Replace all RefugeLocation rows previously loaded from
    source_dataset with the current set of records.

    RefugeLocation has no natural unique key to UPSERT on
    (RefugeID is a random UUID generated per row), so idempotent
    reloading is done by deleting the previous rows tagged with
    this SourceDataset and inserting the current ones, all inside
    one transaction.
    """

    delete_query = text("""
        DELETE FROM "RefugeLocation"
        WHERE "SourceDataset" = :source_dataset;
    """)

    insert_query = text("""
        INSERT INTO "RefugeLocation"
        (
            "Name",
            "Lat",
            "Lng",
            "Category",
            "SourceDataset"
        )
        VALUES
        (
            :Name,
            :Lat,
            :Lng,
            :Category,
            :SourceDataset
        );
    """)

    with engine.begin() as conn:

        conn.execute(
            delete_query,
            {"source_dataset": source_dataset},
        )

        if records:
            conn.execute(insert_query, records)

    return len(records)


def get_valid_sensor_ids():
    """
    Return the set of SensorIDs currently present
    in SensorLocation.

    Used to pre-filter historical records before
    a bulk UPSERT so that rows referencing retired/
    unknown sensors never trigger a foreign-key
    violation on the whole batch.
    """

    query = text("""
        SELECT "SensorID"
        FROM "SensorLocation";
    """)

    with engine.connect() as conn:
        result = conn.execute(query).scalars().all()

    return set(result)


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