import os
from concurrent.futures import ThreadPoolExecutor
from math import cos, hypot, radians
from uuid import uuid4

import polyline
import requests


MAPBOX_DIRECTIONS_URL = (
    "https://api.mapbox.com/directions/v5/mapbox/walking/{coordinates}"
)

METRES_PER_DEGREE_LAT = 111_320

# Mapbox's walking profile returns at most one route even with
# alternatives=true (unlike Google's computeAlternativeRoutes, which gave up
# to three). A single route defeats the whole point of the app — there's
# nothing to rank by sensory score and nothing for construction-avoidance to
# reorder. So when Mapbox gives fewer than this, we synthesise genuine
# alternatives by routing through waypoints offset perpendicular to the
# straight line, nudging the path onto parallel streets (Melbourne's CBD is a
# grid, so these are real walkable options, not invented ones). Each variant
# is a valid Mapbox-computed route that then scores independently against the
# live sensor network.
TARGET_ROUTE_COUNT = 3

# How far off the direct line to push the via waypoint, as a fraction of the
# straight-line origin→destination distance, clamped to a sensible metre range.
OFFSET_FRACTION = 0.18
MIN_OFFSET_METRES = 150
MAX_OFFSET_METRES = 500

# Reject a synthesised alternative that detours to more than this multiple of
# the direct route's length — beyond it the "parallel street" has become an
# absurd loop that no one would actually walk.
MAX_DETOUR_RATIO = 1.8

# Two routes whose sampled paths sit within this average distance of each
# other are treated as the same route (the offset waypoint just snapped back
# onto the direct path) and de-duplicated.
SIMILARITY_THRESHOLD_METRES = 25


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


def _fetch_routes(origin, destination, access_token, via=None, alternatives=False):
    """One call to Mapbox Directions, parsed into our route shape.

    `via`, when given, forces the path through an intermediate waypoint —
    that's how we shift a synthesised alternative onto a parallel street."""
    points = [origin, via, destination] if via else [origin, destination]
    coordinates = ";".join(_coordinate_string(point) for point in points)
    url = MAPBOX_DIRECTIONS_URL.format(coordinates=coordinates)

    try:
        response = requests.get(
            url,
            params={
                "alternatives": "true" if alternatives else "false",
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

        raw_steps = []
        for leg in route.get("legs", []):
            for step in leg.get("steps", []):
                maneuver = step.get("maneuver", {})
                raw_steps.append({
                    "instruction": maneuver.get("instruction", ""),
                    "maneuver": maneuver.get("type"),
                    "distanceMeters": step.get("distance", 0),
                })

        # Routing through an intermediate via waypoint makes Mapbox treat it
        # as a stopover, injecting a spurious "you have arrived / depart"
        # pair mid-route. Drop those non-terminal arrive/depart steps so the
        # turn-by-turn reads as one continuous walk.
        steps = [
            step
            for index, step in enumerate(raw_steps)
            if (index == 0 or index == len(raw_steps) - 1)
            or step["maneuver"] not in ("arrive", "depart")
        ]

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


def _offset_waypoints(origin, destination):
    """Two waypoints offset perpendicular to the origin→destination line, one
    to each side, used to pull synthesised alternatives onto parallel streets."""
    mid_lat = (origin["lat"] + destination["lat"]) / 2
    mid_lng = (origin["lng"] + destination["lng"]) / 2
    reference_lat = radians(mid_lat)
    metres_per_degree_lng = METRES_PER_DEGREE_LAT * cos(reference_lat)

    east = (destination["lng"] - origin["lng"]) * metres_per_degree_lng
    north = (destination["lat"] - origin["lat"]) * METRES_PER_DEGREE_LAT
    straight_distance = hypot(east, north)

    if straight_distance == 0:
        return []

    perpendicular_east = -north / straight_distance
    perpendicular_north = east / straight_distance
    offset_metres = max(
        MIN_OFFSET_METRES,
        min(MAX_OFFSET_METRES, straight_distance * OFFSET_FRACTION),
    )

    waypoints = []
    for sign in (1, -1):
        offset_east = perpendicular_east * offset_metres * sign
        offset_north = perpendicular_north * offset_metres * sign
        waypoints.append({
            "lat": mid_lat + offset_north / METRES_PER_DEGREE_LAT,
            "lng": mid_lng + offset_east / metres_per_degree_lng,
        })

    return waypoints


def _sample_points(encoded_polyline, count=8):
    try:
        points = polyline.decode(encoded_polyline or "")
    except (TypeError, ValueError, IndexError):
        return []

    if len(points) <= count:
        return points

    step = (len(points) - 1) / (count - 1)
    return [points[round(i * step)] for i in range(count)]


def _metres_between(a, b):
    reference_lat = radians((a[0] + b[0]) / 2)
    east = (b[1] - a[1]) * METRES_PER_DEGREE_LAT * cos(reference_lat)
    north = (b[0] - a[0]) * METRES_PER_DEGREE_LAT
    return hypot(east, north)


def _average_nearest(from_points, to_points):
    return sum(
        min(_metres_between(point, other) for other in to_points)
        for point in from_points
    ) / len(from_points)


def _routes_are_similar(polyline_a, polyline_b):
    """True when two paths trace essentially the same streets — a symmetric
    average-nearest-neighbour distance under the threshold. Used to drop a
    synthesised alternative that just snapped back onto an existing route."""
    a = _sample_points(polyline_a)
    b = _sample_points(polyline_b)
    if not a or not b:
        return False

    divergence = (_average_nearest(a, b) + _average_nearest(b, a)) / 2
    return divergence < SIMILARITY_THRESHOLD_METRES


def get_mapbox_routes(origin, destination):
    access_token = os.getenv("MAPBOX_ACCESS_TOKEN")

    if not access_token:
        raise MapboxRoutesConfigurationError(
            "MAPBOX_ACCESS_TOKEN is not configured on the backend."
        )

    routes = _fetch_routes(origin, destination, access_token, alternatives=True)

    if not routes:
        raise MapboxRoutesProviderError(
            "Mapbox Directions returned no route."
        )

    if len(routes) < TARGET_ROUTE_COUNT:
        waypoints = _offset_waypoints(origin, destination)

        def _safe_variant(waypoint):
            # A synthesised alternative failing (odd waypoint, no path) must
            # never take down the request — we already have the real route.
            try:
                return _fetch_routes(origin, destination, access_token, via=waypoint)
            except MapboxRoutesProviderError:
                return []

        variant_lists = []
        if waypoints:
            with ThreadPoolExecutor(max_workers=len(waypoints)) as pool:
                variant_lists = list(pool.map(_safe_variant, waypoints))

        base_distance = routes[0]["distanceMeters"]
        for variants in variant_lists:
            if len(routes) >= TARGET_ROUTE_COUNT:
                break
            for variant in variants:
                if variant["distanceMeters"] > base_distance * MAX_DETOUR_RATIO:
                    continue
                if any(
                    _routes_are_similar(variant["polyline"], existing["polyline"])
                    for existing in routes
                ):
                    continue
                routes.append(variant)
                break

    return routes[:TARGET_ROUTE_COUNT]
