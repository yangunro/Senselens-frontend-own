import argparse
import csv
import time
from datetime import date, datetime, timedelta
from pathlib import Path

from sqlalchemy.exc import IntegrityError

from etl.client import fetch_dataset
from etl.repository import (
    bulk_upsert_pedestrian_history,
    get_checkpoint,
    get_valid_sensor_ids,
    update_checkpoint,
    upsert_pedestrian_history,
)


DATASET = "pedestrian-counting-system-monthly-counts-per-hour"
CHECKPOINT_NAME = "PedestrianHourlyHistory"

FULL_START_DATE = date(2025, 1, 1)

# Conservative recurring API page size.
API_PAGE_SIZE = 20

# Number of records written to Supabase
# in one database transaction during bootstrap.
CSV_BATCH_SIZE = 1000


# ============================================================
# Helpers
# ============================================================

def normalise_date(value):
    """
    Convert supported date values to datetime.date.
    """

    if value is None:
        return None

    if isinstance(value, date) and not isinstance(value, datetime):
        return value

    if isinstance(value, datetime):
        return value.date()

    text_value = str(value).strip()

    if not text_value:
        return None

    try:
        return datetime.fromisoformat(
            text_value.replace("Z", "+00:00")
        ).date()

    except ValueError:
        pass

    try:
        return datetime.strptime(
            text_value,
            "%Y-%m-%d",
        ).date()

    except ValueError:
        return None


def valid_record(record):
    """
    Ensure all required fields are present.
    """

    return (
        record is not None
        and record["SensorID"] is not None
        and record["SensingDate"] is not None
        and record["HourDay"] is not None
        and record["HourlyCount"] is not None
    )


def prepare_record(
    sensor_id,
    sensing_date,
    hour_day,
    hourly_count,
):
    """
    Clean and standardise one historical pedestrian record.
    """

    try:
        sensor_id = int(sensor_id)
        hour_day = int(hour_day)
        hourly_count = int(hourly_count)

    except (TypeError, ValueError):
        return None

    sensing_date = normalise_date(
        sensing_date
    )

    if sensing_date is None:
        return None

    if sensor_id <= 0:
        return None

    if not 0 <= hour_day <= 23:
        return None

    if hourly_count < 0:
        return None

    return {
        "SensorID": sensor_id,
        "SensingDate": sensing_date,
        "HourDay": hour_day,
        "HourlyCount": hourly_count,
    }


def load_record(record):
    """
    UPSERT one record.

    Used mainly as a fallback when a batch contains
    a retired SensorID that violates the current
    SensorLocation foreign-key relationship.
    """

    if not valid_record(record):
        return "skipped"

    try:
        upsert_pedestrian_history(
            record
        )

        return "success"

    except IntegrityError as error:
        print(
            f"Skipped historical record for "
            f"SensorID={record['SensorID']} "
            f"date={record['SensingDate']} "
            f"hour={record['HourDay']}"
        )

        print(
            "Database integrity issue:",
            error.orig,
        )

        return "skipped"


def load_batch(records):
    """
    Bulk UPSERT a group of historical records.

    If the entire batch fails because one or more
    historical sensors violate a foreign-key constraint,
    fall back to individual inserts so valid records
    are still retained.

    Returns:
        loaded_count
        skipped_count
    """

    if not records:
        return 0, 0

    try:
        loaded = (
            bulk_upsert_pedestrian_history(
                records
            )
        )

        return loaded, 0

    except IntegrityError as error:
        print()
        print(
            "Bulk batch hit a database integrity issue."
        )

        print(
            "Falling back to row-by-row loading "
            "for this batch."
        )

        print(
            "Database integrity issue:",
            error.orig,
        )

        loaded = 0
        skipped = 0

        for record in records:
            result = load_record(
                record
            )

            if result == "success":
                loaded += 1

            else:
                skipped += 1

        return loaded, skipped


# ============================================================
# One-Time CSV Bootstrap
# ============================================================

