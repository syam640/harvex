"""
HARVEX Intelligent Crop Recommendation API
GPS/manual location + soil intelligence + weather + AI reasoning + deterministic ranking + Top 15 bilingual
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
import json
import logging
import time

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import User, Farm, WeatherRecord
from app.ml.crop_catalog import CROP_CATALOG, CATALOG_CATEGORIES, get_canonical_id, get_crop, get_all_crop_ids
from app.services.soil_intelligence import get_soil_intelligence, apply_farmer_soil_report, get_data_completeness
from app.services.crop_intelligence import (
    build_recommendation_context,
    compute_deterministic_ranking,
    filter_eligible_crops,
    validate_provenance,
    build_ai_research_context,
)
from app.services.ai import ai_service
from app.services.ai.prompts import system_prompt, crop_research_prompt, crop_research_retry_prompt, crop_research_fallback_prompt
from app.services.ai.reasoning_provider import run_crop_reasoning
from app.core.config import NVIDIA_TEXT_MODEL, NVIDIA_REASONING_FALLBACK_MODEL, AI_REQUEST_TIMEOUT

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/crop-recommendations", tags=["crop-recommendations"])


# =============================================================================
# REQUEST / RESPONSE SCHEMAS (inline to avoid touching schemas.py)
# =============================================================================

from pydantic import BaseModel, Field


class SoilReportInput(BaseModel):
    ph: Optional[float] = None
    nitrogen: Optional[float] = None
    phosphorus: Optional[float] = None
    potassium: Optional[float] = None
    soil_type: Optional[str] = None
    organic_carbon: Optional[float] = None


class CropRecommendationRequest(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_name: Optional[str] = None
    location_source: Optional[str] = "gps"
    season: str = "kharif"
    water_availability: str = "moderate"
    irrigation_method: str = "rainfed"
    soil_report: Optional[SoilReportInput] = None


class CropCandidateResponse(BaseModel):
    crop_id: str
    name_en: str
    name_te: str
    category: str
    suitability_score: float
    component_scores: dict
    limiting_factors: list
    reasoning: Optional[dict] = None
    conflicts: Optional[list] = None
    recommendation_notes: Optional[list] = None
    water_requirement: str
    risk_factors: list
    data_sources: list


class CropRecommendationResponse(BaseModel):
    status: str
    recommendation_status: str = "success"
    recommendation_id: Optional[str] = None
    data_quality: dict
    recommendations: List[CropCandidateResponse]
    total_evaluated: int
    eligible_count: int
    recommendation_engine_version: str = "crop_intelligence_v1"
    ranking_version: str = "crop_rank_v1"
    catalog_version: str = "crop_catalog_v1"
    ai_used: bool = False
    ai_provider: Optional[str] = None
    ai_model: Optional[str] = None
    ai_fallback_used: bool = False
    ai_attempt_count: int = 0
    processing_time_ms: Optional[int] = None


# =============================================================================
# JSON EXTRACTION PIPELINE
# =============================================================================

def _extract_json_from_ai(raw: str) -> Optional[dict]:
    """Robust JSON extraction from AI response.
    Handles: pure JSON, markdown fenced, surrounding prose, malformed."""
    if not raw or not raw.strip():
        return None

    text = raw.strip()

    # Case 1: Pure JSON
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # Case 2: Markdown fenced
    if "```" in text:
        import re
        fence_pattern = r"```(?:json)?\s*\n?(.*?)```"
        match = re.search(fence_pattern, text, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(1).strip())
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass

    # Case 3: Extract JSON from surrounding text
    import re
    brace_match = re.search(r"\{[\s\S]*\}", text)
    if brace_match:
        try:
            parsed = json.loads(brace_match.group(0))
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    # Case 4: Try to fix common issues
    cleaned = text.replace("'", '"')
    cleaned = re.sub(r',\s*}', '}', cleaned)
    cleaned = re.sub(r',\s*]', ']', cleaned)
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    return None


def _validate_ai_crop_response(data: dict, valid_crop_ids: list) -> dict:
    """Validate AI crop research response.
    Returns validation report."""
    issues = []

    if not isinstance(data, dict):
        return {"valid": False, "issues": ["Response is not a dict"]}

    status_val = data.get("recommendation_status")
    if status_val not in ["success", "partial"]:
        issues.append(f"Invalid recommendation_status: {status_val}")

    candidates = data.get("candidates", [])
    if not isinstance(candidates, list):
        issues.append("candidates is not a list")
        return {"valid": False, "issues": issues}

    valid_ids_set = set(valid_crop_ids)
    seen_ids = set()
    for i, c in enumerate(candidates):
        crop_id = c.get("crop_id", "")
        if not crop_id:
            issues.append(f"Candidate {i}: missing crop_id")
        elif crop_id not in valid_ids_set:
            issues.append(f"Candidate {i}: unknown crop_id '{crop_id}'")
        if crop_id in seen_ids:
            issues.append(f"Candidate {i}: duplicate crop_id '{crop_id}'")
        seen_ids.add(crop_id)

        # Check for fabricated measurements
        reasoning = c.get("reasoning", {})
        for field in ["soil", "climate", "water", "irrigation", "season", "location", "risk"]:
            text = reasoning.get(field, "")
            if isinstance(text, str):
                # Check for fabricated NPK/pH values
                import re
                if re.search(r'\b(ph|nitrogen|phosphorus|potassium)\s*[=:]\s*\d+\.?\d*', text.lower()):
                    issues.append(f"Candidate {i}: potential fabricated measurement in {field} reasoning")

    if len(candidates) > 20:
        issues.append(f"Too many candidates: {len(candidates)}")

    return {"valid": len(issues) == 0, "issues": issues}


# =============================================================================
# MAIN ENDPOINT
# =============================================================================

@router.post("", response_model=CropRecommendationResponse)
def intelligent_crop_recommendation(
    request: CropRecommendationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Intelligent crop recommendation using AI + real data + deterministic ranking.

    Flow:
    1. Validate location
    2. Gather soil intelligence (with provenance)
    3. Gather weather intelligence
    4. Filter eligible crops
    5. AI crop research (structured reasoning)
    6. Deterministic ranking
    7. Return Top 15 bilingual results
    """
    start_time = time.time()

    # === STEP 1: Validate Location ===
    if request.latitude is None or request.longitude is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Location (latitude/longitude) is required. Use browser GPS or manual location entry."
        )

    if not (-90 <= request.latitude <= 90) or not (-180 <= request.longitude <= 180):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid coordinates. Latitude must be -90 to 90, longitude -180 to 180."
        )

    location = {
        "latitude": request.latitude,
        "longitude": request.longitude,
        "name": request.location_name or f"{request.latitude:.4f}, {request.longitude:.4f}",
        "source": request.location_source or "gps",
    }

    # === STEP 2: Soil Intelligence ===
    soil_data = get_soil_intelligence(request.latitude, request.longitude)

    # Apply farmer soil report if provided
    if request.soil_report:
        report_dict = {}
        if request.soil_report.ph is not None:
            report_dict["ph"] = request.soil_report.ph
        if request.soil_report.nitrogen is not None:
            report_dict["nitrogen"] = request.soil_report.nitrogen
        if request.soil_report.phosphorus is not None:
            report_dict["phosphorus"] = request.soil_report.phosphorus
        if request.soil_report.potassium is not None:
            report_dict["potassium"] = request.soil_report.potassium
        if request.soil_report.soil_type:
            report_dict["soil_type"] = request.soil_report.soil_type
        if request.soil_report.organic_carbon is not None:
            report_dict["organic_carbon"] = request.soil_report.organic_carbon
        if report_dict:
            soil_data = apply_farmer_soil_report(soil_data, report_dict)

    soil_completeness = get_data_completeness(soil_data)

    # === STEP 3: Weather Intelligence ===
    weather_data = _get_weather_context(request.latitude, request.longitude, db)

    # === STEP 4: Build Context ===
    context = build_recommendation_context(
        location=location,
        weather=weather_data,
        soil=soil_data,
        water_availability=request.water_availability,
        irrigation_method=request.irrigation_method,
        season=request.season,
    )

    # === STEP 5: Filter Eligible Crops ===
    eligible = filter_eligible_crops(CROP_CATALOG, context)
    eligible_ids = [c["crop_id"] for c in eligible]

    if len(eligible) == 0:
        return CropRecommendationResponse(
            status="insufficient_data",
            data_quality={
                "overall": "minimal",
                "missing_data": ["No crops meet the eligibility criteria for current conditions"],
                "soil": soil_completeness,
            },
            recommendations=[],
            total_evaluated=len(CROP_CATALOG),
            eligible_count=0,
            processing_time_ms=int((time.time() - start_time) * 1000),
        )

    # === STEP 6: AI Crop Research (bounded attempts, deterministic ranking always runs) ===
    ai_result = None
    ai_used = False
    ai_provider = None
    ai_model = None
    ai_fallback_used = False
    ai_attempt_count = 0
    ai_status = "unavailable"

    provider = ai_service.get_provider()
    if provider and provider.is_available():
        try:
            ai_context = build_ai_research_context(eligible, context)
            messages = [
                {"role": "system", "content": system_prompt("en")},
                {"role": "user", "content": crop_research_prompt(ai_context, eligible_ids)},
            ]

            ai_attempt_result = run_crop_reasoning(
                provider=provider,
                messages=messages,
                primary_model=NVIDIA_TEXT_MODEL,
                fallback_model=NVIDIA_REASONING_FALLBACK_MODEL,
                valid_crop_ids=eligible_ids,
                timeout=AI_REQUEST_TIMEOUT,
            )

            ai_attempt_count = ai_attempt_result.attempt_count

            if ai_attempt_result.success:
                ai_result = ai_attempt_result.parsed_data
                ai_used = True
                ai_provider = ai_attempt_result.provider
                ai_model = ai_attempt_result.model_used
                ai_fallback_used = ai_attempt_result.fallback_used
                ai_status = "ai_assisted"
                logger.info(
                    "AI crop research succeeded: model=%s fallback=%s attempts=%d parse=%s",
                    ai_model, ai_fallback_used, ai_attempt_count,
                    ai_attempt_result.parse_method,
                )
            else:
                ai_status = "ai_unavailable_deterministic_fallback"
                logger.warning(
                    "AI crop research failed after %d attempts: %s",
                    ai_attempt_count, ai_attempt_result.error,
                )
        except Exception as e:
            ai_status = "ai_unavailable_deterministic_fallback"
            logger.error(f"AI crop research error: {e}")

    # === STEP 7: Deterministic Ranking ===
    # Build AI reasoning lookup if available
    ai_reasoning = {}
    if ai_result and ai_used:
        for c in ai_result.get("candidates", []):
            cid = c.get("crop_id", "")
            if cid in [e["crop_id"] for e in eligible]:
                ai_reasoning[cid] = {
                    "reasoning": c.get("reasoning", {}),
                    "conflicts": c.get("conflicts", []),
                    "recommendation_notes": c.get("recommendation_notes", []),
                }

    # Score all eligible crops
    scored = []
    for crop in eligible:
        ranking = compute_deterministic_ranking(crop, context)
        ai_data = ai_reasoning.get(crop["crop_id"], {})

        scored.append({
            "crop_id": crop["crop_id"],
            "name_en": crop["name_en"],
            "name_te": crop["name_te"],
            "category": crop["category"],
            "suitability_score": ranking["suitability_score"],
            "component_scores": ranking["component_scores"],
            "limiting_factors": ranking["limiting_factors"],
            "reasoning": ai_data.get("reasoning"),
            "conflicts": ai_data.get("conflicts"),
            "recommendation_notes": ai_data.get("recommendation_notes"),
            "water_requirement": crop.get("water_requirement", "medium"),
            "risk_factors": crop.get("risk_factors", []),
            "data_sources": _get_data_sources(soil_data, weather_data),
        })

    # Sort by suitability score
    scored.sort(key=lambda x: x["suitability_score"], reverse=True)

    # Category diversity tie-break: if scores are within 2 points, prefer category diversity
    if len(scored) > 15:
        top_15 = scored[:15]
        categories_seen = set()
        diversified = []
        for s in top_15:
            if s["category"] not in categories_seen or len(diversified) < 10:
                diversified.append(s)
                categories_seen.add(s["category"])
        if len(diversified) >= 10:
            scored = diversified + [s for s in scored if s not in diversified]

    # Final Top 15
    final = scored[:15]

    # === STEP 8: Data Quality Assessment ===
    weather_status = "unavailable"
    if weather_data:
        temp = weather_data.get("temperature")
        if temp and isinstance(temp, dict) and temp.get("value") is not None:
            weather_status = "available"
        elif isinstance(temp, (int, float)):
            weather_status = "available"

    soil_status = soil_data.get("overall_status", "unavailable")

    data_quality = {
        "overall": "good" if weather_status == "available" and soil_status != "unavailable" else "partial" if weather_status == "available" or soil_status != "unavailable" else "minimal",
        "weather": weather_status,
        "soil": soil_status,
        "npk": "unavailable",
        "water": "available",
        "irrigation": "available",
        "missing_data": [],
    }

    if soil_status == "unavailable":
        data_quality["missing_data"].append("soil_intelligence")
    if weather_status == "unavailable":
        data_quality["missing_data"].append("weather_intelligence")

    # Check NPK
    for field in ["nitrogen", "phosphorus", "potassium"]:
        val = soil_data.get(field, {})
        if isinstance(val, dict) and val.get("value") is not None:
            data_quality["npk"] = "partial" if data_quality["npk"] == "unavailable" else data_quality["npk"]

    # === STEP 9: Provenance Validation ===
    provenance = validate_provenance(context)

    elapsed_ms = int((time.time() - start_time) * 1000)

    return CropRecommendationResponse(
        status="success",
        recommendation_status=ai_status,
        data_quality=data_quality,
        recommendations=[
            CropCandidateResponse(**{k: v for k, v in c.items() if k in CropCandidateResponse.model_fields})
            for c in final
        ],
        total_evaluated=len(CROP_CATALOG),
        eligible_count=len(eligible),
        ai_used=ai_used,
        ai_provider=ai_provider,
        ai_model=ai_model,
        ai_fallback_used=ai_fallback_used,
        ai_attempt_count=ai_attempt_count,
        processing_time_ms=elapsed_ms,
    )


