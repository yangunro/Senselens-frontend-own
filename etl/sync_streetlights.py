from etl.cbd_boundary import cbd_boundary_wkt, cbd_bounding_box
from etl.client import fetch_all_in_polygon
from etl.repository import bulk_upsert_streetlights


DATASET = "street-lights-with-emitted-lux-level-council-owned-lights-only"

# Records written to the database per bulk UPSERT.
BATCH_SIZE = 500


def fetch_all_streetlights():
    """
    Fetch every council-owned street light within the Melbourne
    CBD boundary.

    This dataset has 100,000+ records city-wide, far more than
    the app needs (SenseLens only scores routes inside the CBD)
    and far more than the API's offset pagination allows in a
    single query. Scoping to the CBD polygon keeps the result set
    both relevant and within the API's limits.
    """

    return fetch_all_in_polygon(
        DATASET,
        polygon_wkt=cbd_boundary_wkt(),
        bbox=cbd_bounding_box(),
    )


def transform_streetlight(record):
    geo_point = record.get("geo_point_2d") or {}

    ext_id = record.get("ext_id")

    try:
        light_id = int(ext_id)
    except (TypeError, ValueError):
        light_id = None

    return {
        "LightID": light_id,
        "Lat": geo_point.get("lat"),
        "Lng": geo_point.get("lon"),
        "LuxLabel": record.get("label")
    }


def main():
    records = fetch_all_streetlights()

    print(f"Fetched {len(records)} street-light records")

    success = 0
    skipped = 0
    batch = []

    for record in records:

        transformed = transform_streetlight(record)

        if (
            transformed["LightID"] is None
            or transformed["Lat"] is None
            or transformed["Lng"] is None
        ):
            skipped += 1
            continue

        batch.append(transformed)

        if len(batch) >= BATCH_SIZE:
            success += bulk_upsert_streetlights(batch)
            batch.clear()

    if batch:
        success += bulk_upsert_streetlights(batch)
        batch.clear()

    print()
    print("Street-light sync completed!")
    print(f"Inserted/updated: {success}")
    print(f"Skipped/failed: {skipped}")


if __name__ == "__main__":
    main()