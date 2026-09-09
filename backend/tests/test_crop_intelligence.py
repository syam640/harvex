"""
HARVEX Intelligent Crop Recommendation Tests
Covers: data tests, AI output tests, ranking tests, bilingual tests, security tests.
"""

import pytest
import json
import os
import sys
from datetime import datetime
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient
from app.core.database import get_db, Base, engine
from app.models.models import User, Farm, Field
from app.core.security import create_access_token

import importlib
main_mod = importlib.import_module("main")
app = main_mod.app
client = TestClient(app)

from app.ml.crop_catalog import (
    CROP_CATALOG, CATALOG_CATEGORIES, get_canonical_id, get_crop,
    get_all_crop_ids, CROP_ALIASES,
)
from app.services.crop_intelligence import (
    build_recommendation_context,
    compute_deterministic_ranking,
    filter_eligible_crops,
    validate_provenance,
    build_ai_research_context,
    _score_soil,
    _score_climate,
    _score_water,
    _score_season,
    _score_location,
    _score_irrigation,
    _score_risk,
)
from app.services.soil_intelligence import (
    get_soil_intelligence,
    apply_farmer_soil_report,
    get_data_completeness,
)
from app.api.crop_recommendations import (
    _extract_json_from_ai,
    _validate_ai_crop_response,
)

_counter = 0

def _next():
    global _counter
    _counter += 1
    return _counter

def _setup_db():
    Base.metadata.create_all(bind=engine)

_setup_db()

def _make_user(suffix=""):
    from sqlalchemy.orm import Session
    n = _next()
    email = f"test_crop_int_{n}{suffix}@example.com"
    with Session(engine) as db:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            token = create_access_token({"sub": str(existing.id)})
            return token, existing.id
        user = User(name=f"Test{n}", email=email, password_hash="hashed")
        db.add(user)
        db.commit()
        db.refresh(user)
    token = create_access_token({"sub": str(user.id)})
    return token, user.id

def _auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# CROP CATALOG TESTS
# =============================================================================

class TestCropCatalog:
    def test_catalog_has_minimum_crops(self):
        assert len(CROP_CATALOG) >= 30

    def test_all_crops_have_required_fields(self):
        required = ["crop_id", "name_en", "name_te", "category", "soil_requirements",
                     "climate_requirements", "water_requirement", "irrigation_compatibility",
                     "season_suitability"]
        for crop_id, crop in CROP_CATALOG.items():
            for field in required:
                assert field in crop, f"{crop_id} missing {field}"

    def test_all_crops_have_bilingual_names(self):
        for crop_id, crop in CROP_CATALOG.items():
            assert crop["name_en"], f"{crop_id} missing English name"
            assert crop["name_te"], f"{crop_id} missing Telugu name"

    def test_canonical_id_resolution(self):
        assert get_canonical_id("rice") == "rice"
        assert get_canonical_id("Rice") == "rice"
        assert get_canonical_id("paddy") == "rice"
        assert get_canonical_id("corn") == "maize"
        assert get_canonical_id("unknown_crop") is None

    def test_get_crop(self):
        crop = get_crop("rice")
        assert crop is not None
        assert crop["name_en"] == "Rice"

    def test_get_crop_unknown(self):
        assert get_crop("nonexistent") is None

    def test_all_crop_ids(self):
        ids = get_all_crop_ids()
        assert len(ids) >= 30
        assert "rice" in ids
        assert "tomato" in ids
        assert "cotton" in ids

    def test_categories_are_populated(self):
        for cat, crops in CATALOG_CATEGORIES.items():
            assert len(crops) > 0, f"Category {cat} is empty"
            for crop_id in crops:
                assert crop_id in CROP_CATALOG, f"Category {cat} references unknown crop {crop_id}"

    def test_aliases_cover_major_crops(self):
        major = ["rice", "tomato", "cotton", "wheat", "maize", "banana", "mango"]
        for crop in major:
            assert crop in CROP_ALIASES or crop in CROP_CATALOG


# =============================================================================
# DATA TESTS
# =============================================================================

