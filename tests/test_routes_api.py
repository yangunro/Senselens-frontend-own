import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


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
        )


if __name__ == "__main__":
    unittest.main()
