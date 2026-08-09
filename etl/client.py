import random
import time

import requests


BASE_URL = (
    "https://data.melbourne.vic.gov.au/api/explore/v2.1/"
    "catalog/datasets"
)


# ============================================================
# API Request Protection
# ============================================================

# Default number of records requested per API call.
DEFAULT_LIMIT = 20

# Minimum delay between requests from this process.
MIN_REQUEST_INTERVAL_SECONDS = 2.0

# Maximum retries when the API is rate limited or temporarily unavailable.
DEFAULT_MAX_RETRIES = 6

# Maximum amount of time to wait between retries.
MAX_BACKOFF_SECONDS = 120


_last_request_time = 0.0


def _respect_request_interval():
    """
    Prevent requests from being sent too quickly.

    Ensures at least MIN_REQUEST_INTERVAL_SECONDS
    between consecutive requests.
    """

    global _last_request_time

    current_time = time.monotonic()

    elapsed = current_time - _last_request_time

    remaining = (
        MIN_REQUEST_INTERVAL_SECONDS - elapsed
    )

    if remaining > 0:
        time.sleep(remaining)

    _last_request_time = time.monotonic()


def _get_retry_delay(response, attempt):
    """
    Determine how long to wait after receiving HTTP 429.

    If the API provides Retry-After, use it.
    Otherwise use exponential backoff with small random jitter.
    """

    retry_after = response.headers.get("Retry-After")

    if retry_after:
        try:
            return min(
                MAX_BACKOFF_SECONDS,
                float(retry_after),
            )

        except ValueError:
            pass

    # Conservative exponential backoff:
    #
    # attempt 0 -> ~5 seconds
    # attempt 1 -> ~10 seconds
    # attempt 2 -> ~20 seconds
    # attempt 3 -> ~40 seconds
    # attempt 4 -> ~80 seconds
    # attempt 5 -> ~120 seconds

    base_delay = min(
        MAX_BACKOFF_SECONDS,
        5 * (2 ** attempt),
    )

    jitter = random.uniform(
        0,
        1.5,
    )

    return min(
        MAX_BACKOFF_SECONDS,
        base_delay + jitter,
    )


def fetch_dataset(
    dataset_name,
    limit=DEFAULT_LIMIT,
    offset=0,
    order_by=None,
    where=None,
    max_retries=DEFAULT_MAX_RETRIES,
):
    """
    Fetch records from the City of Melbourne Open Data API.

    Includes:

    - small default page size
    - request pacing
    - HTTP 429 handling
    - Retry-After support
    - exponential backoff
    - temporary server-error retry
    - timeout handling
    """

    url = (
        f"{BASE_URL}/"
        f"{dataset_name}/records"
    )

    params = {
        "limit": limit,
        "offset": offset,
    }

    if order_by:
        params["order_by"] = order_by

    if where:
        params["where"] = where

    last_error = None

    for attempt in range(max_retries):

        # ----------------------------------------------------
        # Request pacing
        # ----------------------------------------------------

        _respect_request_interval()

        try:
            response = requests.get(
                url,
                params=params,
                timeout=30,
                headers={
                    "User-Agent": (
                        "SenseLens/1.0 "
                        "(Monash University Industry Project)"
                    )
                },
            )

        except requests.RequestException as error:

            last_error = error

            wait_seconds = min(
                MAX_BACKOFF_SECONDS,
                5 * (2 ** attempt),
            )

            print()
            print("API connection error.")
            print(f"Reason: {error}")

            print(
                f"Retry {attempt + 1}/{max_retries}. "
                f"Waiting {wait_seconds:.1f} seconds..."
            )

            time.sleep(wait_seconds)

            continue

        # ----------------------------------------------------
        # HTTP 429 - Rate limited
        # ----------------------------------------------------

        if response.status_code == 429:

            wait_seconds = _get_retry_delay(
                response,
                attempt,
            )

            print()
            print(
                "City of Melbourne API rate limit reached."
            )

            print(
                f"Retry {attempt + 1}/{max_retries}. "
                f"Waiting {wait_seconds:.1f} seconds..."
            )

            last_error = RuntimeError(
                "HTTP 429 Too Many Requests"
            )

            time.sleep(wait_seconds)

            continue

        # ----------------------------------------------------
        # Temporary server errors
        # ----------------------------------------------------

        if response.status_code in {
            500,
            502,
            503,
            504,
        }:

            wait_seconds = min(
                MAX_BACKOFF_SECONDS,
                5 * (2 ** attempt),
            )

            print()
            print(
                "City of Melbourne API returned "
                f"HTTP {response.status_code}."
            )

            print(
                f"Retry {attempt + 1}/{max_retries}. "
                f"Waiting {wait_seconds:.1f} seconds..."
            )

            last_error = RuntimeError(
                f"HTTP {response.status_code}"
            )

            time.sleep(wait_seconds)

            continue

        # ----------------------------------------------------
        # Other HTTP errors
        # ----------------------------------------------------

        response.raise_for_status()

        # ----------------------------------------------------
        # Successful request
        # ----------------------------------------------------

        return response.json()

    raise RuntimeError(
        "City of Melbourne API request failed after "
        f"{max_retries} attempts. "
        f"Last error: {last_error}"
    )


def fetch_all_in_polygon(
    dataset_name,
    polygon_wkt,
    bbox,
    grid_size=3,
    limit=100,
):
    """
    Fetch every record from a City of Melbourne dataset whose
    location falls within a polygon.

    The API rejects offset + limit > 10,000. City-wide datasets
    (e.g. street lights) can exceed that even after filtering to a
    small area, so the polygon's bounding box is split into a
    grid_size x grid_size grid of smaller rectangles. Each
    rectangle is queried and paginated independently, ANDed with
    the polygon filter, keeping every individual query's offset
    well under the API limit.

    A record exactly on a grid boundary may be fetched more than
    once; callers UPSERT on a stable key, so this is harmless.

    bbox is (min_lon, min_lat, max_lon, max_lat).
    """

    min_lon, min_lat, max_lon, max_lat = bbox

    lon_step = (max_lon - min_lon) / grid_size
    lat_step = (max_lat - min_lat) / grid_size

    records = []

    for i in range(grid_size):

        cell_min_lon = min_lon + i * lon_step
        cell_max_lon = min_lon + (i + 1) * lon_step

        for j in range(grid_size):

            cell_min_lat = min_lat + j * lat_step
            cell_max_lat = min_lat + (j + 1) * lat_step

            cell_wkt = (
                "POLYGON(("
                f"{cell_min_lon} {cell_min_lat}, "
                f"{cell_max_lon} {cell_min_lat}, "
                f"{cell_max_lon} {cell_max_lat}, "
                f"{cell_min_lon} {cell_max_lat}, "
                f"{cell_min_lon} {cell_min_lat}"
                "))"
            )

            where = (
                f"within(geo_point_2d, geom'{polygon_wkt}') "
                f"and within(geo_point_2d, geom'{cell_wkt}')"
            )

            offset = 0

            while True:

                data = fetch_dataset(
                    dataset_name,
                    limit=limit,
                    offset=offset,
                    where=where,
                )

                results = data.get("results", [])

                if not results:
                    break

                records.extend(results)

                if len(results) < limit:
                    break

                offset += limit

                if offset >= 9900:
                    raise RuntimeError(
                        "More than 9,900 records found in one "
                        f"grid cell for {dataset_name}. "
                        "Increase grid_size."
                    )

    return records