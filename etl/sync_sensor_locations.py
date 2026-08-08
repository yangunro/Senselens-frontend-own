import requests

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
    return {
        "SensorID": sensor["location_id"],
        "SensorDescription": sensor.get("sensor_description"),
        "Lat": sensor["latitude"],
        "Lng": sensor["longitude"],
        "Status": sensor.get("status"),
        "InstallationDate": sensor.get("installation_date")
    }


def main():
    sensors = fetch_all_sensors()

    print(f"Fetched {len(sensors)} sensors")

    for sensor in sensors:
        transformed = transform_sensor(sensor)
        upsert_sensor(transformed)

    print("Sensor locations synced successfully!")


if __name__ == "__main__":
    main()