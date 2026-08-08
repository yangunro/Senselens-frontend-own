from fastapi import APIRouter

from app.services.refuges_service import get_refuges


router = APIRouter()


@router.get("/refuges")
def refuges():
    return get_refuges()