from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import joblib
import os
import numpy as np
from typing import Optional
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import User, CropPrediction
from app.schemas.schemas import CropRecommendationRequest, CropRecommendationResponse
from app.ml.crop_knowledge import (
    CROP_KNOWLEDGE, CROP_CATEGORIES, CROP_REGISTRY, REGIONS, SEASONS,
    compute_agronomic_score, get_crop_info, get_canonical_crop
)

router = APIRouter(prefix="/api/crop", tags=["crop"])

MODEL_DIR = "app/ml/models"
MODEL_PATH = f"{MODEL_DIR}/crop_model.joblib"
MODEL_INFO_PATH = f"{MODEL_DIR}/crop_model_info.joblib"

_model_cache = None
_model_info_cache = None

def load_model():
    global _model_cache, _model_info_cache
    if _model_cache is not None and _model_info_cache is not None:
        return _model_cache, _model_info_cache

    if not os.path.exists(MODEL_PATH):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Crop model not found. Please train the model first."
        )
    _model_cache = joblib.load(MODEL_PATH)
    _model_info_cache = joblib.load(MODEL_INFO_PATH)
    return _model_cache, _model_info_cache


def _input_valid(request: CropRecommendationRequest) -> None:
    """Validate input ranges. Reject impossible values."""
    errors = []
    if not (0 <= request.n <= 300):
        errors.append("N must be 0-300 kg/ha")
    if not (0 <= request.p <= 200):
        errors.append("P must be 0-200 kg/ha")
    if not (0 <= request.k <= 300):
        errors.append("K must be 0-300 kg/ha")
    if not (-10 <= request.temperature <= 55):
        errors.append("Temperature must be -10 to 55°C")
    if not (0 <= request.humidity <= 100):
        errors.append("Humidity must be 0-100%")
    if not (0 <= request.ph <= 14):
        errors.append("pH must be 0-14")
    if not (0 <= request.rainfall <= 2000):
        errors.append("Rainfall must be 0-2000 mm")
    if request.region and request.region not in REGIONS:
        errors.append(f"Invalid region. Supported: {', '.join(REGIONS.keys())}")
    if request.season and request.season not in SEASONS:
        errors.append(f"Invalid season. Supported: {', '.join(SEASONS.keys())}")
    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="; ".join(errors)
        )


