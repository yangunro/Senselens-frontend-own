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


DEFAULT_CONSTRUCTION_RADIUS_METRES = 75


def construction_sites_near_route(
    route_points,
    sites,
    radius_metres=DEFAULT_CONSTRUCTION_RADIUS_METRES,
):
    matched = []

    for site in sites:
        distance = distance_to_route_metres(site, route_points)

        if distance is None or distance > radius_metres:
            continue

        matched.append({
            **site,
            "distanceFromRouteM": round(distance, 1),
        })

    return sorted(
        matched,
        key=lambda site: site["distanceFromRouteM"],
    )


DEFAULT_STREETLIGHT_RADIUS_METRES = 40

# Melbourne footpath lighting sits well under 20 lux even on well-lit
# streets — these bands are calibrated to the city's own data (citywide
# average is ~31 lux, min 0.2, max 99), not a general lighting-design
# standard, so "well-lit" here means well-lit relative to Melbourne's own
# streetlight network rather than an absolute engineering benchmark.
DIM_LUX_THRESHOLD = 10
BRIGHT_LUX_THRESHOLD = 30


def route_bounding_box(route_points):
    if not route_points:
        return None

    lats = [point["lat"] for point in route_points]
    lngs = [point["lng"] for point in route_points]

    return min(lats), max(lats), min(lngs), max(lngs)


MAX_LIGHTING_SAMPLE_POINTS = 20


def _decimate(points, max_points=MAX_LIGHTING_SAMPLE_POINTS):
    """A dense Google polyline can carry 80+ points, and Melbourne's
    streetlight coverage is dense enough that a route's bounding box often
    contains thousands of candidates — matching every point against every
    light is too slow for a live request. An average-lux read doesn't need
    metre-precision, so thin the route down first; this is only used for
    the lighting pass, never for anything distance-sensitive like alerts."""
    if len(points) <= max_points:
        return points

    step = (len(points) - 1) / (max_points - 1)
    return [points[round(i * step)] for i in range(max_points)]


# Degrees-per-metre at Melbourne's latitude, used only as a cheap first-pass
# reject before the precise (and much more expensive) trig-based distance
# check — a CBD bounding box can hold thousands of streetlights, so this
# pre-filter is what keeps lighting_summary() fast enough for a live request.
METRES_PER_DEGREE_LAT = 111_320
METRES_PER_DEGREE_LNG = 87_900


def lights_near_route(
    route_points,
    lights,
    radius_metres=DEFAULT_STREETLIGHT_RADIUS_METRES,
):
    sample_points = _decimate(route_points)
    lat_pad = radius_metres / METRES_PER_DEGREE_LAT
    lng_pad = radius_metres / METRES_PER_DEGREE_LNG

    # Bounding box per segment, not per vertex — a light can sit near the
    # middle of a long segment while being far from both of its endpoints,
    # so checking only vertex proximity silently drops real matches.
    segments = list(zip(sample_points, sample_points[1:])) if len(sample_points) > 1 else []
    segment_boxes = [
        (
            min(start["lat"], end["lat"]) - lat_pad,
            max(start["lat"], end["lat"]) + lat_pad,
            min(start["lng"], end["lng"]) - lng_pad,
            max(start["lng"], end["lng"]) + lng_pad,
        )
        for start, end in segments
    ]

    roughly_close = []
    for light in lights:
        for min_lat, max_lat, min_lng, max_lng in segment_boxes:
            if (
                min_lat <= light["lat"] <= max_lat
                and min_lng <= light["lng"] <= max_lng
            ):
                roughly_close.append(light)
                break

    matched = []
    for light in roughly_close:
        distance = distance_to_route_metres(light, sample_points)

        if distance is None or distance > radius_metres:
            continue

        matched.append({
            **light,
            "distanceFromRouteM": round(distance, 1),
        })

    return matched


def lighting_summary(route_points, light_candidates):
    """Average streetlight brightness along a route, and a comfort label
    calibrated to Melbourne's own lux distribution (see thresholds above).

    light_candidates is fetched once per request (see routes_service.get_routes)
    across a bounding box covering every alternative route, not per-route —
    each extra DB round trip added real latency to a live routing request."""
    nearby = lights_near_route(route_points, light_candidates)

    if not nearby:
        return {
            "averageLux": None,
            "matchedLightCount": 0,
            "comfortLabel": None,
        }

    average_lux = sum(light["lux"] for light in nearby) / len(nearby)

    if average_lux < DIM_LUX_THRESHOLD:
        comfort_label = "Dimly lit"
    elif average_lux < BRIGHT_LUX_THRESHOLD:
        comfort_label = "Moderately lit"
    else:
        comfort_label = "Well lit"

    return {
        "averageLux": round(average_lux, 1),
        "matchedLightCount": len(nearby),
        "comfortLabel": comfort_label,
    }


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
    construction_sites=None,
    light_candidates=None,
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
    nearby_construction = construction_sites_near_route(
        route_points,
        construction_sites or [],
    )
    lighting = lighting_summary(route_points, light_candidates or [])
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

    if nearby_construction:
        factors.append({
            "type": "construction",
            "icon": "tool",
            "label": (
                "Passes 1 active construction site"
                if len(nearby_construction) == 1
                else f"Passes {len(nearby_construction)} active construction sites"
            ),
            "matchedSiteCount": len(nearby_construction),
        })

    if lighting["comfortLabel"] is not None:
        factors.append({
            "type": "lighting",
            "icon": "sun",
            "label": f"{lighting['comfortLabel']} path",
            "averageLux": lighting["averageLux"],
        })

    return {
        **route,
        **level,
        "sensoryScore": score,
        "description": description,
        "matchedSensorCount": len(nearby_sensors),
        "hasActiveConstruction": len(nearby_construction) > 0,
        "constructionSitesNearby": len(nearby_construction),
        "averageLux": lighting["averageLux"],
        "lightingComfort": lighting["comfortLabel"],
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
