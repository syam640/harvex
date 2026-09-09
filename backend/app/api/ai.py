"""AI-powered API endpoints for HARVEX."""

import os
import base64
import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import (
    User, Farm, Field, CropCycle, WeatherRecord,
    DiseaseScan, Expense, Harvest, Decision, AIConversation
)
from app.data.locations import get_location_context
from app.services.ai import ai_service
from app.services.ai import schemas as ai_schemas

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["ai"])


def _build_farm_context(user_id: int, db: Session) -> dict:
    """Build comprehensive farm context for AI calls."""
    farm = db.query(Farm).filter(Farm.user_id == user_id).first()
    if not farm:
        return {}

    context = {
        "farm_name": farm.name,
        "location": farm.location_name or "Not specified",
        "latitude": farm.latitude,
        "longitude": farm.longitude,
    }

    field = db.query(Field).filter(Field.farm_id == farm.id).first()
    if field:
        context["field_name"] = field.name
        context["area_acres"] = field.area
        context["soil_type"] = field.soil_type or "Unknown"

    crop_cycle = None
    if field:
        crop_cycle = (
            db.query(CropCycle)
            .filter(CropCycle.field_id == field.id, CropCycle.status == "active")
            .order_by(CropCycle.created_at.desc())
            .first()
        )

    if crop_cycle:
        days = (datetime.utcnow() - crop_cycle.planting_date).days if crop_cycle.planting_date else 0
        context["crop_name"] = crop_cycle.crop_name
        context["planting_date"] = crop_cycle.planting_date.strftime("%Y-%m-%d") if crop_cycle.planting_date else "Unknown"
        context["crop_age_days"] = days
        context["crop_status"] = crop_cycle.status

    weather = None
    if farm:
        weather = (
            db.query(WeatherRecord)
            .filter(WeatherRecord.farm_id == farm.id)
            .order_by(WeatherRecord.created_at.desc())
            .first()
        )
    if weather:
        context["temperature"] = weather.temperature
        context["humidity"] = weather.humidity
        context["rainfall"] = weather.rainfall
        context["wind_speed"] = weather.wind_speed
        context["weather_condition"] = weather.weather_condition
        context["weather_source"] = weather.source

    if crop_cycle:
        disease = (
            db.query(DiseaseScan)
            .filter(DiseaseScan.crop_cycle_id == crop_cycle.id)
            .order_by(DiseaseScan.created_at.desc())
            .first()
        )
        if disease:
            context["last_disease"] = disease.predicted_disease
            context["disease_confidence"] = disease.confidence
            context["disease_severity"] = disease.severity

        expenses = db.query(Expense).filter(Expense.crop_cycle_id == crop_cycle.id).all()
        if expenses:
            context["total_expenses"] = sum(e.amount for e in expenses)
            context["expense_categories"] = {}
            for e in expenses:
                cat = e.category or "Other"
                context["expense_categories"][cat] = context["expense_categories"].get(cat, 0) + e.amount

        harvests = db.query(Harvest).filter(Harvest.crop_cycle_id == crop_cycle.id).all()
        if harvests:
            total_revenue = sum((h.quantity or 0) * (h.selling_price or 0) for h in harvests)
            context["total_revenue"] = total_revenue
            context["harvest_count"] = len(harvests)

    return context


# ============================================================
# AI STATUS
# ============================================================

@router.get("/status")
def ai_status():
    """Check AI provider availability."""
    return ai_service.check_provider_status()


# ============================================================
# AI CROP RECOMMENDATION
# ============================================================

@router.post("/crop-recommendation")
def ai_crop_recommendation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """AI-powered crop recommendation based on farm context."""
    context = _build_farm_context(current_user.id, db)
    if not context:
        raise HTTPException(status_code=400, detail="No farm found. Create a farm first.")

    result = ai_service.crop_recommendation(context)
    return result


# ============================================================
# AI LOCATION-BASED CROP RECOMMENDATION
# ============================================================

@router.post("/location-crop-recommendation")
def ai_location_crop_recommendation(
    state_id: str,
    district_id: str,
    mandal_id: str = None,
    season: str = None,
    soil_type: str = None,
    current_user: User = Depends(get_current_user),
):
    """AI-powered crop recommendation based on location hierarchy."""
    from app.services.ai.prompts import system_prompt, location_crop_recommendation_prompt

    location_context = get_location_context(state_id, district_id)

    prompt = location_crop_recommendation_prompt(
        state_id=state_id,
        district_id=district_id,
        mandal_id=mandal_id,
        season=season,
        soil_type=soil_type,
        location_context=location_context,
    )

    provider = ai_service.get_provider()
    if not provider.is_available():
        return ai_service._ai_unavailable("AI_NOT_CONFIGURED")

    messages = [
        {"role": "system", "content": system_prompt("en")},
        {"role": "user", "content": prompt},
    ]
    result = provider.chat(messages, temperature=0.5, max_tokens=1024)
    if not result["success"]:
        return ai_service._ai_unavailable(result.get("error_code", "AI_FAILED"), result.get("error"))

    parsed = ai_service._parse_json_response(result["content"])
    if not parsed:
        return ai_service._ai_unavailable("AI_INVALID_RESPONSE", "Could not parse crop recommendation")

    return {"available": True, "data": parsed}


# ============================================================
# AI DISEASE ANALYSIS (for non-tomato crops)
# ============================================================

