from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable
from zoneinfo import ZoneInfo


BASE_URL = "https://data.melbourne.vic.gov.au/api/explore/v2.1/catalog/datasets"
DATASETS = {
    "minute_counts": "pedestrian-counting-system-past-hour-counts-per-minute",
    "hourly_counts": "pedestrian-counting-system-monthly-counts-per-hour",
    "sensor_locations": "pedestrian-counting-system-sensor-locations",
    # This intentionally uses the portal's truncated dataset identifier.
    "landmarks": "landmarks-and-places-of-interest-including-schools-theatres-health-services-spor",
    "street_lights": "street-lights-with-emitted-lux-level-council-owned-lights-only",
    "development_activity": "development-activity-monitor",
}

EXPECTED_COLUMNS = {
    "minute_counts": {
        "location_id",
        "sensing_datetime",
        "direction_1",
        "direction_2",
        "total_of_directions",
    },
    "hourly_counts": {
        "id",
        "location_id",
        "sensing_date",
        "hourday",
        "direction_1",
        "direction_2",
        "pedestriancount",
    },
    "sensor_locations": {
        "location_id",
        "sensor_name",
        "status",
        "latitude",
        "longitude",
    },
    "landmarks": {"theme", "sub_theme", "feature_name", "co_ordinates"},
    "street_lights": {"geo_point_2d", "label", "ext_id"},
    "development_activity": {
        "development_key",
        "status",
        "street_address",
        "longitude",
        "latitude",
    },
}

OUTPUT_FIELDS = {
    "sensor_registry": ["location_id", "has_current_metadata"],
    "sensor_location": [
        "location_id",
        "sensor_name",
        "sensor_description",
        "location_type",
        "status",
        "latitude",
        "longitude",
        "direction_1",
        "direction_2",
        "installation_date",
        "note",
    ],
    "pedestrian_minute_count": [
        "location_id",
        "sensing_datetime_utc",
        "direction_1",
        "direction_2",
        "total_of_directions",
    ],
    "pedestrian_hour_count": [
        "source_record_id",
        "location_id",
        "sensing_date",
        "hour_day",
        "direction_1",
        "direction_2",
        "total_of_directions",
    ],
    "landmark_category": ["category_id", "theme", "sub_theme"],
    "landmark": [
        "landmark_id",
        "category_id",
        "feature_name",
        "latitude",
        "longitude",
    ],
    "street_light": [
        "street_light_id",
        "source_prop_id",
        "source_external_id",
        "source_mcc_id",
        "emitted_lux",
        "name",
        "address",
        "asset_class",
        "asset_type",
        "latitude",
        "longitude",
    ],
    "development_activity": [
        "development_id",
        "development_key",
        "status",
        "year_completed",
        "clue_small_area",
        "clue_block",
        "street_address",
        "property_id",
        "town_planning_application",
        "latitude",
        "longitude",
    ],
}


class PipelineError(RuntimeError):
    pass


@dataclass
class CleanResult:
    records: list[dict[str, Any]]
    rejected: list[dict[str, Any]]
    duplicate_count: int
    conflict_count: int = 0


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def compact_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def export_url(dataset_id: str, where: str | None = None) -> str:
    params = {
        "lang": "en",
        "timezone": "Australia/Melbourne",
        "use_labels": "false",
        "delimiter": ",",
    }
    if where:
        params["where"] = where
    return f"{BASE_URL}/{dataset_id}/exports/csv?{urllib.parse.urlencode(params)}"


def download(url: str, destination: Path, attempts: int = 3) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "text/csv",
            "User-Agent": "SenseLens/1.0 (+student project; official open data ingestion)",
        },
    )

    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        temporary = destination.with_suffix(destination.suffix + ".part")
        try:
            with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as output:
                if response.status != 200:
                    raise PipelineError(f"Source returned HTTP {response.status}: {url}")
                shutil.copyfileobj(response, output)
                content_type = response.headers.get("Content-Type", "")
            temporary.replace(destination)
            digest = hashlib.sha256(destination.read_bytes()).hexdigest()
            return {
                "url": url,
                "downloaded_at_utc": compact_utc(utc_now()),
                "bytes": destination.stat().st_size,
                "sha256": digest,
                "content_type": content_type,
            }
        except (OSError, urllib.error.URLError, PipelineError) as error:
            last_error = error
            temporary.unlink(missing_ok=True)
            if attempt < attempts:
                time.sleep(2 ** (attempt - 1))
    raise PipelineError(f"Download failed after {attempts} attempts: {last_error}")


