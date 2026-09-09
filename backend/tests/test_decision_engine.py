import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.decision_engine import (
    analyze_decision,
    normalize_score,
    calculate_profit_score,
    calculate_risk_score,
    calculate_cost_score,
    calculate_water_score,
    calculate_sustainability_score,
    WEIGHTS
)

def test_weights_sum_to_100():
    total = sum(WEIGHTS.values())
    assert abs(total - 1.0) < 0.001, f"Weights sum to {total}, expected 1.0"

def test_normalize_score():
    assert normalize_score(50, 0, 100) == 50.0
    assert normalize_score(0, 0, 100) == 0.0
    assert normalize_score(100, 0, 100) == 100.0
    assert normalize_score(50, 0, 200) == 25.0

def test_scores_remain_0_100():
    result = analyze_decision(
        crop_recommendation={"suitability_score": 0.8},
        disease_result={"predicted_disease": "Healthy", "confidence": 0.9},
        weather={"temperature": 25, "humidity": 60, "rainfall": 10, "agricultural_signals": {"fungal_risk": "Low"}},
        crop_cycle={"crop_name": "Tomato", "planting_date": "2026-09-01"},
        expenses=[{"amount": 5000}]
    )
    
    for score in result["component_scores"].values():
        assert 0 <= score <= 100, f"Score {score} out of range"
    assert 0 <= result["overall_score"] <= 100

def test_higher_risk_produces_lower_score():
    healthy_result = analyze_decision(
        crop_recommendation=None,
        disease_result={"predicted_disease": "Healthy", "confidence": 0.9},
        weather=None,
        crop_cycle=None,
        expenses=[]
    )
    
    diseased_result = analyze_decision(
        crop_recommendation=None,
        disease_result={"predicted_disease": "Late_Blight", "confidence": 0.9},
        weather=None,
        crop_cycle=None,
        expenses=[]
    )
    
    assert healthy_result["component_scores"]["risk"] > diseased_result["component_scores"]["risk"]

def test_missing_data_does_not_crash():
    result = analyze_decision(
        crop_recommendation=None,
        disease_result=None,
        weather=None,
        crop_cycle=None,
        expenses=[]
    )
    
    assert "overall_score" in result
    assert "component_scores" in result
    assert "recommended_action" in result

def test_deterministic_output():
    inputs = {
        "crop_recommendation": {"suitability_score": 0.7},
        "disease_result": {"predicted_disease": "Healthy", "confidence": 0.85},
        "weather": {"temperature": 28, "humidity": 65, "rainfall": 5, "agricultural_signals": {"fungal_risk": "Low"}},
        "crop_cycle": {"crop_name": "Rice", "planting_date": "2026-08-15"},
        "expenses": [{"amount": 3000}]
    }
    
    result1 = analyze_decision(**inputs)
    result2 = analyze_decision(**inputs)
    
    assert result1["overall_score"] == result2["overall_score"]

def test_no_nan_values():
    result = analyze_decision(
        crop_recommendation={"suitability_score": 0.5},
        disease_result={"predicted_disease": "Early_Blight", "confidence": 0.7},
        weather={"temperature": 30, "humidity": 80, "rainfall": 20, "agricultural_signals": {"fungal_risk": "High"}},
        crop_cycle={"crop_name": "Tomato", "planting_date": "2026-09-01"},
        expenses=[{"amount": 10000}]
    )
    
    import math
    for key, value in result["component_scores"].items():
        assert not math.isnan(value), f"NaN in {key}"
    assert not math.isnan(result["overall_score"])

def test_no_division_by_zero():
    result = analyze_decision(
        crop_recommendation=None,
        disease_result=None,
        weather=None,
        crop_cycle=None,
        expenses=[{"amount": 0}]
    )
    
    assert not math.isnan(result["overall_score"])

import math

if __name__ == "__main__":
    test_weights_sum_to_100()
    test_normalize_score()
    test_scores_remain_0_100()
    test_higher_risk_produces_lower_score()
    test_missing_data_does_not_crash()
    test_deterministic_output()
    test_no_nan_values()
    test_no_division_by_zero()
    print("All decision engine tests passed!")
