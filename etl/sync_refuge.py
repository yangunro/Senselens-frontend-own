from etl.cbd_boundary import point_in_cbd
from etl.client import fetch_dataset
from etl.repository import refresh_refuge_locations
from etl.validators import clean_text


LANDMARKS_DATASET = (
    "landmarks-and-places-of-interest-including-schools-theatres-"
    "health-services-spor"
)

CAFES_DATASET = "cafes-and-restaurants-with-seating-capacity"

# Latest available census year in the cafes/restaurants dataset.
CAFES_CENSUS_YEAR = "2024"

# Landmark sub_theme values that are genuinely calm, publicly
# accessible refuge spaces. Not every "landmark" is a refuge (a
# casino, a theatre, a police station are not) -- these are chosen
# from the dataset's real theme/sub_theme values, not invented.
PARK_SUBTHEMES = {
    "Informal Outdoor Facility (Park/Garden/Reserve)",
}

LIBRARY_SUBTHEME = "Library"

# The source data tags "State Library Victoria" as
# theme=Community Use / sub_theme=Public Buildings, even though
# it is, in fact, a library. Corrected by name, not fabricated.
LIBRARY_NAME_OVERRIDES = {
    "State Library Victoria",
}

# No City of Melbourne open dataset for community centres /
# neighbourhood houses was found (searched "community centre",
# "neighbourhood house", "leisure centre", "recreation centre").
# CommunityCentre is intentionally left unpopulated rather than
# mapping unrelated landmarks (courts, theatres, concert halls)
# onto it.


def fetch_all_landmarks():
    """
    This dataset is small (~240 records citywide) so it is fetched
    in full and filtered to the CBD client-side, rather than
    relying on the source API's own geo fields/filters.
    """

    records = []
    limit = 100
    offset = 0

    while True:

        data = fetch_dataset(
            LANDMARKS_DATASET,
            limit=limit,
            offset=offset,
        )

        results = data.get("results", [])
        records.extend(results)

        if len(results) < limit:
            break

        offset += limit

    return records


def transform_landmark(record):
    sub_theme = record.get("sub_theme")
    name = clean_text(record.get("feature_name"))

    coords = record.get("co_ordinates") or {}
    lat = coords.get("lat")
    lon = coords.get("lon")

    if lat is None or lon is None or not name:
        return None

    if not point_in_cbd(lat, lon):
        return None

    if sub_theme in PARK_SUBTHEMES:
        category = "Park"

    elif (
        sub_theme == LIBRARY_SUBTHEME
        or name in LIBRARY_NAME_OVERRIDES
    ):
        category = "Library"

    else:
        return None

    return {
        "Name": name,
        "Lat": lat,
        "Lng": lon,
        "Category": category,
        "SourceDataset": LANDMARKS_DATASET,
    }


def fetch_all_cbd_cafes():
    """
    Scoped server-side to the current census year and to the
    "Melbourne (CBD)" CLUE small area (the same official
    small-area classification already used by
    DevelopmentSite_Status), well under 10,000 rows.
    """

    records = []
    limit = 100
    offset = 0

    where = (
        f"census_year=date'{CAFES_CENSUS_YEAR}-01-01' "
        "and clue_small_area='Melbourne (CBD)'"
    )

    while True:

        data = fetch_dataset(
            CAFES_DATASET,
            limit=limit,
            offset=offset,
            where=where,
        )

        results = data.get("results", [])
        records.extend(results)

        if len(results) < limit:
            break

        offset += limit

    return records


def transform_cafes(records):
    """
    The census has one row per seating type (indoor/outdoor) for
    the same business, so the same property can appear twice.
    Keep one row per property_id.
    """

    seen_properties = set()
    transformed = []

    for record in records:

        property_id = record.get("property_id")
        name = clean_text(record.get("trading_name"))
        lat = record.get("latitude")
        lon = record.get("longitude")

        if (
            not property_id
            or not name
            or lat is None
            or lon is None
        ):
            continue

        if property_id in seen_properties:
            continue

        seen_properties.add(property_id)

        transformed.append({
            "Name": name,
            "Lat": lat,
            "Lng": lon,
            "Category": "Cafe",
            "SourceDataset": CAFES_DATASET,
        })

    return transformed


def main():

    landmarks = fetch_all_landmarks()

    print(f"Fetched {len(landmarks)} landmarks (citywide)")

    parks_and_libraries = []

    for record in landmarks:

        transformed = transform_landmark(record)

        if transformed:
            parks_and_libraries.append(transformed)

    park_count = sum(
        1 for r in parks_and_libraries
        if r["Category"] == "Park"
    )

    library_count = sum(
        1 for r in parks_and_libraries
        if r["Category"] == "Library"
    )

    refresh_refuge_locations(
        LANDMARKS_DATASET,
        parks_and_libraries,
    )

    cafe_rows = fetch_all_cbd_cafes()

    print(
        f"Fetched {len(cafe_rows)} CBD cafe/restaurant "
        f"census rows ({CAFES_CENSUS_YEAR})"
    )

    cafes = transform_cafes(cafe_rows)

    refresh_refuge_locations(
        CAFES_DATASET,
        cafes,
    )

    print()
    print("=====================================")
    print("Refuge Location sync completed")
    print("=====================================")
    print(f"Parks (CBD):            {park_count}")
    print(f"Libraries (CBD):        {library_count}")
    print(f"Cafes/restaurants (CBD): {len(cafes)}")
    print(
        "CommunityCentre:        0 "
        "(no verified City of Melbourne dataset found)"
    )
    print("=====================================")


if __name__ == "__main__":
    main()
