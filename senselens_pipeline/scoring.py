from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable


@dataclass(frozen=True)
class Sensitivities:
    crowd: int
    light: int
    construction: int

    def __post_init__(self) -> None:
        for name, value in (
            ("crowd", self.crowd),
            ("light", self.light),
            ("construction", self.construction),
        ):
            if not 1 <= value <= 5:
                raise ValueError(f"{name} sensitivity must be between 1 and 5")


def _calm_score(values: list[float | None], index: int) -> float:
    available = [value for value in values if value is not None]
    value = values[index]
    if value is None or not available:
        return 50.0
    low, high = min(available), max(available)
    if high == low:
        return 100.0
    return 100.0 * (high - value) / (high - low)


def _benefit_score(values: list[float | None], index: int) -> float:
    available = [value for value in values if value is not None]
    value = values[index]
    if value is None or not available:
        return 50.0
    low, high = min(available), max(available)
    if high == low:
        return 100.0
    return 100.0 * (value - low) / (high - low)


def score_routes(
    route_features: Iterable[dict[str, Any]],
    sensitivities: Sensitivities,
    *,
    max_detour_minutes: float,
    stale_after_minutes: int = 20,
    now_utc: datetime | None = None,
) -> list[dict[str, Any]]:
    """Rank candidate-route feature rows returned by route_factor_inputs.

    Every component is converted to 0-100, where higher means more suitable.
    Missing observations receive a neutral 50 and lower confidence; they are
    never replaced with fabricated measurements.
    """
    routes = [dict(route) for route in route_features]
    if not routes:
        return []
    now_utc = (now_utc or datetime.now(timezone.utc)).astimezone(timezone.utc)

    eligible = [route for route in routes if float(route["detour_minutes"]) <= max_detour_minutes]
    if not eligible:
        return []

    crowd_exposure: list[float | None] = []
    light_exposure: list[float | None] = []
    construction_exposure: list[float | None] = []
    nearby_places: list[float | None] = []
    durations: list[float | None] = []
    live_is_fresh: list[bool] = []

    for route in eligible:
        current = route.get("latest_minute_average")
        historical = route.get("historical_hour_average")
        timestamp = route.get("latest_minute_timestamp_utc")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        fresh = bool(
            current is not None
            and isinstance(timestamp, datetime)
            and timestamp.tzinfo is not None
            and 0 <= (now_utc - timestamp.astimezone(timezone.utc)).total_seconds()
            <= stale_after_minutes * 60
        )
        live_is_fresh.append(fresh)
        if fresh and historical not in (None, 0):
            crowd_exposure.append(float(current) / max(float(historical) / 60.0, 0.01))
        elif historical is not None:
            crowd_exposure.append(float(historical))
        else:
            crowd_exposure.append(None)
        light_exposure.append(None if route.get("average_lux") is None else float(route["average_lux"]))
        count = float(route.get("under_construction_count") or 0)
        nearest = route.get("nearest_construction_m")
        proximity = 0.0 if nearest is None else max(0.0, 1.0 - float(nearest) / 100.0)
        construction_exposure.append(count + proximity)
        nearby_places.append(float(route.get("nearby_place_count") or 0))
        durations.append(float(route["duration_seconds"]))

    sensitivity_total = sensitivities.crowd + sensitivities.light + sensitivities.construction
    weights = {
        "crowd": 0.75 * sensitivities.crowd / sensitivity_total,
        "lighting": 0.75 * sensitivities.light / sensitivity_total,
        "development": 0.75 * sensitivities.construction / sensitivity_total,
        "nearby_place": 0.10,
        "travel_time": 0.15,
    }

    scored: list[dict[str, Any]] = []
    for index, route in enumerate(eligible):
        components = {
            "crowd_score": _calm_score(crowd_exposure, index),
            "lighting_score": _calm_score(light_exposure, index),
            "development_score": _calm_score(construction_exposure, index),
            "nearby_place_score": _benefit_score(nearby_places, index),
            "travel_time_score": _calm_score(durations, index),
        }
        overall = (
            weights["crowd"] * components["crowd_score"]
            + weights["lighting"] * components["lighting_score"]
            + weights["development"] * components["development_score"]
            + weights["nearby_place"] * components["nearby_place_score"]
            + weights["travel_time"] * components["travel_time_score"]
        )
        missing = sum(
            value is None
            for value in (
                crowd_exposure[index],
                light_exposure[index],
                route.get("nearest_construction_m") if route.get("under_construction_count") else 0,
            )
        )
        confidence = "live" if live_is_fresh[index] and missing == 0 else (
            "historical_estimate" if route.get("historical_hour_average") is not None else "limited"
        )
        strongest = sorted(
            (
                ("lower crowd exposure", components["crowd_score"]),
                ("lower light exposure", components["lighting_score"]),
                ("fewer nearby construction indicators", components["development_score"]),
                ("more nearby places", components["nearby_place_score"]),
                ("shorter travel time", components["travel_time_score"]),
            ),
            key=lambda item: item[1],
            reverse=True,
        )[:2]
        explanation = (
            f"Recommended for {strongest[0][0]} and {strongest[1][0]}; "
            f"crowd data confidence is {confidence.replace('_', ' ')}."
        )
        scored.append(
            {
                **route,
                **{name: round(value, 2) for name, value in components.items()},
                "overall_sensory_score": round(overall, 2),
                "data_confidence": confidence,
                "factor_weights": {name: round(value, 4) for name, value in weights.items()},
                "explanation": explanation,
                "scoring_version": "1.0.0",
            }
        )

    return sorted(scored, key=lambda route: (-route["overall_sensory_score"], route["duration_seconds"]))
