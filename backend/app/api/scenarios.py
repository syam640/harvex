from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import User, Scenario, CropCycle, Field, Farm, Expense, DiseaseScan, WeatherRecord
from app.schemas.schemas import ScenarioCreate, ScenarioResponse
from app.services.decision_engine import analyze_decision

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])

SCENARIO_TEMP_MIN = -10
SCENARIO_TEMP_MAX = 60
SCENARIO_HUMIDITY_MIN = 0
SCENARIO_HUMIDITY_MAX = 100
SCENARIO_RAIN_MIN = 0
SCENARIO_RAIN_MAX = 500
SCENARIO_COST_MIN = 0
SCENARIO_COST_MAX = 1_000_000


def _validate_scenario_inputs(input_changes: dict):
    """Validate scenario inputs against legitimate ranges."""
    if input_changes is None:
        return

    if "temperature" in input_changes:
        t = input_changes["temperature"]
        if not isinstance(t, (int, float)) or t < SCENARIO_TEMP_MIN or t > SCENARIO_TEMP_MAX:
            raise HTTPException(status_code=422, detail=f"Temperature must be {SCENARIO_TEMP_MIN}–{SCENARIO_TEMP_MAX}°C")

    if "humidity" in input_changes:
        h = input_changes["humidity"]
        if not isinstance(h, (int, float)) or h < SCENARIO_HUMIDITY_MIN or h > SCENARIO_HUMIDITY_MAX:
            raise HTTPException(status_code=422, detail=f"Humidity must be {SCENARIO_HUMIDITY_MIN}–{SCENARIO_HUMIDITY_MAX}%")

    if "rainfall" in input_changes:
        r = input_changes["rainfall"]
        if not isinstance(r, (int, float)) or r < SCENARIO_RAIN_MIN or r > SCENARIO_RAIN_MAX:
            raise HTTPException(status_code=422, detail=f"Rainfall must be {SCENARIO_RAIN_MIN}–{SCENARIO_RAIN_MAX}mm")

    if "irrigation" in input_changes:
        i = input_changes["irrigation"]
        if not isinstance(i, (int, float)) or i < SCENARIO_RAIN_MIN or i > SCENARIO_RAIN_MAX:
            raise HTTPException(status_code=422, detail=f"Irrigation must be {SCENARIO_RAIN_MIN}–{SCENARIO_RAIN_MAX}mm")

    for field_name in ("additional_cost", "fertilizer_cost", "pesticide_cost"):
        if field_name in input_changes:
            c = input_changes[field_name]
            if not isinstance(c, (int, float)) or c < SCENARIO_COST_MIN or c > SCENARIO_COST_MAX:
                raise HTTPException(status_code=422, detail=f"{field_name} must be ₹{SCENARIO_COST_MIN}–₹{SCENARIO_COST_MAX}")


def gather_scenario_context(crop_cycle_id: int, user_id: int, db: Session):
    """Gather real farm context for scenario simulation."""
    crop_cycle = db.query(CropCycle).join(Field).join(Farm).filter(
        CropCycle.id == crop_cycle_id,
        Farm.user_id == user_id
    ).first()
    if not crop_cycle:
        return None, None

    farm = db.query(Farm).join(Field).filter(Field.id == crop_cycle.field_id).first()

    disease_result = None
    disease_scan = db.query(DiseaseScan).filter(
        DiseaseScan.crop_cycle_id == crop_cycle_id
    ).order_by(DiseaseScan.created_at.desc()).first()
    if disease_scan:
        disease_result = {
            "predicted_disease": disease_scan.predicted_disease,
            "confidence": disease_scan.confidence,
            "severity": disease_scan.severity
        }

    weather_data = None
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
                "agricultural_signals": signals
            }

    expenses = db.query(Expense).filter(Expense.crop_cycle_id == crop_cycle_id).all()
    expenses_list = [{"amount": e.amount, "category": e.category} for e in expenses]

    crop_cycle_data = {
        "crop_name": crop_cycle.crop_name,
        "planting_date": crop_cycle.planting_date.isoformat() if crop_cycle.planting_date else None
    }

    return crop_cycle_data, {
        "disease_result": disease_result,
        "weather": weather_data,
        "crop_cycle": crop_cycle_data,
        "expenses": expenses_list
    }


