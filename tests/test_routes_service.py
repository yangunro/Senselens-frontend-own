import unittest
from unittest.mock import patch

import polyline

from app.services.routes_service import (
    get_route,
    get_route_forecast,
    get_routes,
)


class RoutesServiceTests(unittest.TestCase):
    def test_dynamic_route_forecast_uses_nearby_sensors(self):
        dynamic_route = {
            "nearbySensors": [{"sensorId": 7, "name": "Test sensor"}],
            "pedestrianObservedAt": "2026-08-10T09:00:00+10:00",
        }
        forecast = {"level": "medium"}

        with (
            patch(
                "app.services.routes_service.get_dynamic_route",
                return_value=dynamic_route,
            ),
            patch(
                "app.services.routes_service.build_pedestrian_forecast",
                return_value=forecast,
            ) as build_forecast,
        ):
            result = get_route_forecast("route-1")

        self.assertEqual(result, forecast)
        build_forecast.assert_called_once_with(
            dynamic_route["nearbySensors"],
            route_id="route-1",
            horizon_hours=3,
            data_as_of=dynamic_route["pedestrianObservedAt"],
        )

    def test_selected_destination_uses_coordinate_waypoint(self):
        with (
            patch(
                "app.services.routes_service.get_mapbox_routes",
                return_value=[],
            ) as get_mapbox_routes,
            patch(
                "app.services.routes_service.get_latest_pedestrian_snapshot",
                return_value=None,
            ),
        ):
            get_routes(
                "Melbourne Central",
                -37.8136,
                144.9631,
                -37.8102,
                144.9628,
            )

        get_mapbox_routes.assert_called_once_with(
            {
                "lat": -37.8136,
                "lng": 144.9631,
            },
            {
                "lat": -37.8102,
                "lng": 144.9628,
            },
        )

    def test_dynamic_routes_are_scored_sorted_and_cached(self):
        quiet_polyline = polyline.encode([
            (-37.8136, 144.9600),
            (-37.8136, 144.9700),
        ])
        busy_polyline = polyline.encode([
            (-37.8200, 144.9600),
            (-37.8200, 144.9700),
        ])
        mapbox_routes = [
            {
                "id": "busy-route",
                "distanceMeters": 800,
                "distance": "0.8 km",
                "durationMinutes": 10,
                "duration": "10 min",
                "polyline": busy_polyline,
                "origin": {"lat": -37.8200, "lng": 144.9600},
                "destination": {"lat": -37.8200, "lng": 144.9700},
                "steps": [],
            },
            {
                "id": "lower-crowd-route",
                "distanceMeters": 1000,
                "distance": "1 km",
                "durationMinutes": 13,
                "duration": "13 min",
                "polyline": quiet_polyline,
                "origin": {"lat": -37.8136, "lng": 144.9600},
                "destination": {"lat": -37.8136, "lng": 144.9700},
                "steps": [],
            },
        ]
        snapshot = {
            "observedAt": "2026-08-08T13:04:00+00:00",
            "sensors": [
                {
                    "sensorId": 1,
                    "name": "Lower activity",
                    "minuteCount": 5,
                    "lat": -37.8137,
                    "lng": 144.9650,
                },
                {
                    "sensorId": 2,
                    "name": "Mid activity",
                    "minuteCount": 20,
                    "lat": -37.8400,
                    "lng": 144.9650,
                },
                {
                    "sensorId": 3,
                    "name": "Higher activity",
                    "minuteCount": 50,
                    "lat": -37.8201,
                    "lng": 144.9650,
                },
            ],
        }

        with (
            patch(
                "app.services.routes_service.get_mapbox_routes",
                return_value=mapbox_routes,
            ),
            patch(
                "app.services.routes_service.get_latest_pedestrian_snapshot",
                return_value=snapshot,
            ),
            # Keep this a hermetic unit test — don't let the construction /
            # lighting enrichers reach out to the live database.
            patch(
                "app.services.routes_service.get_active_construction_sites",
                return_value=[],
            ),
            patch(
                "app.services.routes_service.get_lights_in_bounds",
                return_value=[],
            ),
        ):
            summaries = get_routes("Collins Street")

        self.assertEqual(summaries[0]["id"], "lower-crowd-route")
        self.assertTrue(summaries[0]["recommended"])
        self.assertEqual(summaries[0]["level"], "low")
        self.assertEqual(summaries[1]["level"], "high")

        detail = get_route("lower-crowd-route")

        self.assertEqual(detail["matchedSensorCount"], 1)
        self.assertEqual(detail["nearbySensors"][0]["sensorId"], 1)
        self.assertEqual(detail["polyline"], quiet_polyline)


if __name__ == "__main__":
    unittest.main()
