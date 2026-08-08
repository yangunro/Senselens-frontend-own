import requests

from etl.validators import valid_non_negative_count
from etl.repository import upsert_pedestrian_count


API_URL = (
    "https://data.melbourne.vic.gov.au/api/explore/v2.1/"
    "catalog/datasets/"
    "pedestrian-counting-system-past-hour-counts-per-minute/"
    "records"
)


def fetch_latest_records():
    response = requests.get(
        API_URL,
        params={
            "limit": 100,
            "order_by": "sensing_datetime desc",
        },
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    return data.get("results", [])


def transform_record(record):
    sensor_id = record.get("location_id")
    sensing_datetime = record.get("sensing_datetime")
    minute_count = record.get("total_of_directions")

    # Required fields must exist
    if sensor_id is None or sensing_datetime is None:
        return None

    # Count must be numeric and non-negative
    if not valid_non_negative_count(minute_count):
        return None

    return {
        "SensorID": int(sensor_id),
        "DateTimeMinute": sensing_datetime,
        "MinuteCount": int(minute_count),
    }


def main():
    print("Starting live pedestrian sync...")

    try:
        records = fetch_latest_records()

    except requests.RequestException as error:
        print("Failed to fetch pedestrian data from City of Melbourne API.")
        print(f"Reason: {error}")
        return

    print(f"Fetched {len(records)} records")

    inserted_or_updated = 0
    skipped = 0
    failed = 0

    for record in records:
        transformed = transform_record(record)

        if transformed is None:
            print("Skipped invalid pedestrian record:", record)
            skipped += 1
            continue

        try:
            upsert_pedestrian_count(transformed)
            inserted_or_updated += 1

        except Exception as error:
            print(
                "Failed to load pedestrian record:",
                transformed,
            )
            print(f"Reason: {error}")
            failed += 1

    print()
    print("=====================================")
    print("Pedestrian live sync completed")
    print("=====================================")
    print(f"Fetched:          {len(records)}")
    print(f"Inserted/updated: {inserted_or_updated}")
    print(f"Skipped invalid:  {skipped}")
    print(f"Failed to load:   {failed}")
    print("=====================================")


if __name__ == "__main__":
    main()