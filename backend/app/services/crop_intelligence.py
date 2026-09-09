"""
HARVEX Intelligent Crop Recommendation Engine
Deterministic ranking + AI reasoning + soil intelligence + weather context.

Architecture:
External/official data
    |
Structured facts
    |
Crop knowledge catalog
    |
NVIDIA AI reasoning
    |
Validated JSON
    |
Deterministic ranking
    |
Farmer recommendation
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# DETERMINISTIC RANKING WEIGHTS
# =============================================================================

RANKING_WEIGHTS = {
    "soil": 0.20,
    "climate": 0.20,
    "water": 0.15,
    "season": 0.15,
    "location": 0.10,
    "irrigation": 0.10,
    "risk": 0.10,
}


# =============================================================================
# DATA PROVENANCE CHECK
# =============================================================================

def validate_provenance(context: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure no AI-injected measurements silently enter the farm context.
    Returns validation report."""
    issues = []
    soil = context.get("soil", {})
    weather = context.get("weather", {})
    location = context.get("location", {})

    # Soil provenance
    for field in ["ph", "nitrogen", "phosphorus", "potassium", "soil_type", "organic_carbon"]:
        val = soil.get(field)
        if val and isinstance(val, dict):
            status = val.get("status", "unknown")
            source = val.get("source", "unknown")
            is_measured = val.get("is_field_measurement", False)
            if status == "estimated" and is_measured:
                issues.append(f"Soil {field}: estimated but marked as field measurement")
            if status == "unavailable" and val.get("value") is not None:
                issues.append(f"Soil {field}: marked unavailable but has value")

    # Weather provenance
    if weather:
        for field in ["temperature", "humidity", "rainfall"]:
            val = weather.get(field)
            if val and isinstance(val, dict):
                status = val.get("status", "unknown")
                if status == "unavailable" and val.get("value") is not None:
                    issues.append(f"Weather {field}: marked unavailable but has value")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "checked_at": datetime.utcnow().isoformat(),
    }


# =============================================================================
# DETERMINISTIC SUITABILITY SCORING
# =============================================================================

def _score_range(value: float, preferred_range: Tuple[float, float],
                 penalty_per_unit: float = 1.0, max_penalty: float = 40.0) -> float:
    """Score how well a value fits within a preferred range. Returns 0-100."""
    low, high = preferred_range
    if low <= value <= high:
        return 100.0
    distance = min(abs(value - low), abs(value - high))
    penalty = min(distance * penalty_per_unit, max_penalty)
    return max(0.0, 100.0 - penalty)


def _score_soil(crop: Dict, soil_data: Dict) -> Tuple[float, List[str]]:
    """Score soil compatibility: type match (50%) + pH fit (50%)."""
    reasons = []
    soil_req = crop.get("soil_requirements", {})
    compatible_types = [s.lower() for s in soil_req.get("soil_types", [])]

    # Soil type
    soil_type_val = soil_data.get("soil_type")
    if soil_type_val and isinstance(soil_type_val, dict):
        raw_val = soil_type_val.get("value")
        soil_type_value = raw_val.lower() if raw_val else ""
    elif isinstance(soil_type_val, str):
        soil_type_value = soil_type_val.lower()
    else:
        soil_type_value = ""

    if soil_type_value in compatible_types:
        type_score = 100.0
        reasons.append("Suitable soil type")
    elif soil_type_value:
        type_score = 20.0
        reasons.append("Soil type not in preferred list")
    else:
        type_score = 50.0
        reasons.append("Soil type unknown")

    # pH
    ph_data = soil_data.get("ph")
    if ph_data and isinstance(ph_data, dict):
        ph_value = ph_data.get("value")
        ph_status = ph_data.get("status", "unknown")
    elif isinstance(ph_data, (int, float)):
        ph_value = float(ph_data)
        ph_status = "estimated"
    else:
        ph_value = None
        ph_status = "unavailable"

    ph_range = soil_req.get("ph_range", [6.0, 7.5])
    if ph_value is not None:
        ph_score = _score_range(ph_value, tuple(ph_range), penalty_per_unit=20.0, max_penalty=50.0)
        if ph_range[0] <= ph_value <= ph_range[1]:
            reasons.append("Soil pH is within preferred range")
        else:
            reasons.append("Soil pH is outside preferred range")
    else:
        ph_score = 50.0
        reasons.append("pH data unavailable")

    combined = type_score * 0.50 + ph_score * 0.50
    return round(combined, 1), reasons