def normalize_header(value: str) -> str:
    """Normalise portal display labels and API field names to one snake-case form."""
    cleaned = value.removeprefix("\ufeff").strip().casefold()
    cleaned = re.sub(r"[^a-z0-9]+", "_", cleaned).strip("_")
    return cleaned


def read_csv(path: Path, dataset_name: str) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        original_fields = reader.fieldnames or []
        normalised_fields = [normalize_header(field) for field in original_fields]
        if len(set(normalised_fields)) != len(normalised_fields):
            raise PipelineError(f"{dataset_name} contains duplicate columns after normalisation")

        aliases = {
            "hourly_counts": {"total_of_directions": "pedestriancount"},
            "street_lights": {"geo_point": "geo_point_2d"},
        }
        normalised_fields = [aliases.get(dataset_name, {}).get(field, field) for field in normalised_fields]
        if len(set(normalised_fields)) != len(normalised_fields):
            raise PipelineError(f"{dataset_name} contains colliding source-column aliases")

        columns = set(normalised_fields)
        missing = EXPECTED_COLUMNS[dataset_name] - columns
        if missing:
            raise PipelineError(
                f"{dataset_name} schema changed; missing columns: {', '.join(sorted(missing))}"
            )
        rows: list[dict[str, str]] = []
        for source_row in reader:
            row = {
                normalised_fields[index]: source_row.get(original_field, "")
                for index, original_field in enumerate(original_fields)
            }
            if any(text_value.strip() for text_value in row.values() if text_value is not None):
                rows.append(row)
        return rows


def text(value: Any, *, required: bool = False) -> str | None:
    if value is None:
        if required:
            raise ValueError("required text is missing")
        return None
    cleaned = " ".join(str(value).strip().split())
    if not cleaned:
        if required:
            raise ValueError("required text is blank")
        return None
    return cleaned


def integer(value: Any, *, required: bool = True, minimum: int | None = None) -> int | None:
    cleaned = text(value, required=required)
    if cleaned is None:
        return None
    parsed = int(cleaned)
    if minimum is not None and parsed < minimum:
        raise ValueError(f"integer must be >= {minimum}")
    return parsed


def number(value: Any, *, required: bool = True) -> float | None:
    cleaned = text(value, required=required)
    if cleaned is None:
        return None
    parsed = float(cleaned)
    if not math.isfinite(parsed):
        raise ValueError("number must be finite")
    return parsed


def iso_date(value: Any, *, required: bool = True) -> str | None:
    cleaned = text(value, required=required)
    if cleaned is None:
        return None
    return date.fromisoformat(cleaned[:10]).isoformat()


def iso_datetime_utc(value: Any) -> str:
    cleaned = text(value, required=True)
    assert cleaned is not None
    parsed = datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a UTC offset")
    return compact_utc(parsed)


def coordinate_pair(value: Any) -> tuple[float, float]:
    cleaned = text(value, required=True)
    assert cleaned is not None
    parts = [part.strip() for part in cleaned.split(",")]
    if len(parts) != 2:
        raise ValueError("coordinate must contain latitude and longitude")
    latitude, longitude = float(parts[0]), float(parts[1])
    validate_coordinates(latitude, longitude)
    return latitude, longitude


def validate_coordinates(latitude: float, longitude: float) -> None:
    if not (-90 <= latitude <= 90):
        raise ValueError("latitude is outside -90..90")
    if not (-180 <= longitude <= 180):
        raise ValueError("longitude is outside -180..180")


