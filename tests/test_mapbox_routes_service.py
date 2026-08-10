import unittest
from unittest.mock import MagicMock, patch

import polyline

from app.services import mapbox_routes_service as service


def _leg(*step_specs):
    return {
        "steps": [
            {
                "distance": distance,
                "maneuver": {"instruction": instruction, "type": maneuver},
            }
            for instruction, maneuver, distance in step_specs
        ]
    }


def _mapbox_payload(routes):
    return {
        "code": "Ok",
        "waypoints": [
            {"location": [144.9671, -37.8183]},
            {"location": [144.9568, -37.8076]},
        ],
        "routes": routes,
    }


def _response(payload):
    response = MagicMock()
    response.ok = True
    response.json.return_value = payload
    return response


class MapboxRoutesServiceTests(unittest.TestCase):
    def setUp(self):
        patcher = patch.dict("os.environ", {"MAPBOX_ACCESS_TOKEN": "test-token"})
        patcher.start()
        self.addCleanup(patcher.stop)

        self.origin = {"lat": -37.8183, "lng": 144.9671}
        self.destination = {"lat": -37.8076, "lng": 144.9568}

        # Three visibly different paths so nothing gets de-duplicated.
        self.direct = polyline.encode([(-37.8183, 144.9671), (-37.8076, 144.9568)])
        self.east = polyline.encode([(-37.8183, 144.9671), (-37.8130, 144.9660), (-37.8076, 144.9568)])
        self.west = polyline.encode([(-37.8183, 144.9671), (-37.8130, 144.9580), (-37.8076, 144.9568)])

    def test_synthesises_alternatives_when_mapbox_returns_one_route(self):
        direct_payload = _mapbox_payload([
            {"geometry": self.direct, "distance": 1958, "duration": 1440, "legs": [_leg(("Head south", "depart", 60))]},
        ])
        east_payload = _mapbox_payload([
            {"geometry": self.east, "distance": 2036, "duration": 1500, "legs": [_leg(("Head east", "depart", 60))]},
        ])
        west_payload = _mapbox_payload([
            {"geometry": self.west, "distance": 2253, "duration": 1680, "legs": [_leg(("Head west", "depart", 60))]},
        ])

        with patch(
            "app.services.mapbox_routes_service.requests.get",
            side_effect=[_response(direct_payload), _response(east_payload), _response(west_payload)],
        ):
            routes = service.get_mapbox_routes(self.origin, self.destination)

        # One real route plus two synthesised alternatives = three distinct routes.
        self.assertEqual(len(routes), 3)
        self.assertEqual(len({route["polyline"] for route in routes}), 3)

    def test_absurd_detour_is_rejected(self):
        direct_payload = _mapbox_payload([
            {"geometry": self.direct, "distance": 1000, "duration": 720, "legs": [_leg(("Head south", "depart", 60))]},
        ])
        # A variant more than MAX_DETOUR_RATIO longer than the direct route
        # is no longer a "parallel street" — it must be dropped.
        absurd_payload = _mapbox_payload([
            {"geometry": self.east, "distance": 9000, "duration": 6000, "legs": [_leg(("Loop", "depart", 60))]},
        ])

        with patch(
            "app.services.mapbox_routes_service.requests.get",
            side_effect=[_response(direct_payload), _response(absurd_payload), _response(absurd_payload)],
        ):
            routes = service.get_mapbox_routes(self.origin, self.destination)

        self.assertEqual(len(routes), 1)

    def test_intermediate_waypoint_stopover_steps_are_dropped(self):
        # Routing through a via waypoint injects a spurious arrive/depart pair
        # mid-route; those non-terminal stopovers must not leak into the steps.
        direct_payload = _mapbox_payload([
            {
                "geometry": self.east,
                "distance": 2000,
                "duration": 1500,
                "legs": [
                    _leg(("Head south", "depart", 60), ("Arrive at waypoint", "arrive", 0)),
                    _leg(("Depart waypoint", "depart", 0), ("Arrive", "arrive", 40)),
                ],
            },
        ])

        with patch(
            "app.services.mapbox_routes_service.requests.get",
            side_effect=[_response(direct_payload), _response(_mapbox_payload([])), _response(_mapbox_payload([]))],
        ):
            routes = service.get_mapbox_routes(self.origin, self.destination)

        maneuvers = [step["maneuver"] for step in routes[0]["steps"]]
        # First step is a depart, last is an arrive; no stopover pair survives between.
        self.assertEqual(maneuvers[0], "depart")
        self.assertEqual(maneuvers[-1], "arrive")
        self.assertNotIn("arrive", maneuvers[:-1])
        self.assertNotIn("depart", maneuvers[1:])

    def test_missing_token_raises_configuration_error(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(service.MapboxRoutesConfigurationError):
                service.get_mapbox_routes(self.origin, self.destination)


if __name__ == "__main__":
    unittest.main()