def _score_climate(crop: Dict, weather: Dict) -> Tuple[float, List[str]]:
    """Score climate compatibility: temp (40%) + humidity (25%) + rainfall (35%)."""
    reasons = []
    climate_req = crop.get("climate_requirements", {})
    temp_range = climate_req.get("temp_range", [15, 35])
    hum_range = climate_req.get("humidity_range", [40, 80])
    rain_range = climate_req.get("rainfall_mm", [500, 1000])

    # Temperature
    temp_data = weather.get("temperature")
    if temp_data and isinstance(temp_data, dict):
        temp_value = temp_data.get("value")
    elif isinstance(temp_data, (int, float)):
        temp_value = float(temp_data)
    else:
        temp_value = None

    if temp_value is not None:
        temp_score = _score_range(temp_value, tuple(temp_range), penalty_per_unit=4.0, max_penalty=40.0)
        if temp_range[0] <= temp_value <= temp_range[1]:
            reasons.append("Temperature suitable for this crop")
        else:
            reasons.append("Temperature outside preferred range")
    else:
        temp_score = 50.0
        reasons.append("Temperature data unavailable")

    # Humidity
    hum_data = weather.get("humidity")
    if hum_data and isinstance(hum_data, dict):
        hum_value = hum_data.get("value")
    elif isinstance(hum_data, (int, float)):
        hum_value = float(hum_data)
    else:
        hum_value = None

    if hum_value is not None:
        hum_score = _score_range(hum_value, tuple(hum_range), penalty_per_unit=2.0, max_penalty=25.0)
        if hum_range[0] <= hum_value <= hum_range[1]:
            reasons.append("Humidity suitable")
        else:
            reasons.append("Humidity outside preferred range")
    else:
        hum_score = 50.0
        reasons.append("Humidity data unavailable")

    # Rainfall
    rain_data = weather.get("rainfall")
    if rain_data and isinstance(rain_data, dict):
        rain_value = rain_data.get("value")
    elif isinstance(rain_data, (int, float)):
        rain_value = float(rain_data)
    else:
        rain_value = None

    if rain_value is not None:
        rain_score = _score_range(rain_value, tuple(rain_range), penalty_per_unit=0.05, max_penalty=35.0)
        if rain_range[0] <= rain_value <= rain_range[1]:
            reasons.append("Rainfall matches crop requirements")
        else:
            reasons.append("Rainfall outside preferred range")
    else:
        rain_score = 50.0
        reasons.append("Rainfall data unavailable")

    combined = temp_score * 0.40 + hum_score * 0.25 + rain_score * 0.35
    return round(combined, 1), reasons


def _score_water(crop: Dict, water_availability: str) -> Tuple[float, List[str]]:
    """Score water compatibility."""
    reasons = []
    water_req = crop.get("water_requirement", "medium")
    WATER_LEVELS = {"very_limited": 0.15, "limited": 0.3, "moderate": 0.6, "good": 0.8, "abundant": 0.95, "rainfed_only": 0.2}
    WATER_NEED = {"very_low": 0.2, "low": 0.4, "medium": 0.6, "high": 0.85, "very_high": 0.95}

    avail = WATER_LEVELS.get(water_availability, 0.6)
    needed = WATER_NEED.get(water_req, 0.6)

    if avail >= needed:
        score = 100.0
        reasons.append("Water availability meets crop requirement")
    elif avail >= needed * 0.7:
        score = 60.0
        reasons.append("Water availability is marginal for this crop")
    else:
        score = 15.0
        reasons.append("Water availability insufficient for this crop")

    return round(score, 1), reasons


def _score_season(crop: Dict, season: str) -> Tuple[float, List[str]]:
    """Score seasonal suitability."""
    reasons = []
    season_suit = crop.get("season_suitability", {})
    score_val = season_suit.get(season, 0.5)
    score = score_val * 100.0

    if score_val >= 0.8:
        reasons.append("Excellent season for this crop")
    elif score_val >= 0.5:
        reasons.append("Can be grown in this season")
    else:
        reasons.append("Not ideal for this season")

    return round(score, 1), reasons


def _score_location(crop: Dict, location: Dict) -> Tuple[float, List[str]]:
    """Score location suitability based on latitude (approximate region matching)."""
    reasons = []
    lat = location.get("latitude")

    if lat is None:
        return 50.0, ["Location data unavailable"]

    # Approximate region scoring based on latitude
    # Tropical (0-23.5): rice, banana, coconut, sugarcane, cotton
    # Subtropical (23.5-35): wheat, mustard, chickpea, most vegetables
    # Temperate (>35): apple, grapes, lentil
    abs_lat = abs(lat)

    crop_id = crop.get("crop_id", "")
    tropical_crops = {"rice", "banana", "coconut", "sugarcane", "cotton", "jute", "mango", "papaya", "turmeric", "ginger", "chilli"}
    subtropical_crops = {"wheat", "mustard", "chickpea", "pigeon_pea", "groundnut", "tomato", "onion", "potato", "okra", "brinjal", "cabbage", "soybean", "sunflower", "sesame", "maize", "sorghum", "pearl_millet", "finger_millet", "green_gram", "black_gram", "lentil"}
    temperate_crops = {"apple", "grapes", "lentil", "mustard"}

    if abs_lat < 23.5:
        if crop_id in tropical_crops:
            score = 90.0
            reasons.append("Tropical location suits this crop")
        elif crop_id in subtropical_crops:
            score = 70.0
            reasons.append("Location is warm; crop may grow with care")
        else:
            score = 50.0
            reasons.append("Location may not be ideal")
    elif abs_lat < 35:
        if crop_id in subtropical_crops:
            score = 85.0
            reasons.append("Subtropical location suits this crop")
        elif crop_id in tropical_crops:
            score = 55.0
            reasons.append("Location may be too cool for this tropical crop")
        else:
            score = 60.0
            reasons.append("Moderate location match")
    else:
        if crop_id in temperate_crops:
            score = 80.0
            reasons.append("Temperate location suits this crop")
        else:
            score = 35.0
            reasons.append("Location may be too cold for this crop")

    return round(score, 1), reasons


