import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.decision_engine import analyze_decision


def _base_context():
    return {
        "disease_result": {"predicted_disease": "Healthy", "confidence": 0.9},
        "weather": {
            "temperature": 28,
            "humidity": 65,
            "rainfall": 5,
            "wind_speed": 3,
            "agricultural_signals": {"fungal_risk": "Low", "heat_stress": "Low", "rain_risk": "Low"}
        },
        "crop_cycle": {"crop_name": "Tomato", "planting_date": "2026-09-01"},
        "expenses": [{"amount": 2000, "category": "Seeds"}, {"amount": 1500, "category": "Fertilizer"}]
    }


def test_input_changes_temperature_affects_scores():
    ctx = _base_context()
    base = analyze_decision(
        crop_recommendation=None,
        disease_result=ctx["disease_result"],
        weather=ctx["weather"],
        crop_cycle=ctx["crop_cycle"],
        expenses=ctx["expenses"]
    )

    modified_weather = {**ctx["weather"], "temperature": 5}
    modified = analyze_decision(
        crop_recommendation=None,
        disease_result=ctx["disease_result"],
        weather=modified_weather,
        crop_cycle=ctx["crop_cycle"],
        expenses=ctx["expenses"]
    )

    assert base["component_scores"]["profit"] != modified["component_scores"]["profit"], \
        f"Temperature change should affect profit: base={base['component_scores']['profit']}, modified={modified['component_scores']['profit']}"
    assert base["overall_score"] != modified["overall_score"], \
        f"Temperature change should affect overall: base={base['overall_score']}, modified={modified['overall_score']}"
    print(f"  PASS: temp 28→5 changed profit {base['component_scores']['profit']}→{modified['component_scores']['profit']}, overall {base['overall_score']}→{modified['overall_score']}")


def test_input_changes_rainfall_affects_water_score():
    ctx = _base_context()
    base = analyze_decision(
        crop_recommendation=None,
        disease_result=ctx["disease_result"],
        weather=ctx["weather"],
        crop_cycle=ctx["crop_cycle"],
        expenses=ctx["expenses"]
    )

    modified_weather = {**ctx["weather"], "rainfall": 30}
    modified = analyze_decision(
        crop_recommendation=None,
        disease_result=ctx["disease_result"],
        weather=modified_weather,
        crop_cycle=ctx["crop_cycle"],
        expenses=ctx["expenses"]
    )

    assert base["component_scores"]["water"] != modified["component_scores"]["water"], \
        f"Rainfall change should affect water score: base={base['component_scores']['water']}, modified={modified['component_scores']['water']}"
    print(f"  PASS: rainfall 5→30 changed water {base['component_scores']['water']}→{modified['component_scores']['water']}")


def test_input_changes_expenses_affect_cost_score():
    ctx = _base_context()
    base = analyze_decision(
        crop_recommendation=None,
        disease_result=ctx["disease_result"],
        weather=ctx["weather"],
        crop_cycle=ctx["crop_cycle"],
        expenses=ctx["expenses"]
    )

    modified_expenses = ctx["expenses"] + [{"amount": 15000, "category": "Other"}]
    modified = analyze_decision(
        crop_recommendation=None,
        disease_result=ctx["disease_result"],
        weather=ctx["weather"],
        crop_cycle=ctx["crop_cycle"],
        expenses=modified_expenses
    )

    assert base["component_scores"]["cost"] != modified["component_scores"]["cost"], \
        f"Expense change should affect cost: base={base['component_scores']['cost']}, modified={modified['component_scores']['cost']}"
    print(f"  PASS: expenses +15000 changed cost {base['component_scores']['cost']}→{modified['component_scores']['cost']}")


def test_input_changes_disease_affects_risk():
    ctx = _base_context()
    base = analyze_decision(
        crop_recommendation=None,
        disease_result=ctx["disease_result"],
        weather=ctx["weather"],
        crop_cycle=ctx["crop_cycle"],
        expenses=ctx["expenses"]
    )

    modified_disease = {"predicted_disease": "Late_Blight", "confidence": 0.9}
    modified = analyze_decision(
        crop_recommendation=None,
        disease_result=modified_disease,
        weather=ctx["weather"],
        crop_cycle=ctx["crop_cycle"],
        expenses=ctx["expenses"]
    )

    assert base["component_scores"]["risk"] != modified["component_scores"]["risk"], \
        f"Disease change should affect risk: base={base['component_scores']['risk']}, modified={modified['component_scores']['risk']}"
    assert modified["component_scores"]["risk"] < base["component_scores"]["risk"], \
        f"Disease should lower risk score: base={base['component_scores']['risk']}, modified={modified['component_scores']['risk']}"
    print(f"  PASS: Healthy→Late_Blight changed risk {base['component_scores']['risk']}→{modified['component_scores']['risk']}")


def test_current_plan_vs_modified_produces_different_results():
    ctx = _base_context()

    current_plan = analyze_decision(
        crop_recommendation=None,
        disease_result=ctx["disease_result"],
        weather=ctx["weather"],
        crop_cycle=ctx["crop_cycle"],
        expenses=ctx["expenses"]
    )

    modified_weather = {**ctx["weather"], "rainfall": 30, "irrigation": 0}
    modified_expenses = ctx["expenses"] + [{"amount": 3000, "category": "Other"}]
    modified_plan = analyze_decision(
        crop_recommendation=None,
        disease_result=ctx["disease_result"],
        weather=modified_weather,
        crop_cycle=ctx["crop_cycle"],
        expenses=modified_expenses
    )

    assert current_plan["overall_score"] != modified_plan["overall_score"], \
        f"Current and modified plans must differ: both={current_plan['overall_score']}"
    print(f"  PASS: Current Plan ({current_plan['overall_score']}) ≠ Modified Plan ({modified_plan['overall_score']})")


