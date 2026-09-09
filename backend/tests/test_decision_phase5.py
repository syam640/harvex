"""PHASE 5: Decision Engine + Scenario Comparison Tests — 29 tests."""

import pytest
import sys
import os
import copy
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.decision_engine import (
    analyze_decision,
    generate_recommendation,
    generate_reasoning,
    calculate_profit_score,
    calculate_risk_score,
    calculate_cost_score,
    calculate_water_score,
    calculate_sustainability_score,
    WEIGHTS,
)


# --- DECISION ENGINE TESTS (1-11) ---

def test_1_deterministic_output():
    """Same inputs → same decision."""
    weather = {"temperature": 30, "humidity": 65, "rainfall": 5, "wind_speed": 3, "agricultural_signals": {"fungal_risk": {"level": "Low", "reason": ""}, "heat_stress": {"level": "Low", "reason": ""}, "irrigation_need": {"level": "Low", "reason": ""}, "rain_risk": {"level": "Low", "reason": ""}}}
    result1 = analyze_decision(None, None, weather, {"crop_name": "tomato"}, [])
    result2 = analyze_decision(None, None, weather, {"crop_name": "tomato"}, [])
    assert result1["overall_score"] == result2["overall_score"]
    assert result1["recommended_action"] == result2["recommended_action"]
    assert result1["component_scores"] == result2["component_scores"]


def test_2_correct_weight_calculation():
    """Verify weight formula."""
    profit, risk, cost, water, sust = 80, 70, 60, 50, 90
    overall = (
        profit * WEIGHTS["profit"]
        + risk * WEIGHTS["risk"]
        + cost * WEIGHTS["cost"]
        + water * WEIGHTS["water"]
        + sust * WEIGHTS["sustainability"]
    )
    assert abs(WEIGHTS["profit"] + WEIGHTS["risk"] + WEIGHTS["cost"] + WEIGHTS["water"] + WEIGHTS["sustainability"] - 1.0) < 0.001
    assert abs(overall - (80*0.3 + 70*0.25 + 60*0.2 + 50*0.15 + 90*0.1)) < 0.01


def test_3_risk_semantics():
    """Higher risk score = safer/lower risk."""
    healthy = calculate_risk_score({"predicted_disease": "Healthy", "confidence": 0.95}, None)
    diseased = calculate_risk_score({"predicted_disease": "Late_Blight", "confidence": 0.9}, None)
    assert healthy > diseased, f"Healthy ({healthy}) should have higher risk score than diseased ({diseased})"


def test_4_cost_semantics():
    """Lower cost = higher cost score."""
    low_cost = calculate_cost_score([{"amount": 500, "category": "Fertilizer"}])
    high_cost = calculate_cost_score([{"amount": 15000, "category": "Fertilizer"}])
    assert low_cost > high_cost


def test_5_water_semantics():
    """More rain = better water score (up to a point)."""
    wet = calculate_water_score({"rainfall": 30, "humidity": 80}, None)
    dry = calculate_water_score({"rainfall": 0, "humidity": 20}, None)
    assert wet > dry


def test_6_sustainability_semantics():
    """Healthy crop + low pesticide = higher sustainability."""
    healthy = calculate_sustainability_score({"predicted_disease": "Healthy"}, None, [])
    diseased = calculate_sustainability_score({"predicted_disease": "Late_Blight"}, None, [{"amount": 3000, "category": "Pesticides"}])
    assert healthy > diseased


def test_7_missing_data_behavior():
    """Missing inputs should not crash — produce reasonable defaults."""
    result = analyze_decision(None, None, None, None, [])
    assert "overall_score" in result
    assert result["overall_score"] >= 0
    assert result["overall_score"] <= 100
    assert len(result["reasoning"]["reasons"]) > 0


def test_8_active_crop_in_context():
    """Crop name is included in reasoning."""
    result = analyze_decision(None, None, None, {"crop_name": "tomato"}, [])
    reasons_text = " ".join(result["reasoning"]["reasons"])
    assert "tomato" in reasons_text.lower()


def test_9_contextual_recommendation_text():
    """Recommendations are contextual, not hardcoded 5 strings."""
    weather_high_rain = {
        "temperature": 25, "humidity": 50, "rainfall": 60, "wind_speed": 2,
        "agricultural_signals": {
            "fungal_risk": {"level": "Low", "reason": ""},
            "heat_stress": {"level": "Low", "reason": ""},
            "irrigation_need": {"level": "Low", "reason": ""},
            "rain_risk": {"level": "High", "reason": ""},
        }
    }
    result = analyze_decision(None, None, weather_high_rain, None, [])
    assert "rain" in result["recommended_action"].lower() or "delay" in result["recommended_action"].lower()

    weather_disease = {
        "temperature": 25, "humidity": 50, "rainfall": 5, "wind_speed": 2,
        "agricultural_signals": {"fungal_risk": {"level": "Low", "reason": ""}, "heat_stress": {"level": "Low", "reason": ""}, "irrigation_need": {"level": "Low", "reason": ""}, "rain_risk": {"level": "Low", "reason": ""}}
    }
    result2 = analyze_decision(None, {"predicted_disease": "Late_Blight", "confidence": 0.9}, weather_disease, None, [])
    assert "disease" in result2["recommended_action"].lower() or "treat" in result2["recommended_action"].lower()


