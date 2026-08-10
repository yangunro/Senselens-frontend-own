from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Literal
from app.services.routes_service import (
    create_route,
    get_route,
    get_route_alerts,
    get_route_forecast,
    get_route_quiet_spaces,
    get_routes,
    save_route_sensors,
)
from app.services.google_routes_service import (
    GoogleRoutesConfigurationError,
    GoogleRoutesProviderError,
)
from app.services.forecast_service import ForecastModelUnavailable


router = APIRouter()


class CreateRouteRequest(BaseModel):
    originLat: float
    originLng: float
    destLat: float
    destLng: float
    routeType: Literal["Low", "Balanced", "Fast"]
    distanceM: int
    estDurationMin: int


class RouteSensorItem(BaseModel):
    sensorId: int
    sequenceOrder: int


class RouteSensorsRequest(BaseModel):
    sensors: list[RouteSensorItem]


@router.get("/routes")
def routes(
    destination: str | None = Query(
        default=None,
        min_length=1,
        max_length=200,
    ),
    origin_lat: float | None = Query(
        default=None,
        alias="originLat",
        ge=-90,
        le=90,
    ),
    origin_lng: float | None = Query(
        default=None,
        alias="originLng",
        ge=-180,
        le=180,
    ),
    destination_lat: float | None = Query(
        default=None,
        alias="destinationLat",
        ge=-90,
        le=90,
    ),
    destination_lng: float | None = Query(
        default=None,
        alias="destinationLng",
        ge=-180,
        le=180,
    ),
):
    if destination and (
        origin_lat is None
        or origin_lng is None
    ):
        raise HTTPException(
            status_code=422,
            detail=(
                "originLat and originLng are required "
                "when generating a route."
            ),
        )

    if (
        destination_lat is None
    ) != (
        destination_lng is None
    ):
        raise HTTPException(
            status_code=422,
            detail=(
                "destinationLat and destinationLng "
                "must be provided together."
            ),
        )

    try:
        return get_routes(
            destination,
            origin_lat,
            origin_lng,
            destination_lat,
            destination_lng,
        )
    except GoogleRoutesConfigurationError as error:
        raise HTTPException(
            status_code=503,
            detail=str(error),
        ) from error
    except GoogleRoutesProviderError as error:
        raise HTTPException(
            status_code=502,
            detail=str(error),
        ) from error


@router.post("/routes")
def create_new_route(payload: CreateRouteRequest):
    try:
        return create_route(
            origin_lat=payload.originLat,
            origin_lng=payload.originLng,
            dest_lat=payload.destLat,
            dest_lng=payload.destLng,
            route_type=payload.routeType,
            distance_m=payload.distanceM,
            est_duration_min=payload.estDurationMin,
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to create route: {str(error)}",
        )


@router.get("/routes/{route_id}")
def route_detail(route_id: UUID):
    route = get_route(route_id)

    if route is None:
        raise HTTPException(
            status_code=404,
            detail="Route not found",
        )

    return route


@router.get("/routes/{route_id}/alerts")
def route_alerts(route_id: UUID):
    return get_route_alerts(route_id)


@router.get("/routes/{route_id}/forecast")
def route_forecast(route_id: UUID):
    try:
        forecast = get_route_forecast(route_id)
    except ForecastModelUnavailable as error:
        raise HTTPException(
            status_code=503,
            detail=str(error),
        ) from error

    if forecast is None:
        raise HTTPException(
            status_code=404,
            detail="Forecast data not available for this route",
        )

    return forecast


@router.get("/routes/{route_id}/quiet-spaces")
def route_quiet_spaces(route_id: UUID):
    return get_route_quiet_spaces(route_id)


@router.post("/routes/{route_id}/sensors")
def attach_route_sensors(
    route_id: UUID,
    payload: RouteSensorsRequest,
):
    result = save_route_sensors(
        route_id=route_id,
        sensors=[
            {
                "sensorId": sensor.sensorId,
                "sequenceOrder": sensor.sequenceOrder,
            }
            for sensor in payload.sensors
        ],
    )

    if not result["success"]:
        if result["error"] == "route_not_found":
            raise HTTPException(
                status_code=404,
                detail="Route not found",
            )

        if result["error"] == "sensor_not_found":
            raise HTTPException(
                status_code=404,
                detail=f"Sensor {result['sensorId']} not found",
            )

    return result
