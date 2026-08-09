import math


EARTH_RADIUS_M = 6371000


def latlon_to_local_meters(lat, lon, ref_lat, ref_lon):
    """
    Convert (lat, lon) to approximate local (x, y) metres relative
    to (ref_lat, ref_lon), using an equirectangular projection.

    Accurate to within a few metres at city-block scale (the CBD
    is ~2km across); not meant for long distances.
    """

    x = (
        math.radians(lon - ref_lon)
        * math.cos(math.radians((lat + ref_lat) / 2))
        * EARTH_RADIUS_M
    )

    y = math.radians(lat - ref_lat) * EARTH_RADIUS_M

    return x, y


def distance_point_to_segment_m(point, seg_start, seg_end):
    """
    Shortest distance, in metres, from a (lat, lon) point to the
    straight-line segment between two (lat, lon) points.
    """

    ax, ay = 0.0, 0.0

    bx, by = latlon_to_local_meters(
        seg_end[0], seg_end[1], seg_start[0], seg_start[1],
    )

    px, py = latlon_to_local_meters(
        point[0], point[1], seg_start[0], seg_start[1],
    )

    dx = bx - ax
    dy = by - ay

    length_sq = dx * dx + dy * dy

    if length_sq == 0:
        t = 0.0
    else:
        t = ((px - ax) * dx + (py - ay) * dy) / length_sq
        t = max(0.0, min(1.0, t))

    closest_x = ax + t * dx
    closest_y = ay + t * dy

    return math.hypot(px - closest_x, py - closest_y)
