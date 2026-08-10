from sqlalchemy import text

from app.database import engine


def get_active_construction_sites():
    """Only 'Under Construction' sites are relevant to route avoidance —
    'Approved' sites haven't broken ground yet and 'Completed' ones no
    longer disrupt a walking route."""
    query = text("""
        SELECT
            "PropertyID",
            "CLUE_SmallArea",
            "Lat",
            "Lng"
        FROM "DevelopmentSite_Status"
        WHERE "Status" = 'Under Construction'
          AND "Lat" IS NOT NULL
          AND "Lng" IS NOT NULL;
    """)

    with engine.connect() as conn:
        rows = conn.execute(query).mappings().all()

    return [
        {
            "siteId": row["PropertyID"],
            "area": row["CLUE_SmallArea"],
            "lat": float(row["Lat"]),
            "lng": float(row["Lng"]),
        }
        for row in rows
    ]
