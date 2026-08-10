import unittest
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from app.services.forecast_service import (
    build_pedestrian_forecast,
    classify_prediction,
)


MODEL_FIXTURE = {
    "modelType": "per-sensor calendar linear regression",
    "modelVersion": "pedestrian-linear-v1",
    "trainedAt": "2026-08-10T00:00:00+00:00",
    "target": "pedestrians_per_minute",
    "trainingRange": {
        "start": "2025-01-01",
        "end": "2026-08-09",
    },
    "globalModel": {
        "coefficients": [16, 0, 0, 0, 0, 0, 0],
    },
    "sensorModels": {
        "1": {
            "coefficients": [4, 0, 0, 0, 0, 0, 0],
        },
    },
}


class ForecastServiceTests(unittest.TestCase):
    def test_risk_band_boundaries_use_rounded_counts_per_minute(self):
        self.assertEqual(classify_prediction(5.49)["level"], "low")
        self.assertEqual(classify_prediction(5.50)["level"], "medium")
        self.assertEqual(classify_prediction(14.49)["level"], "medium")
        self.assertEqual(classify_prediction(14.50)["level"], "high")

    def test_builds_three_hour_per_sensor_forecast_and_alerts(self):
        now = datetime(
            2026,
            8,
            10,
            10,
            35,
            tzinfo=ZoneInfo("Australia/Melbourne"),
        )
        sensors = [
            {
                "sensorId": 1,
                "name": "Quiet sensor",
                "lat": -37.81,
                "lng": 144.96,
            },
            {
                "sensorId": 2,
                "name": "Busy sensor",
                "lat": -37.82,
                "lng": 144.97,
            },
        ]

        with patch(
            "app.services.forecast_service.load_forecast_model",
            return_value=MODEL_FIXTURE,
        ):
            result = build_pedestrian_forecast(
                sensors,
                route_id="route-1",
                horizon_hours=3,
                now=now,
                data_as_of="2026-08-10T10:30:00+10:00",
            )

        self.assertEqual(result["sensoryIndicator"], "HIGH SENSORY")
        self.assertEqual(result["level"], "high")
        self.assertEqual(result["horizonHours"], 3)
        self.assertEqual(len(result["forecasts"]), 3)
        self.assertEqual(len(result["alerts"]), 3)
        self.assertEqual(
            result["forecasts"][0]["forecastAt"],
            "2026-08-10T11:00:00+10:00",
        )
        self.assertEqual(
            result["forecasts"][2]["forecastAt"],
            "2026-08-10T13:00:00+10:00",
        )
        first_hour_sensors = result["forecasts"][0]["sensors"]
        self.assertEqual(first_hour_sensors[0]["sensorId"], 2)
        self.assertEqual(first_hour_sensors[0]["level"], "high")
        self.assertEqual(first_hour_sensors[1]["level"], "low")
        self.assertEqual(first_hour_sensors[1]["modelScope"], "sensor")

    def test_requires_at_least_one_sensor(self):
        self.assertIsNone(build_pedestrian_forecast([]))


if __name__ == "__main__":
    unittest.main()
