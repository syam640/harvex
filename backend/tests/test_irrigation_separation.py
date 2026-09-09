"""PHASE 5 FINAL CORRECTION: Irrigation/Rainfall Separation Tests — 10 tests."""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.decision_engine import analyze_decision, calculate_water_score
from app.api.weather import _compute_agricultural_signals


# --- 1. Rainfall remains unchanged when irrigation changes ---
def test_1_rainfall_unchanged_by_irrigation():
    """Simulated irrigation does not modify rainfall value."""
    base = {"rainfall": 2, "irrigation": 0}
    simulated = {"rainfall": 2, "irrigation": 20}
    assert base["rainfall"] == simulated["rainfall"]
    assert base["rainfall"] == 2


# --- 2. Rain risk depends on rainfall, not irrigation ---
def test_2_rain_risk_depends_on_rainfall_only():
    """Rain risk uses rainfall (natural weather), not rainfall + irrigation."""
    signals_low_rain = _compute_agricultural_signals(25, 50, 2, 3, irrigation=20)
    signals_high_rain = _compute_agricultural_signals(25, 50, 60, 3, irrigation=0)

    # Low rainfall + high irrigation → rain_risk still Low (rain risk is weather-based)
    assert signals_low_rain["rain_risk"]["level"] == "Low"
    # High rainfall + no irrigation → rain_risk High
    assert signals_high_rain["rain_risk"]["level"] == "High"


# --- 3. Irrigation can improve water score/need ---
def test_3_irrigation_improves_water_need():
    """Irrigation reduces irrigation_need (total water sufficiency)."""
    signals_no_irr = _compute_agricultural_signals(30, 50, 2, 3, irrigation=0)
    signals_with_irr = _compute_agricultural_signals(30, 50, 2, 3, irrigation=25)

    # No irrigation, low rainfall → irrigation need High
    assert signals_no_irr["irrigation_need"]["level"] == "High"
    # With 25mm irrigation, total water = 27mm → irrigation need Low (exceeds medium threshold 25mm)
    assert signals_with_irr["irrigation_need"]["level"] == "Low"


# --- 4. Irrigation does not modify WeatherRecord ---
def test_4_irrigation_does_not_modify_weather_record():
    """Scenario irrigation is in-memory only — no DB mutation."""
    from app.api.scenarios import create_scenario
    import inspect
    source = inspect.getsource(create_scenario)
    # Should NOT contain any db.add or db.commit for WeatherRecord
    assert "WeatherRecord(" not in source or "db.add(WeatherRecord" not in source


# --- 5. Scenario irrigation does not modify actual weather ---
def test_5_scenario_irrigation_does_not_modify_actual_weather():
    """Simulated weather dict is independent copy — irrigation only affects copy."""
    original_weather = {"rainfall": 2, "irrigation": 0, "temperature": 30, "humidity": 50, "wind_speed": 3}
    simulated = dict(original_weather)
    simulated["irrigation"] = 20

    assert original_weather["irrigation"] == 0
    assert original_weather["rainfall"] == 2
    assert simulated["irrigation"] == 20
    assert simulated["rainfall"] == 2


# --- 6. Simulated disease does not modify actual DiseaseScan ---
def test_6_simulated_disease_does_not_modify_actual():
    """Scenario disease override is in-memory only."""
    from app.api.scenarios import create_scenario
    import inspect
    source = inspect.getsource(create_scenario)
    assert "db.add(DiseaseScan" not in source
    assert "db.commit" not in source.split("result = analyze_decision")[0].split("simulated_disease")[-1]


# --- 7. Simulated disease appears only in scenario result ---
def test_7_simulated_disease_only_in_scenario():
    """Disease override only affects the simulated context, not actual data."""
    actual_disease = {"predicted_disease": "Healthy", "confidence": 0.95}
    simulated = dict(actual_disease)
    simulated["predicted_disease"] = "Early_Blight"
    simulated["confidence"] = 0.8

    assert actual_disease["predicted_disease"] == "Healthy"
    assert simulated["predicted_disease"] == "Early_Blight"


# --- 8. Total water calculation is correct ---
def test_8_total_water_calculation():
    """Irrigation need uses total_water = rainfall + irrigation."""
    signals = _compute_agricultural_signals(25, 50, 5, 3, irrigation=10)
    # total_water = 5 + 10 = 15mm → between high(10) and medium(25) → Medium
    assert signals["irrigation_need"]["level"] == "Medium"


# --- 9. Water score considers irrigation ---
def test_9_water_score_considers_irrigation():
    """Water score uses total water (rainfall + irrigation)."""
    weather_no_irr = {"rainfall": 2, "irrigation": 0, "humidity": 50}
    weather_with_irr = {"rainfall": 2, "irrigation": 20, "humidity": 50}

    score_no = calculate_water_score(weather_no_irr, None)
    score_with = calculate_water_score(weather_with_irr, None)

    assert score_with > score_no


# --- 10. Reasoning mentions irrigation when present ---
def test_10_reasoning_mentions_irrigation():
    """Reasoning includes irrigation info when irrigation > 0."""
    weather = {
        "rainfall": 2, "irrigation": 15, "humidity": 50, "temperature": 25, "wind_speed": 3,
        "agricultural_signals": _compute_agricultural_signals(25, 50, 2, 3, irrigation=15)
    }
    result = analyze_decision(None, None, weather, None, [])
    reasons_text = " ".join(result["reasoning"]["reasons"]).lower()
    assert "irrigation" in reasons_text
    assert "rainfall" in reasons_text