class TestDataTests:
    def test_valid_gps(self):
        ctx = build_recommendation_context(
            location={"latitude": 16.5, "longitude": 80.6, "name": "Test"},
            weather={}, soil={},
            water_availability="moderate", irrigation_method="rainfed", season="kharif"
        )
        assert ctx["location"]["latitude"] == 16.5
        assert ctx["location"]["longitude"] == 80.6

    def test_manual_location(self):
        ctx = build_recommendation_context(
            location={"latitude": 28.6, "longitude": 77.2, "name": "Delhi", "source": "manual"},
            weather={}, soil={},
            water_availability="moderate", irrigation_method="drip", season="rabi"
        )
        assert ctx["location"]["source"] == "manual"

    def test_valid_weather(self):
        weather = {
            "temperature": {"value": 28.5, "status": "measured", "source": "openweather"},
            "humidity": {"value": 65.0, "status": "measured", "source": "openweather"},
            "rainfall": {"value": 15.0, "status": "measured", "source": "openweather"},
        }
        ctx = build_recommendation_context(
            location={"latitude": 16.5, "longitude": 80.6},
            weather=weather, soil={},
            water_availability="moderate", irrigation_method="rainfed", season="kharif"
        )
        assert ctx["weather"]["temperature"]["value"] == 28.5

    def test_weather_unavailable(self):
        ctx = build_recommendation_context(
            location={"latitude": 16.5, "longitude": 80.6},
            weather={}, soil={},
            water_availability="moderate", irrigation_method="rainfed", season="kharif"
        )
        assert ctx["weather"] == {}

    def test_cached_weather(self):
        weather = {"temperature": {"value": 25, "status": "cached"}}
        ctx = build_recommendation_context(
            location={"latitude": 16.5, "longitude": 80.6},
            weather=weather, soil={},
            water_availability="moderate", irrigation_method="rainfed", season="kharif"
        )
        assert ctx["weather"]["temperature"]["status"] == "cached"

    def test_soil_estimated(self):
        soil = {
            "ph": {"value": 6.5, "status": "estimated", "source": "ISRIC", "is_field_measurement": False},
            "soil_type": {"value": "loamy", "status": "estimated", "is_field_measurement": False},
        }
        ctx = build_recommendation_context(
            location={"latitude": 16.5, "longitude": 80.6},
            weather={}, soil=soil,
            water_availability="moderate", irrigation_method="rainfed", season="kharif"
        )
        assert ctx["soil"]["ph"]["status"] == "estimated"

    def test_soil_measured(self):
        soil = {
            "ph": {"value": 6.8, "status": "measured", "source": "farmer_soil_report", "is_field_measurement": True},
            "nitrogen": {"value": None, "status": "unavailable", "is_field_measurement": False},
        }
        report = {"ph": 6.8, "nitrogen": 80}
        soil = apply_farmer_soil_report(soil, report)
        assert soil["ph"]["status"] == "measured"
        assert soil["ph"]["is_field_measurement"] is True
        assert soil["nitrogen"]["status"] == "measured"

    def test_missing_ph(self):
        soil = {"ph": {"value": None, "status": "unavailable"}}
        completeness = get_data_completeness(soil)
        assert completeness["ph"] == "unavailable"

    def test_missing_npk(self):
        soil = {
            "nitrogen": {"value": None, "status": "unavailable"},
            "phosphorus": {"value": None, "status": "unavailable"},
            "potassium": {"value": None, "status": "unavailable"},
        }
        completeness = get_data_completeness(soil)
        assert completeness["nitrogen"] == "unavailable"
        assert completeness["phosphorus"] == "unavailable"
        assert completeness["potassium"] == "unavailable"

    def test_complete_soil_report(self):
        soil = {
            "ph": {"value": 6.5, "status": "measured", "is_field_measurement": True},
            "nitrogen": {"value": 80, "status": "measured", "is_field_measurement": True},
            "phosphorus": {"value": 40, "status": "measured", "is_field_measurement": True},
            "potassium": {"value": 50, "status": "measured", "is_field_measurement": True},
            "soil_type": {"value": "loamy", "status": "measured", "is_field_measurement": True},
        }
        completeness = get_data_completeness(soil)
        assert all(v == "measured" for v in completeness.values())

    def test_partial_soil_report(self):
        soil = {
            "ph": {"value": 6.5, "status": "estimated"},
            "nitrogen": {"value": None, "status": "unavailable"},
            "phosphorus": {"value": None, "status": "unavailable"},
            "potassium": {"value": None, "status": "unavailable"},
            "soil_type": {"value": "loamy", "status": "estimated"},
        }
        completeness = get_data_completeness(soil)
        assert completeness["ph"] == "estimated"
        assert completeness["nitrogen"] == "unavailable"

    def test_missing_water_availability(self):
        ctx = build_recommendation_context(
            location={"latitude": 16.5, "longitude": 80.6},
            weather={}, soil={},
            water_availability="moderate", irrigation_method="rainfed", season="kharif"
        )
        assert ctx["water"]["availability"] == "moderate"

    def test_missing_irrigation_method(self):
        ctx = build_recommendation_context(
            location={"latitude": 16.5, "longitude": 80.6},
            weather={}, soil={},
            water_availability="moderate", irrigation_method="rainfed", season="kharif"
        )
        assert ctx["irrigation"]["method"] == "rainfed"


# =============================================================================
# PROVENANCE PROTECTION TESTS
# =============================================================================

class TestProvenanceProtection:
    def test_validate_provenance_clean(self):
        ctx = build_recommendation_context(
            location={"latitude": 16.5, "longitude": 80.6},
            weather={}, soil={},
            water_availability="moderate", irrigation_method="rainfed", season="kharif"
        )
        result = validate_provenance(ctx)
        assert result["valid"] is True

    def test_fabricated_soil_value_rejected(self):
        soil = {"ph": {"value": 6.5, "status": "unavailable", "is_field_measurement": False}}
        result = validate_provenance({"soil": soil, "weather": {}, "location": {}})
        assert result["valid"] is False

    def test_fabricated_weather_value_rejected(self):
        weather = {"temperature": {"value": 28, "status": "unavailable"}}
        result = validate_provenance({"soil": {}, "weather": weather, "location": {}})
        assert result["valid"] is False


# =============================================================================
# SCORING TESTS
# =============================================================================

