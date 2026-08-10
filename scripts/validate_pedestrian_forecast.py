"""Time-based holdout validation for the pedestrian forecast model."""

import argparse
import json
import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import text

from app.database import engine
from app.services.forecast_service import (
    MODEL_FEATURE_NAMES,
    MODEL_VERSION,
    build_model_features,
    classify_prediction,
)
from scripts.train_pedestrian_forecast import (
    LinearStats,
    MINIMUM_SENSOR_SAMPLES,
    fit_model,
)


DEFAULT_REPORT_PATH = (
    Path(__file__).resolve().parent.parent
    / "app"
    / "model_artifacts"
    / "pedestrian_forecast_validation_v1.json"
)
BANDS = ("low", "medium", "high")


class ValidationMetrics:
    def __init__(self):
        self.count = 0
        self.absolute_error = 0.0
        self.squared_error = 0.0
        self.sum_actual = 0.0
        self.sum_actual_squared = 0.0
        self.confusion = {
            actual: {predicted: 0 for predicted in BANDS}
            for actual in BANDS
        }

    def add(self, actual, predicted):
        error = predicted - actual
        self.count += 1
        self.absolute_error += abs(error)
        self.squared_error += error * error
        self.sum_actual += actual
        self.sum_actual_squared += actual * actual
        actual_band = classify_prediction(actual)["level"]
        predicted_band = classify_prediction(predicted)["level"]
        self.confusion[actual_band][predicted_band] += 1

    def summary(self):
        if self.count == 0:
            return None

        total_variance = (
            self.sum_actual_squared
            - self.sum_actual * self.sum_actual / self.count
        )
        true_positive = {
            band: self.confusion[band][band]
            for band in BANDS
        }
        actual_total = {
            band: sum(self.confusion[band].values())
            for band in BANDS
        }
        predicted_total = {
            band: sum(
                self.confusion[actual][band]
                for actual in BANDS
            )
            for band in BANDS
        }
        precision = {}
        recall = {}
        f1 = {}

        for band in BANDS:
            precision[band] = (
                true_positive[band] / predicted_total[band]
                if predicted_total[band]
                else 0.0
            )
            recall[band] = (
                true_positive[band] / actual_total[band]
                if actual_total[band]
                else 0.0
            )
            denominator = precision[band] + recall[band]
            f1[band] = (
                2 * precision[band] * recall[band] / denominator
                if denominator
                else 0.0
            )

        return {
            "rows": self.count,
            "mae": round(self.absolute_error / self.count, 4),
            "rmse": round(math.sqrt(self.squared_error / self.count), 4),
            "r2": (
                round(1 - self.squared_error / total_variance, 4)
                if total_variance > 0
                else None
            ),
            "bandAccuracy": round(
                sum(true_positive.values()) / self.count,
                4,
            ),
            "macroF1": round(sum(f1.values()) / len(BANDS), 4),
            "highPrecision": round(precision["high"], 4),
            "highRecall": round(recall["high"], 4),
            "actualBandRows": actual_total,
            "predictedBandRows": predicted_total,
            "confusionMatrix": self.confusion,
        }


def _percentile(values, fraction):
    ordered = sorted(values)
    index = round((len(ordered) - 1) * fraction)
    return round(ordered[index], 4)


def _distribution(values):
    return {
        "minimum": round(min(values), 4),
        "p25": _percentile(values, 0.25),
        "median": _percentile(values, 0.50),
        "p75": _percentile(values, 0.75),
        "maximum": round(max(values), 4),
    }


def _predict(coefficients, features):
    return max(
        0.0,
        sum(
            coefficient * feature
            for coefficient, feature in zip(coefficients, features)
        ),
    )


def _latest_history_date():
    query = text("""
        SELECT MAX("SensingDate")
        FROM "PedestrianHourlyHistory"
        WHERE "HourlyCount" IS NOT NULL
          AND "HourlyCount" >= 0;
    """)

    with engine.connect() as conn:
        return conn.execute(query).scalar_one()


