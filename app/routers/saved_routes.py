from fastapi import APIRouter

from app.services.saved_routes_service import get_saved_routes


router = APIRouter()


@router.get("/saved-routes")
def saved_routes():
    return get_saved_routes()