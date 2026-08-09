from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.saved_routes_service import (
    delete_saved_route,
    get_saved_routes,
    save_route,
)


router = APIRouter()


class SaveRouteRequest(BaseModel):
    routeId: UUID
    label: str


@router.get("/saved-routes")
def saved_routes():
    return get_saved_routes()


@router.post("/saved-routes")
def create_saved_route(payload: SaveRouteRequest):
    try:
        saved_route = save_route(
            route_id=payload.routeId,
            label=payload.label,
        )

    except Exception as error:
        error_message = str(error)

        if "foreign key" in error_message.lower():
            raise HTTPException(
                status_code=404,
                detail="Route not found",
            )

        raise HTTPException(
            status_code=500,
            detail="Unable to save route",
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