def validate_model(holdout_days=42):
    if holdout_days < 7:
        raise ValueError("holdout_days must be at least 7.")

    latest_date = _latest_history_date()

    if latest_date is None:
        raise RuntimeError("No pedestrian history is available.")

    validation_start = latest_date - timedelta(days=holdout_days - 1)
    feature_count = len(MODEL_FEATURE_NAMES)
    per_sensor_stats = defaultdict(lambda: LinearStats(feature_count))
    global_stats = LinearStats(feature_count)
    calendar_totals = defaultdict(lambda: [0.0, 0])
    sensor_totals = defaultdict(lambda: [0.0, 0])

    training_query = text("""
        SELECT
            "SensorID" AS sensor_id,
            "SensingDate" AS sensing_date,
            "HourDay" AS hour_day,
            "HourlyCount" AS hourly_count
        FROM "PedestrianHourlyHistory"
        WHERE "HourlyCount" IS NOT NULL
          AND "HourlyCount" >= 0
          AND "SensingDate" < :validation_start;
    """)

    with engine.connect().execution_options(stream_results=True) as conn:
        rows = conn.execute(
            training_query,
            {"validation_start": validation_start},
        ).yield_per(10_000)

        for row in rows:
            sensor_id = int(row.sensor_id)
            hour = int(row.hour_day)
            target = float(row.hourly_count) / 60.0
            features = build_model_features((row.sensing_date, hour))
            per_sensor_stats[sensor_id].add(features, target)
            global_stats.add(features, target)
            calendar_key = (
                sensor_id,
                row.sensing_date.weekday(),
                hour,
            )
            calendar_totals[calendar_key][0] += target
            calendar_totals[calendar_key][1] += 1
            sensor_totals[sensor_id][0] += target
            sensor_totals[sensor_id][1] += 1

    global_model = fit_model(global_stats)
    sensor_models = {
        sensor_id: fit_model(stats)
        for sensor_id, stats in per_sensor_stats.items()
        if stats.count >= MINIMUM_SENSOR_SAMPLES
    }
    global_mean = global_stats.sum_y / global_stats.count
    model_metrics = ValidationMetrics()
    baseline_metrics = ValidationMetrics()
    per_sensor_metrics = defaultdict(ValidationMetrics)
    fallback_rows = 0

    validation_query = text("""
        SELECT
            "SensorID" AS sensor_id,
            "SensingDate" AS sensing_date,
            "HourDay" AS hour_day,
            "HourlyCount" AS hourly_count
        FROM "PedestrianHourlyHistory"
        WHERE "HourlyCount" IS NOT NULL
          AND "HourlyCount" >= 0
          AND "SensingDate" >= :validation_start
        ORDER BY "SensingDate", "HourDay", "SensorID";
    """)

    with engine.connect().execution_options(stream_results=True) as conn:
        rows = conn.execute(
            validation_query,
            {"validation_start": validation_start},
        ).yield_per(10_000)

        for row in rows:
            sensor_id = int(row.sensor_id)
            hour = int(row.hour_day)
            actual = float(row.hourly_count) / 60.0
            features = build_model_features((row.sensing_date, hour))
            sensor_model = sensor_models.get(sensor_id)

            if sensor_model is None:
                sensor_model = global_model
                fallback_rows += 1

            predicted = _predict(sensor_model["coefficients"], features)
            calendar_key = (
                sensor_id,
                row.sensing_date.weekday(),
                hour,
            )
            total, count = calendar_totals.get(calendar_key, (0.0, 0))

            if count:
                baseline = total / count
            else:
                sensor_total, sensor_count = sensor_totals.get(
                    sensor_id,
                    (0.0, 0),
                )
                baseline = (
                    sensor_total / sensor_count
                    if sensor_count
                    else global_mean
                )

            model_metrics.add(actual, predicted)
            baseline_metrics.add(actual, baseline)
            per_sensor_metrics[sensor_id].add(actual, predicted)

    model_summary = model_metrics.summary()
    baseline_summary = baseline_metrics.summary()
    sensor_summaries = [
        metrics.summary()
        for metrics in per_sensor_metrics.values()
        if metrics.count > 0
    ]
    rmse_improvement = (
        (
            baseline_summary["rmse"] - model_summary["rmse"]
        )
        / baseline_summary["rmse"]
        * 100
        if baseline_summary["rmse"]
        else None
    )
    mae_improvement = (
        (
            baseline_summary["mae"] - model_summary["mae"]
        )
        / baseline_summary["mae"]
        * 100
        if baseline_summary["mae"]
        else None
    )

    return {
        "schemaVersion": 1,
        "modelVersion": MODEL_VERSION,
        "validatedAt": datetime.now(timezone.utc).isoformat(),
        "method": "chronological holdout retraining",
        "split": {
            "trainingEnd": (validation_start - timedelta(days=1)).isoformat(),
            "validationStart": validation_start.isoformat(),
            "validationEnd": latest_date.isoformat(),
            "holdoutDays": holdout_days,
            "trainingRows": global_stats.count,
            "validationRows": model_metrics.count,
            "trainedSensorModels": len(sensor_models),
            "globalFallbackValidationRows": fallback_rows,
        },
        "linearRegression": model_summary,
        "historicalWeekdayHourBaseline": baseline_summary,
        "comparison": {
            "rmseImprovementPercent": round(rmse_improvement, 2),
            "maeImprovementPercent": round(mae_improvement, 2),
        },
        "perSensorLinearRegression": {
            "sensorCount": len(sensor_summaries),
            "rmse": _distribution([
                summary["rmse"]
                for summary in sensor_summaries
            ]),
            "mae": _distribution([
                summary["mae"]
                for summary in sensor_summaries
            ]),
            "r2": _distribution([
                summary["r2"]
                for summary in sensor_summaries
                if summary["r2"] is not None
            ]),
            "bandAccuracy": _distribution([
                summary["bandAccuracy"]
                for summary in sensor_summaries
            ]),
        },
    }


def main():
    parser = argparse.ArgumentParser(
        description="Validate the forecast model on unseen future dates.",
    )
    parser.add_argument(
        "--holdout-days",
        type=int,
        default=42,
        help="Number of latest calendar days reserved for validation.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help="Validation report JSON path.",
    )
    args = parser.parse_args()
    report = validate_model(args.holdout_days)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    model = report["linearRegression"]
    baseline = report["historicalWeekdayHourBaseline"]
    comparison = report["comparison"]
    print(f"Report written to: {args.output}")
    print(f"Split: {report['split']}")
    print(f"Linear regression: {model}")
    print(f"Historical baseline: {baseline}")
    print(f"Comparison: {comparison}")
    print(
        "Per-sensor distributions: "
        f"{report['perSensorLinearRegression']}"
    )


if __name__ == "__main__":
    main()
