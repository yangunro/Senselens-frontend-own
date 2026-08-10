import os
from uuid import uuid4

import requests


MAPBOX_DIRECTIONS_URL = (
    "https://api.mapbox.com/directions/v5/mapbox/walking/{coordinates}"
)


class MapboxRoutesConfigurationError(RuntimeError):
    pass


class MapboxRoutesProviderError(RuntimeError):
    pass


def _coordinate_string(point):
    # Mapbox Directions takes coordinates only, unlike Google Routes' API
    # which could geocode a free-text address itself. Not a real limitation
    # in practice — the frontend always resolves a destination to lat/lng
    # (via its own geocoding) before calling this endpoint.
    if not isinstance(point, dict) or point.get("lat") is None or point.get("lng") is None:
        raise MapboxRoutesProviderError(
            "Mapbox Directions requires coordinates, not a place name."
        )

    return f"{point['lng']},{point['lat']}"


def _distance_to_km(distance_metres):
    return round(distance_metres / 1000, 1)


def get_mapbox_routes(origin, destination):
    access_token = os.getenv("MAPBOX_ACCESS_TOKEN")

    if not access_token:
        raise MapboxRoutesConfigurationError(
            "MAPBOX_ACCESS_TOKEN is not configured on the backend."
        )

    coordinates = f"{_coordinate_string(origin)};{_coordinate_string(destination)}"
    url = MAPBOX_DIRECTIONS_URL.format(coordinates=coordinates)

    try:
        response = requests.get(
            url,
            params={
                "alternatives": "true",
                # precision-5 encoding — matches what route_analysis_service's
                # decode_route() (the `polyline` package) expects by default;
                # "polyline6" would silently produce garbled coordinates.
                "geometries": "polyline",
                "steps": "true",
                "overview": "full",
                "language": "en",
                "access_token": access_token,
            },
            timeout=20,
        )
    except requests.RequestException as error:
        raise MapboxRoutesProviderError(
            "Unable to reach Mapbox Directions."
        ) from error

    if not response.ok:
        raise MapboxRoutesProviderError(
            f"Mapbox Directions returned HTTP {response.status_code}."
        )

    try:
        payload = response.json()
    except requests.JSONDecodeError as error:
        raise MapboxRoutesProviderError(
            "Mapbox Directions returned an invalid response."
        ) from error

    if payload.get("code") != "Ok":
        raise MapboxRoutesProviderError(
            f"Mapbox Directions could not find a route ({payload.get('code')})."
        )

    waypoints = payload.get("waypoints") or []
    origin_location = waypoints[0]["location"] if len(waypoints) > 0 else None
    destination_location = waypoints[-1]["location"] if len(waypoints) > 1 else None

    routes = []

    for route in payload.get("routes", []):
        distance_metres = route.get("distance", 0)
        duration_minutes = round(route.get("duration", 0) / 60)
        steps = []

        for leg in route.get("legs", []):
            for step in leg.get("steps", []):
                maneuver = step.get("maneuver", {})
                steps.append({
                    "instruction": maneuver.get("instruction", ""),
                    "maneuver": maneuver.get("type"),
                    "distanceMeters": step.get("distance", 0),
                })

        routes.append({
            "id": str(uuid4()),
            "distanceMeters": distance_metres,
            "distance": f"{_distance_to_km(distance_metres):g} km",
            "durationMinutes": duration_minutes,
            "duration": f"{duration_minutes} min",
            "polyline": route.get("geometry"),
            "origin": {
                "lat": origin_location[1] if origin_location else origin.get("lat"),
                "lng": origin_location[0] if origin_location else origin.get("lng"),
            },
            "destination": {
                "lat": destination_location[1] if destination_location else destination.get("lat"),
                "lng": destination_location[0] if destination_location else destination.get("lng"),
            },
            "steps": steps,
        })

    return routes
