from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import (
    User, CropCycle, Field, Farm, WeatherRecord,
    Decision, AIConversation, Expense, Harvest, DiseaseScan
)
from app.schemas.schemas import AssistantRequest, AssistantResponse
from app.services.ai import ai_service

router = APIRouter(prefix="/api/assistant", tags=["assistant"])

MAX_HISTORY = 6


def get_farm_context(user_id: int, db: Session) -> dict:
    farm = db.query(Farm).filter(Farm.user_id == user_id).first()
    if not farm:
        return {}

    field = db.query(Field).filter(Field.farm_id == farm.id).first()
    crop_cycle = None
    if field:
        crop_cycle = (
            db.query(CropCycle)
            .filter(CropCycle.field_id == field.id, CropCycle.status == "active")
            .order_by(CropCycle.created_at.desc())
            .first()
        )

    context = {
        "farm_name": farm.name,
        "location": farm.location_name or "Not specified",
    }

    if field:
        context["field_name"] = field.name
        context["soil_type"] = field.soil_type or "Not specified"

    if crop_cycle:
        context["crop_name"] = crop_cycle.crop_name
        context["planting_date"] = (
            crop_cycle.planting_date.strftime("%Y-%m-%d")
            if crop_cycle.planting_date else "Unknown"
        )
        context["crop_status"] = crop_cycle.status
        days = (datetime.utcnow() - crop_cycle.planting_date).days if crop_cycle.planting_date else 0
        context["crop_age_days"] = str(days)

        if crop_cycle.predicted_yield is not None:
            context["predicted_yield"] = f"{crop_cycle.predicted_yield} kg"

        weather = (
            db.query(WeatherRecord)
            .filter(WeatherRecord.farm_id == farm.id)
            .order_by(WeatherRecord.created_at.desc())
            .first()
        )
        if weather:
            context["current_temperature"] = f"{weather.temperature} C"
            context["current_humidity"] = f"{weather.humidity}%"
            context["weather_condition"] = weather.weather_condition or "Unknown"
            context["recent_rainfall"] = f"{weather.rainfall} mm"

        disease = (
            db.query(DiseaseScan)
            .filter(DiseaseScan.crop_cycle_id == crop_cycle.id)
            .order_by(DiseaseScan.created_at.desc())
            .first()
        )
        if disease:
            context["latest_disease_scan"] = disease.predicted_disease or "Unknown"
            context["disease_confidence"] = f"{disease.confidence}%" if disease.confidence else "Unknown"
            context["disease_severity"] = disease.severity or "Unknown"

        expenses = db.query(Expense).filter(Expense.crop_cycle_id == crop_cycle.id).all()
        if expenses:
            total_cost = sum(e.amount for e in expenses)
            context["total_expenses"] = f"Rs {total_cost:,.0f}"
            context["expense_count"] = str(len(expenses))

        harvests = db.query(Harvest).filter(Harvest.crop_cycle_id == crop_cycle.id).all()
        if harvests:
            total_revenue = sum(
                (h.quantity or 0) * (h.selling_price or 0) for h in harvests
            )
            context["total_harvests"] = str(len(harvests))
            context["total_revenue"] = f"Rs {total_revenue:,.0f}"

        decision = (
            db.query(Decision)
            .filter(Decision.crop_cycle_id == crop_cycle.id)
            .order_by(Decision.created_at.desc())
            .first()
        )
        if decision:
            context["last_recommendation"] = decision.recommended_action
            context["decision_score"] = f"{decision.score}/100" if decision.score else "Unknown"

    return context


def _get_conversation_history(user_id: int, db: Session) -> list:
    recent = (
        db.query(AIConversation)
        .filter(AIConversation.user_id == user_id)
        .order_by(AIConversation.created_at.desc())
        .limit(MAX_HISTORY)
        .all()
    )
    recent.reverse()
    history = []
    for conv in recent:
        history.append({"role": "user", "content": conv.question})
        history.append({"role": "assistant", "content": conv.answer})
    return history


def generate_fallback_response(context: dict, question: str, language: str) -> str:
    if language == "te":
        return (
            "AI Assistant ప్రస్తుతం అందుబాటులో లేదు. "
            "మీ HARVEX పొలం సమాచారం ఇప్పటికీ అందుబాటులో ఉంది. "
            "వ్యవసాయ సలహా కోసం మీ స్థానిక వ్యవసాయ నిపుణుడిని సంప్రదించండి."
        )
    return (
        "AI Assistant is currently unavailable. "
        "Core HARVEX farm intelligence is still available. "
        "For agricultural advice, please consult your local agricultural expert."
    )


@router.post("/chat", response_model=AssistantResponse)
def chat_with_assistant(
    request: AssistantRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    context = get_farm_context(current_user.id, db)

    crop_cycle = None
    field = db.query(Field).join(Farm).filter(Farm.user_id == current_user.id).first()
    if field:
        crop_cycle = (
            db.query(CropCycle)
            .filter(CropCycle.field_id == field.id, CropCycle.status == "active")
            .order_by(CropCycle.created_at.desc())
            .first()
        )

    history = _get_conversation_history(current_user.id, db)

    ai_result = ai_service.assistant_chat(context, request.question, history, request.language)

    answer = ai_result.get("answer")
    source = ai_result.get("source", "unknown")
    model = ai_result.get("model")

    if not answer:
        answer = generate_fallback_response(context, request.question, request.language)
        source = "fallback"
        model = None

    conversation = AIConversation(
        user_id=current_user.id,
        crop_cycle_id=crop_cycle.id if crop_cycle else None,
        question=request.question,
        answer=answer,
        language=request.language,
    )
    db.add(conversation)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(f"Failed to save assistant conversation: {e}")

    return AssistantResponse(
        answer=answer,
        language=request.language,
        source=source,
        model=model,
    )
