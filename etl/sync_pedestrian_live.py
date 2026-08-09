from etl.client import fetch_dataset
from etl.repository import upsert_pedestrian_count
from etl.validators import valid_non_negative_count


DATASET = (
    "pedestrian-counting-system-"
    "past-hour-counts-per-minute"
)


# ============================================================
# Extract
# ============================================================

def fetch_latest_records():
    """
    Fetch the latest pedestrian readings.

    Only one City of Melbourne API request is made
    during each live ETL execution.

    A maximum of 20 records is requested.
    """

    data = fetch_dataset(
        dataset_name=DATASET,
        limit=20,
        offset=0,
        order_by="sensing_datetime desc",
    )

    return data.get(
        "results",
        [],
    )


# ============================================================
# Transform / Validate
# ============================================================

def transform_record(record):
    """
    Clean and validate one pedestrian API record.
    """

    sensor_id = record.get(
        "location_id"
    )

    sensing_datetime = record.get(
        "sensing_datetime"
    )

    minute_count = record.get(
        "total_of_directions"
    )

    # --------------------------------------------------------
    # Required fields
    # --------------------------------------------------------

    if (
        sensor_id is None
        or sensing_datetime is None
    ):
        return None

    # --------------------------------------------------------
    # Count validation
    # --------------------------------------------------------

    if not valid_non_negative_count(
        minute_count
    ):
        return None

    # --------------------------------------------------------
    # Type conversion
    # --------------------------------------------------------

    try:
        sensor_id = int(
            sensor_id
        )

        minute_count = int(
            minute_count
        )

    except (
        TypeError,
        ValueError,
    ):
        return None

    return {
        "SensorID":
            sensor_id,

        "DateTimeMinute":
            sensing_datetime,

        "MinuteCount":
            minute_count,
    }


# ============================================================
# ETL
# ============================================================

def main():

    print()
    print(
        "====================================="
    )

    print(
        "SenseLens Live Pedestrian ETL"
    )

    print(
        "====================================="
    )

    print(
        "Starting live pedestrian sync..."
    )

    # --------------------------------------------------------
    # Extract
    # --------------------------------------------------------

    try:
        records = fetch_latest_records()

    except Exception as error:

        print()
        print(
            "Live pedestrian extraction failed."
        )

        print(
            f"Reason: {error}"
        )

        print(
            "No database changes were made."
        )

        print(
            "====================================="
        )

        return

    print(
        f"Fetched {len(records)} records"
    )

    # --------------------------------------------------------
    # Counters
    # --------------------------------------------------------

    inserted_or_updated = 0

    skipped = 0

    failed = 0

    # --------------------------------------------------------
    # Transform + Load
    # --------------------------------------------------------

    for record in records:

        transformed = transform_record(
            record
        )

        # Invalid record
        if transformed is None:

            skipped += 1

            print(
                "Skipped invalid pedestrian record:"
            )

            print(
                record
            )

            continue

        # ----------------------------------------------------
        # Load
        # ----------------------------------------------------

        try:
            upsert_pedestrian_count(
                transformed
            )

            inserted_or_updated += 1

        except Exception as error:

            failed += 1

            print()
            print(
                "Failed to load pedestrian record:"
            )

            print(
                transformed
            )

            print(
                f"Reason: {error}"
            )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print()
    print(
        "====================================="
    )

    print(
        "Live Pedestrian ETL Completed"
    )

    print(
        "====================================="
    )

    print(
        f"Fetched:          "
        f"{len(records)}"
    )

    print(
        f"Inserted/updated: "
        f"{inserted_or_updated}"
    )

    print(
        f"Skipped invalid:  "
        f"{skipped}"
    )

    print(
        f"Failed to load:   "
        f"{failed}"
    )

    print(
        "====================================="
    )


if __name__ == "__main__":
    main()