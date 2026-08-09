from fastapi import APIRouter, HTTPException

from app.services.pedestrian_service import (
    get_latest_pedestrian_snapshot,
)


router = APIRouter()


@router.get("/pedestrian-counts/latest")
def latest_pedestrian_counts():
    snapshot = get_latest_pedestrian_snapshot()

    if snapshot is None:
        raise HTTPException(
            status_code=404,
            detail="No pedestrian data is available.",
        )

    return snapshot
