import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.forecast_service import ForecastModelUnavailable


class RoutesApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()

    def test_dynamic_route_requires_both_origin_coordinates(self):
        response = self.client.get(
            "/routes",
            params={"destination": "Melbourne Central"},
        )

        self.assertEqual(response.status_code, 422)
        self.assertIn("originLat", response.json()["detail"])

    def test_dynamic_route_passes_user_origin_to_service(self):
        with patch(
            "app.routers.routes.get_routes",
            return_value=[],
        ) as get_routes:
            response = self.client.get(
                "/routes",
                params={
                    "destination": "Melbourne Central",
                    "originLat": -37.8136,
                    "originLng": 144.9631,
                },
            )

        self.assertEqual(response.status_code, 200)
        get_routes.assert_called_once_with(
            "Melbourne Central",
            -37.8136,
            144.9631,
            None,
            None,
            False,
        )

    def test_destination_coordinates_must_be_provided_together(self):
        response = self.client.get(
            "/routes",
            params={
                "destination": "Melbourne Central",
                "originLat": -37.8136,
                "originLng": 144.9631,
                "destinationLat": -37.8100,
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertIn(
            "destinationLng",
            response.json()["detail"],
        )

    def test_selected_destination_coordinates_reach_service(self):
        with patch(
            "app.routers.routes.get_routes",
            return_value=[],
        ) as get_routes:
            response = self.client.get(
                "/routes",
                params={
                    "destination": "Melbourne Central",
                    "originLat": -37.8136,
                    "originLng": 144.9631,
                    "destinationLat": -37.8102,
                    "destinationLng": 144.9628,
                },
            )

        self.assertEqual(response.status_code, 200)
        get_routes.assert_called_once_with(
            "Melbourne Central",
            -37.8136,
            144.9631,
            -37.8102,
            144.9628,
            False,
        )

    def test_route_forecast_returns_service_unavailable_without_model(self):
        route_id = "8af6859d-e9e6-4f34-b747-19951af3444c"

        with patch(
            "app.routers.routes.get_route_forecast",
            side_effect=ForecastModelUnavailable("Model is unavailable."),
        ):
            response = self.client.get(f"/routes/{route_id}/forecast")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], "Model is unavailable.")

    def test_map_wide_forecast_accepts_horizon_alias(self):
        service_result = {
            "horizonHours": 2,
            "forecasts": [],
            "alerts": [],
        }

        with patch(
            "app.routers.pedestrian.get_active_sensor_forecast",
            return_value=service_result,
        ) as get_forecast:
            response = self.client.get(
                "/pedestrian-forecasts",
                params={"horizonHours": 2},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), service_result)
        get_forecast.assert_called_once_with(horizon_hours=2)

    def test_map_wide_forecast_rejects_more_than_three_hours(self):
        response = self.client.get(
            "/pedestrian-forecasts",
            params={"horizonHours": 4},
        )

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
