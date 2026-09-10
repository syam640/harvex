import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import User, CropCycle, Decision, Expense, Field, Farm, DiseaseScan, WeatherRecord
from app.schemas.schemas import DecisionRequest, DecisionResponse
from app.services.decision_engine import analyze_decision

logger = logging.getLogger("harvex.decision")

router = APIRouter(prefix="/api/decision", tags=["decision"])

def gather_farm_context(crop_cycle_id: int, user_id: int, db: Session):
    crop_cycle = db.query(CropCycle).join(Field).join(Farm).filter(
        CropCycle.id == crop_cycle_id,
        Farm.user_id == user_id
    ).first()

    if not crop_cycle:
        return None, None

    farm = db.query(Farm).join(Field).filter(Field.id == crop_cycle.field_id).first()

    crop_rec = None
    disease_result = None
    weather_data = None
    expenses_list = []

    disease_scan = db.query(DiseaseScan).filter(
        DiseaseScan.crop_cycle_id == crop_cycle_id
    ).order_by(DiseaseScan.created_at.desc()).first()

    if disease_scan:
        disease_result = {
            "predicted_disease": disease_scan.predicted_disease,
            "confidence": disease_scan.confidence,
            "severity": disease_scan.severity
        }

    if farm:
        weather_record = db.query(WeatherRecord).filter(
            WeatherRecord.farm_id == farm.id
        ).order_by(WeatherRecord.created_at.desc()).first()

        if weather_record:
            from app.api.weather import _compute_agricultural_signals
            signals = _compute_agricultural_signals(
                weather_record.temperature or 0,
                weather_record.humidity or 0,
                weather_record.rainfall or 0,
                weather_record.wind_speed or 0
            )
            weather_data = {
                "temperature": weather_record.temperature,
                "humidity": weather_record.humidity,
                "rainfall": weather_record.rainfall,
                "wind_speed": weather_record.wind_speed,
                "weather_condition": weather_record.weather_condition,
                "agricultural_signals": signals
            }

    expenses = db.query(Expense).filter(Expense.crop_cycle_id == crop_cycle_id).all()
    expenses_list = [{"amount": e.amount, "category": e.category} for e in expenses]

    crop_cycle_data = {
        "crop_name": crop_cycle.crop_name,
        "planting_date": crop_cycle.planting_date.isoformat() if crop_cycle.planting_date else None
    }

    return crop_cycle_data, {
        "crop_recommendation": crop_rec,
        "disease_result": disease_result,
        "weather": weather_data,
        "crop_cycle": crop_cycle_data,
        "expenses": expenses_list
    }

@router.post("/analyze", response_model=DecisionResponse)
def analyze_farm_decision(
    request: DecisionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    crop_cycle = db.query(CropCycle).join(Field).join(Farm).filter(
        CropCycle.id == request.crop_cycle_id,
        Farm.user_id == current_user.id
    ).first()

    if not crop_cycle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Crop cycle not found"
        )

    crop_cycle_data, context = gather_farm_context(request.crop_cycle_id, current_user.id, db)

    if context is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Could not gather farm context"
        )

    try:
        result = analyze_decision(
            crop_recommendation=context["crop_recommendation"],
            disease_result=context["disease_result"],
            weather=context["weather"],
            crop_cycle=context["crop_cycle"],
            expenses=context["expenses"]
        )
    except Exception as e:
        logger.error(f"Decision engine failed: {e}")
        raise HTTPException(status_code=500, detail="Decision analysis failed.")

    decision = Decision(
        crop_cycle_id=request.crop_cycle_id,
        recommended_action=result["recommended_action"],
        score=result["overall_score"],
        profit_score=result["component_scores"]["profit"],
        risk_score=result["component_scores"]["risk"],
        cost_score=result["component_scores"]["cost"],
        water_score=result["component_scores"]["water"],
        sustainability_score=result["component_scores"]["sustainability"],
        reasoning_json=result["reasoning"]
    )
    db.add(decision)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save decision.")

    return DecisionResponse(
        recommended_action=result["recommended_action"],
        overall_score=result["overall_score"],
        component_scores=result["component_scores"],
        reasoning={"reasons": result["reasoning"]}
    )