def _score_irrigation(crop: Dict, irrigation_method: str) -> Tuple[float, List[str]]:
    """Score irrigation compatibility."""
    reasons = []
    compatible = crop.get("irrigation_compatibility", [])

    if irrigation_method.lower() in [m.lower() for m in compatible]:
        score = 100.0
        reasons.append("Irrigation method compatible")
    elif irrigation_method.lower() == "rainfed" and "rainfed" in compatible:
        score = 100.0
        reasons.append("Rainfed farming compatible")
    elif irrigation_method.lower() == "rainfed":
        water_req = crop.get("water_requirement", "medium")
        if water_req in ["very_low", "low"]:
            score = 70.0
            reasons.append("Low water crop; may survive rainfed")
        else:
            score = 30.0
            reasons.append("Rainfed may be insufficient for this crop")
    else:
        score = 50.0
        reasons.append("Irrigation method not in preferred list")

    return round(score, 1), reasons


def _score_risk(crop: Dict, weather: Dict) -> Tuple[float, List[str]]:
    """Score risk: higher risk = lower score."""
    reasons = []
    risk_factors = crop.get("risk_factors", [])
    risk_score = 80.0  # base

    # Check weather for risk amplifiers
    temp_data = weather.get("temperature")
    if temp_data and isinstance(temp_data, dict):
        temp_val = temp_data.get("value")
    elif isinstance(temp_data, (int, float)):
        temp_val = float(temp_data)
    else:
        temp_val = None

    if temp_val and temp_val > 35:
        risk_score -= 15
        reasons.append("High temperature increases risk")
    if temp_val and temp_val < 10:
        risk_score -= 10
        reasons.append("Cold temperature increases risk")

    hum_data = weather.get("humidity")
    if hum_data and isinstance(hum_data, dict):
        hum_val = hum_data.get("value")
    elif isinstance(hum_data, (int, float)):
        hum_val = float(hum_data)
    else:
        hum_val = None

    if hum_val and hum_val > 80:
        risk_score -= 10
        reasons.append("High humidity increases disease risk")

    if not reasons:
        reasons.append("No major risk factors identified")

    return round(max(0.0, min(100.0, risk_score)), 1), reasons


def compute_deterministic_ranking(
    crop: Dict,
    context: Dict[str, Any],
) -> Dict[str, Any]:
    """Compute deterministic suitability score for a crop.
    Returns score + component breakdown + reasons."""
    soil = context.get("soil", {})
    weather = context.get("weather", {})
    water_raw = context.get("water", {})
    if isinstance(water_raw, dict):
        water_availability = water_raw.get("availability", "moderate")
    else:
        water_availability = water_raw or "moderate"
    season_raw = context.get("season", "kharif")
    if isinstance(season_raw, dict):
        season = season_raw.get("value", "kharif")
    else:
        season = season_raw or "kharif"
    location = context.get("location", {})
    irrigation_raw = context.get("irrigation", {})
    if isinstance(irrigation_raw, dict):
        irrigation = irrigation_raw.get("method", "rainfed")
    else:
        irrigation = irrigation_raw or "rainfed"

    soil_score, soil_reasons = _score_soil(crop, soil)
    climate_score, climate_reasons = _score_climate(crop, weather)
    water_score, water_reasons = _score_water(crop, water_availability)
    season_score, season_reasons = _score_season(crop, season)
    location_score, location_reasons = _score_location(crop, location)
    irrigation_score, irrigation_reasons = _score_irrigation(crop, irrigation)
    risk_score, risk_reasons = _score_risk(crop, weather)

    components = {
        "soil": soil_score,
        "climate": climate_score,
        "water": water_score,
        "season": season_score,
        "location": location_score,
        "irrigation": irrigation_score,
        "risk": risk_score,
    }

    overall = sum(
        components[k] * RANKING_WEIGHTS[k] for k in RANKING_WEIGHTS
    )

    limiting = [k for k, v in components.items() if v < 40]

    all_reasons = {
        "soil": soil_reasons,
        "climate": climate_reasons,
        "water": water_reasons,
        "season": season_reasons,
        "location": location_reasons,
        "irrigation": irrigation_reasons,
        "risk": risk_reasons,
    }

    return {
        "suitability_score": round(overall, 1),
        "component_scores": {k: round(v, 1) for k, v in components.items()},
        "limiting_factors": limiting,
        "all_reasons": all_reasons,
    }