def bootstrap_from_csv(
    csv_path,
    full_load=False,
):
    """
    One-time catch-up using a City of Melbourne
    whole-dataset CSV export.

    The downloaded CSV is ordered newest -> oldest.

    Therefore the checkpoint is NOT updated while
    processing the file.

    It is updated once, only after the entire CSV
    finishes successfully.
    """

    path = Path(
        csv_path
    )

    if not path.exists():
        raise FileNotFoundError(
            f"CSV file not found: {path}"
        )

    checkpoint = get_checkpoint(
        CHECKPOINT_NAME
    )

    if full_load:
        start_day = FULL_START_DATE

    elif checkpoint is None:
        start_day = FULL_START_DATE

    else:
        start_day = (
            checkpoint
            + timedelta(days=1)
        )

    # Cache the current set of valid SensorIDs once so
    # rows referencing retired/unknown sensors can be
    # filtered out before they ever reach a bulk batch.
    # This keeps batches clean and avoids the slow
    # row-by-row fallback in load_batch().
    valid_sensor_ids = get_valid_sensor_ids()

    print()
    print(
        "====================================="
    )

    print(
        "Historical Pedestrian CSV Bootstrap"
    )

    print(
        "====================================="
    )

    print(
        f"CSV file   : {path}"
    )

    print(
        f"Start date : {start_day}"
    )

    print(
        f"Batch size : {CSV_BATCH_SIZE}"
    )

    print(
        f"Known sensors : {len(valid_sensor_ids)}"
    )

    print()

    total_seen = 0
    total_eligible = 0
    total_loaded = 0
    total_skipped = 0
    total_unknown_sensor = 0

    unknown_sensor_counts = {}

    newest_loaded_date = None
    oldest_loaded_date = None

    batch = []

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as csv_file:

        reader = csv.DictReader(
            csv_file
        )

        required_columns = {
            "Location_ID",
            "Sensing_Date",
            "HourDay",
            "Total_of_Directions",
        }

        actual_columns = set(
            reader.fieldnames or []
        )

        missing_columns = (
            required_columns
            - actual_columns
        )

        if missing_columns:
            raise RuntimeError(
                "CSV is missing required columns: "
                + ", ".join(
                    sorted(
                        missing_columns
                    )
                )
            )

        for row in reader:

            total_seen += 1

            sensing_date = (
                normalise_date(
                    row.get(
                        "Sensing_Date"
                    )
                )
            )

            if sensing_date is None:
                total_skipped += 1
                continue

            # Skip records already covered
            # by the checkpoint.
            if sensing_date < start_day:
                continue

            total_eligible += 1

            transformed = (
                prepare_record(
                    sensor_id=row.get(
                        "Location_ID"
                    ),
                    sensing_date=row.get(
                        "Sensing_Date"
                    ),
                    hour_day=row.get(
                        "HourDay"
                    ),
                    hourly_count=row.get(
                        "Total_of_Directions"
                    ),
                )
            )

            if transformed is None:
                total_skipped += 1
                continue

            if transformed["SensorID"] not in valid_sensor_ids:
                total_skipped += 1
                total_unknown_sensor += 1

                unknown_sensor_counts[
                    transformed["SensorID"]
                ] = (
                    unknown_sensor_counts.get(
                        transformed["SensorID"], 0
                    )
                    + 1
                )

                continue

            batch.append(
                transformed
            )

            if (
                newest_loaded_date is None
                or sensing_date
                > newest_loaded_date
            ):
                newest_loaded_date = (
                    sensing_date
                )

            if (
                oldest_loaded_date is None
                or sensing_date
                < oldest_loaded_date
            ):
                oldest_loaded_date = (
                    sensing_date
                )

            # --------------------------------------------
            # Bulk database write
            # --------------------------------------------

            if len(batch) >= CSV_BATCH_SIZE:

                loaded, skipped = (
                    load_batch(
                        batch
                    )
                )

                total_loaded += loaded
                total_skipped += skipped

                batch.clear()

            # --------------------------------------------
            # Progress
            # --------------------------------------------

            if total_seen % 10000 == 0:
                print(
                    f"Processed "
                    f"{total_seen:,} CSV rows "
                    f"| eligible="
                    f"{total_eligible:,} "
                    f"| loaded="
                    f"{total_loaded:,} "
                    f"| skipped="
                    f"{total_skipped:,}"
                )

        # ====================================================
        # Final incomplete batch
        # ====================================================

        if batch:

            loaded, skipped = (
                load_batch(
                    batch
                )
            )

            total_loaded += loaded
            total_skipped += skipped

            batch.clear()

    # ========================================================
    # Checkpoint
    # ========================================================

    # Only advance after the ENTIRE file
    # has finished successfully.

    if newest_loaded_date is not None:

        update_checkpoint(
            CHECKPOINT_NAME,
            newest_loaded_date,
        )

        print()
        print(
            f"Checkpoint updated → "
            f"{newest_loaded_date}"
        )

    else:
        print()
        print(
            "No new historical records "
            "were loaded."
        )

    # ========================================================
    # Summary
    # ========================================================

    print()
    print(
        "====================================="
    )

    print(
        "CSV Bootstrap Completed"
    )

    print(
        "====================================="
    )

    print(
        f"Rows inspected : "
        f"{total_seen:,}"
    )

    print(
        f"Eligible rows  : "
        f"{total_eligible:,}"
    )

    print(
        f"Loaded/updated : "
        f"{total_loaded:,}"
    )

    print(
        f"Skipped        : "
        f"{total_skipped:,}"
    )

    print(
        f"  of which unknown/retired sensor : "
        f"{total_unknown_sensor:,}"
    )

    print(
        f"Oldest loaded  : "
        f"{oldest_loaded_date}"
    )

    print(
        f"Newest loaded  : "
        f"{newest_loaded_date}"
    )

    print(
        "====================================="
    )

    if unknown_sensor_counts:
        print()
        print(
            "Skipped unknown/retired SensorIDs:"
        )

        for sensor_id, count in sorted(
            unknown_sensor_counts.items()
        ):
            print(
                f"  SensorID {sensor_id}: "
                f"{count:,} rows"
            )


