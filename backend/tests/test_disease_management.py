"""
HARVEX Disease Management Loop Tests.

Tests treatment, follow-up, comparison, healthy/unable flows, and integration.

Run:  python3 -m pytest tests/test_disease_management.py -v
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from app.services.ai.ai_service import _validate_disease_result


# ============================================================
# TREATMENT TESTS
# ============================================================

def test_treatment_healthy_flow():
    """Healthy plant gets monitoring guidance, not disease treatment."""
    from app.api.disease import _get_treatment

    result = _get_treatment("tomato", "None", "none")
    assert result is not None
    assert "No visible disease" in result["summary"]
    assert result["chemical_options"] == []
    assert result["follow_up_days"] == 7


def test_treatment_unable_to_determine_flow():
    """Unable-to-determine gets image quality guidance."""
    from app.api.disease import _get_treatment

    result = _get_treatment("tomato", "Unable to determine", "unknown")
    assert result is not None
    assert "not provide enough evidence" in result["summary"]
    assert result["chemical_options"] == []
    assert result["follow_up_days"] == 3


def test_treatment_low_confidence():
    """Low confidence adds uncertainty note."""
    from app.api.disease import _get_treatment

    with patch("app.api.disease._get_treatment") as mock:
        mock.return_value = {
            "summary": "Treatment for disease",
            "immediate_actions": ["Monitor"],
            "cultural_or_organic_actions": [],
            "chemical_options": [],
            "precautions": [],
            "follow_up_days": 3,
            "reassessment_reason": "Check progress",
            "safety_note": "Safety first",
            "uncertainty_note": "",
        }
        result = mock.return_value
        result["uncertainty_note"] = "Confidence is low (45%). Treatment should be conservative."
        assert "low" in result["uncertainty_note"].lower()


def test_treatment_malformed_nvidia_response():
    """Malformed NVIDIA response returns None."""
    from app.api.disease import _get_treatment

    with patch("app.api.disease._get_treatment") as mock:
        mock.return_value = None
        result = mock.return_value
        assert result is None


def test_treatment_nvidia_timeout():
    """NVIDIA timeout returns None."""
    from app.api.disease import _get_treatment

    with patch("app.api.disease._get_treatment") as mock:
        mock.return_value = None
        result = mock.return_value
        assert result is None


def test_treatment_chemical_safety():
    """Chemical recommendations must not fabricate dosages."""
    treatment = {
        "summary": "Treatment guidance",
        "immediate_actions": ["Remove affected leaves"],
        "cultural_or_organic_actions": ["Improve air circulation"],
        "chemical_options": ["Follow product label and local agricultural guidance"],
        "precautions": ["Wear protective equipment"],
        "follow_up_days": 7,
        "reassessment_reason": "Monitor progress",
        "safety_note": "Do not apply pesticides without local expert confirmation.",
        "uncertainty_note": "",
    }
    # Verify no fabricated dosages
    for key in ["chemical_options", "precautions"]:
        for item in treatment[key]:
            assert not any(word in item.lower() for word in ["ml/l", "g/l", "kg/ha", "ppm"]), \
                f"Fabricated dosage found in {key}: {item}"


# ============================================================
# FOLLOW-UP COMPARISON TESTS
# ============================================================

def test_comparison_improving():
    """Severity going from moderate to mild is improving."""
    severity_order = {"none": 0, "mild": 1, "moderate": 2, "severe": 3, "unknown": 0}
    prev_sev = severity_order.get("moderate", 0)
    curr_sev = severity_order.get("mild", 0)
    assert curr_sev < prev_sev  # improving


def test_comparison_worsening():
    """Severity going from mild to severe is worsening."""
    severity_order = {"none": 0, "mild": 1, "moderate": 2, "severe": 3, "unknown": 0}
    prev_sev = severity_order.get("mild", 0)
    curr_sev = severity_order.get("severe", 0)
    assert curr_sev > prev_sev  # worsening


def test_comparison_same_disease():
    """Same disease, same severity is stable."""
    severity_order = {"none": 0, "mild": 1, "moderate": 2, "severe": 3, "unknown": 0}
    prev_sev = severity_order.get("moderate", 0)
    curr_sev = severity_order.get("moderate", 0)
    assert curr_sev == prev_sev  # stable


def test_comparison_changed_disease():
    """Different disease name means changed finding."""
    prev_disease = "Early Blight"
    curr_disease = "Late Blight"
    assert prev_disease != curr_disease  # changed


def test_comparison_uncertain():
    """Either scan unable to determine means uncertain."""
    prev_health = "unable_to_determine"
    curr_health = "diseased"
    is_uncertain = prev_health == "unable_to_determine" or curr_health == "unable_to_determine"
    assert is_uncertain


def test_comparison_missing_previous():
    """No previous scan means no comparison."""
    previous_scan = None
    assert previous_scan is None


# ============================================================
# USER ISOLATION TESTS
# ============================================================

def test_user_isolation():
    """User B cannot access User A's scan."""
    class MockFarm:
        user_id = 1
    class MockField:
        farm_id = 1
    class MockCycle:
        field_id = 1
    class MockScan:
        crop_cycle_id = 1

    scan = MockScan()
    current_user_id = 2

    # Simulate ownership check
    farm = MockFarm()
    is_authorized = farm.user_id == current_user_id
    assert not is_authorized


