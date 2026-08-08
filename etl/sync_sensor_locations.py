import requests
from etl.validators import (
    clean_text,
    valid_melbourne_coordinates,
)
from etl.repository import upsert_sensor


API_URL = (
    "https://data.melbourne.vic.gov.au/api/explore/v2.1/"
    "catalog/datasets/"
    "pedestrian-counting-system-sensor-locations/"
    "records"
)


def fetch_all_sensors():
    sensors = []
    limit = 100
    offset = 0

    while True:
        response = requests.get(
            API_URL,
            params={
                "limit": limit,
                "offset": offset
            },
            timeout=30
        )

        response.raise_for_status()

        data = response.json()
        results = data["results"]

        sensors.extend(results)

        if len(results) < limit:
            break

        offset += limit

    return sensors


def transform_sensor(sensor):
    lat = sensor.get("latitude")
    lng = sensor.get("longitude")

    if not valid_melbourne_coordinates(lat, lng):
        return None

    return {
        "SensorID": sensor.get("location_id"),
        "SensorDescription": clean_text(
            sensor.get("sensor_description")
        ),
        "Lat": float(lat),
        "Lng": float(lng),
        "Status": clean_text(sensor.get("status")),
        "InstallationDate": sensor.get("installation_date"),
    }


def main():
    sensors = fetch_all_sensors()

    print(f"Fetched {len(sensors)} sensors")

    for sensor in sensors:
        transformed = transform_sensor(sensor)
        if transformed is None:
            print("Skipped invalid sensor:", sensor)
            continue

        upsert_sensor(transformed)

    print("Sensor locations synced successfully!")


if __name__ == "__main__":
    main()