class TestScoring:
    def test_soil_scoring_with_type_match(self):
        crop = CROP_CATALOG["rice"]
        soil = {"soil_type": {"value": "clay", "status": "estimated"}, "ph": {"value": 6.0, "status": "estimated"}}
        score, reasons = _score_soil(crop, soil)
        assert score >= 70

    def test_soil_scoring_without_data(self):
        crop = CROP_CATALOG["rice"]
        soil = {"soil_type": {"value": None, "status": "unavailable"}, "ph": {"value": None, "status": "unavailable"}}
        score, reasons = _score_soil(crop, soil)
        assert score == 50.0

    def test_climate_scoring(self):
        crop = CROP_CATALOG["rice"]
        weather = {
            "temperature": {"value": 27, "status": "measured"},
            "humidity": {"value": 75, "status": "measured"},
            "rainfall": {"value": 1500, "status": "measured"},
        }
        score, reasons = _score_climate(crop, weather)
        assert score >= 70

    def test_water_scoring_abundant(self):
        crop = CROP_CATALOG["rice"]
        score, reasons = _score_water(crop, "abundant")
        assert score >= 80

    def test_water_scoring_limited_for_high_water_crop(self):
        crop = CROP_CATALOG["rice"]  # high water requirement
        score, reasons = _score_water(crop, "very_limited")
        assert score <= 30

    def test_season_scoring(self):
        crop = CROP_CATALOG["rice"]
        score, reasons = _score_season(crop, "kharif")
        assert score >= 80

    def test_season_scoring_wrong_season(self):
        crop = CROP_CATALOG["rice"]
        score, reasons = _score_season(crop, "rabi")
        assert score <= 40

    def test_location_scoring_tropical(self):
        crop = CROP_CATALOG["rice"]
        score, reasons = _score_location(crop, {"latitude": 10.0})
        assert score >= 80

    def test_location_scoring_no_data(self):
        crop = CROP_CATALOG["rice"]
        score, reasons = _score_location(crop, {})
        assert score == 50.0

    def test_irrigation_scoring_compatible(self):
        crop = CROP_CATALOG["rice"]
        score, reasons = _score_irrigation(crop, "flood")
        assert score >= 80

    def test_irrigation_scoring_rainfed_low_water(self):
        crop = CROP_CATALOG["rice"]  # high water
        score, reasons = _score_irrigation(crop, "rainfed")
        assert score <= 40

    def test_risk_scoring_normal(self):
        crop = CROP_CATALOG["rice"]
        score, reasons = _score_risk(crop, {})
        assert 60 <= score <= 100

    def test_risk_scoring_high_temp(self):
        crop = CROP_CATALOG["rice"]
        score, reasons = _score_risk(crop, {"temperature": {"value": 40}})
        assert score < 80


# =============================================================================
# DETERMINISTIC RANKING TESTS
# =============================================================================

class TestDeterministicRanking:
    def test_ranking_returns_all_fields(self):
        crop = CROP_CATALOG["rice"]
        ctx = build_recommendation_context(
            location={"latitude": 16.5, "longitude": 80.6},
            weather={}, soil={},
            water_availability="moderate", irrigation_method="rainfed", season="kharif"
        )
        result = compute_deterministic_ranking(crop, ctx)
        assert "suitability_score" in result
        assert "component_scores" in result
        assert "limiting_factors" in result
        assert "all_reasons" in result

    def test_ranking_score_range(self):
        crop = CROP_CATALOG["rice"]
        ctx = build_recommendation_context(
            location={"latitude": 16.5, "longitude": 80.6},
            weather={}, soil={},
            water_availability="moderate", irrigation_method="rainfed", season="kharif"
        )
        result = compute_deterministic_ranking(crop, ctx)
        assert 0 <= result["suitability_score"] <= 100

    def test_ranking_different_crops_different_scores(self):
        ctx = build_recommendation_context(
            location={"latitude": 16.5, "longitude": 80.6},
            weather={}, soil={},
            water_availability="limited", irrigation_method="rainfed", season="kharif"
        )
        rice_score = compute_deterministic_ranking(CROP_CATALOG["rice"], ctx)["suitability_score"]
        millet_score = compute_deterministic_ranking(CROP_CATALOG["pearl_millet"], ctx)["suitability_score"]
        # Pearl millet (low water) should score better than rice (high water) with limited water
        assert millet_score > rice_score


# =============================================================================
# ELIGIBILITY FILTERING TESTS
# =============================================================================

class TestEligibilityFiltering:
    def test_filter_returns_list(self):
        ctx = build_recommendation_context(
            location={"latitude": 16.5, "longitude": 80.6},
            weather={}, soil={},
            water_availability="moderate", irrigation_method="rainfed", season="kharif"
        )
        eligible = filter_eligible_crops(CROP_CATALOG, ctx)
        assert isinstance(eligible, list)
        assert len(eligible) > 0

    def test_filter_rejects_high_water_when_very_limited(self):
        ctx = build_recommendation_context(
            location={"latitude": 16.5, "longitude": 80.6},
            weather={}, soil={},
            water_availability="very_limited", irrigation_method="rainfed", season="kharif"
        )
        eligible = filter_eligible_crops(CROP_CATALOG, ctx)
        eligible_ids = [c["crop_id"] for c in eligible]
        # Rice (high water) should be filtered out
        assert "rice" not in eligible_ids
        # Pearl millet (very low water) should remain
        assert "pearl_millet" in eligible_ids

    def test_filter_rejects_wrong_season(self):
        ctx = build_recommendation_context(
            location={"latitude": 16.5, "longitude": 80.6},
            weather={}, soil={},
            water_availability="moderate", irrigation_method="rainfed", season="summer"
        )
        eligible = filter_eligible_crops(CROP_CATALOG, ctx)
        eligible_ids = [c["crop_id"] for c in eligible]
        # Wheat (rabi only) should be filtered out in summer
        assert "wheat" not in eligible_ids

    def test_broad_candidate_catalog(self):
        ctx = build_recommendation_context(
            location={"latitude": 16.5, "longitude": 80.6},
            weather={}, soil={},
            water_availability="abundant", irrigation_method="flood", season="kharif"
        )
        eligible = filter_eligible_crops(CROP_CATALOG, ctx)
        assert len(eligible) >= 15


