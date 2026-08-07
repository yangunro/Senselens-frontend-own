from __future__ import annotations

import csv
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import psycopg
    from psycopg import sql
except ImportError:  # Offline cleaning and file validation do not need Psycopg.
    psycopg = None  # type: ignore[assignment]
    sql = None  # type: ignore[assignment]


@dataclass(frozen=True)
class TableLoad:
    table: str
    columns: tuple[str, ...]
    conflict_columns: tuple[str, ...]


TABLE_LOADS = (
    TableLoad(
        "sensor_registry",
        ("location_id", "has_current_metadata"),
        ("location_id",),
    ),
    TableLoad(
        "sensor_location",
        (
            "location_id", "sensor_name", "sensor_description", "location_type", "status",
            "latitude", "longitude", "direction_1", "direction_2", "installation_date", "note",
        ),
        ("location_id",),
    ),
    TableLoad(
        "pedestrian_minute_count",
        ("location_id", "sensing_datetime_utc", "direction_1", "direction_2", "total_of_directions"),
        ("location_id", "sensing_datetime_utc"),
    ),
    TableLoad(
        "pedestrian_hour_count",
        (
            "source_record_id", "location_id", "sensing_date", "hour_day",
            "direction_1", "direction_2", "total_of_directions",
        ),
        ("location_id", "sensing_date", "hour_day"),
    ),
    TableLoad(
        "landmark_category",
        ("category_id", "theme", "sub_theme"),
        ("category_id",),
    ),
    TableLoad(
        "landmark",
        ("landmark_id", "category_id", "feature_name", "latitude", "longitude"),
        ("landmark_id",),
    ),
    TableLoad(
        "street_light",
        (
            "street_light_id", "source_prop_id", "source_external_id", "source_mcc_id",
            "emitted_lux", "name", "address", "asset_class", "asset_type", "latitude", "longitude",
        ),
        ("street_light_id",),
    ),
    TableLoad(
        "development_activity",
        (
            "development_id", "development_key", "status", "year_completed", "clue_small_area",
            "clue_block", "street_address", "property_id", "town_planning_application",
            "latitude", "longitude",
        ),
        ("development_id",),
    ),
)


class DatabaseLoadError(RuntimeError):
    pass


def connection_string() -> str:
    """Use DATABASE_URL when set, otherwise libpq's PG* environment variables."""
    return os.environ.get("DATABASE_URL", "")


def resolve_latest_run(output_dir: Path) -> Path:
    latest_path = output_dir / "latest.json"
    if not latest_path.exists():
        raise DatabaseLoadError(f"Latest run pointer not found: {latest_path}")
    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    run_dir = Path(latest["run_directory"])
    if not run_dir.is_dir():
        raise DatabaseLoadError(f"Run directory does not exist: {run_dir}")
    return run_dir


def read_summary(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "metadata" / "run_summary.json"
    if not path.exists():
        raise DatabaseLoadError(f"Run summary not found: {path}")
    summary = json.loads(path.read_text(encoding="utf-8"))
    if summary.get("status") != "succeeded":
        raise DatabaseLoadError("Only a completely successful pipeline run can be loaded")
    if summary.get("mock_or_fallback_records_used") is not False:
        raise DatabaseLoadError("Run is not eligible: mock/fallback data flag is not false")
    return summary


def csv_row_count(path: Path) -> int:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return max(0, sum(1 for _ in csv.reader(handle)) - 1)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def validate_clean_files(run_dir: Path, summary: dict[str, Any]) -> None:
    expected = summary.get("clean_row_counts", {})
    selected = set(summary.get("loaded_tables", expected))
    known = {table.table for table in TABLE_LOADS}
    unknown = selected - known
    if unknown:
        raise DatabaseLoadError(f"Run contains unknown destination tables: {', '.join(sorted(unknown))}")
    if not selected:
        raise DatabaseLoadError("Run does not contain any destination tables")
    for table in (item for item in TABLE_LOADS if item.table in selected):
        path = run_dir / "clean" / f"{table.table}.csv"
        if not path.exists():
            raise DatabaseLoadError(f"Clean file is missing: {path}")
        actual = csv_row_count(path)
        if actual != expected.get(table.table):
            raise DatabaseLoadError(
                f"Row-count mismatch for {table.table}: summary={expected.get(table.table)}, file={actual}"
            )
        expected_file = summary.get("clean_files", {}).get(table.table)
        if expected_file is not None:
            actual_hash = file_sha256(path)
            if actual_hash != expected_file.get("sha256"):
                raise DatabaseLoadError(f"SHA-256 mismatch for {table.table}")


def copy_to_stage(cursor: psycopg.Cursor[Any], table: TableLoad, csv_path: Path) -> int:
    if sql is None:  # pragma: no cover - guarded by load_run
        raise DatabaseLoadError("Database loading requires Psycopg")
    stage_name = f"stage_{table.table}"
    cursor.execute(
        sql.SQL("CREATE TEMP TABLE {} (LIKE {} INCLUDING DEFAULTS EXCLUDING GENERATED) ON COMMIT DROP")
        .format(sql.Identifier(stage_name), sql.Identifier(table.table))
    )
    copy_statement = sql.SQL("COPY {} ({}) FROM STDIN WITH (FORMAT CSV, HEADER TRUE)").format(
        sql.Identifier(stage_name),
        sql.SQL(", ").join(sql.Identifier(column) for column in table.columns),
    )
    with csv_path.open("r", encoding="utf-8", newline="") as source:
        with cursor.copy(copy_statement) as copy:
            while chunk := source.read(1024 * 1024):
                copy.write(chunk)

    update_columns = [column for column in table.columns if column not in table.conflict_columns]
    assignments = sql.SQL(", ").join(
        sql.SQL("{} = EXCLUDED.{}").format(sql.Identifier(column), sql.Identifier(column))
        for column in update_columns
    )
    upsert = sql.SQL(
        "INSERT INTO {} ({}) SELECT {} FROM {} "
        "ON CONFLICT ({}) DO UPDATE SET {}"
    ).format(
        sql.Identifier(table.table),
        sql.SQL(", ").join(sql.Identifier(column) for column in table.columns),
        sql.SQL(", ").join(sql.Identifier(column) for column in table.columns),
        sql.Identifier(stage_name),
        sql.SQL(", ").join(sql.Identifier(column) for column in table.conflict_columns),
        assignments,
    )
    cursor.execute(upsert)
    cursor.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(stage_name)))
    return int(cursor.fetchone()[0])


