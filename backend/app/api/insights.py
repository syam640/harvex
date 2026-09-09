from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import User, CropCycle, Harvest, Expense, Field, Farm
from app.schemas.schemas import PredictionVsRealityResponse

router = APIRouter(prefix="/api/crop-cycles", tags=["insights"])

@router.get("/{cycle_id}/prediction-vs-reality", response_model=PredictionVsRealityResponse)
def get_prediction_vs_reality(
    cycle_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    crop_cycle = db.query(CropCycle).join(Field).join(Farm).filter(
        CropCycle.id == cycle_id,
        Farm.user_id == current_user.id
    ).first()

    if not crop_cycle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Crop cycle not found"
        )

    harvests = db.query(Harvest).filter(Harvest.crop_cycle_id == cycle_id).all()
    expenses = db.query(Expense).filter(Expense.crop_cycle_id == cycle_id).all()

    predicted_yield = crop_cycle.predicted_yield
    has_prediction = predicted_yield is not None

    actual_yield = None
    if harvests:
        actual_yield = sum(h.quantity for h in harvests)

    difference = None
    percentage_deviation = None

    if has_prediction and actual_yield is not None:
        difference = actual_yield - predicted_yield
        if predicted_yield != 0:
            percentage_deviation = (difference / predicted_yield) * 100

    total_revenue = sum((h.quantity or 0) * (h.selling_price or 0) for h in harvests)
    total_cost = sum(e.amount or 0 for e in expenses)
    net_profit = total_revenue - total_cost if (total_revenue > 0 or total_cost > 0) else None

    return PredictionVsRealityResponse(
        predicted_yield=predicted_yield,
        actual_yield=actual_yield,
        difference=difference,
        percentage_deviation=percentage_deviation,
        has_prediction=has_prediction,
        total_revenue=total_revenue,
        total_cost=total_cost,
        net_profit=net_profit,
        harvest_count=len(harvests),
        expense_count=len(expenses),
    )