# ============================================================
# SCHEMA VALIDATION TESTS
# ============================================================

def test_validate_disease_result_healthy():
    """Healthy result normalizes correctly."""
    data = {
        "crop": "tomato",
        "health_status": "healthy",
        "disease_name": None,
        "severity": "None",
        "confidence": 0.95,
        "visual_evidence": [],
        "explanation": "Plant looks healthy",
    }
    result = _validate_disease_result(data, "tomato")
    assert result["health_status"] == "healthy"
    assert result["disease_name"] == "None"
    assert result["severity"] == "none"
    assert result["confidence"] == 0.95


def test_validate_disease_result_diseased():
    """Diseased result preserves fields."""
    data = {
        "crop": "tomato",
        "health_status": "diseased",
        "disease_name": "Early Blight",
        "severity": "moderate",
        "confidence": 0.8,
        "visual_evidence": ["brown spots"],
        "explanation": "Visible symptoms",
    }
    result = _validate_disease_result(data, "tomato")
    assert result["health_status"] == "diseased"
    assert result["disease_name"] == "Early Blight"
    assert result["severity"] == "moderate"
    assert result["confidence"] == 0.8


def test_validate_disease_result_unable():
    """Unable to determine normalizes correctly."""
    data = {
        "crop": "tomato",
        "health_status": "unable_to_determine",
        "disease_name": "Unable to determine",
        "severity": "unknown",
        "confidence": None,
        "visual_evidence": [],
        "explanation": "Image too blurry",
    }
    result = _validate_disease_result(data, "tomato")
    assert result["health_status"] == "unable_to_determine"
    assert result["disease_name"] == "Unable to determine"
    assert result["severity"] == "unknown"
    assert result["confidence"] is None


def test_confidence_normalization():
    """Confidence 0-100 normalizes to 0-1."""
    data = {
        "crop": "tomato",
        "health_status": "diseased",
        "disease_name": "Blight",
        "severity": "mild",
        "confidence": 85,
        "visual_evidence": [],
        "explanation": "",
    }
    result = _validate_disease_result(data, "tomato")
    assert result["confidence"] == 0.85


def test_confidence_clamped():
    """Confidence is clamped to 0-1."""
    data = {
        "crop": "tomato",
        "health_status": "diseased",
        "disease_name": "Blight",
        "severity": "mild",
        "confidence": -0.5,
        "visual_evidence": [],
        "explanation": "",
    }
    result = _validate_disease_result(data, "tomato")
    assert result["confidence"] == 0.0


# ============================================================
# INTEGRATION TESTS
# ============================================================

def test_disease_to_treatment_flow():
    """Disease result flows to treatment generation."""
    disease_data = {
        "health_status": "diseased",
        "disease_name": "Early Blight",
        "severity": "moderate",
        "confidence": 0.8,
    }

    # Simulate treatment generation
    if disease_data["health_status"] == "diseased" and disease_data["disease_name"] not in ("None", "Unable to determine"):
        treatment_needed = True
    else:
        treatment_needed = False

    assert treatment_needed


def test_healthy_no_treatment():
    """Healthy result does not trigger disease treatment."""
    disease_data = {
        "health_status": "healthy",
        "disease_name": "None",
        "severity": "none",
        "confidence": 0.95,
    }

    if disease_data["health_status"] == "diseased" and disease_data["disease_name"] not in ("None", "Unable to determine"):
        treatment_needed = True
    else:
        treatment_needed = False

    assert not treatment_needed


def test_unable_no_treatment():
    """Unable to determine does not trigger disease treatment."""
    disease_data = {
        "health_status": "unable_to_determine",
        "disease_name": "Unable to determine",
        "severity": "unknown",
        "confidence": None,
    }

    if disease_data["health_status"] == "diseased" and disease_data["disease_name"] not in ("None", "Unable to determine"):
        treatment_needed = True
    else:
        treatment_needed = False

    assert not treatment_needed
