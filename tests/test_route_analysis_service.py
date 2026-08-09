import unittest

import polyline

from app.services.route_analysis_service import (
    analyse_route,
    decode_route,
    distance_to_route_metres,
)


class RouteAnalysisServiceTests(unittest.TestCase):
    def setUp(self):
        self.encoded_route = polyline.encode([
            (-37.8136, 144.9600),
            (-37.8136, 144.9700),
        ])

    def test_decodes_google_polyline(self):
        points = decode_route(self.encoded_route)

        self.assertEqual(len(points), 2)
        self.assertAlmostEqual(points[0]["lat"], -37.8136, places=4)
        self.assertAlmostEqual(points[1]["lng"], 144.9700, places=4)

    def test_calculates_distance_to_route_segment(self):
        points = decode_route(self.encoded_route)
        distance = distance_to_route_metres(
            {"lat": -37.8137, "lng": 144.9650},
            points,
        )

        self.assertLess(distance, 15)

    def test_scores_route_using_nearby_sensors(self):
        snapshot = {
            "observedAt": "2026-08-08T13:04:00+00:00",
            "sensors": [
                {
                    "sensorId": 1,
                    "name": "Near route",
                    "minuteCount": 5,
                    "lat": -37.8137,
                    "lng": 144.9650,
                },
                {
                    "sensorId": 2,
                    "name": "Outside route buffer",
                    "minuteCount": 20,
                    "lat": -37.8300,
                    "lng": 144.9650,
                },
                {
                    "sensorId": 3,
                    "name": "Busy reference sensor",
                    "minuteCount": 50,
                    "lat": -37.8400,
                    "lng": 144.9650,
                },
            ],
        }

        analysed = analyse_route(
            {"id": "route-low", "polyline": self.encoded_route},
            snapshot,
        )

        self.assertEqual(analysed["matchedSensorCount"], 1)
        self.assertEqual(analysed["nearbySensors"][0]["sensorId"], 1)
        self.assertEqual(analysed["sensoryScore"], 33)
        self.assertEqual(analysed["level"], "low")

    def test_missing_nearby_sensor_is_insufficient_not_low(self):
        analysed = analyse_route(
            {"id": "route-unknown", "polyline": self.encoded_route},
            {
                "observedAt": "2026-08-08T13:04:00+00:00",
                "sensors": [{
                    "sensorId": 9,
                    "name": "Far away",
                    "minuteCount": 0,
                    "lat": -37.9000,
                    "lng": 145.1000,
                }],
            },
        )

        self.assertIsNone(analysed["sensoryScore"])
        self.assertEqual(analysed["level"], "unknown")
        self.assertEqual(
            analysed["levelLabel"],
            "INSUFFICIENT DATA",
        )


if __name__ == "__main__":
    unittest.main()