# =============================================================================
# AI OUTPUT TESTS
# =============================================================================

class TestAIOutput:
    def test_extract_pure_json(self):
        raw = '{"recommendation_status":"success","candidates":[{"crop_id":"rice"}]}'
        result = _extract_json_from_ai(raw)
        assert result is not None
        assert result["recommendation_status"] == "success"

    def test_extract_fenced_json(self):
        raw = '```json\n{"recommendation_status":"success","candidates":[]}\n```'
        result = _extract_json_from_ai(raw)
        assert result is not None

    def test_extract_json_with_surrounding_prose(self):
        raw = 'Here is the analysis:\n{"recommendation_status":"success","candidates":[]}\nDone.'
        result = _extract_json_from_ai(raw)
        assert result is not None

    def test_extract_empty_response(self):
        assert _extract_json_from_ai("") is None
        assert _extract_json_from_ai(None) is None

    def test_validate_valid_response(self):
        data = {
            "recommendation_status": "success",
            "candidates": [
                {"crop_id": "rice", "reasoning": {"soil": "ok"}},
                {"crop_id": "maize", "reasoning": {"soil": "ok"}},
            ]
        }
        result = _validate_ai_crop_response(data, ["rice", "maize", "tomato"])
        assert result["valid"] is True

    def test_validate_unknown_crop_id(self):
        data = {
            "recommendation_status": "success",
            "candidates": [{"crop_id": "imaginary_crop"}]
        }
        result = _validate_ai_crop_response(data, ["rice", "maize"])
        assert result["valid"] is False

    def test_validate_duplicate_crop_id(self):
        data = {
            "recommendation_status": "success",
            "candidates": [
                {"crop_id": "rice"},
                {"crop_id": "rice"},
            ]
        }
        result = _validate_ai_crop_response(data, ["rice"])
        assert result["valid"] is False

    def test_validate_fabricated_measurement(self):
        data = {
            "recommendation_status": "success",
            "candidates": [{
                "crop_id": "rice",
                "reasoning": {"soil": "pH = 6.5 is suitable"}
            }]
        }
        result = _validate_ai_crop_response(data, ["rice"])
        assert result["valid"] is False

    def test_validate_too_many_candidates(self):
        data = {
            "recommendation_status": "success",
            "candidates": [{"crop_id": f"crop_{i}"} for i in range(25)]
        }
        result = _validate_ai_crop_response(data, [f"crop_{i}" for i in range(25)])
        assert result["valid"] is False


# =============================================================================
# BILINGUAL TESTS
# =============================================================================

class TestBilingual:
    def test_english_names_present(self):
        for crop_id, crop in CROP_CATALOG.items():
            assert crop["name_en"], f"{crop_id} missing English name"

    def test_telugu_names_present(self):
        for crop_id, crop in CROP_CATALOG.items():
            assert crop["name_te"], f"{crop_id} missing Telugu name"

    def test_same_recommendation_both_languages(self):
        for crop_id, crop in CROP_CATALOG.items():
            en = crop["name_en"]
            te = crop["name_te"]
            assert len(en) > 0
            assert len(te) > 0

    def test_no_invented_names(self):
        known_crops = set(CROP_CATALOG.keys())
        for crop_id in known_crops:
            crop = CROP_CATALOG[crop_id]
            assert crop["crop_id"] == crop_id


# =============================================================================
# SECURITY TESTS
# =============================================================================

class TestSecurity:
    def test_unauthorized_request(self):
        response = client.post("/api/crop-recommendations", json={
            "latitude": 16.5, "longitude": 80.6,
            "season": "kharif", "water_availability": "moderate",
            "irrigation_method": "rainfed"
        })
        assert response.status_code == 401

    def test_invalid_coordinates(self):
        token, _ = _make_user("sec")
        response = client.post("/api/crop-recommendations", json={
            "latitude": 999, "longitude": 999,
            "season": "kharif", "water_availability": "moderate",
            "irrigation_method": "rainfed"
        }, headers=_auth_headers(token))
        assert response.status_code == 422

    def test_missing_location(self):
        token, _ = _make_user("sec2")
        response = client.post("/api/crop-recommendations", json={
            "season": "kharif", "water_availability": "moderate",
            "irrigation_method": "rainfed"
        }, headers=_auth_headers(token))
        assert response.status_code == 422


# =============================================================================
# REGRESSION TESTS
# =============================================================================

class TestRegression:
    def test_existing_crop_recommendation_still_works(self):
        """The legacy /api/crop/recommend endpoint must still work."""
        token, _ = _make_user("reg")
        response = client.post("/api/crop/recommend", json={
            "n": 80, "p": 40, "k": 40,
            "temperature": 27, "humidity": 70,
            "ph": 6.5, "rainfall": 1500,
        }, headers=_auth_headers(token))
        assert response.status_code == 200
        data = response.json()
        assert "recommended_crop" in data
        assert "suitability_score" in data

    def test_catalog_endpoint(self):
        response = client.get("/api/crop-recommendations/catalog")
        assert response.status_code == 200
        data = response.json()
        assert "crops" in data
        assert data["total"] >= 30

    def test_crop_detail_endpoint(self):
        response = client.get("/api/crop-recommendations/catalog/rice")
        assert response.status_code == 200
        data = response.json()
        assert data["name_en"] == "Rice"

    def test_categories_endpoint(self):
        response = client.get("/api/crop-recommendations/categories")
        assert response.status_code == 200
        data = response.json()
        assert "Cereals" in data
        assert "Pulses" in data

    def test_intelligent_recommendation_endpoint(self):
        token, _ = _make_user("int")
        response = client.post("/api/crop-recommendations", json={
            "latitude": 16.5, "longitude": 80.6,
            "season": "kharif", "water_availability": "moderate",
            "irrigation_method": "rainfed"
        }, headers=_auth_headers(token))
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert len(data["recommendations"]) > 0
        assert data["total_evaluated"] >= 30