def load_run(run_dir: Path, conninfo: str | None = None) -> dict[str, int]:
    if psycopg is None:
        raise DatabaseLoadError(
            "Database loading requires Psycopg. Run: python3 -m pip install -r requirements.txt"
        )
    summary = read_summary(run_dir)
    validate_clean_files(run_dir, summary)
    selected = set(summary.get("loaded_tables", summary["clean_row_counts"]))
    loaded_counts: dict[str, int] = {}
    try:
        with psycopg.connect(connection_string() if conninfo is None else conninfo) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT PostGIS_Version()")
                cursor.fetchone()
                for table in (item for item in TABLE_LOADS if item.table in selected):
                    count = copy_to_stage(cursor, table, run_dir / "clean" / f"{table.table}.csv")
                    loaded_counts[table.table] = count

                freshness = summary["live_minute_freshness"]
                cursor.execute(
                    """
                    INSERT INTO ingestion_run (
                        run_id, pipeline_status, started_at_utc, finished_at_utc,
                        source_name, source_mode, mock_or_fallback_records_used,
                        rejected_row_count, live_minute_is_stale,
                        live_minute_latest_record_utc, clean_row_counts,
                        duplicate_counts, source_downloads
                    ) VALUES (
                        %(run_id)s, %(status)s, %(started)s, %(finished)s,
                        %(source)s, %(source_mode)s, %(mock)s,
                        %(rejected)s, %(stale)s, %(latest)s,
                        %(clean)s::jsonb, %(duplicates)s::jsonb, %(downloads)s::jsonb
                    )
                    ON CONFLICT (run_id) DO UPDATE SET
                        loaded_at_utc = NOW(),
                        rejected_row_count = EXCLUDED.rejected_row_count,
                        live_minute_is_stale = EXCLUDED.live_minute_is_stale,
                        live_minute_latest_record_utc = EXCLUDED.live_minute_latest_record_utc,
                        clean_row_counts = EXCLUDED.clean_row_counts,
                        duplicate_counts = EXCLUDED.duplicate_counts,
                        source_downloads = EXCLUDED.source_downloads
                    """,
                    {
                        "run_id": summary["run_id"],
                        "status": summary["status"],
                        "started": summary["started_at_utc"],
                        "finished": summary["finished_at_utc"],
                        "source": summary["source"],
                        "source_mode": summary["source_mode"],
                        "mock": summary["mock_or_fallback_records_used"],
                        "rejected": summary["rejected_row_count"],
                        "stale": freshness["is_stale"],
                        "latest": freshness["latest_record_utc"],
                        "clean": json.dumps(summary["clean_row_counts"]),
                        "duplicates": json.dumps(summary["duplicate_counts"]),
                        "downloads": json.dumps(summary["downloads"]),
                    },
                )
    except psycopg.Error as error:
        raise DatabaseLoadError(f"Database load failed and was rolled back: {error}") from error
    return loaded_counts
