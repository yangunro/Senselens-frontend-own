from bisect import bisect_right
from math import cos, hypot, radians

import polyline


EARTH_RADIUS_METRES = 6_371_000
DEFAULT_SENSOR_RADIUS_METRES = 150


def decode_route(encoded_polyline):
    if not encoded_polyline:
        return []

    try:
        coordinates = polyline.decode(encoded_polyline)
    except (TypeError, ValueError, IndexError):
        return []

    return [
        {"lat": latitude, "lng": longitude}
        for latitude, longitude in coordinates
    ]


def _project(point, reference_latitude):
    latitude = radians(point["lat"])
    longitude = radians(point["lng"])
    reference = radians(reference_latitude)

    return (
        EARTH_RADIUS_METRES * longitude * cos(reference),
        EARTH_RADIUS_METRES * latitude,
    )


def distance_to_segment_metres(point, start, end):
    """Approximate point-to-segment distance using a local projection."""
    reference_latitude = point["lat"]
    point_x, point_y = _project(point, reference_latitude)
    start_x, start_y = _project(start, reference_latitude)
    end_x, end_y = _project(end, reference_latitude)

    delta_x = end_x - start_x
    delta_y = end_y - start_y
    segment_length_squared = delta_x ** 2 + delta_y ** 2

    if segment_length_squared == 0:
        return hypot(point_x - start_x, point_y - start_y)

    ratio = (
        (point_x - start_x) * delta_x
        + (point_y - start_y) * delta_y
    ) / segment_length_squared
    ratio = max(0, min(1, ratio))

    nearest_x = start_x + ratio * delta_x
    nearest_y = start_y + ratio * delta_y

    return hypot(point_x - nearest_x, point_y - nearest_y)


def distance_to_route_metres(point, route_points):
    if not route_points:
        return None

    if len(route_points) == 1:
        return distance_to_segment_metres(
            point,
            route_points[0],
            route_points[0],
        )

    return min(
        distance_to_segment_metres(point, start, end)
        for start, end in zip(route_points, route_points[1:])
    )


def sensors_near_route(
    route_points,
    sensors,
    radius_metres=DEFAULT_SENSOR_RADIUS_METRES,
):
    matched = []

    for sensor in sensors:
        distance = distance_to_route_metres(sensor, route_points)

        if distance is None or distance > radius_metres:
            continue

        matched.append({
            **sensor,
            "distanceFromRouteM": round(distance, 1),
        })

    return sorted(
        matched,
        key=lambda sensor: sensor["distanceFromRouteM"],
    )


def refuges_near_route(
    route_points,
    refuges,
    radius_metres=DEFAULT_SENSOR_RADIUS_METRES,
):
    matched = []

    for refuge in refuges:
        distance = distance_to_route_metres(refuge, route_points)

        if distance is None or distance > radius_metres:
            continue

        matched.append({
            **refuge,
            "distanceFromRouteM": round(distance, 1),
        })

    return sorted(
        matched,
        key=lambda refuge: refuge["distanceFromRouteM"],
    )


def _weighted_average_count(sensors):
    if not sensors:
        return None

    weighted_total = 0
    total_weight = 0

    for sensor in sensors:
        distance = sensor["distanceFromRouteM"]
        weight = 1 / (1 + distance / 50)
        weighted_total += sensor["minuteCount"] * weight
        total_weight += weight

    return weighted_total / total_weight


def _percentile_score(value, reference_values):
    if value is None or not reference_values:
        return None

    ordered = sorted(reference_values)
    rank = bisect_right(ordered, value)

    return round(rank / len(ordered) * 100)


def _score_level(score):
    if score is None:
        return {
            "level": "unknown",
            "levelLabel": "INSUFFICIENT DATA",
        }

    if score < 35:
        return {
            "level": "low",
            "levelLabel": "LOW SENSORY",
        }

    if score < 65:
        return {
            "level": "medium",
            "levelLabel": "MEDIUM SENSORY",
        }

    return {
        "level": "high",
        "levelLabel": "HIGH SENSORY",
    }


def analyse_route(
    route,
    pedestrian_snapshot,
    radius_metres=DEFAULT_SENSOR_RADIUS_METRES,
):
    route_points = decode_route(route.get("polyline"))
    sensors = (
        pedestrian_snapshot.get("sensors", [])
        if pedestrian_snapshot
        else []
    )
    nearby_sensors = sensors_near_route(
        route_points,
        sensors,
        radius_metres,
    )
    route_average = _weighted_average_count(nearby_sensors)
    score = _percentile_score(
        route_average,
        [sensor["minuteCount"] for sensor in sensors],
    )
    level = _score_level(score)

    if score is None:
        description = (
            "No reporting pedestrian sensor is close enough to "
            "score this route reliably."
        )
        factors = []
    else:
        activity_label = {
            "low": "Lower pedestrian activity",
            "medium": "Moderate pedestrian activity",
            "high": "Higher pedestrian activity",
        }[level["level"]]
        description = (
            f"Crowd exposure is at approximately the {score}th "
            "percentile of current reporting sensors."
        )
        factors = [{
            "type": "crowd",
            "icon": "users",
            "label": activity_label,
            "score": score,
            "matchedSensorCount": len(nearby_sensors),
        }]

    return {
        **route,
        **level,
        "sensoryScore": score,
        "description": description,
        "matchedSensorCount": len(nearby_sensors),
        "routeAverageCount": (
            round(route_average, 2)
            if route_average is not None
            else None
        ),
        "pedestrianObservedAt": (
            pedestrian_snapshot.get("observedAt")
            if pedestrian_snapshot
            else None
        ),
        "sensorRadiusM": radius_metres,
        "nearbySensors": nearby_sensors,
        "factors": factors,
    }