# =============================================================================
# ELIGIBILITY FILTERING
# =============================================================================

def filter_eligible_crops(
    catalog: Dict[str, Dict],
    context: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Filter crops that are potentially eligible based on hard constraints."""
    eligible = []
    water_raw = context.get("water", {})
    if isinstance(water_raw, dict):
        water_availability = water_raw.get("availability", "moderate")
    else:
        water_availability = water_raw or "moderate"
    season_raw = context.get("season", "kharif")
    # Handle season as dict or string
    if isinstance(season_raw, dict):
        season = season_raw.get("value", "kharif")
    else:
        season = season_raw or "kharif"

    WATER_LEVELS = {"very_limited": 0.15, "limited": 0.3, "moderate": 0.6, "good": 0.8, "abundant": 0.95, "rainfed_only": 0.2}
    WATER_NEED = {"very_low": 0.2, "low": 0.4, "medium": 0.6, "high": 0.85, "very_high": 0.95}

    avail = WATER_LEVELS.get(water_availability, 0.6)

    for crop_id, crop in catalog.items():
        # Water hard filter: if availability is very limited, reject high/very_high water crops
        water_req = crop.get("water_requirement", "medium")
        needed = WATER_NEED.get(water_req, 0.6)
        if avail < needed * 0.5:
            continue  # Too water-scarce for this crop

        # Season hard filter: reject if season suitability < 0.1
        season_suit = crop.get("season_suitability", {})
        if season and season_suit.get(season, 0.5) < 0.1:
            continue

        eligible.append(crop)

    return eligible


# =============================================================================
# BUILD RECOMMENDATION CONTEXT
# =============================================================================

def build_recommendation_context(
    location: Dict[str, Any],
    weather: Dict[str, Any],
    soil: Dict[str, Any],
    water_availability: str,
    irrigation_method: str,
    season: str,
    farm_history: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Build structured recommendation context."""
    return {
        "location": {
            "latitude": location.get("latitude"),
            "longitude": location.get("longitude"),
            "name": location.get("name", "Unknown"),
            "source": location.get("source", "unknown"),
            "timestamp": datetime.utcnow().isoformat(),
        },
        "season": {
            "value": season,
            "current_date": datetime.utcnow().isoformat(),
        },
        "weather": weather,
        "soil": soil,
        "water": {
            "availability": water_availability,
        },
        "irrigation": {
            "method": irrigation_method,
        },
        "farm_history": farm_history or {},
    }


# =============================================================================
# BUILD AI RESEARCH CONTEXT
# =============================================================================

def build_ai_research_context(
    candidates: List[Dict[str, Any]],
    context: Dict[str, Any],
) -> str:
    """Build structured prompt for AI crop research."""
    context_summary = {
        "location": context.get("location", {}),
        "season": context.get("season", {}),
        "water_availability": context.get("water_availability"),
        "irrigation_method": context.get("irrigation_method"),
        "soil_status": {},
        "weather_status": {},
    }

    soil = context.get("soil", {})
    for field in ["ph", "soil_type", "nitrogen", "phosphorus", "potassium"]:
        val = soil.get(field)
        if val and isinstance(val, dict):
            context_summary["soil_status"][field] = {
                "value": val.get("value"),
                "status": val.get("status", "unknown"),
            }
        elif isinstance(val, (int, float, str)):
            context_summary["soil_status"][field] = {"value": val, "status": "provided"}

    weather = context.get("weather", {})
    for field in ["temperature", "humidity", "rainfall"]:
        val = weather.get(field)
        if val and isinstance(val, dict):
            context_summary["weather_status"][field] = {
                "value": val.get("value"),
                "status": val.get("status", "unknown"),
            }
        elif isinstance(val, (int, float)):
            context_summary["weather_status"][field] = {"value": val, "status": "measured"}

    candidate_summary = []
    for c in candidates:
        candidate_summary.append({
            "crop_id": c.get("crop_id"),
            "name": c.get("name_en"),
            "category": c.get("category"),
            "water_requirement": c.get("water_requirement"),
            "season_suitability": c.get("season_suitability"),
            "risk_factors": c.get("risk_factors", []),
        })

    return json.dumps({
        "farm_context": context_summary,
        "candidate_crops": candidate_summary,
    }, indent=2)
