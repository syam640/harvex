from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import User, Harvest, CropCycle, Field, Farm
from app.schemas.schemas import HarvestCreate, HarvestResponse

router = APIRouter(prefix="/api/crop-cycles", tags=["harvest"])

UNIT_CONVERSIONS = {
    "kg": 1.0,
    "quintal": 100.0,
    "tonnes": 1000.0,
    "pieces": 1.0,
}

def _verify_cycle_ownership(cycle_id: int, user: User, db: Session) -> CropCycle:
    crop_cycle = db.query(CropCycle).join(Field).join(Farm).filter(
        CropCycle.id == cycle_id,
        Farm.user_id == user.id
    ).first()
    if not crop_cycle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Crop cycle not found"
        )
    return crop_cycle

def _verify_harvest_ownership(harvest_id: int, user: User, db: Session) -> Harvest:
    harvest = db.query(Harvest).join(CropCycle).join(Field).join(Farm).filter(
        Harvest.id == harvest_id,
        Farm.user_id == user.id
    ).first()
    if not harvest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Harvest record not found"
        )
    return harvest

def _convert_to_kg(quantity: float, unit: str) -> float:
    return quantity * UNIT_CONVERSIONS.get(unit, 1.0)

def _build_harvest_response(harvest: Harvest) -> HarvestResponse:
    return HarvestResponse(
        id=harvest.id,
        crop_cycle_id=harvest.crop_cycle_id,
        harvest_date=harvest.harvest_date,
        quantity=harvest.quantity,
        unit=harvest.unit,
        selling_price=harvest.selling_price,
        buyer=harvest.buyer,
        market=harvest.market,
        revenue=HarvestResponse.compute_revenue(harvest.quantity, harvest.selling_price),
        created_at=harvest.created_at,
    )

@router.get("/{cycle_id}/harvests", response_model=List[HarvestResponse])
def get_harvests(
    cycle_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    _verify_cycle_ownership(cycle_id, current_user, db)
    harvests = db.query(Harvest).filter(Harvest.crop_cycle_id == cycle_id).all()
    return [_build_harvest_response(h) for h in harvests]

@router.post("/{cycle_id}/harvests", response_model=HarvestResponse)
def create_harvest(
    cycle_id: int,
    harvest_data: HarvestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    _verify_cycle_ownership(cycle_id, current_user, db)

    if harvest_data.quantity <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantity must be positive"
        )
    if harvest_data.unit and harvest_data.unit not in UNIT_CONVERSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid unit: {harvest_data.unit}. Valid: {sorted(UNIT_CONVERSIONS.keys())}"
        )
    if harvest_data.selling_price is not None and harvest_data.selling_price < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selling price cannot be negative"
        )

    harvest = Harvest(
        crop_cycle_id=cycle_id,
        harvest_date=harvest_data.harvest_date,
        quantity=harvest_data.quantity,
        unit=harvest_data.unit,
        selling_price=harvest_data.selling_price,
        buyer=harvest_data.buyer,
        market=harvest_data.market
    )
    db.add(harvest)
    db.commit()
    db.refresh(harvest)

    return _build_harvest_response(harvest)

@router.put("/{cycle_id}/harvests/{harvest_id}", response_model=HarvestResponse)
def update_harvest(
    cycle_id: int,
    harvest_id: int,
    harvest_data: HarvestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    _verify_cycle_ownership(cycle_id, current_user, db)
    harvest = _verify_harvest_ownership(harvest_id, current_user, db)

    if harvest.crop_cycle_id != cycle_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Harvest does not belong to this crop cycle"
        )
    if harvest_data.quantity <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantity must be positive"
        )
    if harvest_data.unit and harvest_data.unit not in UNIT_CONVERSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid unit: {harvest_data.unit}. Valid: {sorted(UNIT_CONVERSIONS.keys())}"
        )

    harvest.harvest_date = harvest_data.harvest_date
    harvest.quantity = harvest_data.quantity
    harvest.unit = harvest_data.unit
    harvest.selling_price = harvest_data.selling_price
    harvest.buyer = harvest_data.buyer
    harvest.market = harvest_data.market
    db.commit()
    db.refresh(harvest)

    return _build_harvest_response(harvest)

@router.delete("/{cycle_id}/harvests/{harvest_id}")
def delete_harvest(
    cycle_id: int,
    harvest_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    _verify_cycle_ownership(cycle_id, current_user, db)
    harvest = _verify_harvest_ownership(harvest_id, current_user, db)

    if harvest.crop_cycle_id != cycle_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Harvest does not belong to this crop cycle"
        )

    db.delete(harvest)
    db.commit()

    return {"message": "Harvest record deleted successfully", "deleted_id": harvest_id}
