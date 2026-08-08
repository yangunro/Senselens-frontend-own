import requests


BASE_URL = (
    "https://data.melbourne.vic.gov.au/api/explore/v2.1/"
    "catalog/datasets"
)


import time
import requests


BASE_URL = (
    "https://data.melbourne.vic.gov.au/api/explore/v2.1/"
    "catalog/datasets"
)


def fetch_dataset(
    dataset_name,
    limit=100,
    offset=0,
    order_by=None,
    where=None,
    max_retries=5
):
    url = f"{BASE_URL}/{dataset_name}/records"

    params = {
        "limit": limit,
        "offset": offset
    }

    if order_by:
        params["order_by"] = order_by

    if where:
        params["where"] = where

    for attempt in range(max_retries):
        response = requests.get(
            url,
            params=params,
            timeout=30
        )

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")

            if retry_after:
                wait_seconds = int(retry_after)
            else:
                wait_seconds = 2 ** attempt

            print(
                f"Rate limited. Waiting {wait_seconds} seconds..."
            )

            time.sleep(wait_seconds)
            continue

        response.raise_for_status()

        # Small delay even after successful requests
        time.sleep(0.25)

        return response.json()

    raise RuntimeError(
        f"API rate limit persisted after {max_retries} retries."
    )


