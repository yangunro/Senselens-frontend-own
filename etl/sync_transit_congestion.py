from datetime import datetime, timezone

from etl.geo import distance_point_to_segment_m
from etl.repository import bulk_insert_transit_signals, get_all_routes
from etl.transit_client import fetch_vehicle_positions


# A vehicle counts as "near" a route if it is within this many
# metres of the straight line between the route's origin and
# destination. Route currently stores only origin/destination
# points, not a real path polyline, so this is a deliberate
# straight-line-corridor approximation -- not true path matching.
# 150m is roughly one CBD block; close enough that a pedestrian on
# the route would plausibly notice a crowded vehicle.
MATCH_RADIUS_M = 150

# GTFS-Realtime VehiclePosition.OccupancyStatus (official enum,
# confirmed against gtfs-realtime-bindings 2.2.0) -> this
# project's occupancy_status DB enum. NO_DATA_AVAILABLE (7) has no
# honest mapping and is skipped rather than guessed.
OCCUPANCY_STATUS_MAP = {
    0: "ManySeats",       # EMPTY
    1: "ManySeats",       # MANY_SEATS_AVAILABLE
    2: "FewSeats",        # FEW_SEATS_AVAILABLE
    3: "Standing",        # STANDING_ROOM_ONLY
    4: "Standing",        # CRUSHED_STANDING_ROOM_ONLY
    5: "Full",            # FULL
    6: "NotAccepting",    # NOT_ACCEPTING_PASSENGERS
    8: "NotAccepting",    # NOT_BOARDABLE
}

# GTFS-Realtime has no direct "congestion level" field for buses/
# trams/trains. CongestionLevel is derived from the vehicle's real
# reported occupancy as a documented heuristic, not invented
# independently of source data.
CONGESTION_FROM_OCCUPANCY = {
    "ManySeats": "Smooth",
    "FewSeats": "StopGo",
    "Standing": "Congested",
    "Full": "Severe",
    "NotAccepting": "Severe",
}


def extract_vehicle_observations(feed):
    observations = []

    for entity in feed.entity:

        if not entity.HasField("vehicle"):
            continue

        vehicle = entity.vehicle

        if not vehicle.HasField("position"):
            continue

        if not vehicle.HasField("occupancy_status"):
            continue

        occupancy_status = OCCUPANCY_STATUS_MAP.get(
            vehicle.occupancy_status
        )

        if occupancy_status is None:
            continue

        occupancy_pct = None

        if vehicle.HasField("occupancy_percentage"):
            occupancy_pct = vehicle.occupancy_percentage

        if vehicle.HasField("timestamp") and vehicle.timestamp:
            observed_at = datetime.fromtimestamp(
                vehicle.timestamp, tz=timezone.utc,
            )
        else:
            observed_at = datetime.now(timezone.utc)

        observations.append({
            "lat": vehicle.position.latitude,
            "lon": vehicle.position.longitude,
            "occupancy_status": occupancy_status,
            "occupancy_pct": occupancy_pct,
            "observed_at": observed_at,
        })

    return observations


def match_observations_to_routes(observations, routes, mode):
    signals = []

    for obs in observations:

        point = (obs["lat"], obs["lon"])

        for route in routes:

            seg_start = (
                float(route["OriginLat"]),
                float(route["OriginLng"]),
            )

            seg_end = (
                float(route["DestLat"]),
                float(route["DestLng"]),
            )

            distance = distance_point_to_segment_m(
                point, seg_start, seg_end,
            )

            if distance > MATCH_RADIUS_M:
                continue

            signals.append({
                "RouteID": route["RouteID"],
                "VehicleMode": mode,
                "CongestionLevel": CONGESTION_FROM_OCCUPANCY[
                    obs["occupancy_status"]
                ],
                "OccupancyStatus": obs["occupancy_status"],
                "OccupancyPct": obs["occupancy_pct"],
                "ObservedAt": obs["observed_at"],
            })

    return signals


def sync_mode(mode, routes):
    feed = fetch_vehicle_positions(mode)

    observations = extract_vehicle_observations(feed)

    signals = match_observations_to_routes(
        observations, routes, mode,
    )

    return len(observations), signals


def main():

    routes = get_all_routes()

    print(f"Stored routes to match against: {len(routes)}")

    if not routes:
        print("No stored routes. Nothing to match.")
        return

    all_signals = []
    total_observed = 0

    for mode in ("Train", "Tram", "Bus"):

        try:
            observed_count, signals = sync_mode(mode, routes)

        except Exception as error:
            print(f"{mode}: failed - {error}")
            continue

        total_observed += observed_count
        all_signals.extend(signals)

        print(
            f"{mode}: {observed_count} vehicles with occupancy "
            f"data, {len(signals)} matched within "
            f"{MATCH_RADIUS_M}m of a stored route"
        )

    loaded = bulk_insert_transit_signals(all_signals)

    print()
    print("=====================================")
    print("Transit Congestion sync completed")
    print("=====================================")
    print(f"Vehicles observed (all modes): {total_observed}")
    print(f"Signals recorded:              {loaded}")
    print("=====================================")


if __name__ == "__main__":
    main()
