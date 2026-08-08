from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.services.routes_service import (
    get_route,
    get_route_alerts,
    get_routes,
)


router = APIRouter()


@router.get("/routes")
def routes(
    destination: str | None = Query(default=None)
):
    return get_routes(destination)


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