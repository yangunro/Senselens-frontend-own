from fastapi import APIRouter, HTTPException, Query

from app.services.forecast_service import (
    ForecastModelUnavailable,
    get_active_sensor_forecast,
)
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


@router.get("/pedestrian-forecasts")
def pedestrian_forecasts(
    horizon_hours: int = Query(
        default=3,
        alias="horizonHours",
        ge=1,
        le=3,
    ),
):
    """Return map-wide per-sensor predictions for the next 1-3 hours."""
    try:
        forecast = get_active_sensor_forecast(
            horizon_hours=horizon_hours,
        )
    except ForecastModelUnavailable as error:
        raise HTTPException(
            status_code=503,
            detail=str(error),
        ) from error

    if forecast is None:
        raise HTTPException(
            status_code=404,
            detail="No active pedestrian sensors are available.",
        )

    return forecast