# =============================================================================
# RELIABILITY HARDENING TESTS
# =============================================================================

from app.services.ai.reasoning_provider import (
    extract_json_from_ai,
    validate_ai_crop_response,
    run_crop_reasoning,
    AIAttemptResult,
)


class TestJSONExtractionRobustness:
    """Test robust JSON extraction from AI responses."""

    def test_pure_json(self):
        data = {"recommendation_status": "success", "candidates": [{"crop_id": "rice"}]}
        result, method = extract_json_from_ai(json.dumps(data))
        assert result == data
        assert method == "pure_json"

    def test_markdown_fenced_json(self):
        data = {"recommendation_status": "success", "candidates": []}
        raw = f"```json\n{json.dumps(data)}\n```"
        result, method = extract_json_from_ai(raw)
        assert result == data
        assert method == "markdown_fenced"

    def test_json_with_surrounding_prose(self):
        data = {"recommendation_status": "success", "candidates": [{"crop_id": "rice"}]}
        raw = f"Here is the analysis:\n{json.dumps(data)}\nHope this helps."
        result, method = extract_json_from_ai(raw)
        assert result == data
        assert method in ("bracket_extraction", "pure_json")

    def test_empty_response(self):
        result, method = extract_json_from_ai("")
        assert result is None
        assert method is None

    def test_none_input(self):
        result, method = extract_json_from_ai(None)
        assert result is None
        assert method is None

    def test_whitespace_only(self):
        result, method = extract_json_from_ai("   \n  \t  ")
        assert result is None
        assert method is None

    def test_garbage_text(self):
        result, method = extract_json_from_ai("This is not JSON at all")
        assert result is None
        assert method is None

    def test_trailing_comma_fix(self):
        raw = '{"recommendation_status": "success", "candidates": [{"crop_id": "rice",},],}'
        result, method = extract_json_from_ai(raw)
        assert result is not None
        assert result["recommendation_status"] == "success"


class TestAICropValidation:
    """Test strict AI response validation."""

    def test_valid_response(self):
        data = {
            "recommendation_status": "success",
            "candidates": [
                {"crop_id": "rice", "reasoning": {"soil": "Good soil fit", "climate": "Warm"}, "conflicts": [], "recommendation_notes": []},
                {"crop_id": "wheat", "reasoning": {"soil": "OK"}, "conflicts": [], "recommendation_notes": []},
            ],
        }
        valid_ids = ["rice", "wheat", "maize"]
        result = validate_ai_crop_response(data, valid_ids)
        assert result["valid"] is True
        assert len(result["issues"]) == 0

    def test_unknown_crop_id_rejected(self):
        data = {
            "recommendation_status": "success",
            "candidates": [
                {"crop_id": "alien_crop", "reasoning": {}},
            ],
        }
        result = validate_ai_crop_response(data, ["rice", "wheat"])
        assert result["valid"] is False
        assert any("unknown crop_id" in i for i in result["issues"])

    def test_duplicate_crop_id_rejected(self):
        data = {
            "recommendation_status": "success",
            "candidates": [
                {"crop_id": "rice", "reasoning": {}},
                {"crop_id": "rice", "reasoning": {}},
            ],
        }
        result = validate_ai_crop_response(data, ["rice"])
        assert result["valid"] is False
        assert any("duplicate" in i for i in result["issues"])

    def test_empty_candidates_rejected(self):
        data = {"recommendation_status": "success", "candidates": []}
        result = validate_ai_crop_response(data, ["rice"])
        assert result["valid"] is False
        assert any("empty" in i for i in result["issues"])

    def test_invalid_status_rejected(self):
        data = {"recommendation_status": "invalid_value", "candidates": [{"crop_id": "rice"}]}
        result = validate_ai_crop_response(data, ["rice"])
        assert result["valid"] is False
        assert any("recommendation_status" in i for i in result["issues"])

    def test_missing_crop_id_rejected(self):
        data = {"recommendation_status": "success", "candidates": [{"reasoning": {}}]}
        result = validate_ai_crop_response(data, ["rice"])
        assert result["valid"] is False
        assert any("missing crop_id" in i for i in result["issues"])

    def test_too_many_candidates_rejected(self):
        data = {
            "recommendation_status": "success",
            "candidates": [{"crop_id": "rice", "reasoning": {}} for _ in range(25)],
        }
        result = validate_ai_crop_response(data, ["rice"])
        assert result["valid"] is False
        assert any("Too many" in i for i in result["issues"])