# =============================================================================
# HELPERS
# =============================================================================

def _get_weather_context(lat: float, lon: float, db: Session) -> dict:
    """Fetch weather from existing weather_records cache or return unavailable."""
    try:
        from app.api.weather import _fetch_current_weather_from_api
        weather_raw = _fetch_current_weather_from_api(lat, lon)
        if weather_raw and weather_raw.get("success"):
            data = weather_raw.get("data", {})
            temp = data.get("temperature", {})
            hum = data.get("humidity", {})
            rain = data.get("rainfall", {})
            return {
                "temperature": {"value": temp.get("value"), "status": "measured", "source": "openweather"} if isinstance(temp, dict) else {"value": temp, "status": "measured", "source": "openweather"} if temp else {"value": None, "status": "unavailable"},
                "humidity": {"value": hum.get("value"), "status": "measured", "source": "openweather"} if isinstance(hum, dict) else {"value": hum, "status": "measured", "source": "openweather"} if hum else {"value": None, "status": "unavailable"},
                "rainfall": {"value": rain.get("value"), "status": "measured", "source": "openweather"} if isinstance(rain, dict) else {"value": rain, "status": "measured", "source": "openweather"} if rain else {"value": None, "status": "unavailable"},
                "wind_speed": {"value": data.get("wind_speed", {}).get("value") if isinstance(data.get("wind_speed"), dict) else data.get("wind_speed"), "status": "measured", "source": "openweather"},
                "condition": data.get("condition", {}).get("value") if isinstance(data.get("condition"), dict) else data.get("condition", ""),
            }
    except Exception as e:
        logger.warning(f"Weather fetch failed: {e}")

    # Try cached weather from DB
    try:
        farm = db.query(Farm).filter(
            Farm.latitude >= round(lat, 2) - 0.005,
            Farm.latitude <= round(lat, 2) + 0.005,
            Farm.longitude >= round(lon, 2) - 0.005,
            Farm.longitude <= round(lon, 2) + 0.005,
        ).first()
        if farm:
            record = db.query(WeatherRecord).filter(
                WeatherRecord.farm_id == farm.id
            ).order_by(WeatherRecord.created_at.desc()).first()
            if record:
                return {
                    "temperature": {"value": record.temperature, "status": "cached", "source": "weather_cache"},
                    "humidity": {"value": record.humidity, "status": "cached", "source": "weather_cache"},
                    "rainfall": {"value": record.rainfall, "status": "cached", "source": "weather_cache"},
                    "wind_speed": {"value": record.wind_speed, "status": "cached", "source": "weather_cache"},
                    "condition": {"value": record.weather_condition, "status": "cached", "source": "weather_cache"},
                }
    except Exception:
        pass

    return {}