# ============================================================
# Recurring Historical API Extraction
# ============================================================

def fetch_day(day):
    """
    Fetch one missing historical day from
    City of Melbourne.

    This is for normal recurring updates,
    not the one-time bootstrap.
    """

    next_day = (
        day
        + timedelta(days=1)
    )

    where = (
        f"sensing_date >= "
        f"date'{day.isoformat()}' "
        f"AND sensing_date < "
        f"date'{next_day.isoformat()}'"
    )

    records = []

    offset = 0

    while True:

        data = fetch_dataset(
            DATASET,
            limit=API_PAGE_SIZE,
            offset=offset,
            order_by=(
                "sensing_date, "
                "location_id, "
                "hourday"
            ),
            where=where,
        )

        results = data.get(
            "results",
            [],
        )

        if not results:
            break

        records.extend(
            results
        )

        if len(results) < API_PAGE_SIZE:
            break

        offset += API_PAGE_SIZE

        if offset >= 9900:
            raise RuntimeError(
                f"More than 9,900 records "
                f"found for {day}. "
                "Daily API chunking is no "
                "longer appropriate."
            )

    return records


def transform_api_record(record):
    """
    Convert API fields into database fields.
    """

    return prepare_record(
        sensor_id=record.get(
            "location_id"
        ),
        sensing_date=record.get(
            "sensing_date"
        ),
        hour_day=record.get(
            "hourday"
        ),
        hourly_count=record.get(
            "pedestriancount"
        ),
    )