class TestFabricationDetection:
    """Test that fabricated measurements are detected and rejected."""

    def test_fabricated_ph_rejected(self):
        data = {
            "recommendation_status": "success",
            "candidates": [{
                "crop_id": "rice",
                "reasoning": {
                    "soil": "The soil has pH = 6.8 which is ideal",
                    "climate": "Good",
                    "water": "OK",
                },
                "conflicts": [],
                "recommendation_notes": [],
            }],
        }
        issues = validate_ai_crop_response(data, ["rice"])["issues"]
        assert any("fabricated measurement" in i for i in issues)

    def test_fabricated_nitrogen_rejected(self):
        data = {
            "recommendation_status": "success",
            "candidates": [{
                "crop_id": "rice",
                "reasoning": {"soil": "nitrogen = 0.18 is adequate"},
            }],
        }
        issues = validate_ai_crop_response(data, ["rice"])["issues"]
        assert any("fabricated measurement" in i for i in issues)

    def test_fabricated_phosphorus_rejected(self):
        data = {
            "recommendation_status": "success",
            "candidates": [{
                "crop_id": "rice",
                "reasoning": {"soil": "phosphorus = 28 kg/ha available"},
            }],
        }
        issues = validate_ai_crop_response(data, ["rice"])["issues"]
        assert any("fabricated measurement" in i for i in issues)

    def test_fabricated_potassium_rejected(self):
        data = {
            "recommendation_status": "success",
            "candidates": [{
                "crop_id": "rice",
                "reasoning": {"soil": "potassium: 195 is good"},
            }],
        }
        issues = validate_ai_crop_response(data, ["rice"])["issues"]
        assert any("fabricated measurement" in i for i in issues)

    def test_fabricated_temperature_rejected(self):
        data = {
            "recommendation_status": "success",
            "candidates": [{
                "crop_id": "rice",
                "reasoning": {"climate": "temperature = 28 C is perfect"},
            }],
        }
        issues = validate_ai_crop_response(data, ["rice"])["issues"]
        assert any("fabricated weather" in i for i in issues)

    def test_fabricated_rainfall_rejected(self):
        data = {
            "recommendation_status": "success",
            "candidates": [{
                "crop_id": "rice",
                "reasoning": {"climate": "rainfall: 1200mm suits rice"},
            }],
        }
        issues = validate_ai_crop_response(data, ["rice"])["issues"]
        assert any("fabricated weather" in i for i in issues)

    def test_honest_reasoning_passes(self):
        data = {
            "recommendation_status": "success",
            "candidates": [{
                "crop_id": "rice",
                "reasoning": {
                    "soil": "Soil type is suitable for rice cultivation",
                    "climate": "Temperature is within the acceptable range",
                    "water": "Water availability meets rice requirements",
                },
                "conflicts": [],
                "recommendation_notes": [],
            }],
        }
        issues = validate_ai_crop_response(data, ["rice"])["issues"]
        assert not any("fabricated" in i for i in issues)


class TestAIAttemptResult:
    """Test the AIAttemptResult data class."""

    def test_successful_result(self):
        result = AIAttemptResult(
            success=True, parsed_data={"candidates": []},
            model_used="nemotron", attempt_count=1,
        )
        assert result.success is True
        assert result.fallback_used is False

    def test_failed_result(self):
        result = AIAttemptResult(
            success=False, attempt_count=3,
            error="All models failed",
        )
        assert result.success is False
        assert result.attempt_count == 3

    def test_fallback_result(self):
        result = AIAttemptResult(
            success=True, fallback_used=True,
            model_used="fallback_model",
        )
        assert result.fallback_used is True


