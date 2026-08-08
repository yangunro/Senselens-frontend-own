from fastapi import APIRouter
from pydantic import BaseModel

from app.services.preferences_service import (
    get_preferences,
    save_preferences,
)


router = APIRouter()


class SliderPreference(BaseModel):
    key: str
    label: str
    value: int


class TogglePreference(BaseModel):
    key: str
    label: str
    note: str | None = None
    value: bool


class PreferencesPayload(BaseModel):
    sliders: list[SliderPreference]
    toggles: list[TogglePreference]


@router.get("/preferences")
def preferences():
    return get_preferences()


@router.post("/preferences")
def update_preferences(payload: PreferencesPayload):
    return save_preferences(payload)