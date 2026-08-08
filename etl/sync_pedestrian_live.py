import requests

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
            "order_by": "sensing_datetime desc"
        },
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    return data["results"]


def transform_record(record):
    return {
        "SensorID": record["location_id"],
        "DateTimeMinute": record["sensing_datetime"],
        "MinuteCount": record["total_of_directions"]
    }


def main():
    records = fetch_latest_records()

    print(f"Fetched {len(records)} records")

    inserted_or_updated = 0
    skipped = 0

    for record in records:
        try:
            transformed = transform_record(record)

            if (
                transformed["SensorID"] is None
                or transformed["DateTimeMinute"] is None
                or transformed["MinuteCount"] is None
            ):
                skipped += 1
                continue

            upsert_pedestrian_count(transformed)
            inserted_or_updated += 1

        except KeyError as error:
            print(f"Skipped record - missing field: {error}")
            skipped += 1

        except Exception as error:
            print(f"Failed record: {error}")
            skipped += 1

    print()
    print("Pedestrian live sync completed!")
    print(f"Inserted/updated: {inserted_or_updated}")
    print(f"Skipped/failed: {skipped}")


if __name__ == "__main__":
    main()