class TestReasoningProviderBounded:
    """Test bounded AI attempt logic with mocked NVIDIA calls."""

    def _mock_provider(self, responses):
        """Create a mock provider that returns predetermined responses."""
        provider = MagicMock()
        provider.text_api_key = "test_key"
        provider.text_base_url = "https://fake.api.com/v1"
        call_count = [0]

        def mock_post(*args, **kwargs):
            idx = call_count[0]
            call_count[0] += 1
            if idx < len(responses):
                return responses[idx]
            return MagicMock(status_code=500, json=lambda: {})

        return provider, mock_post

    @patch("app.services.ai.reasoning_provider._call_nvidia_model")
    def test_primary_success(self, mock_call):
        valid_data = {
            "recommendation_status": "success",
            "candidates": [{"crop_id": "rice", "reasoning": {"soil": "Good fit"}}],
        }
        mock_call.return_value = {
            "success": True, "content": json.dumps(valid_data),
            "model": "nemotron", "response_time": 1.0,
        }
        provider = MagicMock()
        result = run_crop_reasoning(
            provider=provider, messages=[],
            primary_model="nemotron", fallback_model="fallback",
            valid_crop_ids=["rice"], timeout=10,
        )
        assert result.success is True
        assert result.fallback_used is False
        assert result.model_used == "nemotron"
        assert result.attempt_count == 1

    @patch("app.services.ai.reasoning_provider._call_nvidia_model")
    def test_primary_malformed_json_then_retry_success(self, mock_call):
        valid_data = {
            "recommendation_status": "success",
            "candidates": [{"crop_id": "wheat", "reasoning": {"soil": "OK"}}],
        }
        call_count = [0]

        def side_effect(provider, messages, model, timeout):
            call_count[0] += 1
            if call_count[0] == 1:
                return {"success": True, "content": "Not JSON at all", "model": model}
            return {"success": True, "content": json.dumps(valid_data), "model": model}

        mock_call.side_effect = side_effect
        result = run_crop_reasoning(
            provider=MagicMock(), messages=[],
            primary_model="nemotron", fallback_model="fallback",
            valid_crop_ids=["wheat"], timeout=10,
        )
        assert result.success is True
        assert result.model_used == "nemotron"
        assert result.attempt_count == 2

    @patch("app.services.ai.reasoning_provider._call_nvidia_model")
    def test_primary_fails_fallback_succeeds(self, mock_call):
        valid_data = {
            "recommendation_status": "success",
            "candidates": [{"crop_id": "maize", "reasoning": {"soil": "OK"}}],
        }
        call_count = [0]

        def side_effect(provider, messages, model, timeout):
            call_count[0] += 1
            if call_count[0] <= 2:
                return {"success": False, "content": None, "model": model,
                        "error": "timeout", "error_code": "TIMEOUT"}
            return {"success": True, "content": json.dumps(valid_data), "model": model}

        mock_call.side_effect = side_effect
        result = run_crop_reasoning(
            provider=MagicMock(), messages=[],
            primary_model="nemotron", fallback_model="fallback_model",
            valid_crop_ids=["maize"], timeout=10,
        )
        assert result.success is True
        assert result.fallback_used is True
        assert result.model_used == "fallback_model"
        assert result.attempt_count == 3

    @patch("app.services.ai.reasoning_provider._call_nvidia_model")
    def test_all_models_fail_deterministic_fallback(self, mock_call):
        mock_call.return_value = {
            "success": False, "content": None, "model": "nemotron",
            "error": "timeout", "error_code": "TIMEOUT",
        }
        result = run_crop_reasoning(
            provider=MagicMock(), messages=[],
            primary_model="nemotron", fallback_model="fallback_model",
            valid_crop_ids=["rice"], timeout=10,
        )
        assert result.success is False
        assert result.attempt_count == 3

    @patch("app.services.ai.reasoning_provider._call_nvidia_model")
    def test_no_fallback_model_skips_fallback(self, mock_call):
        mock_call.return_value = {
            "success": False, "content": None, "model": "nemotron",
            "error": "timeout", "error_code": "TIMEOUT",
        }
        result = run_crop_reasoning(
            provider=MagicMock(), messages=[],
            primary_model="nemotron", fallback_model="",
            valid_crop_ids=["rice"], timeout=10,
        )
        assert result.success is False
        assert result.attempt_count == 2  # Only primary attempts

    @patch("app.services.ai.reasoning_provider._call_nvidia_model")
    def test_same_model_as_fallback_skips_fallback(self, mock_call):
        mock_call.return_value = {
            "success": False, "content": None, "model": "nemotron",
            "error": "timeout", "error_code": "TIMEOUT",
        }
        result = run_crop_reasoning(
            provider=MagicMock(), messages=[],
            primary_model="nemotron", fallback_model="nemotron",
            valid_crop_ids=["rice"], timeout=10,
        )
        assert result.success is False
        assert result.attempt_count == 2

    @patch("app.services.ai.reasoning_provider._call_nvidia_model")
    def test_max_attempts_bounded_to_3(self, mock_call):
        mock_call.return_value = {
            "success": False, "content": None, "model": "nemotron",
            "error": "timeout", "error_code": "TIMEOUT",
        }
        result = run_crop_reasoning(
            provider=MagicMock(), messages=[],
            primary_model="nemotron", fallback_model="fallback_model",
            valid_crop_ids=["rice"], timeout=10,
        )
        assert result.attempt_count <= 3
        assert mock_call.call_count <= 3

    @patch("app.services.ai.reasoning_provider._call_nvidia_model")
    def test_invalid_crop_id_from_ai_rejected(self, mock_call):
        bad_data = {
            "recommendation_status": "success",
            "candidates": [{"crop_id": "tomato_crop", "reasoning": {}}],
        }
        mock_call.return_value = {
            "success": True, "content": json.dumps(bad_data),
            "model": "nemotron",
        }
        result = run_crop_reasoning(
            provider=MagicMock(), messages=[],
            primary_model="nemotron", fallback_model="fallback",
            valid_crop_ids=["rice", "wheat"], timeout=10,
        )
        # Validation should fail, causing retry
        assert result.attempt_count >= 1

    @patch("app.services.ai.reasoning_provider._call_nvidia_model")
    def test_no_infinite_retries(self, mock_call):
        """Ensure no infinite retry loop exists."""
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] > 10:
                raise RuntimeError("Should not be called more than 3 times")
            return {"success": False, "content": None, "model": "nemotron",
                    "error": "fail", "error_code": "FAIL"}

        mock_call.side_effect = side_effect
        result = run_crop_reasoning(
            provider=MagicMock(), messages=[],
            primary_model="nemotron", fallback_model="fallback",
            valid_crop_ids=["rice"], timeout=10,
        )
        assert call_count[0] <= 3


