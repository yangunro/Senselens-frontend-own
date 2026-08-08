from sqlalchemy import text

from app.database import engine


def get_refuges():
    query = text("""
        SELECT
            "RefugeID",
            "Name",
            "Lat",
            "Lng",
            "Category",
            "SourceDataset",
            "CuratedQuietScore"
        FROM "RefugeLocation"
        ORDER BY "CuratedQuietScore" DESC NULLS LAST;
    """)

    with engine.connect() as conn:
        rows = conn.execute(query).mappings().all()

    return [
        {
            "refugeId": str(row["RefugeID"]),
            "name": row["Name"],
            "lat": float(row["Lat"]) if row["Lat"] is not None else None,
            "lng": float(row["Lng"]) if row["Lng"] is not None else None,
            "category": row["Category"],
            "sourceDataset": row["SourceDataset"],
            "quietScore": (
                float(row["CuratedQuietScore"])
                if row["CuratedQuietScore"] is not None
                else None
            ),
        }
        for row in rows
    ]