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
    destination: str | None = Query(default=None)
):
    return get_routes(destination)


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
    forecast = get_route_forecast(route_id)

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