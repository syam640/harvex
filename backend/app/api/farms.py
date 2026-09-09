from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import User, Farm, Field, CropCycle, CropCycleStatus
from app.schemas.schemas import FarmCreate, FarmResponse, FieldCreate, FieldResponse, CropCycleCreate, CropCycleResponse

router = APIRouter(prefix="/api", tags=["farms"])

@router.get("/farms", response_model=List[FarmResponse])
def get_farms(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    farms = db.query(Farm).filter(Farm.user_id == current_user.id).all()
    return [FarmResponse.model_validate(farm) for farm in farms]

@router.post("/farms", response_model=FarmResponse)
def create_farm(
    farm_data: FarmCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    farm = Farm(
        user_id=current_user.id,
        name=farm_data.name,
        location_name=farm_data.location_name,
        latitude=farm_data.latitude,
        longitude=farm_data.longitude,
        area=farm_data.area
    )
    db.add(farm)
    db.commit()
    db.refresh(farm)
    return FarmResponse.model_validate(farm)

@router.get("/farms/{farm_id}/fields", response_model=List[FieldResponse])
def get_fields(
    farm_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    farm = db.query(Farm).filter(
        Farm.id == farm_id,
        Farm.user_id == current_user.id
    ).first()
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farm not found"
        )
    fields = db.query(Field).filter(Field.farm_id == farm_id).all()
    return [FieldResponse.model_validate(field) for field in fields]

@router.post("/farms/{farm_id}/fields", response_model=FieldResponse)
def create_field(
    farm_id: int,
    field_data: FieldCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    farm = db.query(Farm).filter(
        Farm.id == farm_id,
        Farm.user_id == current_user.id
    ).first()
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farm not found"
        )
    
    field = Field(
        farm_id=farm_id,
        name=field_data.name,
        area=field_data.area,
        soil_type=field_data.soil_type
    )
    db.add(field)
    db.commit()
    db.refresh(field)
    return FieldResponse.model_validate(field)

@router.post("/crop-cycles", response_model=CropCycleResponse)
def create_crop_cycle(
    cycle_data: CropCycleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    field = db.query(Field).join(Farm).filter(
        Field.id == cycle_data.field_id,
        Farm.user_id == current_user.id
    ).first()
    if not field:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Field not found"
        )
    
    # Deactivate any existing active crop cycles on this field
    old_active = db.query(CropCycle).filter(
        CropCycle.field_id == cycle_data.field_id,
        CropCycle.status == CropCycleStatus.ACTIVE.value,
    ).all()
    for old in old_active:
        old.status = CropCycleStatus.COMPLETED.value

    cycle = CropCycle(
        field_id=cycle_data.field_id,
        crop_name=cycle_data.crop_name,
        planting_date=cycle_data.planting_date,
        expected_harvest_date=cycle_data.expected_harvest_date
    )
    db.add(cycle)
    db.commit()
    db.refresh(cycle)
    return CropCycleResponse.model_validate(cycle)

@router.get("/crop-cycles/{cycle_id}", response_model=CropCycleResponse)
def get_crop_cycle(
    cycle_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cycle = db.query(CropCycle).join(Field).join(Farm).filter(
        CropCycle.id == cycle_id,
        Farm.user_id == current_user.id
    ).first()
    if not cycle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Crop cycle not found"
        )
    return CropCycleResponse.model_validate(cycle)

@router.get("/fields/{field_id}/crop-cycles", response_model=List[CropCycleResponse])
def get_field_crop_cycles(
    field_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    field = db.query(Field).join(Farm).filter(
        Field.id == field_id,
        Farm.user_id == current_user.id
    ).first()
    if not field:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Field not found"
        )
    cycles = db.query(CropCycle).filter(CropCycle.field_id == field_id).all()
    return [CropCycleResponse.model_validate(c) for c in cycles]


class FarmLocationUpdate(BaseModel):
    latitude: float
    longitude: float
    location_name: Optional[str] = None


@router.patch("/farms/location", response_model=FarmResponse)
def update_farm_location(
    data: FarmLocationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update the authenticated user's primary farm coordinates."""
    if not (-90 <= data.latitude <= 90):
        raise HTTPException(status_code=400, detail="Latitude must be between -90 and 90")
    if not (-180 <= data.longitude <= 180):
        raise HTTPException(status_code=400, detail="Longitude must be between -180 and 180")

    farm = db.query(Farm).filter(Farm.user_id == current_user.id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="No farm found. Create a farm first.")

    farm.latitude = data.latitude
    farm.longitude = data.longitude
    if data.location_name:
        farm.location_name = data.location_name
    db.commit()
    db.refresh(farm)
    return FarmResponse.model_validate(farm)
