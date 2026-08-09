import os

import requests
from dotenv import load_dotenv
from google.transit import gtfs_realtime_pb2


load_dotenv()


# Confirmed against Transport Victoria's published OpenAPI specs
# at https://opendata.transport.vic.gov.au/dataset/gtfs-realtime
# (gtfsr_metro_train_vehicle_positions.openapi.json,
# gtfsr_yarra_trams_vehicle_positions.openapi.json,
# gtfsr_metro_bus_vehicle_positions.openapi.json).
BASE_URL = (
    "https://api.opendata.transport.vic.gov.au/"
    "opendata/public-transport/gtfs/realtime/v1"
)

VEHICLE_POSITIONS_PATHS = {
    "Train": f"{BASE_URL}/metro/vehicle-positions",
    "Tram": f"{BASE_URL}/tram/vehicle-positions",
    "Bus": f"{BASE_URL}/bus/vehicle-positions",
}


def fetch_vehicle_positions(mode):
    """
    Fetch and parse a GTFS-Realtime VehiclePositions feed from
    Transport Victoria's Open Data Portal.

    mode is one of "Train", "Tram", "Bus" (matches the
    vehicle_mode DB enum). Requires TV_API_KEY in the environment,
    sent as the "KeyId" header per Transport Victoria's API docs.

    Returns a parsed gtfs_realtime_pb2.FeedMessage.
    """

    api_key = os.getenv("TV_API_KEY")

    if not api_key:
        raise RuntimeError(
            "TV_API_KEY is not set. Get a key from "
            "https://opendata.transport.vic.gov.au and add it "
            "to .env."
        )

    url = VEHICLE_POSITIONS_PATHS[mode]

    response = requests.get(
        url,
        headers={"KeyId": api_key},
        timeout=30,
    )

    if response.status_code == 401:
        raise RuntimeError(
            f"Transport Victoria rejected the API key for {mode}: "
            f"{response.headers.get('WWW-Authenticate', response.text)}"
        )

    response.raise_for_status()

    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(response.content)

    return feed