def test_identical_inputs_produce_identical_results():
    ctx = _base_context()
    result1 = analyze_decision(
        crop_recommendation=None,
        disease_result=ctx["disease_result"],
        weather=ctx["weather"],
        crop_cycle=ctx["crop_cycle"],
        expenses=ctx["expenses"]
    )
    result2 = analyze_decision(
        crop_recommendation=None,
        disease_result=ctx["disease_result"],
        weather=ctx["weather"],
        crop_cycle=ctx["crop_cycle"],
        expenses=ctx["expenses"]
    )

    assert result1["overall_score"] == result2["overall_score"], \
        f"Identical inputs must produce identical scores: {result1['overall_score']} vs {result2['overall_score']}"
    for key in result1["component_scores"]:
        assert result1["component_scores"][key] == result2["component_scores"][key], \
            f"Component {key} differs: {result1['component_scores'][key]} vs {result2['component_scores'][key]}"
    print(f"  PASS: Identical inputs → identical scores ({result1['overall_score']})")


def test_empty_input_changes_no_modification():
    ctx = _base_context()
    base = analyze_decision(
        crop_recommendation=None,
        disease_result=ctx["disease_result"],
        weather=ctx["weather"],
        crop_cycle=ctx["crop_cycle"],
        expenses=ctx["expenses"]
    )

    modified_weather = dict(ctx["weather"])
    modified_expenses = list(ctx["expenses"])
    result = analyze_decision(
        crop_recommendation=None,
        disease_result=ctx["disease_result"],
        weather=modified_weather,
        crop_cycle=ctx["crop_cycle"],
        expenses=modified_expenses
    )

    assert base["overall_score"] == result["overall_score"], \
        f"Empty input_changes must not change score: {base['overall_score']} vs {result['overall_score']}"
    print(f"  PASS: Empty input_changes → same score ({result['overall_score']})")


def test_multiple_changes_compound():
    ctx = _base_context()
    base = analyze_decision(
        crop_recommendation=None,
        disease_result=ctx["disease_result"],
        weather=ctx["weather"],
        crop_cycle=ctx["crop_cycle"],
        expenses=ctx["expenses"]
    )

    modified_weather = {**ctx["weather"], "temperature": 5, "humidity": 90, "rainfall": 30}
    modified_expenses = ctx["expenses"] + [{"amount": 10000, "category": "Pesticides"}]
    modified = analyze_decision(
        crop_recommendation=None,
        disease_result=ctx["disease_result"],
        weather=modified_weather,
        crop_cycle=ctx["crop_cycle"],
        expenses=modified_expenses
    )

    changed_scores = []
    for key in base["component_scores"]:
        if base["component_scores"][key] != modified["component_scores"][key]:
            changed_scores.append(key)

    assert len(changed_scores) >= 2, \
        f"At least 2 scores should change with multiple modifications, got {len(changed_scores)}: {changed_scores}"
    assert base["overall_score"] != modified["overall_score"]
    print(f"  PASS: Multiple changes affected {len(changed_scores)} scores ({changed_scores}), overall {base['overall_score']}→{modified['overall_score']}")


def test_irrigation_adds_to_rainfall():
    ctx = _base_context()
    base_weather = ctx["weather"]
    base_rainfall = base_weather["rainfall"]

    modified_weather = {**base_weather, "rainfall": base_rainfall + 15}
    base = analyze_decision(
        crop_recommendation=None,
        disease_result=ctx["disease_result"],
        weather=base_weather,
        crop_cycle=ctx["crop_cycle"],
        expenses=ctx["expenses"]
    )
    modified = analyze_decision(
        crop_recommendation=None,
        disease_result=ctx["disease_result"],
        weather=modified_weather,
        crop_cycle=ctx["crop_cycle"],
        expenses=ctx["expenses"]
    )

    assert base["component_scores"]["water"] != modified["component_scores"]["water"], \
        f"Irrigation should affect water score"
    print(f"  PASS: Irrigation +15mm changed water {base['component_scores']['water']}→{modified['component_scores']['water']}")


def test_pesticide_cost_affects_sustainability():
    ctx = _base_context()
    base = analyze_decision(
        crop_recommendation=None,
        disease_result=ctx["disease_result"],
        weather=ctx["weather"],
        crop_cycle=ctx["crop_cycle"],
        expenses=ctx["expenses"]
    )

    modified_expenses = ctx["expenses"] + [{"amount": 3000, "category": "Pesticides"}]
    modified = analyze_decision(
        crop_recommendation=None,
        disease_result=ctx["disease_result"],
        weather=ctx["weather"],
        crop_cycle=ctx["crop_cycle"],
        expenses=modified_expenses
    )

    assert base["component_scores"]["cost"] != modified["component_scores"]["cost"], \
        f"Pesticide cost should affect cost score"
    print(f"  PASS: Pesticide ₹3000 changed cost {base['component_scores']['cost']}→{modified['component_scores']['cost']}")


if __name__ == "__main__":
    print("Running scenario comparison tests...\n")
    test_input_changes_temperature_affects_scores()
    test_input_changes_rainfall_affects_water_score()
    test_input_changes_expenses_affect_cost_score()
    test_input_changes_disease_affects_risk()
    test_current_plan_vs_modified_produces_different_results()
    test_identical_inputs_produce_identical_results()
    test_empty_input_changes_no_modification()
    test_multiple_changes_compound()
    test_irrigation_adds_to_rainfall()
    test_pesticide_cost_affects_sustainability()
    print("\nAll scenario comparison tests passed!")