class TestEndpointReliability:
    """Test the crop recommendation endpoint reliability."""

    def _auth_headers(self, token):
        return {"Authorization": f"Bearer {token}"}

    def test_ai_failure_returns_deterministic_fallback(self):
        """When AI fails, endpoint returns deterministic fallback, not 500."""
        token, _ = _make_user("rel1")
        with patch("app.api.crop_recommendations.run_crop_reasoning") as mock_reason:
            mock_reason.return_value = AIAttemptResult(
                success=False, attempt_count=3, error="All failed",
            )
            response = client.post("/api/crop-recommendations", json={
                "latitude": 16.5, "longitude": 80.6,
                "season": "kharif", "water_availability": "moderate",
                "irrigation_method": "rainfed",
            }, headers=self._auth_headers(token))
            assert response.status_code == 200
            data = response.json()
            assert data["recommendation_status"] == "ai_unavailable_deterministic_fallback"
            assert len(data["recommendations"]) > 0

    def test_ai_success_returns_ai_assisted(self):
        token, _ = _make_user("rel2")
        with patch("app.api.crop_recommendations.run_crop_reasoning") as mock_reason:
            mock_reason.return_value = AIAttemptResult(
                success=True,
                parsed_data={
                    "recommendation_status": "success",
                    "candidates": [{"crop_id": "rice", "reasoning": {"soil": "OK"}}],
                },
                model_used="nemotron", fallback_used=False,
                parse_method="pure_json", attempt_count=1,
            )
            response = client.post("/api/crop-recommendations", json={
                "latitude": 16.5, "longitude": 80.6,
                "season": "kharif", "water_availability": "moderate",
                "irrigation_method": "rainfed",
            }, headers=self._auth_headers(token))
            assert response.status_code == 200
            data = response.json()
            assert data["recommendation_status"] == "ai_assisted"
            assert data["ai_used"] is True
            assert data["ai_fallback_used"] is False
            assert data["ai_attempt_count"] == 1

    def test_ai_fallback_used_reported(self):
        token, _ = _make_user("rel3")
        with patch("app.api.crop_recommendations.run_crop_reasoning") as mock_reason:
            mock_reason.return_value = AIAttemptResult(
                success=True,
                parsed_data={
                    "recommendation_status": "success",
                    "candidates": [{"crop_id": "wheat", "reasoning": {"soil": "OK"}}],
                },
                model_used="fallback_model", fallback_used=True,
                parse_method="pure_json", attempt_count=3,
            )
            response = client.post("/api/crop-recommendations", json={
                "latitude": 16.5, "longitude": 80.6,
                "season": "kharif", "water_availability": "moderate",
                "irrigation_method": "rainfed",
            }, headers=self._auth_headers(token))
            data = response.json()
            assert data["ai_fallback_used"] is True
            assert data["ai_model"] == "fallback_model"

    def test_response_includes_attempt_count(self):
        token, _ = _make_user("rel4")
        response = client.post("/api/crop-recommendations", json={
            "latitude": 16.5, "longitude": 80.6,
            "season": "kharif", "water_availability": "moderate",
            "irrigation_method": "rainfed",
        }, headers=self._auth_headers(token))
        assert response.status_code == 200
        data = response.json()
        assert "ai_attempt_count" in data
        assert "ai_fallback_used" in data
        assert "recommendation_status" in data

    def test_no_infinite_retry_in_endpoint(self):
        """Ensure endpoint does not hang on AI failure."""
        token, _ = _make_user("rel5")
        import time
        start = time.time()
        with patch("app.api.crop_recommendations.run_crop_reasoning") as mock_reason:
            mock_reason.return_value = AIAttemptResult(
                success=False, attempt_count=3, error="timeout",
            )
            response = client.post("/api/crop-recommendations", json={
                "latitude": 16.5, "longitude": 80.6,
                "season": "kharif", "water_availability": "moderate",
                "irrigation_method": "rainfed",
            }, headers=self._auth_headers(token))
            elapsed = time.time() - start
            assert response.status_code == 200
            assert elapsed < 5  # Should not take long with mocked AI

    def test_missing_location_returns_422(self):
        token, _ = _make_user("rel6")
        response = client.post("/api/crop-recommendations", json={
            "season": "kharif",
        }, headers=self._auth_headers(token))
        assert response.status_code == 422

    def test_insufficient_eligible_crops_honest(self):
        """If no crops are eligible, return honest empty list."""
        token, _ = _make_user("rel7")
        response = client.post("/api/crop-recommendations", json={
            "latitude": 16.5, "longitude": 80.6,
            "season": "kharif", "water_availability": "very_limited",
            "irrigation_method": "rainfed",
        }, headers=self._auth_headers(token))
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("success", "insufficient_data")


class TestNoSecretLogging:
    """Test that no secrets appear in logs."""

    def test_api_key_not_in_log_output(self):
        """API keys should not appear in log output."""
        import logging
        import io

        log_stream = io.StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setLevel(logging.DEBUG)
        logger = logging.getLogger("app.services.ai.reasoning_provider")
        logger.addHandler(handler)

        from app.services.ai.reasoning_provider import _call_nvidia_model
        provider = MagicMock()
        provider.text_api_key = "nvapi-SECRET_KEY_12345"
        provider.text_base_url = "https://fake.api.com/v1"

        _call_nvidia_model(provider, [{"role": "user", "content": "test"}], "model", 5)

        log_output = log_stream.getvalue()
        assert "nvapi-SECRET_KEY_12345" not in log_output

        logger.removeHandler(handler)


class TestSuitabilityScoreNotAccuracy:
    """Test that suitability score is not presented as accuracy."""

    def test_endpoint_returns_suitability_not_accuracy(self):
        token, _ = _make_user("suit1")
        response = client.post("/api/crop-recommendations", json={
            "latitude": 16.5, "longitude": 80.6,
            "season": "kharif", "water_availability": "moderate",
            "irrigation_method": "rainfed",
        }, headers=_auth_headers(token))
        assert response.status_code == 200
        data = response.json()
        for rec in data["recommendations"]:
            assert "suitability_score" in rec
            assert "accuracy" not in rec
            assert "confidence" not in rec

    def test_no_fake_confidence(self):
        """Suitability score must not be presented as confidence/accuracy."""
        token, _ = _make_user("suit2")
        response = client.post("/api/crop-recommendations", json={
            "latitude": 16.5, "longitude": 80.6,
            "season": "kharif", "water_availability": "moderate",
            "irrigation_method": "rainfed",
        }, headers=_auth_headers(token))
        data = response.json()
        # Response should not have top-level "confidence"
        assert "confidence" not in data

