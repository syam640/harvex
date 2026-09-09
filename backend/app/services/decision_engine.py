from typing import Dict, Any, Optional, List

WEIGHTS = {
    "profit": 0.30,
    "risk": 0.25,
    "cost": 0.20,
    "water": 0.15,
    "sustainability": 0.10
}


def normalize_score(value, min_val=0, max_val=100):
    if max_val == min_val:
        return 50.0
    normalized = ((value - min_val) / (max_val - min_val)) * 100
    return max(0, min(100, normalized))


def calculate_profit_score(crop_recommendation, disease_result, weather):
    score = 70.0

    if crop_recommendation:
        score += crop_recommendation.get("suitability_score", 0) * 20

    if disease_result:
        confidence = disease_result.get("confidence", 0)
        if disease_result.get("predicted_disease") == "Healthy":
            score += 10
        else:
            score -= confidence * 15

    if weather:
        temp = weather.get("temperature", 25)
        if 20 <= temp <= 30:
            score += 5
        elif temp < 10 or temp > 40:
            score -= 10

    return normalize_score(score)


def calculate_risk_score(disease_result, weather):
    score = 80.0

    if disease_result:
        disease = disease_result.get("predicted_disease", "")
        confidence = disease_result.get("confidence", 0)

        if disease == "Healthy":
            score += 15
        elif disease in ["Late_Blight", "Mosaic_Virus"]:
            score -= confidence * 25
        elif disease in ["Early_Blight", "Bacterial_Spot"]:
            score -= confidence * 15

    if weather:
        signals = weather.get("agricultural_signals", {})
        fungal = signals.get("fungal_risk", {})
        if isinstance(fungal, dict):
            fungal_level = fungal.get("level", "Low")
        else:
            fungal_level = fungal

        heat = signals.get("heat_stress", {})
        if isinstance(heat, dict):
            heat_level = heat.get("level", "Low")
        else:
            heat_level = heat

        if fungal_level == "High":
            score -= 15
        elif fungal_level == "Medium":
            score -= 8

        if heat_level == "High":
            score -= 10

    return normalize_score(score)


def calculate_cost_score(expenses):
    if not expenses:
        return 70.0

    total_cost = sum(e.get("amount", 0) for e in expenses)

    if total_cost < 1000:
        return 90.0
    elif total_cost < 5000:
        return 75.0
    elif total_cost < 10000:
        return 60.0
    else:
        return 45.0


def calculate_water_score(weather, crop_cycle):
    score = 75.0

    if weather:
        rainfall = weather.get("rainfall", 0)
        irrigation = weather.get("irrigation", 0)
        total_water = rainfall + irrigation
        humidity = weather.get("humidity", 50)

        if total_water > 20:
            score += 15
        elif total_water > 5:
            score += 8

        if humidity > 70:
            score += 5
        elif humidity < 30:
            score -= 10

    if crop_cycle:
        crop = crop_cycle.get("crop_name", "").lower()
        if crop in ["rice", "sugarcane"]:
            score += 5
        elif crop in ["millet", "sorghum"]:
            score -= 5

    return normalize_score(score)


def calculate_sustainability_score(disease_result, weather, expenses):
    score = 75.0

    if disease_result:
        if disease_result.get("predicted_disease") == "Healthy":
            score += 10

    if weather:
        signals = weather.get("agricultural_signals", {})
        fungal = signals.get("fungal_risk", {})
        if isinstance(fungal, dict):
            fungal_level = fungal.get("level", "Low")
        else:
            fungal_level = fungal

        if fungal_level == "Low":
            score += 5

    if expenses:
        pesticide_cost = sum(
            e.get("amount", 0) for e in expenses
            if e.get("category") == "Pesticides"
        )
        if pesticide_cost > 2000:
            score -= 10

    return normalize_score(score)


def _get_signal_level(signals: dict, key: str) -> str:
    """Extract signal level handling both dict {level, reason} and plain string formats."""
    val = signals.get(key, {})
    if isinstance(val, dict):
        return val.get("level", "Low")
    if isinstance(val, str):
        return val
    return "Low"


def analyze_decision(
    crop_recommendation: Optional[Dict[str, Any]],
    disease_result: Optional[Dict[str, Any]],
    weather: Optional[Dict[str, Any]],
    crop_cycle: Optional[Dict[str, Any]],
    expenses: list
):
    profit_score = calculate_profit_score(crop_recommendation, disease_result, weather)
    risk_score = calculate_risk_score(disease_result, weather)
    cost_score = calculate_cost_score(expenses)
    water_score = calculate_water_score(weather, crop_cycle)
    sustainability_score = calculate_sustainability_score(disease_result, weather, expenses)

    overall_score = (
        profit_score * WEIGHTS["profit"]
        + risk_score * WEIGHTS["risk"]
        + cost_score * WEIGHTS["cost"]
        + water_score * WEIGHTS["water"]
        + sustainability_score * WEIGHTS["sustainability"]
    )

    recommendation = generate_recommendation(
        profit_score, risk_score, cost_score, water_score, sustainability_score,
        disease_result, weather, crop_cycle, expenses
    )

    reasoning = generate_reasoning(
        profit_score, risk_score, cost_score, water_score, sustainability_score,
        disease_result, weather, crop_cycle, crop_recommendation, expenses
    )

    return {
        "recommended_action": recommendation,
        "overall_score": round(overall_score, 2),
        "component_scores": {
            "profit": round(profit_score, 2),
            "risk": round(risk_score, 2),
            "cost": round(cost_score, 2),
            "water": round(water_score, 2),
            "sustainability": round(sustainability_score, 2),
        },
        "reasoning": {"reasons": reasoning},
        "weights": WEIGHTS,
    }