@router.get("/{cycle_id}", response_model=List[ScenarioResponse])
def get_scenarios(
    cycle_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    crop_cycle = db.query(CropCycle).join(Field).join(Farm).filter(
        CropCycle.id == cycle_id,
        Farm.user_id == current_user.id
    ).first()

    if not crop_cycle:
        raise HTTPException(status_code=404, detail="Crop cycle not found")

    scenarios = db.query(Scenario).filter(Scenario.crop_cycle_id == cycle_id).all()
    return [ScenarioResponse.from_scenario(s) for s in scenarios]


@router.post("", response_model=ScenarioResponse)
def create_scenario(
    scenario_data: ScenarioCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    crop_cycle = db.query(CropCycle).join(Field).join(Farm).filter(
        CropCycle.id == scenario_data.crop_cycle_id,
        Farm.user_id == current_user.id
    ).first()

    if not crop_cycle:
        raise HTTPException(status_code=404, detail="Crop cycle not found")

    # Validate inputs
    _validate_scenario_inputs(scenario_data.input_changes)

    # Gather real context
    _, context = gather_scenario_context(scenario_data.crop_cycle_id, current_user.id, db)

    if context is None:
        raise HTTPException(status_code=404, detail="Could not gather farm context")

    input_changes = scenario_data.input_changes or {}

    # Build simulated context (deep copy — never mutate real data)
    simulated_weather = dict(context.get("weather")) if context.get("weather") else None
    simulated_disease = dict(context.get("disease_result")) if context.get("disease_result") else None
    simulated_crop_cycle = dict(context.get("crop_cycle")) if context.get("crop_cycle") else None
    simulated_expenses = list(context.get("expenses", []))

    # Apply weather overrides
    if simulated_weather:
        if "temperature" in input_changes:
            simulated_weather["temperature"] = input_changes["temperature"]
        if "humidity" in input_changes:
            simulated_weather["humidity"] = input_changes["humidity"]
        if "rainfall" in input_changes:
            simulated_weather["rainfall"] = input_changes["rainfall"]
        if "irrigation" in input_changes:
            simulated_weather["irrigation"] = input_changes["irrigation"]
        if "wind_speed" in input_changes:
            simulated_weather["wind_speed"] = input_changes["wind_speed"]
        # Recompute agricultural signals for simulated weather
        if simulated_weather.get("temperature") is not None:
            from app.api.weather import _compute_agricultural_signals
            simulated_weather["agricultural_signals"] = _compute_agricultural_signals(
                simulated_weather.get("temperature", 0),
                simulated_weather.get("humidity", 0),
                simulated_weather.get("rainfall", 0),
                simulated_weather.get("wind_speed", 0),
                simulated_weather.get("irrigation", 0),
            )

    # Apply disease overrides
    if simulated_disease:
        if "disease_confidence" in input_changes:
            simulated_disease["confidence"] = input_changes["disease_confidence"]
        if "disease_name" in input_changes:
            simulated_disease["predicted_disease"] = input_changes["disease_name"]

    # Apply crop overrides
    if simulated_crop_cycle:
        if "crop_name" in input_changes:
            simulated_crop_cycle["crop_name"] = input_changes["crop_name"]

    # Apply cost overrides
    if "additional_cost" in input_changes:
        simulated_expenses = simulated_expenses + [{"amount": input_changes["additional_cost"], "category": "Other"}]
    if "fertilizer_cost" in input_changes:
        simulated_expenses = simulated_expenses + [{"amount": input_changes["fertilizer_cost"], "category": "Fertilizer"}]
    if "pesticide_cost" in input_changes:
        simulated_expenses = simulated_expenses + [{"amount": input_changes["pesticide_cost"], "category": "Pesticides"}]

    # Run decision engine on SIMULATED context (with crop context!)
    result = analyze_decision(
        crop_recommendation=None,
        disease_result=simulated_disease,
        weather=simulated_weather,
        crop_cycle=simulated_crop_cycle,
        expenses=simulated_expenses
    )

    scenario = Scenario(
        crop_cycle_id=scenario_data.crop_cycle_id,
        scenario_name=scenario_data.scenario_name,
        input_changes_json=scenario_data.input_changes,
        profit_score=result["component_scores"]["profit"],
        risk_score=result["component_scores"]["risk"],
        water_score=result["component_scores"]["water"],
        cost_score=result["component_scores"]["cost"],
        sustainability_score=result["component_scores"]["sustainability"],
        overall_score=result["overall_score"],
        recommendation=result["recommended_action"]
    )
    db.add(scenario)
    db.commit()
    db.refresh(scenario)

    return ScenarioResponse.from_scenario(scenario)
