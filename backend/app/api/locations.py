from fastapi import APIRouter, Depends
from app.core.auth import get_current_user
from app.models.models import User
from app.data.locations import (
    get_states, get_districts, get_mandals, get_towns, get_location_context
)

router = APIRouter(prefix="/api/locations", tags=["locations"])


@router.get("/states")
def list_states(lang: str = "en", current_user: User = Depends(get_current_user)):
    return get_states(lang)


@router.get("/states/{state_id}/districts")
def list_districts(state_id: str, lang: str = "en", current_user: User = Depends(get_current_user)):
    return get_districts(state_id, lang)


@router.get("/states/{state_id}/districts/{district_id}/mandals")
def list_mandals(state_id: str, district_id: str, lang: str = "en", current_user: User = Depends(get_current_user)):
    return get_mandals(state_id, district_id, lang)


@router.get("/states/{state_id}/districts/{district_id}/mandals/{mandal_id}/towns")
def list_towns(state_id: str, district_id: str, mandal_id: str, lang: str = "en", current_user: User = Depends(get_current_user)):
    return get_towns(state_id, district_id, mandal_id, lang)


@router.get("/states/{state_id}/districts/{district_id}/context")
def location_context(state_id: str, district_id: str, current_user: User = Depends(get_current_user)):
    return get_location_context(state_id, district_id)