@router.post("/disease-analysis")
async def ai_disease_analysis(
    file: UploadFile = File(...),
    crop_name: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """AI vision-powered disease analysis for any crop."""
    if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Use JPEG, PNG, or WEBP.")

    image_bytes = await file.read()
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max 10MB.")
    if len(image_bytes) < 1024:
        raise HTTPException(status_code=400, detail="Image too small.")

    # Convert to base64 data URL for NVIDIA vision
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    mime = file.content_type or "image/jpeg"
    image_url = f"data:{mime};base64,{b64}"

    context = _build_farm_context(current_user.id, db)
    result = ai_service.disease_analysis(crop_name, image_url, context)
    return result


# ============================================================
# AI TREATMENT
# ============================================================

@router.post("/treatment")
def ai_treatment(
    crop_name: str,
    disease: str,
    severity: str = "medium",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """AI treatment recommendation."""
    context = _build_farm_context(current_user.id, db)
    weather = {
        "temperature": context.get("temperature"),
        "humidity": context.get("humidity"),
        "rainfall": context.get("rainfall"),
        "condition": context.get("weather_condition"),
    }
    result = ai_service.treatment_analysis(crop_name, disease, severity, weather)
    return result


# ============================================================
# AI RISK ANALYSIS
# ============================================================

@router.post("/risk")
def ai_risk(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """AI risk analysis for the current crop."""
    context = _build_farm_context(current_user.id, db)
    crop = context.get("crop_name", "unknown")
    stage = f"Day {context.get('crop_age_days', 0)}" if context.get("crop_age_days") else "Unknown"

    weather = {
        "temperature": context.get("temperature"),
        "humidity": context.get("humidity"),
        "rainfall": context.get("rainfall"),
        "wind_speed": context.get("wind_speed"),
        "condition": context.get("weather_condition"),
    }

    disease_info = None
    if context.get("last_disease"):
        disease_info = {
            "disease": context["last_disease"],
            "confidence": context.get("disease_confidence"),
            "severity": context.get("disease_severity"),
        }

    result = ai_service.risk_analysis(crop, stage, weather, disease_info)
    return result


# ============================================================
# AI IRRIGATION
# ============================================================

@router.post("/irrigation")
def ai_irrigation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """AI irrigation recommendation."""
    context = _build_farm_context(current_user.id, db)
    crop = context.get("crop_name", "unknown")
    stage = f"Day {context.get('crop_age_days', 0)}" if context.get("crop_age_days") else "Unknown"

    weather = {
        "temperature": context.get("temperature"),
        "humidity": context.get("humidity"),
        "rainfall": context.get("rainfall"),
        "wind_speed": context.get("wind_speed"),
        "condition": context.get("weather_condition"),
    }

    result = ai_service.irrigation_analysis(
        crop, stage, weather, context.get("soil_type")
    )
    return result


# ============================================================
# AI FINANCIAL ANALYSIS
# ============================================================

@router.post("/financial")
def ai_financial(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """AI financial analysis for the current crop cycle."""
    context = _build_farm_context(current_user.id, db)
    crop = context.get("crop_name", "unknown")

    expenses_list = []
    if context.get("expense_categories"):
        for cat, amt in context["expense_categories"].items():
            expenses_list.append({"category": cat, "amount": amt})

    harvests_list = []
    field = db.query(Field).join(Farm).filter(Farm.user_id == current_user.id).first()
    if field:
        cycle = (
            db.query(CropCycle)
            .filter(CropCycle.field_id == field.id, CropCycle.status == "active")
            .order_by(CropCycle.created_at.desc()).first()
        )
        if cycle:
            for h in db.query(Harvest).filter(Harvest.crop_cycle_id == cycle.id).all():
                harvests_list.append({
                    "quantity": h.quantity,
                    "unit": h.unit,
                    "selling_price": h.selling_price,
                    "revenue": (h.quantity or 0) * (h.selling_price or 0),
                })

    result = ai_service.financial_analysis(expenses_list, harvests_list, crop)
    return result


# ============================================================
# AI INSIGHTS
# ============================================================

@router.post("/insights")
def ai_insights(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """AI-generated farm insights."""
    context = _build_farm_context(current_user.id, db)

    expenses_summary = None
    if context.get("expense_categories"):
        expenses_summary = {
            "total": context.get("total_expenses", 0),
            "categories": context.get("expense_categories", {}),
        }

    harvest_summary = None
    if context.get("total_revenue"):
        harvest_summary = {
            "total_revenue": context["total_revenue"],
            "harvest_count": context.get("harvest_count", 0),
        }

    weather_summary = None
    if context.get("temperature"):
        weather_summary = {
            "temperature": context["temperature"],
            "humidity": context["humidity"],
            "rainfall": context["rainfall"],
            "condition": context.get("weather_condition"),
        }

    result = ai_service.farm_insights(context, expenses_summary, harvest_summary)
    return result


# ============================================================
# AI WHAT-IF ANALYSIS
# ============================================================

@router.post("/what-if")
def ai_what_if(
    scenario_changes: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """AI what-if scenario analysis."""
    context = _build_farm_context(current_user.id, db)

    current_decision = {}
    crop = context.get("crop_name", "unknown")
    field = db.query(Field).join(Farm).filter(Farm.user_id == current_user.id).first()
    if field:
        cycle = (
            db.query(CropCycle)
            .filter(CropCycle.field_id == field.id, CropCycle.status == "active")
            .order_by(CropCycle.created_at.desc()).first()
        )
        if cycle:
            decision = (
                db.query(Decision)
                .filter(Decision.crop_cycle_id == cycle.id)
                .order_by(Decision.created_at.desc()).first()
            )
            if decision:
                current_decision = {
                    "recommended_action": decision.recommended_action,
                    "score": decision.score,
                    "reasoning": decision.reasoning,
                }

    result = ai_service.what_if_analysis(current_decision, scenario_changes, context)
    return result
