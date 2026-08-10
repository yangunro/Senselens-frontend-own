from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.saved_routes_service import (
    delete_saved_route,
    get_saved_routes,
    save_route,
)


router = APIRouter()


class RoutePoint(BaseModel):
    lat: float
    lng: float


class SaveRouteRequest(BaseModel):
    label: str
    origin: RoutePoint
    destination: RoutePoint
    level: str = "unknown"
    distanceM: int
    durationMin: int


@router.get("/saved-routes")
def saved_routes():
    return get_saved_routes()


@router.post("/saved-routes")
def create_saved_route(payload: SaveRouteRequest):
    try:
        saved_route = save_route(
            label=payload.label,
            origin={"lat": payload.origin.lat, "lng": payload.origin.lng},
            destination={
                "lat": payload.destination.lat,
                "lng": payload.destination.lng,
            },
            level=payload.level,
            distance_m=payload.distanceM,
            duration_min=payload.durationMin,
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to save route: {str(error)}",
        )

    if saved_route is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    return saved_route

@router.delete("/saved-routes/{saved_route_id}")
def remove_saved_route(saved_route_id: UUID):
    deleted_route = delete_saved_route(saved_route_id)

    if deleted_route is None:
        raise HTTPException(
            status_code=404,
            detail="Saved route not found",
        )

    return {
        "success": True,
        "message": "Saved route deleted successfully",
        "savedRoute": deleted_route,
    }