from etl.client import fetch_dataset
from etl.repository import upsert_streetlight


DATASET = "street-lights-with-emitted-lux-level-council-owned-lights-only"


def fetch_all_streetlights():
    records = []
    limit = 100
    offset = 0

    while True:
        data = fetch_dataset(
            DATASET,
            limit=limit,
            offset=offset
        )

        results = data["results"]
        records.extend(results)

        if len(results) < limit:
            break

        offset += limit

    return records


def transform_streetlight(record):
    return {
        "LightID": record.get("prop_id"),
        "Lat": record.get("latitude"),
        "Lng": record.get("longitude"),
        "LuxLabel": record.get("label")
    }


def main():
    records = fetch_all_streetlights()

    print(f"Fetched {len(records)} street-light records")

    success = 0
    skipped = 0

    for record in records:
        try:
            transformed = transform_streetlight(record)

            if (
                transformed["LightID"] is None
                or transformed["Lat"] is None
                or transformed["Lng"] is None
            ):
                print("Skipped missing required data:", record)
                skipped += 1
                continue

            upsert_streetlight(transformed)
            success += 1

        except Exception as error:
            print("Skipped record:", record)
            print("Reason:", error)
            skipped += 1

    print()
    print("Street-light sync completed!")
    print(f"Inserted/updated: {success}")
    print(f"Skipped/failed: {skipped}")


if __name__ == "__main__":
    main()