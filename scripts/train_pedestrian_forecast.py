"""Train per-sensor linear pedestrian forecast models from Supabase history."""

import argparse
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

from app.database import engine
from app.services.forecast_service import (
    DEFAULT_MODEL_PATH,
    MODEL_FEATURE_NAMES,
    MODEL_VERSION,
    build_model_features,
)


MINIMUM_SENSOR_SAMPLES = 24 * 28
RIDGE_STRENGTH = 1e-8


class LinearStats:
    def __init__(self, feature_count):
        self.count = 0
        self.xtx = [
            [0.0 for _ in range(feature_count)]
            for _ in range(feature_count)
        ]
        self.xty = [0.0 for _ in range(feature_count)]
        self.sum_y = 0.0
        self.sum_y_squared = 0.0

    def add(self, features, target):
        self.count += 1
        self.sum_y += target
        self.sum_y_squared += target * target

        for row_index, row_value in enumerate(features):
            self.xty[row_index] += row_value * target

            for column_index, column_value in enumerate(features):
                self.xtx[row_index][column_index] += (
                    row_value * column_value
                )


def solve_linear_system(matrix, values):
    """Solve a small dense system with pivoted Gaussian elimination."""
    size = len(values)
    augmented = [
        [*matrix[row], values[row]]
        for row in range(size)
    ]

    for pivot_column in range(size):
        pivot_row = max(
            range(pivot_column, size),
            key=lambda row: abs(augmented[row][pivot_column]),
        )
        pivot_value = augmented[pivot_row][pivot_column]

        if abs(pivot_value) < 1e-12:
            raise RuntimeError("Linear regression matrix is singular.")

        augmented[pivot_column], augmented[pivot_row] = (
            augmented[pivot_row],
            augmented[pivot_column],
        )

        divisor = augmented[pivot_column][pivot_column]
        augmented[pivot_column] = [
            value / divisor
            for value in augmented[pivot_column]
        ]

        for row in range(size):
            if row == pivot_column:
                continue

            factor = augmented[row][pivot_column]
            augmented[row] = [
                current - factor * pivot
                for current, pivot in zip(
                    augmented[row],
                    augmented[pivot_column],
                )
            ]

    return [augmented[row][-1] for row in range(size)]


def fit_model(stats):
    matrix = [row[:] for row in stats.xtx]

    for index in range(1, len(matrix)):
        matrix[index][index] += RIDGE_STRENGTH

    coefficients = solve_linear_system(matrix, stats.xty)
    beta_xty = sum(
        coefficient * value
        for coefficient, value in zip(coefficients, stats.xty)
    )
    beta_xtx_beta = sum(
        coefficients[row] * stats.xtx[row][column] * coefficients[column]
        for row in range(len(coefficients))
        for column in range(len(coefficients))
    )
    squared_error = max(
        0.0,
        stats.sum_y_squared - 2 * beta_xty + beta_xtx_beta,
    )
    total_variance = max(
        0.0,
        stats.sum_y_squared
        - (stats.sum_y * stats.sum_y / stats.count),
    )

    return {
        "coefficients": [round(value, 10) for value in coefficients],
        "trainingSamples": stats.count,
        "trainingRmse": round(math.sqrt(squared_error / stats.count), 4),
        "trainingR2": (
            round(1 - squared_error / total_variance, 4)
            if total_variance > 0
            else None
        ),
    }


def train_model():
    query = text("""
        SELECT
            "SensorID" AS sensor_id,
            "SensingDate" AS sensing_date,
            "HourDay" AS hour_day,
            "HourlyCount" AS hourly_count
        FROM "PedestrianHourlyHistory"
        WHERE "HourlyCount" IS NOT NULL
          AND "HourlyCount" >= 0
        ORDER BY "SensingDate", "HourDay", "SensorID";
    """)
    feature_count = len(MODEL_FEATURE_NAMES)
    per_sensor = defaultdict(lambda: LinearStats(feature_count))
    global_stats = LinearStats(feature_count)
    earliest_date = None
    latest_date = None

    with engine.connect().execution_options(stream_results=True) as conn:
        result = conn.execute(query).yield_per(10_000)

        for row in result:
            sensing_date = row.sensing_date
            features = build_model_features(
                (sensing_date, int(row.hour_day))
            )
            target_per_minute = float(row.hourly_count) / 60.0
            per_sensor[int(row.sensor_id)].add(
                features,
                target_per_minute,
            )
            global_stats.add(features, target_per_minute)
            earliest_date = (
                sensing_date
                if earliest_date is None
                else min(earliest_date, sensing_date)
            )
            latest_date = (
                sensing_date
                if latest_date is None
                else max(latest_date, sensing_date)
            )

    sensor_models = {
        str(sensor_id): fit_model(stats)
        for sensor_id, stats in sorted(per_sensor.items())
        if stats.count >= MINIMUM_SENSOR_SAMPLES
    }

    return {
        "schemaVersion": 1,
        "modelType": "per-sensor calendar linear regression",
        "modelVersion": MODEL_VERSION,
        "target": "pedestrians_per_minute",
        "trainedAt": datetime.now(timezone.utc).isoformat(),
        "trainingRange": {
            "start": earliest_date.isoformat(),
            "end": latest_date.isoformat(),
        },
        "features": MODEL_FEATURE_NAMES,
        "minimumSensorSamples": MINIMUM_SENSOR_SAMPLES,
        "sensorModelCount": len(sensor_models),
        "globalModel": fit_model(global_stats),
        "sensorModels": sensor_models,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Train the SenseLens pedestrian forecast model.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_MODEL_PATH,
        help="JSON model artifact path.",
    )
    args = parser.parse_args()

    model = train_model()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(model, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(f"Model written to: {args.output}")
    print(f"Sensor models: {model['sensorModelCount']}")
    print(f"Training rows: {model['globalModel']['trainingSamples']}")
    print(f"Training range: {model['trainingRange']}")
    print(f"Global training RMSE: {model['globalModel']['trainingRmse']}")
    print(f"Global training R2: {model['globalModel']['trainingR2']}")


if __name__ == "__main__":
    main()
