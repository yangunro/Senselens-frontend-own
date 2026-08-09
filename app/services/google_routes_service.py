import os
from uuid import uuid4

import requests


GOOGLE_ROUTES_URL = (
    "https://routes.googleapis.com/directions/v2:computeRoutes"
)


class GoogleRoutesConfigurationError(RuntimeError):
    pass


class GoogleRoutesProviderError(RuntimeError):
    pass


def _create_waypoint(value):
    if isinstance(value, str):
        return {"address": value}

    return {
        "location": {
            "latLng": {
                "latitude": value["lat"],
                "longitude": value["lng"],
            }
        }
    }


def _duration_to_minutes(duration):
    if not duration:
        return 0

    try:
        seconds = float(str(duration).removesuffix("s"))
    except ValueError:
        return 0

    return round(seconds / 60)


def _distance_to_km(distance_metres):
    return round(distance_metres / 1000, 1)


def get_google_routes(origin, destination):
    api_key = os.getenv("GOOGLE_ROUTES_API_KEY")

    if not api_key:
        raise GoogleRoutesConfigurationError(
            "GOOGLE_ROUTES_API_KEY is not configured on the backend."
        )

    try:
        response = requests.post(
            GOOGLE_ROUTES_URL,
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": api_key,
                "X-Goog-FieldMask": ",".join([
                    "routes.distanceMeters",
                    "routes.duration",
                    "routes.polyline.encodedPolyline",
                    "routes.legs.startLocation",
                    "routes.legs.endLocation",
                    "routes.legs.steps.distanceMeters",
                    "routes.legs.steps.staticDuration",
                    "routes.legs.steps.navigationInstruction",
                ]),
            },
            json={
                "origin": _create_waypoint(origin),
                "destination": _create_waypoint(destination),
                "travelMode": "WALK",
                "computeAlternativeRoutes": True,
                "languageCode": "en-AU",
                "units": "METRIC",
            },
            timeout=20,
        )
    except requests.RequestException as error:
        raise GoogleRoutesProviderError(
            "Unable to reach Google Routes."
        ) from error

    if not response.ok:
        raise GoogleRoutesProviderError(
            f"Google Routes returned HTTP {response.status_code}."
        )

    try:
        payload = response.json()
    except requests.JSONDecodeError as error:
        raise GoogleRoutesProviderError(
            "Google Routes returned an invalid response."
        ) from error

    routes = []

    for route in payload.get("routes", []):
        distance_metres = route.get("distanceMeters", 0)
        duration_minutes = _duration_to_minutes(route.get("duration"))
        legs = route.get("legs", [])
        steps = []

        for leg in legs:
            for step in leg.get("steps", []):
                navigation = step.get("navigationInstruction", {})
                steps.append({
                    "instruction": navigation.get("instructions", ""),
                    "maneuver": navigation.get("maneuver"),
                    "distanceMeters": step.get("distanceMeters", 0),
                })

        start_lat_lng = (
            legs[0]
            .get("startLocation", {})
            .get("latLng", {})
            if legs
            else {}
        )
        end_lat_lng = (
            legs[-1]
            .get("endLocation", {})
            .get("latLng", {})
            if legs
            else {}
        )

        routes.append({
            "id": str(uuid4()),
            "distanceMeters": distance_metres,
            "distance": f"{_distance_to_km(distance_metres):g} km",
            "durationMinutes": duration_minutes,
            "duration": f"{duration_minutes} min",
            "polyline": route.get("polyline", {}).get("encodedPolyline"),
            "origin": {
                "lat": start_lat_lng.get("latitude"),
                "lng": start_lat_lng.get("longitude"),
            },
            "destination": {
                "lat": end_lat_lng.get("latitude"),
                "lng": end_lat_lng.get("longitude"),
            },
            "steps": steps,
        })

    return routes
