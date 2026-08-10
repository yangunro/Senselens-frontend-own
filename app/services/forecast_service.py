import json
import math
import os
from datetime import date, datetime, time, timedelta
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import text

from app.database import engine


MELBOURNE_TIMEZONE = ZoneInfo("Australia/Melbourne")
MODEL_REFERENCE_DATE = date(2025, 1, 1)
MODEL_VERSION = "pedestrian-linear-v1"
MODEL_FEATURE_NAMES = [
    "intercept",
    "trend_years",
    "hour_sin",
    "hour_cos",
    "weekday_sin",
    "weekday_cos",
    "is_weekend",
]
DEFAULT_MODEL_PATH = (
    Path(__file__).resolve().parent.parent
    / "model_artifacts"
    / "pedestrian_forecast_linear_v1.json"
)
MAX_FORECAST_HOURS = 3


class ForecastModelUnavailable(RuntimeError):
    pass


def build_model_features(value):
    """Build the calendar features used by training and prediction."""
    if isinstance(value, datetime):
        local_value = value
        if local_value.tzinfo is not None:
            local_value = local_value.astimezone(MELBOURNE_TIMEZONE)
        sensing_date = local_value.date()
        hour = local_value.hour
    else:
        sensing_date, hour = value

    hour_phase = 2 * math.pi * hour / 24
    weekday_phase = 2 * math.pi * sensing_date.weekday() / 7

    return [
        1.0,
        (sensing_date - MODEL_REFERENCE_DATE).days / 365.25,
        math.sin(hour_phase),
        math.cos(hour_phase),
        math.sin(weekday_phase),
        math.cos(weekday_phase),
        1.0 if sensing_date.weekday() >= 5 else 0.0,
    ]


def _model_path():
    configured_path = os.getenv("PEDESTRIAN_FORECAST_MODEL_PATH")
    return Path(configured_path) if configured_path else DEFAULT_MODEL_PATH


@lru_cache(maxsize=1)
def load_forecast_model():
    path = _model_path()

    if not path.exists():
        raise ForecastModelUnavailable(
            "The pedestrian forecast model artifact is not deployed."
        )

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ForecastModelUnavailable(
            "The pedestrian forecast model artifact is invalid."
        ) from error

    if (
        payload.get("modelVersion") != MODEL_VERSION
        or payload.get("features") != MODEL_FEATURE_NAMES
        or not payload.get("sensorModels")
        or not payload.get("globalModel")
    ):
        raise ForecastModelUnavailable(
            "The pedestrian forecast model artifact is incompatible."
        )

    return payload


def _predict(coefficients, features):
    prediction = sum(
        coefficient * feature
        for coefficient, feature in zip(coefficients, features)
    )
    return max(0.0, prediction)


def classify_prediction(predicted_count):
    """Map rounded counts/minute to US-2.2 crowd-risk bands."""
    rounded_count = max(0, int(math.floor(predicted_count + 0.5)))

    if rounded_count <= 5:
        return {
            "level": "low",
            "levelLabel": "LOW SENSORY",
            "predictedCountPerMinute": rounded_count,
        }

    if rounded_count < 15:
        return {
            "level": "medium",
            "levelLabel": "MEDIUM SENSORY",
            "predictedCountPerMinute": rounded_count,
        }

    return {
        "level": "high",
        "levelLabel": "HIGH SENSORY",
        "predictedCountPerMinute": rounded_count,
    }


def _normalise_now(now):
    if now is None:
        return datetime.now(MELBOURNE_TIMEZONE)

    if now.tzinfo is None:
        return now.replace(tzinfo=MELBOURNE_TIMEZONE)

    return now.astimezone(MELBOURNE_TIMEZONE)


def _forecast_times(now, horizon_hours):
    local_now = _normalise_now(now)
    first_hour = local_now.replace(
        minute=0,
        second=0,
        microsecond=0,
    ) + timedelta(hours=1)

    return [
        first_hour + timedelta(hours=offset)
        for offset in range(horizon_hours)
    ]


def _sensor_model(model, sensor_id):
    return model["sensorModels"].get(
        str(sensor_id),
        model["globalModel"],
    )


def _predict_sensor(sensor, forecast_at, model):
    sensor_model = _sensor_model(model, sensor["sensorId"])
    predicted_count = _predict(
        sensor_model["coefficients"],
        build_model_features(forecast_at),
    )
    band = classify_prediction(predicted_count)

    return {
        "sensorId": sensor["sensorId"],
        "name": sensor.get("name") or f"Sensor {sensor['sensorId']}",
        "lat": sensor.get("lat"),
        "lng": sensor.get("lng"),
        **band,
        "modelScope": (
            "sensor"
            if str(sensor["sensorId"]) in model["sensorModels"]
            else "global"
        ),
    }


def _level_rank(level):
    return {
        "low": 0,
        "medium": 1,
        "high": 2,
    }[level]


def _forecast_basis(level, prediction, high_risk_count):
    predicted_count = prediction["predictedCountPerMinute"]

    if level == "high":
        return (
            f"{high_risk_count} route sensor area(s) are predicted to reach "
            f"high crowd activity; the highest estimate is {predicted_count} "
            "pedestrians per minute."
        )

    if level == "medium":
        return (
            "No route sensor area is predicted to be highly crowded in the "
            f"next hour; the highest estimate is {predicted_count} pedestrians "
            "per minute."
        )

    return (
        "Route sensor areas are predicted to remain relatively calm in the "
        f"next hour; the highest estimate is {predicted_count} pedestrians "
        "per minute."
    )