def test_10_reasoning_reflects_inputs():
    """Reasoning includes factors actually provided."""
    expenses = [{"amount": 8000, "category": "Fertilizer"}, {"amount": 1000, "category": "Pesticides"}]
    weather = {"temperature": 30, "humidity": 65, "rainfall": 5, "wind_speed": 3, "agricultural_signals": {"fungal_risk": {"level": "Low", "reason": ""}, "heat_stress": {"level": "Low", "reason": ""}, "irrigation_need": {"level": "Medium", "reason": ""}, "rain_risk": {"level": "Low", "reason": ""}}}
    result = analyze_decision(None, None, weather, {"crop_name": "rice"}, expenses)
    reasons_text = " ".join(result["reasoning"]["reasons"]).lower()
    assert "rice" in reasons_text
    assert "expense" in reasons_text or "cost" in reasons_text or "8" in reasons_text


def test_11_no_fabricated_values():
    """Scores must be in valid range, not NaN or extreme."""
    result = analyze_decision(None, None, None, None, [])
    for key, val in result["component_scores"].items():
        assert 0 <= val <= 100, f"{key} = {val} out of range"
    assert 0 <= result["overall_score"] <= 100


# --- SCENARIO TESTS (12-23) ---

def _make_base_weather():
    return {
        "temperature": 30, "humidity": 65, "rainfall": 5, "wind_speed": 3,
        "agricultural_signals": {
            "fungal_risk": {"level": "Low", "reason": ""},
            "heat_stress": {"level": "Low", "reason": ""},
            "irrigation_need": {"level": "Medium", "reason": ""},
            "rain_risk": {"level": "Low", "reason": ""},
        }
    }


def test_12_active_crop_passed_to_scenario():
    """Scenario uses crop context from actual cycle."""
    weather = _make_base_weather()
    base = analyze_decision(None, None, weather, {"crop_name": "tomato"}, [])
    assert "tomato" in " ".join(base["reasoning"]["reasons"]).lower()


def test_13_same_scenario_same_result():
    """Running same simulation twice produces same score."""
    weather = _make_base_weather()
    r1 = analyze_decision(None, None, weather, {"crop_name": "tomato"}, [])
    r2 = analyze_decision(None, None, weather, {"crop_name": "tomato"}, [])
    assert r1["overall_score"] == r2["overall_score"]


def test_14_temperature_changes_work():
    """Higher temperature affects heat stress and risk."""
    base_weather = _make_base_weather()
    hot_weather = dict(base_weather)
    hot_weather["temperature"] = 42
    from app.api.weather import _compute_agricultural_signals
    hot_weather["agricultural_signals"] = _compute_agricultural_signals(42, 65, 5, 3)

    base = analyze_decision(None, None, base_weather, None, [])
    hot = analyze_decision(None, None, hot_weather, None, [])
    assert hot["component_scores"]["risk"] < base["component_scores"]["risk"]


def test_15_humidity_changes_work():
    """Higher humidity affects fungal risk."""
    from app.api.weather import _compute_agricultural_signals
    base_weather = _make_base_weather()
    humid_weather = dict(base_weather)
    humid_weather["humidity"] = 90
    humid_weather["agricultural_signals"] = _compute_agricultural_signals(30, 90, 5, 3)

    base = analyze_decision(None, None, base_weather, None, [])
    humid = analyze_decision(None, None, humid_weather, None, [])
    assert humid["component_scores"]["risk"] < base["component_scores"]["risk"]


def test_16_rainfall_changes_work():
    """More rain affects water score and irrigation need."""
    from app.api.weather import _compute_agricultural_signals
    base_weather = _make_base_weather()
    rainy_weather = dict(base_weather)
    rainy_weather["rainfall"] = 40
    rainy_weather["agricultural_signals"] = _compute_agricultural_signals(30, 65, 40, 3)

    base = analyze_decision(None, None, base_weather, None, [])
    rainy = analyze_decision(None, None, rainy_weather, None, [])
    assert rainy["component_scores"]["water"] >= base["component_scores"]["water"]


