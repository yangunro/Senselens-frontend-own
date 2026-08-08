from fastapi import APIRouter

from app.services.cbd_status_service import get_cbd_status


router = APIRouter()


@router.get("/cbd-status")
def cbd_status():
    return get_cbd_status()