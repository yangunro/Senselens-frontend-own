from sqlalchemy import text

from app.database import engine
from etl.repository import update_checkpoint


DATASET = "PedestrianHourlyHistory"


def find_latest_complete_day():
    query = text("""
        SELECT
            "SensingDate",
            COUNT(*) AS record_count
        FROM "PedestrianHourlyHistory"
        GROUP BY "SensingDate"
        ORDER BY "SensingDate";
    """)

    with engine.connect() as conn:
        rows = conn.execute(query).fetchall()

    if not rows:
        return None

    previous_day = None
    latest_contiguous_day = None

    for row in rows:
        current_day = row.SensingDate

        if previous_day is None:
            latest_contiguous_day = current_day
            previous_day = current_day
            continue

        expected_next_day = previous_day.fromordinal(
            previous_day.toordinal() + 1
        )

        if current_day != expected_next_day:
            break

        latest_contiguous_day = current_day
        previous_day = current_day

    return latest_contiguous_day


def main():
    latest_day = find_latest_complete_day()

    if latest_day is None:
        print("No historical pedestrian data found.")
        return

    update_checkpoint(
        DATASET,
        latest_day
    )

    print(
        f"Checkpoint initialized successfully: "
        f"{DATASET} -> {latest_day}"
    )


if __name__ == "__main__":
    main()