def build_pedestrian_forecast(
    sensors,
    *,
    route_id=None,
    horizon_hours=MAX_FORECAST_HOURS,
    now=None,
    data_as_of=None,
):
    if not 1 <= horizon_hours <= MAX_FORECAST_HOURS:
        raise ValueError(
            f"horizon_hours must be between 1 and {MAX_FORECAST_HOURS}."
        )

    usable_sensors = [
        sensor
        for sensor in sensors
        if sensor.get("sensorId") is not None
    ]

    if not usable_sensors:
        return None

    model = load_forecast_model()
    generated_at = _normalise_now(now)
    forecasts = []
    alerts = []

    for hours_ahead, forecast_at in enumerate(
        _forecast_times(generated_at, horizon_hours),
        start=1,
    ):
        predictions = [
            _predict_sensor(sensor, forecast_at, model)
            for sensor in usable_sensors
        ]
        predictions.sort(
            key=lambda item: item["predictedCountPerMinute"],
            reverse=True,
        )
        highest = predictions[0]
        high_risk = [
            prediction
            for prediction in predictions
            if prediction["level"] == "high"
        ]

        forecasts.append({
            "hoursAhead": hours_ahead,
            "forecastAt": forecast_at.isoformat(),
            "level": highest["level"],
            "levelLabel": highest["levelLabel"],
            "maximumPredictedCountPerMinute": (
                highest["predictedCountPerMinute"]
            ),
            "sensorCount": len(predictions),
            "highRiskSensorCount": len(high_risk),
            "sensors": predictions,
        })

        for prediction in high_risk:
            alerts.append({
                "type": "predictive_crowd",
                "level": "high",
                "title": "HIGH CROWD ACTIVITY PREDICTED",
                "message": (
                    f"{prediction['name']} may reach "
                    f"{prediction['predictedCountPerMinute']} pedestrians "
                    f"per minute in about {hours_ahead} hour(s)."
                ),
                "hoursAhead": hours_ahead,
                "forecastAt": forecast_at.isoformat(),
                **prediction,
            })

    next_hour = forecasts[0]
    next_hour_highest = next_hour["sensors"][0]
    highest_horizon = max(
        forecasts,
        key=lambda item: (
            _level_rank(item["level"]),
            item["maximumPredictedCountPerMinute"],
        ),
    )
    next_hour_basis = _forecast_basis(
        next_hour["level"],
        next_hour_highest,
        next_hour["highRiskSensorCount"],
    )

    return {
        "routeId": str(route_id) if route_id is not None else None,
        # Compatibility fields consumed by the current map-page banner.
        "sensoryIndicator": next_hour["levelLabel"],
        "level": next_hour["level"],
        "levelLabel": next_hour["levelLabel"],
        "basis": next_hour_basis,
        "forecastAt": next_hour["forecastAt"],
        "predictedCountPerMinute": (
            next_hour["maximumPredictedCountPerMinute"]
        ),
        # Detailed US-2.2 response for map markers and future-hour alerts.
        "generatedAt": generated_at.isoformat(),
        "dataAsOf": data_as_of,
        "horizonHours": horizon_hours,
        "hasPredictiveAlert": bool(alerts),
        "highestForecastLevel": highest_horizon["level"],
        "model": {
            "modelType": model["modelType"],
            "modelVersion": model["modelVersion"],
            "trainedAt": model["trainedAt"],
            "target": model["target"],
            "trainingRange": model["trainingRange"],
        },
        "forecasts": forecasts,
        "alerts": alerts,
    }


def get_active_sensor_forecast(horizon_hours=MAX_FORECAST_HOURS, now=None):
    query = text("""
        SELECT
            sl."SensorID" AS sensor_id,
            sl."SensorDescription" AS sensor_name,
            sl."Lat" AS lat,
            sl."Lng" AS lng,
            latest."DateTimeMinute" AS observed_at
        FROM "SensorLocation" sl
        LEFT JOIN LATERAL (
            SELECT pc."DateTimeMinute"
            FROM "PedestrianCount" pc
            WHERE pc."SensorID" = sl."SensorID"
            ORDER BY pc."DateTimeMinute" DESC
            LIMIT 1
        ) latest ON TRUE
        WHERE sl."Status" = 'A'
          AND sl."Lat" IS NOT NULL
          AND sl."Lng" IS NOT NULL
        ORDER BY sl."SensorID";
    """)

    with engine.connect() as conn:
        rows = conn.execute(query).mappings().all()

    observed_values = [
        row["observed_at"]
        for row in rows
        if row["observed_at"] is not None
    ]
    data_as_of = max(observed_values).isoformat() if observed_values else None

    return build_pedestrian_forecast(
        [
            {
                "sensorId": row["sensor_id"],
                "name": row["sensor_name"],
                "lat": float(row["lat"]),
                "lng": float(row["lng"]),
            }
            for row in rows
        ],
        horizon_hours=horizon_hours,
        now=now,
        data_as_of=data_as_of,
    )


def historical_datetime(sensing_date, hour):
    """Convert one database history row to Melbourne local time."""
    return datetime.combine(
        sensing_date,
        time(hour=int(hour)),
        tzinfo=MELBOURNE_TIMEZONE,
    )