@router.post("/recommend", response_model=CropRecommendationResponse)
def recommend_crop(
    request: CropRecommendationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    _input_valid(request)

    model, model_info = load_model()

    # === ML MODEL INFERENCE ===
    input_data = np.array([[
        request.n, request.p, request.k,
        request.temperature, request.humidity,
        request.ph, request.rainfall
    ]], dtype=float)

    ml_probabilities = model.predict_proba(input_data)[0]
    ml_classes = model_info['classes']

    # === AGRONOMIC SCORING FOR ALL CROPS ===
    scored_crops = []
    for idx, crop_name in enumerate(ml_classes):
        ml_prob = float(ml_probabilities[idx])

        # ML suitability: normalize probability to 0-100 scale
        ml_suitability = ml_prob * 100.0

        # Agronomic multi-component scoring
        agro = compute_agronomic_score(
            crop_name,
            n=request.n, p=request.p, k=request.k,
            temperature=request.temperature,
            humidity=request.humidity,
            rainfall=request.rainfall,
            ph=request.ph,
            soil_type=request.soil_type or "loamy",
            water_availability=request.water_availability or "medium",
            region=request.region,
            season=request.season,
        )

        # Combined score: ML contributes 25%, agronomic contributes 75%
        # This gives agronomic context dominance while still using the ML model
        # as a pattern recognizer. The ML model captures non-linear interactions
        # between N/P/K/temperature/humidity/pH/rainfall that the rule-based
        # agronomic layer cannot.
        combined = ml_suitability * 0.25 + agro["overall_score"] * 0.75

        # Canonical crop identity
        canonical = get_canonical_crop(crop_name)

        scored_crops.append({
            "model_label": crop_name,
            "canonical_id": canonical["canonical_id"],
            "display_name": canonical["display_name"],
            "category": canonical["category"],
            "ml_suitability": round(ml_suitability, 1),
            "agronomic_score": round(agro["overall_score"], 1),
            "overall_score": round(combined, 1),
            "component_scores": agro["component_scores"],
            "reasons": _build_reasons(agro),
            "limiting_factors": agro["limiting_factors"],
            "all_reasons": agro["all_reasons"],
        })

    # Sort by overall score descending
    scored_crops.sort(key=lambda x: x["overall_score"], reverse=True)

    primary = scored_crops[0]
    alternatives = scored_crops[1:6]

    # Input metadata
    input_dict = {
        "N": request.n,
        "P": request.p,
        "K": request.k,
        "temperature": request.temperature,
        "humidity": request.humidity,
        "ph": request.ph,
        "rainfall": request.rainfall,
        "region": REGIONS.get(request.region, request.region or "Not specified"),
        "season": SEASONS.get(request.season, request.season or "Not specified"),
        "soil_type": request.soil_type or "Not specified",
        "water_availability": request.water_availability or "Not specified",
        "n_source": "Laboratory measurement" if request.n_measured else "Estimated from soil type",
        "p_source": "Laboratory measurement" if request.p_measured else "Estimated from soil type",
        "k_source": "Laboratory measurement" if request.k_measured else "Estimated from soil type",
        "ph_source": "Laboratory measurement" if request.ph_measured else "Estimated from soil type",
    }

    # Categories output
    categories_output = {}
    for cat_name, cat_info in CROP_CATEGORIES.items():
        cat_crops = [c for c in scored_crops if c["model_label"] in cat_info["crops"]]
        if cat_crops:
            categories_output[cat_name] = cat_crops

    return CropRecommendationResponse(
        recommended_crop=primary["display_name"],
        suitability_score=primary["overall_score"] / 100,
        alternatives=[
            {
                "crop": a["display_name"],
                "score": a["overall_score"] / 100,
                "reasons": a["reasons"],
                "category": a["category"],
                "component_scores": a["component_scores"],
                "limiting_factors": a["limiting_factors"],
            }
            for a in alternatives
        ],
        model_version=model_info.get('model_version', 'v1.0'),
        input_data=input_dict,
        categories=categories_output,
        primary_reasons=primary.get("reasons", []),
    )


def _build_reasons(agro_result: dict) -> list:
    """Build a concise list of top reasons from the agronomic scoring."""
    reasons = []
    all_reasons = agro_result.get("all_reasons", {})

    # Add top reason from each component
    for component in ["climate", "nutrients", "soil", "water", "region", "season"]:
        comp_reasons = all_reasons.get(component, [])
        if comp_reasons:
            reasons.append(comp_reasons[0])

    # Add limiting factors
    for lf in agro_result.get("limiting_factors", []):
        reasons.append(f"Limiting factor: {lf}")

    return reasons


@router.get("/knowledge/{crop_name}")
def get_crop_knowledge(crop_name: str, current_user: User = Depends(get_current_user)):
    info = get_crop_info(crop_name)
    if not info:
        raise HTTPException(status_code=404, detail=f"Crop '{crop_name}' not found in knowledge base")
    canonical = get_canonical_crop(crop_name)
    return {
        "crop": crop_name,
        "display_name": canonical["display_name"],
        "category": canonical["category"],
        "scientific_name": info.get("scientific_name"),
        "preferred_temp_range": info.get("preferred_temp_range"),
        "preferred_humidity_range": info.get("preferred_humidity_range"),
        "preferred_ph_range": info.get("preferred_ph_range"),
        "water_requirement": info.get("water_requirement"),
        "rainfall_requirement_mm": info.get("rainfall_requirement_mm"),
        "soil_compatibility": info.get("soil_compatibility"),
        "common_diseases": info.get("common_diseases"),
        "crop_duration_days": info.get("crop_duration_days"),
        "management_notes": info.get("management_notes"),
    }


@router.get("/categories")
def get_crop_categories(current_user: User = Depends(get_current_user)):
    return CROP_CATEGORIES


@router.get("/regions")
def get_regions(current_user: User = Depends(get_current_user)):
    return REGIONS


@router.get("/seasons")
def get_seasons(current_user: User = Depends(get_current_user)):
    return SEASONS


@router.get("/all")
def get_all_crops(current_user: User = Depends(get_current_user)):
    """Return all supported crops with canonical info for the manual 'Start a Crop' flow."""
    crops = []
    for model_label, reg_info in CROP_REGISTRY.items():
        info = CROP_KNOWLEDGE.get(model_label, {})
        crops.append({
            "model_label": model_label,
            "canonical_id": reg_info["canonical_id"],
            "display_name": reg_info["display_name"],
            "category": reg_info["category"],
            "scientific_name": info.get("scientific_name"),
            "water_requirement": info.get("water_requirement"),
            "preferred_temp_range": info.get("preferred_temp_range"),
            "crop_duration_days": info.get("crop_duration_days"),
        })
    return crops