def generate_recommendation(
    profit, risk, cost, water, sustainability,
    disease_result, weather, crop_cycle, expenses
):
    """Generate contextual recommendation based on actual inputs."""
    reasons = []

    # Disease-driven action
    if disease_result and disease_result.get("predicted_disease") not in (None, "Healthy", ""):
        disease = disease_result.get("predicted_disease", "unknown disease")
        confidence = disease_result.get("confidence", 0)
        if confidence > 0.7:
            return f"Treat detected disease ({disease.replace('_', ' ')}) promptly — high confidence detection"
        else:
            return f"Inspect crop for possible {disease.replace('_', ' ')} — moderate confidence detection"

    # Weather-driven irrigation decisions
    if weather:
        signals = weather.get("agricultural_signals", {})
        rain_risk = _get_signal_level(signals, "rain_risk")
        heat_stress = _get_signal_level(signals, "heat_stress")
        irrigation_need = _get_signal_level(signals, "irrigation_need")
        fungal_risk = _get_signal_level(signals, "fungal_risk")

        if rain_risk == "High":
            return "Delay irrigation — significant rainfall expected"
        if heat_stress == "High" and irrigation_need == "High":
            return "Irrigate immediately and provide shade — extreme heat with high water need"
        if heat_stress == "High":
            return "Increase irrigation and consider shade protection — high heat stress"
        if irrigation_need == "High" and rain_risk != "High":
            return "Schedule irrigation soon — water need is high and no significant rain expected"
        if fungal_risk == "High":
            return "Monitor for fungal disease and improve air circulation — high humidity risk"

    # Cost pressure
    if cost < 55:
        return "Review and reduce input costs — current spending is high relative to budget"

    # General based on overall score
    if overall := (profit * 0.3 + risk * 0.25 + cost * 0.2 + water * 0.15 + sustainability * 0.1):
        if overall >= 78:
            return "Continue current farming plan — conditions are favorable"
        elif overall >= 60:
            return "Monitor conditions and adjust as needed — moderate suitability"
        else:
            return "Review farm management strategy — several factors need attention"

    return "Continue current farming practices"


def generate_reasoning(
    profit, risk, cost, water, sustainability,
    disease_result, weather, crop_cycle, crop_recommendation, expenses
):
    """Generate reasoning that explains ALL relevant components."""
    reasons = []

    # Crop context
    if crop_cycle and crop_cycle.get("crop_name"):
        reasons.append(f"Growing: {crop_cycle['crop_name']}")

    # Profit
    if profit >= 78:
        reasons.append("Expected economic outcome is favorable")
    elif profit >= 60:
        reasons.append("Economic outlook is moderate")
    else:
        reasons.append("Economic pressure is elevated — review cost structure")

    # Risk
    if disease_result:
        disease = disease_result.get("predicted_disease", "Unknown")
        confidence = disease_result.get("confidence", 0)
        if disease == "Healthy":
            reasons.append(f"Crop appears healthy (confidence: {confidence:.0%})")
        elif disease:
            reasons.append(f"Detected {disease.replace('_', ' ')} with {confidence:.0%} confidence")
    if weather:
        signals = weather.get("agricultural_signals", {})
        fungal = _get_signal_level(signals, "fungal_risk")
        heat = _get_signal_level(signals, "heat_stress")
        if fungal in ("High", "Medium"):
            reasons.append(f"Fungal risk is {fungal.lower()} — monitor closely")
        if heat in ("High", "Medium"):
            reasons.append(f"Heat stress is {heat.lower()} — consider protective measures")

    # Cost
    if expenses:
        total = sum(e.get("amount", 0) for e in expenses)
        if total > 5000:
            reasons.append(f"Total expenses are ₹{total:,.0f} — cost pressure is high")
        elif total > 0:
            reasons.append(f"Total expenses are ₹{total:,.0f} — within manageable range")
    else:
        reasons.append("No expenses recorded yet")

    # Water
    if weather:
        rainfall = weather.get("rainfall", 0)
        irrigation = weather.get("irrigation", 0)
        humidity = weather.get("humidity", 0)
        irrigation_need = _get_signal_level(weather.get("agricultural_signals", {}), "irrigation_need")
        if irrigation > 0:
            total = rainfall + irrigation
            if irrigation_need == "High":
                reasons.append(f"Water need is high (total: {total}mm = rainfall {rainfall}mm + irrigation {irrigation}mm)")
            elif irrigation_need == "Medium":
                reasons.append(f"Water need is moderate (total: {total}mm = rainfall {rainfall}mm + irrigation {irrigation}mm)")
            else:
                reasons.append(f"Water sufficiency is adequate (total: {total}mm = rainfall {rainfall}mm + irrigation {irrigation}mm)")
        else:
            if irrigation_need == "High":
                reasons.append(f"Water need is high (rainfall: {rainfall}mm, humidity: {humidity}%)")
            elif irrigation_need == "Medium":
                reasons.append(f"Water need is moderate (rainfall: {rainfall}mm)")
            else:
                reasons.append(f"Water need is low (rainfall: {rainfall}mm)")

    # Sustainability
    if sustainability >= 78:
        reasons.append("Sustainability outlook is positive")
    elif sustainability < 60:
        reasons.append("Sustainability concerns — review pesticide usage and practices")

    if not reasons:
        reasons.append("Insufficient data for detailed analysis")

    return reasons
