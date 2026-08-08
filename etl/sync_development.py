from etl.client import fetch_dataset
from etl.repository import upsert_development
from etl.validators import (
    clean_text,
    normalize_status,
    valid_melbourne_coordinates,
)


DATASET = "development-activity-monitor"


def fetch_all_developments():
    records = []
    limit = 100
    offset = 0

    while True:
        data = fetch_dataset(
            DATASET,
            limit=limit,
            offset=offset,
        )

        results = data.get("results", [])
        records.extend(results)

        if len(results) < limit:
            break

        offset += limit

    return records


def transform_record(record):
    property_id = record.get("property_id")
    lat = record.get("latitude")
    lng = record.get("longitude")
    status = normalize_status(record.get("status"))

    if property_id is None:
        return None

    if status is None:
        return None

    if not valid_melbourne_coordinates(lat, lng):
        return None

    return {
        "PropertyID": int(property_id),
        "CLUE_SmallArea": clean_text(
            record.get("clue_small_area")
        ),
        "Status": status,
        "DevelopmentType": clean_text(
            record.get("development_type")
        ),
        "Lat": float(lat),
        "Lng": float(lng),
    }


def main():
    print("Starting Development Activity sync...")

    try:
        records = fetch_all_developments()

    except Exception as error:
        print("Failed to fetch Development Activity data.")
        print(f"Reason: {error}")
        return

    print(f"Fetched {len(records)} development records")

    inserted_or_updated = 0
    skipped = 0
    failed = 0

    for record in records:
        transformed = transform_record(record)

        if transformed is None:
            print("Skipped invalid development record:", record)
            skipped += 1
            continue

        try:
            upsert_development(transformed)
            inserted_or_updated += 1

        except Exception as error:
            print()
            print("Failed to load development record:")
            print(transformed)
            print(f"Reason: {error}")

            failed += 1

    print()
    print("=====================================")
    print("Development Activity sync completed")
    print("=====================================")
    print(f"Fetched:          {len(records)}")
    print(f"Inserted/updated: {inserted_or_updated}")
    print(f"Skipped invalid:  {skipped}")
    print(f"Failed to load:   {failed}")
    print("=====================================")


if __name__ == "__main__":
    main()