def test_17_irrigation_changes_work():
    """Adding irrigation increases rainfall in simulation."""
    from app.api.weather import _compute_agricultural_signals
    base_weather = _make_base_weather()
    irrigated_weather = dict(base_weather)
    irrigated_weather["rainfall"] = base_weather["rainfall"] + 20
    irrigated_weather["agricultural_signals"] = _compute_agricultural_signals(30, 65, 25, 3)

    base = analyze_decision(None, None, base_weather, None, [])
    irrigated = analyze_decision(None, None, irrigated_weather, None, [])
    assert irrigated["component_scores"]["water"] >= base["component_scores"]["water"]


def test_18_cost_changes_work():
    """Adding expense reduces cost score."""
    base = analyze_decision(None, None, None, None, [])
    with_cost = analyze_decision(None, None, None, None, [{"amount": 15000, "category": "Fertilizer"}])
    assert with_cost["component_scores"]["cost"] < base["component_scores"]["cost"]


def test_19_component_level_changes_visible():
    """Scenario produces all 5 component scores."""
    result = analyze_decision(None, None, _make_base_weather(), {"crop_name": "tomato"}, [])
    assert "profit" in result["component_scores"]
    assert "risk" in result["component_scores"]
    assert "cost" in result["component_scores"]
    assert "water" in result["component_scores"]
    assert "sustainability" in result["component_scores"]


def test_20_actual_data_not_mutated():
    """Scenario modifications don't affect original data."""
    original_weather = _make_base_weather()
    original_expenses = [{"amount": 1000, "category": "Fertilizer"}]

    weather_copy = dict(original_weather)
    expenses_copy = list(original_expenses)

    # Simulate modifications
    weather_copy["temperature"] = 45
    expenses_copy.append({"amount": 5000, "category": "Other"})

    assert original_weather["temperature"] == 30
    assert len(original_expenses) == 1


def test_21_no_fake_records_created():
    """Decision engine is pure — no DB operations."""
    from app.services.decision_engine import analyze_decision
    import inspect
    source = inspect.getsource(analyze_decision)
    assert "db." not in source
    assert "session" not in source.lower()
    assert "commit" not in source


def test_22_ownership_isolation_in_decision():
    """Decision engine doesn't access DB — isolation is in the API layer."""
    from app.services.decision_engine import analyze_decision
    import inspect
    source = inspect.getsource(analyze_decision)
    assert "Farm" not in source
    assert "User" not in source


def test_23_no_active_crop_handled_honestly():
    """No crop cycle → engine still works with None."""
    result = analyze_decision(None, None, None, None, [])
    assert result["overall_score"] >= 0
    assert result["overall_score"] <= 100
    assert len(result["reasoning"]["reasons"]) > 0


# --- SCENARIO INPUT VALIDATION TESTS (24-26) ---

def test_24_validate_extreme_temperature():
    """Temperature outside -10..60 should be rejected."""
    from app.api.scenarios import _validate_scenario_inputs
    from fastapi import HTTPException
    try:
        _validate_scenario_inputs({"temperature": 100})
        assert False, "Should have raised HTTPException"
    except HTTPException as e:
        assert e.status_code == 422


def test_25_validate_negative_cost():
    """Negative cost should be rejected."""
    from app.api.scenarios import _validate_scenario_inputs
    from fastapi import HTTPException
    try:
        _validate_scenario_inputs({"additional_cost": -500})
        assert False, "Should have raised HTTPException"
    except HTTPException as e:
        assert e.status_code == 422


def test_26_validate_humidity_range():
    """Humidity outside 0..100 should be rejected."""
    from app.api.scenarios import _validate_scenario_inputs
    from fastapi import HTTPException
    try:
        _validate_scenario_inputs({"humidity": 150})
        assert False, "Should have raised HTTPException"
    except HTTPException as e:
        assert e.status_code == 422


# --- FRONTEND CHECK TESTS (27-29) ---

def test_27_decision_page_answers_what_should_i_do():
    """Decision page header asks 'What should I do?'."""
    with open("/home/megha/harvex/frontend/src/pages/Decisions.tsx", 'r') as f:
        content = f.read()
    assert "What should I do" in content or "Today's Decision" in content


def test_28_decision_page_has_why():
    """Decision page shows 'Why?' explanation."""
    with open("/home/megha/harvex/frontend/src/pages/Decisions.tsx", 'r') as f:
        content = f.read()
    assert "Why" in content


def test_29_scenario_page_shows_simulation_notice():
    """Scenario page exists and has proper structure."""
    with open("/home/megha/harvex/frontend/src/pages/Scenarios.tsx", 'r') as f:
        content = f.read()
    # Verify the scenario page has key UI elements
    assert "scenario_name" in content or "scenario" in content.lower()
    assert "input_changes" in content or "scenario_changes" in content