def stable_bigint(*parts: Any) -> int:
    value = "\x1f".join("" if part is None else str(part).strip().casefold() for part in parts)
    digest = hashlib.sha256(value.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") & ((1 << 63) - 1)


def clean_with_key(
    rows: Iterable[dict[str, Any]],
    transform: Callable[[dict[str, Any]], dict[str, Any]],
    key: Callable[[dict[str, Any]], tuple[Any, ...]],
    dataset: str,
) -> CleanResult:
    accepted: dict[tuple[Any, ...], dict[str, Any]] = {}
    accepted_source: dict[tuple[Any, ...], tuple[int, dict[str, Any]]] = {}
    conflicted_keys: set[tuple[Any, ...]] = set()
    rejected: list[dict[str, Any]] = []
    exact_duplicates = 0
    conflict_keys: set[tuple[Any, ...]] = set()
    for row_number, row in enumerate(rows, start=2):
        try:
            cleaned = transform(row)
            record_key = key(cleaned)
            if record_key in conflicted_keys:
                rejected.append(
                    {
                        "dataset": dataset,
                        "source_row": row_number,
                        "reason": f"conflicting duplicate key {record_key!r}",
                        "record": row,
                    }
                )
                continue
            if record_key not in accepted:
                accepted[record_key] = cleaned
                accepted_source[record_key] = (row_number, row)
                continue
            if accepted[record_key] == cleaned:
                exact_duplicates += 1
                continue

            # Do not choose an arbitrary winner when the same logical key has
            # different values. Quarantine every variant for human review.
            conflict_keys.add(record_key)
            conflicted_keys.add(record_key)
            original_row_number, original_row = accepted_source.pop(record_key)
            accepted.pop(record_key)
            rejected.extend(
                [
                    {
                        "dataset": dataset,
                        "source_row": original_row_number,
                        "reason": f"conflicting duplicate key {record_key!r}",
                        "record": original_row,
                    },
                    {
                        "dataset": dataset,
                        "source_row": row_number,
                        "reason": f"conflicting duplicate key {record_key!r}",
                        "record": row,
                    },
                ]
            )
        except (AssertionError, TypeError, ValueError) as error:
            rejected.append(
                {
                    "dataset": dataset,
                    "source_row": row_number,
                    "reason": str(error),
                    "record": row,
                }
            )
    return CleanResult(
        list(accepted.values()),
        rejected,
        exact_duplicates,
        len(conflict_keys),
    )


def clean_sensors(rows: Iterable[dict[str, Any]]) -> CleanResult:
    def transform(row: dict[str, Any]) -> dict[str, Any]:
        latitude = number(row.get("latitude"))
        longitude = number(row.get("longitude"))
        assert latitude is not None and longitude is not None
        validate_coordinates(latitude, longitude)
        source_location = text(row.get("location"))
        if source_location is not None:
            point_latitude, point_longitude = coordinate_pair(source_location)
            if abs(point_latitude - latitude) > 1e-7 or abs(point_longitude - longitude) > 1e-7:
                raise ValueError("location point does not match latitude and longitude")
        status = text(row.get("status"), required=True)
        status = status.upper() if status is not None else status
        if status not in {"A", "I", "R"}:
            raise ValueError("status must be A, I or R")
        return {
            "location_id": integer(row.get("location_id"), minimum=1),
            "sensor_name": text(row.get("sensor_name"), required=True),
            "sensor_description": text(row.get("sensor_description")),
            "location_type": text(row.get("location_type")),
            "status": status,
            "latitude": latitude,
            "longitude": longitude,
            "direction_1": text(row.get("direction_1")),
            "direction_2": text(row.get("direction_2")),
            "installation_date": iso_date(row.get("installation_date"), required=False),
            "note": text(row.get("note")),
        }

    return clean_with_key(rows, transform, lambda row: (row["location_id"],), "sensor_locations")


def clean_minute_counts(rows: Iterable[dict[str, Any]], valid_sensor_ids: set[int]) -> CleanResult:
    def transform(row: dict[str, Any]) -> dict[str, Any]:
        location_id = integer(row.get("location_id"), minimum=1)
        assert location_id is not None
        if location_id not in valid_sensor_ids:
            raise ValueError(f"unknown location_id {location_id}")
        direction_1 = integer(row.get("direction_1"), required=False, minimum=0)
        direction_2 = integer(row.get("direction_2"), required=False, minimum=0)
        total = integer(row.get("total_of_directions"), minimum=0)
        if direction_1 is not None and direction_2 is not None and total != direction_1 + direction_2:
            raise ValueError("total_of_directions does not equal direction_1 + direction_2")
        sensing_datetime_utc = iso_datetime_utc(row.get("sensing_datetime"))
        parsed = datetime.fromisoformat(str(row.get("sensing_datetime")).replace("Z", "+00:00"))
        local = parsed.astimezone(ZoneInfo("Australia/Melbourne"))
        source_date = text(row.get("sensing_date"))
        source_time = text(row.get("sensing_time"))
        if source_date is not None and source_date != local.date().isoformat():
            raise ValueError("sensing_date does not match sensing_datetime in Melbourne time")
        if source_time is not None and source_time[:5] != local.strftime("%H:%M"):
            raise ValueError("sensing_time does not match sensing_datetime in Melbourne time")
        return {
            "location_id": location_id,
            "sensing_datetime_utc": sensing_datetime_utc,
            "direction_1": direction_1,
            "direction_2": direction_2,
            "total_of_directions": total,
        }

    return clean_with_key(
        rows,
        transform,
        lambda row: (row["location_id"], row["sensing_datetime_utc"]),
        "minute_counts",
    )


def clean_hourly_counts(rows: Iterable[dict[str, Any]]) -> CleanResult:
    def transform(row: dict[str, Any]) -> dict[str, Any]:
        location_id = integer(row.get("location_id"), minimum=1)
        assert location_id is not None
        hour_day = integer(row.get("hourday"), minimum=0)
        assert hour_day is not None
        if hour_day > 23:
            raise ValueError("hourday must be 0..23")
        direction_1 = integer(row.get("direction_1"), required=False, minimum=0)
        direction_2 = integer(row.get("direction_2"), required=False, minimum=0)
        total = integer(row.get("pedestriancount"), minimum=0)
        if direction_1 is not None and direction_2 is not None and total != direction_1 + direction_2:
            raise ValueError("pedestriancount does not equal direction_1 + direction_2")
        return {
            "source_record_id": integer(row.get("id"), minimum=1),
            "location_id": location_id,
            "sensing_date": iso_date(row.get("sensing_date")),
            "hour_day": hour_day,
            "direction_1": direction_1,
            "direction_2": direction_2,
            "total_of_directions": total,
        }

    return clean_with_key(
        rows,
        transform,
        lambda row: (row["location_id"], row["sensing_date"], row["hour_day"]),
        "hourly_counts",
    )


def clean_sensor_registry(
    sensors: CleanResult,
    minutes: CleanResult,
    hours: CleanResult,
) -> CleanResult:
    """Build the stable sensor parent set used by both current and historical facts.

    The current sensor-location source does not retain every retired location ID
    present in the historical hourly source. Keeping a separate registry avoids
    discarding valid historical observations while preserving the current
    sensor-location table exactly as published.
    """
    current_ids = {int(row["location_id"]) for row in sensors.records}
    all_ids = current_ids | {
        int(row["location_id"])
        for result in (minutes, hours)
        for row in result.records
    }
    records = [
        {
            "location_id": location_id,
            "has_current_metadata": location_id in current_ids,
        }
        for location_id in sorted(all_ids)
    ]
    return CleanResult(records=records, rejected=[], duplicate_count=0)


def clean_landmarks(rows: Iterable[dict[str, Any]]) -> tuple[CleanResult, CleanResult]:
    categories: dict[tuple[str, str], dict[str, Any]] = {}
    landmarks: dict[tuple[Any, ...], dict[str, Any]] = {}
    rejected: list[dict[str, Any]] = []
    duplicates = 0

    for row_number, row in enumerate(rows, start=2):
        try:
            theme = text(row.get("theme"), required=True)
            sub_theme = text(row.get("sub_theme"), required=True)
            feature_name = text(row.get("feature_name"), required=True)
            assert theme is not None and sub_theme is not None and feature_name is not None
            latitude, longitude = coordinate_pair(row.get("co_ordinates"))
            category_key = (theme.casefold(), sub_theme.casefold())
            category_id = stable_bigint(theme, sub_theme)
            categories[category_key] = {
                "category_id": category_id,
                "theme": theme,
                "sub_theme": sub_theme,
            }
            landmark = {
                "landmark_id": stable_bigint(feature_name, f"{latitude:.8f}", f"{longitude:.8f}"),
                "category_id": category_id,
                "feature_name": feature_name,
                "latitude": latitude,
                "longitude": longitude,
            }
            key = (feature_name.casefold(), round(latitude, 8), round(longitude, 8))
            if key in landmarks:
                duplicates += 1
            landmarks[key] = landmark
        except (AssertionError, TypeError, ValueError) as error:
            rejected.append(
                {
                    "dataset": "landmarks",
                    "source_row": row_number,
                    "reason": str(error),
                    "record": row,
                }
            )

    category_result = CleanResult(list(categories.values()), [], 0)
    landmark_result = CleanResult(list(landmarks.values()), rejected, duplicates)
    return category_result, landmark_result


def clean_street_lights(rows: Iterable[dict[str, Any]]) -> CleanResult:
    def transform(row: dict[str, Any]) -> dict[str, Any]:
        latitude, longitude = coordinate_pair(row.get("geo_point_2d"))
        geo_shape = text(row.get("geo_shape"))
        if geo_shape is not None:
            shape = json.loads(geo_shape)
            coordinates = shape.get("coordinates")
            if shape.get("type") != "Point" or not isinstance(coordinates, list) or len(coordinates) != 2:
                raise ValueError("geo_shape must be a GeoJSON Point")
            shape_longitude = number(coordinates[0])
            shape_latitude = number(coordinates[1])
            assert shape_latitude is not None and shape_longitude is not None
            if abs(shape_latitude - latitude) > 1e-9 or abs(shape_longitude - longitude) > 1e-9:
                raise ValueError("geo_shape does not match geo_point")
        emitted_lux = number(row.get("label"))
        assert emitted_lux is not None
        if emitted_lux < 0:
            raise ValueError("emitted lux must be non-negative")
        source_prop_id = text(row.get("prop_id"))
        source_external_id = text(row.get("ext_id"))
        source_mcc_id = text(row.get("mcc_id"))
        street_light_id = integer(source_external_id, minimum=1)
        return {
            "street_light_id": street_light_id,
            "source_prop_id": source_prop_id,
            "source_external_id": source_external_id,
            "source_mcc_id": source_mcc_id,
            "emitted_lux": emitted_lux,
            "name": text(row.get("name")),
            "address": text(row.get("addresspt1")) or text(row.get("addresspt")),
            "asset_class": text(row.get("asset_clas")),
            "asset_type": text(row.get("asset_type")),
            "latitude": latitude,
            "longitude": longitude,
        }

    return clean_with_key(
        rows,
        transform,
        lambda row: (row["street_light_id"],),
        "street_lights",
    )


def clean_development_activity(rows: Iterable[dict[str, Any]]) -> CleanResult:
    def transform(row: dict[str, Any]) -> dict[str, Any]:
        latitude = number(row.get("latitude"))
        longitude = number(row.get("longitude"))
        assert latitude is not None and longitude is not None
        validate_coordinates(latitude, longitude)
        source_point = text(row.get("geopoint"))
        if source_point is not None:
            point_latitude, point_longitude = coordinate_pair(source_point)
            if abs(point_latitude - latitude) > 1e-7 or abs(point_longitude - longitude) > 1e-7:
                raise ValueError("geopoint does not match latitude and longitude")
        development_key = text(row.get("development_key"), required=True)
        status = text(row.get("status"), required=True)
        street_address = text(row.get("street_address"), required=True)
        assert development_key is not None and status is not None and street_address is not None
        status = status.upper()
        allowed_statuses = {"APPLIED", "APPROVED", "UNDER CONSTRUCTION", "COMPLETED"}
        if status not in allowed_statuses:
            raise ValueError(f"unsupported development status {status!r}")
        year_text = text(row.get("year_completed"))
        year_completed = None
        if year_text:
            year_completed = int(year_text[:4])
            if not 1900 <= year_completed <= 2200:
                raise ValueError("year_completed is outside the expected range")
        if status == "COMPLETED" and year_completed is None:
            raise ValueError("completed development is missing year_completed")
        property_id = text(row.get("property_id"))
        return {
            "development_id": stable_bigint(
                development_key,
                property_id,
                street_address,
                f"{latitude:.8f}",
                f"{longitude:.8f}",
            ),
            "development_key": development_key,
            "status": status,
            "year_completed": year_completed,
            "clue_small_area": text(row.get("clue_small_area")),
            "clue_block": integer(row.get("clue_block"), required=False, minimum=0),
            "street_address": street_address,
            "property_id": property_id,
            "town_planning_application": text(row.get("town_planning_application")),
            "latitude": latitude,
            "longitude": longitude,
        }

    return clean_with_key(
        rows,
        transform,
        lambda row: (row["development_id"],),
        "development_activity",
    )


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def write_csv(path: Path, records: list[dict[str, Any]], fields: list[str]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)
    with temporary.open("r", encoding="utf-8", newline="") as handle:
        written_rows = max(0, sum(1 for _ in csv.reader(handle)) - 1)
    if written_rows != len(records):
        temporary.unlink(missing_ok=True)
        raise PipelineError(
            f"Incomplete clean CSV write for {path.name}: expected {len(records)}, found {written_rows}"
        )
    temporary.replace(path)
    return {
        "rows": written_rows,
        "bytes": path.stat().st_size,
        "sha256": file_sha256(path),
    }


def write_rejected(path: Path, results: Iterable[CleanResult]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for result in results:
            for rejected in result.rejected:
                handle.write(json.dumps(rejected, ensure_ascii=False, default=str) + "\n")
                count += 1
    return count


def freshness(minutes: CleanResult, now: datetime, stale_after_minutes: int) -> dict[str, Any]:
    latest = max(
        (datetime.fromisoformat(row["sensing_datetime_utc"].replace("Z", "+00:00")) for row in minutes.records),
        default=None,
    )
    if latest is None:
        return {"latest_record_utc": None, "age_minutes": None, "is_stale": True}
    age = max(0.0, (now - latest).total_seconds() / 60)
    return {
        "latest_record_utc": compact_utc(latest),
        "age_minutes": round(age, 1),
        "stale_after_minutes": stale_after_minutes,
        "is_stale": age > stale_after_minutes,
    }


def run(output_dir: Path, minute_lookback_minutes: int, historical_days: int, stale_after_minutes: int) -> Path:
    started = utc_now()
    run_id = started.strftime("%Y%m%dT%H%M%SZ")
    run_dir = output_dir / "runs" / run_id
    raw_dir = run_dir / "raw"
    clean_dir = run_dir / "clean"

    minute_start = started - timedelta(minutes=minute_lookback_minutes)
    history_start = started.date() - timedelta(days=historical_days)
    urls = {
        "sensor_locations": export_url(DATASETS["sensor_locations"]),
        "minute_counts": export_url(
            DATASETS["minute_counts"],
            f"sensing_datetime >= date'{compact_utc(minute_start)}'",
        ),
        "hourly_counts": export_url(
            DATASETS["hourly_counts"],
            f"sensing_date >= date'{history_start.isoformat()}'",
        ),
        "landmarks": export_url(DATASETS["landmarks"]),
        "street_lights": export_url(DATASETS["street_lights"]),
        "development_activity": export_url(DATASETS["development_activity"]),
    }

    downloads: dict[str, Any] = {}
    raw_rows: dict[str, list[dict[str, str]]] = {}
    for name in (
        "sensor_locations",
        "minute_counts",
        "hourly_counts",
        "landmarks",
        "street_lights",
        "development_activity",
    ):
        path = raw_dir / f"{name}.csv"
        print(f"Downloading {name}...", flush=True)
        downloads[name] = download(urls[name], path)
        raw_rows[name] = read_csv(path, name)

    sensors = clean_sensors(raw_rows["sensor_locations"])
    valid_sensor_ids = {int(row["location_id"]) for row in sensors.records}
    minutes = clean_minute_counts(raw_rows["minute_counts"], valid_sensor_ids)
    hours = clean_hourly_counts(raw_rows["hourly_counts"])
    registry = clean_sensor_registry(sensors, minutes, hours)
    categories, landmarks = clean_landmarks(raw_rows["landmarks"])
    street_lights = clean_street_lights(raw_rows["street_lights"])
    development_activity = clean_development_activity(raw_rows["development_activity"])

    results = {
        "sensor_registry": registry,
        "sensor_location": sensors,
        "pedestrian_minute_count": minutes,
        "pedestrian_hour_count": hours,
        "landmark_category": categories,
        "landmark": landmarks,
        "street_light": street_lights,
        "development_activity": development_activity,
    }
    clean_files = {}
    for name, result in results.items():
        clean_files[name] = write_csv(
            clean_dir / f"{name}.csv", result.records, OUTPUT_FIELDS[name]
        )

    rejected_count = write_rejected(run_dir / "rejected" / "rows.jsonl", results.values())
    finished = utc_now()
    summary = {
        "run_id": run_id,
        "status": "succeeded",
        "started_at_utc": compact_utc(started),
        "finished_at_utc": compact_utc(finished),
        "source": "City of Melbourne Open Data",
        "source_mode": "official CSV export API",
        "mock_or_fallback_records_used": False,
        "loaded_tables": list(results),
        "filters": {
            "minute_lookback_minutes": minute_lookback_minutes,
            "historical_days": historical_days,
        },
        "downloads": downloads,
        "raw_row_counts": {name: len(rows) for name, rows in raw_rows.items()},
        "clean_row_counts": {name: len(result.records) for name, result in results.items()},
        "clean_files": clean_files,
        "duplicate_counts": {name: result.duplicate_count for name, result in results.items()},
        "conflicting_key_counts": {name: result.conflict_count for name, result in results.items()},
        "rejected_row_count": rejected_count,
        "live_minute_freshness": freshness(minutes, finished, stale_after_minutes),
    }
    metadata_dir = run_dir / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    (metadata_dir / "run_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "latest.json").write_text(
        json.dumps({"run_id": run_id, "run_directory": str(run_dir.resolve())}, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary["clean_row_counts"], indent=2))
    print(f"Latest minute data: {json.dumps(summary['live_minute_freshness'])}")
    return run_dir


def run_live(output_dir: Path, minute_lookback_minutes: int, stale_after_minutes: int) -> Path:
    """Ingest only the small, frequently changing live source and its sensor parent table."""
    started = utc_now()
    run_id = started.strftime("%Y%m%dT%H%M%SZ-live")
    run_dir = output_dir / "runs" / run_id
    raw_dir = run_dir / "raw"
    clean_dir = run_dir / "clean"
    minute_start = started - timedelta(minutes=minute_lookback_minutes)
    urls = {
        "sensor_locations": export_url(DATASETS["sensor_locations"]),
        "minute_counts": export_url(
            DATASETS["minute_counts"],
            f"sensing_datetime >= date'{compact_utc(minute_start)}'",
        ),
    }

    downloads: dict[str, Any] = {}
    raw_rows: dict[str, list[dict[str, str]]] = {}
    for name in ("sensor_locations", "minute_counts"):
        path = raw_dir / f"{name}.csv"
        print(f"Downloading {name}...", flush=True)
        downloads[name] = download(urls[name], path)
        raw_rows[name] = read_csv(path, name)

    sensors = clean_sensors(raw_rows["sensor_locations"])
    valid_sensor_ids = {int(row["location_id"]) for row in sensors.records}
    minutes = clean_minute_counts(raw_rows["minute_counts"], valid_sensor_ids)
    results = {
        "sensor_registry": clean_sensor_registry(
            sensors,
            minutes,
            CleanResult(records=[], rejected=[], duplicate_count=0),
        ),
        "sensor_location": sensors,
        "pedestrian_minute_count": minutes,
    }
    clean_files = {}
    for name, result in results.items():
        clean_files[name] = write_csv(
            clean_dir / f"{name}.csv", result.records, OUTPUT_FIELDS[name]
        )

    rejected_count = write_rejected(run_dir / "rejected" / "rows.jsonl", results.values())
    finished = utc_now()
    summary = {
        "run_id": run_id,
        "status": "succeeded",
        "started_at_utc": compact_utc(started),
        "finished_at_utc": compact_utc(finished),
        "source": "City of Melbourne Open Data",
        "source_mode": "official CSV export API (live profile)",
        "mock_or_fallback_records_used": False,
        "loaded_tables": list(results),
        "filters": {"minute_lookback_minutes": minute_lookback_minutes},
        "downloads": downloads,
        "raw_row_counts": {name: len(rows) for name, rows in raw_rows.items()},
        "clean_row_counts": {name: len(result.records) for name, result in results.items()},
        "clean_files": clean_files,
        "duplicate_counts": {name: result.duplicate_count for name, result in results.items()},
        "conflicting_key_counts": {name: result.conflict_count for name, result in results.items()},
        "rejected_row_count": rejected_count,
        "live_minute_freshness": freshness(minutes, finished, stale_after_minutes),
    }
    metadata_dir = run_dir / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    (metadata_dir / "run_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "latest-live.json").write_text(
        json.dumps({"run_id": run_id, "run_directory": str(run_dir.resolve())}, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary["clean_row_counts"], indent=2))
    print(f"Latest minute data: {json.dumps(summary['live_minute_freshness'])}")
    return run_dir


LOCAL_CSV_FILES = {
    "minute_counts": "pedestrian-counting-system-past-hour-counts-per-minute.csv",
    "hourly_counts": "pedestrian-counting-system-monthly-counts-per-hour.csv",
    "sensor_locations": "pedestrian-counting-system-sensor-locations.csv",
    "landmarks": "landmarks-and-places-of-interest-including-schools-theatres-health-services-spor.csv",
    "street_lights": "street-lights-with-emitted-lux-level-council-owned-lights-only.csv",
    "development_activity": "development-activity-monitor.csv",
}


def clean_downloaded_csvs(input_dir: Path, output_dir: Path, stale_after_minutes: int) -> Path:
    """Clean all six official portal CSV snapshots without generating source rows."""
    started = utc_now()
    run_id = started.strftime("%Y%m%dT%H%M%S%fZ-csv")
    run_dir = output_dir / "runs" / run_id
    raw_dir = run_dir / "raw"
    clean_dir = run_dir / "clean"

    raw_rows: dict[str, list[dict[str, str]]] = {}
    source_files: dict[str, Any] = {}
    for dataset_name, filename in LOCAL_CSV_FILES.items():
        source_path = input_dir / filename
        if not source_path.is_file():
            raise PipelineError(f"Required official CSV is missing: {source_path}")
        raw_path = raw_dir / f"{dataset_name}.csv"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, raw_path)
        source_files[dataset_name] = {
            "file_name": filename,
            "imported_at_utc": compact_utc(started),
            "bytes": raw_path.stat().st_size,
            "sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
        }
        raw_rows[dataset_name] = read_csv(raw_path, dataset_name)

    sensors = clean_sensors(raw_rows["sensor_locations"])
    valid_sensor_ids = {int(row["location_id"]) for row in sensors.records}
    minutes = clean_minute_counts(raw_rows["minute_counts"], valid_sensor_ids)
    hours = clean_hourly_counts(raw_rows["hourly_counts"])
    registry = clean_sensor_registry(sensors, minutes, hours)
    categories, landmarks = clean_landmarks(raw_rows["landmarks"])
    street_lights = clean_street_lights(raw_rows["street_lights"])
    development_activity = clean_development_activity(raw_rows["development_activity"])

    results = {
        "sensor_registry": registry,
        "sensor_location": sensors,
        "pedestrian_minute_count": minutes,
        "pedestrian_hour_count": hours,
        "landmark_category": categories,
        "landmark": landmarks,
        "street_light": street_lights,
        "development_activity": development_activity,
    }
    source_for_table = {
        "sensor_location": "sensor_locations",
        "pedestrian_minute_count": "minute_counts",
        "pedestrian_hour_count": "hourly_counts",
        "landmark": "landmarks",
        "street_light": "street_lights",
        "development_activity": "development_activity",
    }
    clean_files = {}
    for table_name, result in results.items():
        source_name = source_for_table.get(table_name)
        if source_name is not None:
            accounted = len(result.records) + len(result.rejected) + result.duplicate_count
            if accounted != len(raw_rows[source_name]):
                raise PipelineError(
                    f"Row-accounting failure for {source_name}: "
                    f"raw={len(raw_rows[source_name])}, accounted={accounted}"
                )
        clean_files[table_name] = write_csv(
            clean_dir / f"{table_name}.csv", result.records, OUTPUT_FIELDS[table_name]
        )

    rejected_count = write_rejected(run_dir / "rejected" / "rows.jsonl", results.values())
    finished = utc_now()
    summary = {
        "run_id": run_id,
        "status": "succeeded",
        "started_at_utc": compact_utc(started),
        "finished_at_utc": compact_utc(finished),
        "source": "City of Melbourne Open Data",
        "source_mode": "official portal CSV snapshots",
        "mock_or_fallback_records_used": False,
        "loaded_tables": list(results),
        "downloads": source_files,
        "raw_row_counts": {name: len(rows) for name, rows in raw_rows.items()},
        "clean_row_counts": {name: len(result.records) for name, result in results.items()},
        "clean_files": clean_files,
        "duplicate_counts": {name: result.duplicate_count for name, result in results.items()},
        "conflicting_key_counts": {name: result.conflict_count for name, result in results.items()},
        "rejected_row_counts": {name: len(result.rejected) for name, result in results.items()},
        "rejected_row_count": rejected_count,
        "live_minute_freshness": freshness(minutes, finished, stale_after_minutes),
    }
    metadata_dir = run_dir / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    (metadata_dir / "run_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "latest.json").write_text(
        json.dumps({"run_id": run_id, "run_directory": str(run_dir.resolve())}, indent=2),
        encoding="utf-8",
    )
    return run_dir


def positive_integer(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest and clean official SenseLens datasets")
    parser.add_argument("--output-dir", type=Path, default=Path("data"))
    parser.add_argument("--minute-lookback-minutes", type=positive_integer, default=90)
    parser.add_argument("--historical-days", type=positive_integer, default=30)
    parser.add_argument(
        "--stale-after-minutes",
        type=positive_integer,
        default=20,
        help="Mark the minute source stale when its newest record is older than this value",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        run(
            output_dir=args.output_dir,
            minute_lookback_minutes=args.minute_lookback_minutes,
            historical_days=args.historical_days,
            stale_after_minutes=args.stale_after_minutes,
        )
        return 0
    except (PipelineError, OSError) as error:
        print(f"Pipeline failed: {error}", file=sys.stderr)
        return 1