def process_day(day, valid_sensor_ids):
    """
    Fetch and load one complete missing day.
    """

    records = fetch_day(
        day
    )

    print(
        f"Fetched: {len(records)}"
    )

    transformed_records = []

    skipped = 0

    for raw_record in records:

        transformed = (
            transform_api_record(
                raw_record
            )
        )

        if transformed is None:
            skipped += 1
            continue

        if transformed["SensorID"] not in valid_sensor_ids:
            skipped += 1
            continue

        transformed_records.append(
            transformed
        )

    loaded = 0

    # Also bulk-load incremental API data
    # into Supabase.

    for start in range(
        0,
        len(transformed_records),
        CSV_BATCH_SIZE,
    ):

        batch = transformed_records[
            start:
            start + CSV_BATCH_SIZE
        ]

        batch_loaded, batch_skipped = (
            load_batch(
                batch
            )
        )

        loaded += batch_loaded
        skipped += batch_skipped

    return (
        loaded,
        skipped,
    )


# ============================================================
# Daily Incremental Sync
# ============================================================

def run_incremental_sync():
    """
    Normal production mode.

    Starts from checkpoint + 1 and retrieves
    only missing historical dates.
    """

    checkpoint = get_checkpoint(
        CHECKPOINT_NAME
    )

    if checkpoint is None:
        start_day = FULL_START_DATE

    else:
        start_day = (
            checkpoint
            + timedelta(days=1)
        )

    end_day = date.today()

    valid_sensor_ids = get_valid_sensor_ids()

    print()
    print(
        "====================================="
    )

    print(
        "Historical Pedestrian Incremental ETL"
    )

    print(
        "====================================="
    )

    print(
        f"Start date : {start_day}"
    )

    print(
        f"End date   : {end_day}"
    )

    print()

    if start_day > end_day:

        print(
            "Historical pedestrian data "
            "is already up to date."
        )

        return

    current_day = start_day

    total_success = 0
    total_skipped = 0
    completed_days = 0

    while current_day <= end_day:

        print()
        print(
            "-------------------------------------"
        )

        print(
            f"Processing {current_day}"
        )

        print(
            "-------------------------------------"
        )

        try:

            success, skipped = (
                process_day(
                    current_day,
                    valid_sensor_ids,
                )
            )

        except Exception as error:

            print()
            print(
                "ETL STOPPED"
            )

            print(
                f"Failed date: "
                f"{current_day}"
            )

            print(
                f"Reason: {error}"
            )

            print()

            print(
                "The checkpoint was NOT "
                "advanced."
            )

            print(
                "The next run will retry "
                "this same date."
            )

            break

        print(
            f"Inserted/updated: "
            f"{success}"
        )

        print(
            f"Skipped:          "
            f"{skipped}"
        )

        total_success += success
        total_skipped += skipped

        update_checkpoint(
            CHECKPOINT_NAME,
            current_day,
        )

        print(
            f"Checkpoint updated → "
            f"{current_day}"
        )

        completed_days += 1

        current_day += timedelta(
            days=1
        )

        # fetch_dataset already performs
        # rate-safe request pacing.
        time.sleep(2)

    print()
    print(
        "====================================="
    )

    print(
        "Historical Incremental ETL Summary"
    )

    print(
        "====================================="
    )

    print(
        f"Days completed:   "
        f"{completed_days}"
    )

    print(
        f"Inserted/updated: "
        f"{total_success}"
    )

    print(
        f"Skipped records:  "
        f"{total_skipped}"
    )

    print(
        "====================================="
    )


# ============================================================
# CLI
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Synchronise historical "
            "pedestrian hourly counts."
        )
    )

    parser.add_argument(
        "--bootstrap-csv",
        type=str,
        metavar="CSV_FILE",
        help=(
            "One-time catch-up/rebuild "
            "using a downloaded City of "
            "Melbourne whole-dataset CSV."
        ),
    )

    parser.add_argument(
        "--full",
        action="store_true",
        help=(
            "When used with --bootstrap-csv, "
            "reload from FULL_START_DATE "
            "rather than checkpoint + 1."
        ),
    )

    args = parser.parse_args()

    if args.bootstrap_csv:

        bootstrap_from_csv(
            csv_path=(
                args.bootstrap_csv
            ),
            full_load=args.full,
        )

    else:

        run_incremental_sync()


if __name__ == "__main__":
    main()