def _get_data_sources(soil_data: dict, weather_data: dict) -> list:
    """Build data source provenance list."""
    sources = []
    if soil_data and soil_data.get("overall_status") != "unavailable":
        sources.append({
            "name": soil_data.get("provider", "Unknown"),
            "type": "soil",
            "status": soil_data.get("overall_status"),
            "resolution": soil_data.get("resolution"),
        })
    if weather_data:
        temp = weather_data.get("temperature", {})
        source = temp.get("source", "unknown") if isinstance(temp, dict) else "unknown"
        status = temp.get("status", "unknown") if isinstance(temp, dict) else "unknown"
        sources.append({
            "name": source,
            "type": "weather",
            "status": status,
        })
    return sources


# =============================================================================
# CROP CATALOG ENDPOINTS
# =============================================================================

@router.get("/catalog")
def get_crop_catalog():
    """Return full crop catalog with bilingual names."""
    crops = []
    for crop_id, crop in CROP_CATALOG.items():
        crops.append({
            "crop_id": crop_id,
            "name_en": crop["name_en"],
            "name_te": crop["name_te"],
            "category": crop["category"],
            "water_requirement": crop.get("water_requirement"),
            "growth_duration_days": crop.get("growth_duration_days"),
        })
    return {"crops": crops, "categories": CATALOG_CATEGORIES, "total": len(crops)}


@router.get("/catalog/{crop_id}")
def get_crop_detail(crop_id: str):
    """Return detailed crop information."""
    crop = get_crop(crop_id)
    if not crop:
        raise HTTPException(status_code=404, detail=f"Crop '{crop_id}' not found in catalog")
    return crop


@router.get("/categories")
def get_categories():
    """Return crop categories."""
    return CATALOG_CATEGORIES
