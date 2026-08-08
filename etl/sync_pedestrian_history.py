import argparse
import time
from datetime import date, timedelta

from sqlalchemy.exc import IntegrityError

from etl.client import fetch_dataset
from etl.repository import (
    get_checkpoint,
    update_checkpoint,
    upsert_pedestrian_history,
)


DATASET = "pedestrian-counting-system-monthly-counts-per-hour"
CHECKPOINT_NAME = "PedestrianHourlyHistory"

# Used only when:
#   python -m etl.sync_pedestrian_history --full
FULL_START_DATE = date(2025, 1, 1)


def fetch_day(day):
    """
    Fetch all historical pedestrian records for one day.

    We deliberately fetch one day at a time so each query stays
    comfortably below the City of Melbourne API's pagination limit.
    """

    next_day = day + timedelta(days=1)

    where = (
        f"sensing_date >= date'{day.isoformat()}' "
        f"AND sensing_date < date'{next_day.isoformat()}'"
    )

    records = []

    limit = 100
    offset = 0

    while True:
        data = fetch_dataset(
            DATASET,
            limit=limit,
            offset=offset,
            order_by="sensing_date, location_id, hourday",
            where=where,
        )

        results = data.get("results", [])

        if not results:
            break

        records.extend(results)

        # Last page
        if len(results) < limit:
            break

        offset += limit

        # Safety guard
        if offset >= 9900:
            raise RuntimeError(
                f"More than 9,900 records found for {day}. "
                "Day-level chunking is no longer small enough."
            )

    return records


def transform_record(record):
    """
    Convert City of Melbourne field names into our database fields.
    """

    return {
        "SensorID": record.get("location_id"),
        "SensingDate": record.get("sensing_date"),
        "HourDay": record.get("hourday"),
        "HourlyCount": record.get("pedestriancount"),
    }


def get_start_day(full_load):
    """
    Work out where the ETL should begin.

    Normal run:
        checkpoint + 1 day

    --full run:
        FULL_START_DATE
    """

    if full_load:
        return FULL_START_DATE

    checkpoint = get_checkpoint(CHECKPOINT_NAME)

    if checkpoint is None:
        return FULL_START_DATE

    return checkpoint + timedelta(days=1)


def valid_record(record):
    """
    Check whether all required fields are present.
    """

    return (
        record["SensorID"] is not None
        and record["SensingDate"] is not None
        and record["HourDay"] is not None
        and record["HourlyCount"] is not None
    )


def process_day(day):
    """
    Fetch and process one complete day.

    Returns:
        success_count
        skipped_count

    Raises an exception for serious failures so the checkpoint
    will NOT move forward.
    """

    records = fetch_day(day)

    print(f"Fetched: {len(records)}")

    success = 0
    skipped = 0

    for raw_record in records:

        transformed = transform_record(raw_record)

        # Missing source data:
        # skip the individual record but continue processing the day.
        if not valid_record(transformed):
            print(
                "Skipped record with missing required fields:",
                transformed,
            )

            skipped += 1
            continue

        try:
            upsert_pedestrian_history(transformed)
            success += 1

        except IntegrityError as error:
            # We already know historical data can reference retired
            # sensors that are absent from the current SensorLocation
            # dataset.
            #
            # For now, record these as skipped rather than crashing
            # the entire ingestion job.
            print(
                f"Skipped historical record for "
                f"SensorID={transformed['SensorID']} "
                f"on {transformed['SensingDate']} "
                f"hour={transformed['HourDay']}"
            )

            print("Database integrity issue:", error.orig)

            skipped += 1

        except Exception:
            # Any unexpected database/programming error is serious.
            # Re-raise it so the day is NOT checkpointed.
            raise

    return success, skipped


def main():

    parser = argparse.ArgumentParser(
        description="Synchronise historical pedestrian hourly counts."
    )

    parser.add_argument(
        "--full",
        action="store_true",
        help=(
            "Start again from FULL_START_DATE. "
            "Existing records are safely updated using UPSERT."
        ),
    )

    args = parser.parse_args()

    start_day = get_start_day(args.full)
    end_day = date.today()

    print()
    print("=====================================")
    print("Historical Pedestrian ETL")
    print("=====================================")
    print(f"Start date : {start_day}")
    print(f"End date   : {end_day}")
    print()

    if start_day > end_day:
        print("Historical pedestrian data is already up to date.")
        return

    current_day = start_day

    total_success = 0
    total_skipped = 0
    completed_days = 0

    while current_day <= end_day:

        print()
        print("-------------------------------------")
        print(f"Processing {current_day}")
        print("-------------------------------------")

        try:
            success, skipped = process_day(current_day)

        except Exception as error:
            print()
            print("ETL STOPPED")
            print(f"Failed date: {current_day}")
            print(f"Reason: {error}")
            print()
            print(
                "The checkpoint was NOT advanced. "
                "The next run will retry this same date."
            )

            break

        print(f"Inserted/updated: {success}")
        print(f"Skipped:          {skipped}")

        total_success += success
        total_skipped += skipped

        # Only advance the checkpoint AFTER the API fetch
        # and day's processing have completed without a fatal error.
        update_checkpoint(
            CHECKPOINT_NAME,
            current_day,
        )

        print(
            f"Checkpoint updated → {current_day}"
        )

        completed_days += 1

        current_day += timedelta(days=1)

        # Don't hammer the external API.
        time.sleep(1)

    print()
    print("=====================================")
    print("Historical ETL Summary")
    print("=====================================")
    print(f"Days completed:      {completed_days}")
    print(f"Inserted/updated:    {total_success}")
    print(f"Skipped records:     {total_skipped}")
    print("=====================================")


if __name__ == "__main__":
    main()