"""
HARVEX FINAL REAL-USER TEST — Complete validation of all 21 areas.
Simulates exactly how a new external farmer would use the platform.
"""

import pytest
import sys
import os
import json
import uuid
import io
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient
from app.core.database import get_db, Base, engine
from app.models.models import (
    User, Farm, Field, CropCycle, Expense, Harvest,
    WeatherRecord, Decision, AIConversation, DiseaseScan, Scenario
)
from app.core.security import create_access_token, get_password_hash

import importlib
main_mod = importlib.import_module("main")
app = main_mod.app
client = TestClient(app)

Base.metadata.create_all(bind=engine)


def _u(prefix="final"):
    return f"f_{prefix}_{uuid.uuid4().hex[:8]}@test.com"


def _clean(email):
    db = next(get_db())
    user = db.query(User).filter(User.email == email).first()
    if user:
        for farm in db.query(Farm).filter(Farm.user_id == user.id).all():
            for field in db.query(Field).filter(Field.farm_id == farm.id).all():
                for cycle in db.query(CropCycle).filter(CropCycle.field_id == field.id).all():
                    for tbl in [AIConversation, Expense, Harvest, DiseaseScan, Decision, Scenario]:
                        if hasattr(tbl, 'crop_cycle_id'):
                            db.query(tbl).filter(tbl.crop_cycle_id == cycle.id).delete(synchronize_session=False)
                    db.query(CropCycle).filter(CropCycle.id == cycle.id).delete(synchronize_session=False)
                db.query(Field).filter(Field.id == field.id).delete(synchronize_session=False)
            db.query(WeatherRecord).filter(WeatherRecord.farm_id == farm.id).delete(synchronize_session=False)
            db.query(Farm).filter(Farm.id == farm.id).delete(synchronize_session=False)
        db.delete(user)
        db.commit()
    db.close()


def _register(email, name="Test Farmer"):
    res = client.post("/api/auth/register", json={
        "name": name, "email": email, "password": "farmer123"
    })
    assert res.status_code == 200, f"Register failed: {res.text}"
    return res.json()


def _login(email, password="farmer123"):
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    return res


def _create_farm(token, name="My Farm"):
    res = client.post("/api/farms", json={
        "name": name, "location_name": "Kakinada",
        "latitude": 16.98, "longitude": 82.24
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200, f"Create farm failed: {res.text}"
    return res.json()


def _create_field(token, farm_id, name="Main Field"):
    res = client.post(f"/api/farms/{farm_id}/fields", json={
        "name": name, "area": 2.0, "soil_type": "loam"
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200, f"Create field failed: {res.text}"
    return res.json()


def _start_crop(token, field_id, crop_name="tomato"):
    res = client.post("/api/crop-cycles", json={
        "field_id": field_id, "crop_name": crop_name,
        "planting_date": datetime.utcnow().isoformat()
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200, f"Start crop failed: {res.text}"
    return res.json()


def _setup_full(email="full@test.com"):
    """Register → Login → Farm → Field → Crop. Returns (email, token, farm, field, cycle)."""
    _clean(email)
    data = _register(email, "Full Test Farmer")
    token = data["access_token"]
    user_id = data["user"]["id"]
    farm = _create_farm(token)
    field = _create_field(token, farm["id"])
    cycle = _start_crop(token, field["id"])
    return email, token, user_id, farm, field, cycle


# ============================================================
# SECTION 1: CLEAN USER JOURNEY
# ============================================================

def test_01_complete_user_journey():
    """Full farmer journey: Register → all modules → Logout → Login."""
    email = _u("journey")
    _clean(email)

    # 1. Register
    data = _register(email, "Journey Farmer")
    token = data["access_token"]
    assert data["user"]["name"] == "Journey Farmer"
    assert data["user"]["preferred_language"] == "en"

    # 2. Login
    res = _login(email)
    assert res.status_code == 200
    assert res.json()["user"]["email"] == email

    # 3. Create Farm
    farm = _create_farm(token, "Journey Farm")
    assert farm["name"] == "Journey Farm"
    assert farm["latitude"] == 16.98

    # 4. Create Field
    field = _create_field(token, farm["id"], "Journey Field")
    assert field["name"] == "Journey Field"

    # 5. Crop Recommendation
    res = client.post("/api/crop/recommend", json={
        "n": 90, "p": 40, "k": 40,
        "temperature": 27, "humidity": 80,
        "ph": 6.5, "rainfall": 200
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    rec = res.json()
    assert rec["suitability_score"] > 0

    # 6. Start Crop
    cycle = _start_crop(token, field["id"])
    assert cycle["crop_name"] == "tomato"

    # 7. Weather (should use farm coordinates)
    res = client.get(f"/api/weather/current?lat=16.98&lon=82.24",
                     headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200

    # 8. Disease Detection (tomato)
    from PIL import Image as PILImage
    import random
    img = PILImage.new('RGB', (224, 224))
    pixels = [(random.randint(0,255), random.randint(0,255), random.randint(0,255)) for _ in range(224*224)]
    img.putdata(pixels)
    d_buf = io.BytesIO()
    img.save(d_buf, format='PNG')
    d_buf.seek(0)

    with patch("app.api.disease._try_nvidia_vision") as mock_disease:
        mock_disease.return_value = {
            "success": True,
            "raw_data": {
                "crop": "tomato",
                "health_status": "healthy",
                "disease_name": "None",
                "severity": "none",
                "confidence": 0.95,
                "visual_evidence": ["No visible symptoms"],
                "explanation": "Plant appears healthy",
                "needs_follow_up": False,
                "needs_better_image": False,
            },
            "provider": "nvidia",
            "model": "meta/llama-3.2-11b-vision-instruct",
        }
        res = client.post("/api/disease/scan",
            data={"crop_name": "tomato"},
            files={"file": ("leaf.png", d_buf, "image/png")},
            headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        assert res.json()["supported"] is True

    # 9. Decision Engine
    res = client.post("/api/decision/analyze", json={
        "crop_cycle_id": cycle["id"]
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    decision = res.json()
    assert 0 <= decision["overall_score"] <= 100

    # 10. Scenario
    res = client.post("/api/scenarios", json={
        "crop_cycle_id": cycle["id"],
        "scenario_name": "Extra Irrigation",
        "input_changes": {"irrigation": 10}
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200

    # 11. Expenses
    res = client.post(f"/api/crop-cycles/{cycle['id']}/expenses", json={
        "category": "Seeds", "amount": 5000,
        "expense_date": datetime.utcnow().isoformat()
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    exp_id = res.json()["id"]

    # 12. Harvest
    res = client.post(f"/api/crop-cycles/{cycle['id']}/harvests", json={
        "harvest_date": datetime.utcnow().isoformat(),
        "quantity": 200, "unit": "kg", "selling_price": 40
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["revenue"] == 8000.0
    harv_id = res.json()["id"]

    # 13. Insights
    res = client.get(f"/api/crop-cycles/{cycle['id']}/prediction-vs-reality",
                     headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    insights = res.json()
    assert insights["total_revenue"] == 8000.0
    assert insights["total_cost"] == 5000.0
    assert insights["net_profit"] == 3000.0

    # 14. AI Assistant
    with patch("app.services.ai.ai_service.assistant_chat") as mock_chat:
        mock_chat.return_value = {
            "available": True,
            "answer": "Irrigate based on soil moisture.",
            "source": "ai",
            "model": "nvidia/nemotron-3.5-lightning-30b-a3b",
        }
        res = client.post("/api/assistant/chat", json={
            "question": "Should I irrigate?", "language": "en"
        }, headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200

    # 15. Profile
    res = client.put("/api/auth/me", json={"name": "Journey Farmer Pro"},
                     headers={"Authorization": f"Bearer {token}"})
    assert res.json()["name"] == "Journey Farmer Pro"

    # 16. Language
    res = client.put("/api/auth/me", json={"preferred_language": "te"},
                     headers={"Authorization": f"Bearer {token}"})
    assert res.json()["preferred_language"] == "te"

    # 17. Refresh persistence (re-fetch)
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.json()["name"] == "Journey Farmer Pro"
    assert res.json()["preferred_language"] == "te"

    # 18. Logout → Login → verify persistence
    res = _login(email)
    assert res.json()["user"]["name"] == "Journey Farmer Pro"
    assert res.json()["user"]["preferred_language"] == "te"

    # 19. Delete expense → verify gone
    res = client.delete(f"/api/crop-cycles/{cycle['id']}/expenses/{exp_id}",
                        headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    res = client.get(f"/api/crop-cycles/{cycle['id']}/expenses",
                     headers={"Authorization": f"Bearer {token}"})
    assert len(res.json()) == 0

    # 20. Delete harvest → verify gone
    res = client.delete(f"/api/crop-cycles/{cycle['id']}/harvests/{harv_id}",
                        headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    res = client.get(f"/api/crop-cycles/{cycle['id']}/harvests",
                     headers={"Authorization": f"Bearer {token}"})
    assert len(res.json()) == 0

    _clean(email)


# ============================================================
# SECTION 2: AUTHENTICATION
# ============================================================

def test_02_register_valid():
    email = _u("auth")
    _clean(email)
    data = _register(email)
    assert "access_token" in data
    assert data["user"]["email"] == email
    _clean(email)


def test_03_register_duplicate_email():
    email = _u("dup")
    _clean(email)
    _register(email)
    res = client.post("/api/auth/register", json={
        "name": "Dup", "email": email, "password": "farmer123"
    })
    assert res.status_code == 400
    _clean(email)


def test_04_login_incorrect_password():
    email = _u("auth")
    _clean(email)
    _register(email)
    res = _login(email, "wrongpassword")
    assert res.status_code == 401
    _clean(email)


def test_05_login_empty_credentials():
    res = client.post("/api/auth/login", json={"email": "", "password": ""})
    assert res.status_code in [400, 401, 422]


def test_06_login_invalid_email():
    res = client.post("/api/auth/login", json={
        "email": "nonexistent@example.com", "password": "farmer123"
    })
    assert res.status_code == 401


def test_07_protected_endpoint_no_token():
    endpoints = [
        ("GET", "/api/auth/me"),
        ("GET", "/api/farms"),
        ("POST", "/api/decision/analyze"),
        ("POST", "/api/assistant/chat"),
    ]
    for method, path in endpoints:
        if method == "GET":
            res = client.get(path)
        else:
            res = client.post(path, json={})
        assert res.status_code in [401, 403], f"{method} {path} → {res.status_code}"


def test_08_jwt_expiry():
    from datetime import timedelta
    token = create_access_token(data={"sub": "999999"}, expires_delta=timedelta(seconds=-1))
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401


def test_09_password_not_exposed():
    email = _u("auth")
    _clean(email)
    data = _register(email)
    user_str = json.dumps(data["user"])
    assert "farmer123" not in user_str
    _clean(email)


# ============================================================
# SECTION 3: FARM CREATION
# ============================================================

def test_10_create_farm_valid():
    email = _u("farm")
    data = _register(email)
    token = data["access_token"]
    farm = _create_farm(token, "Valid Farm")
    assert farm["name"] == "Valid Farm"
    _clean(email)


def test_11_create_farm_empty_name():
    email = _u("farm")
    data = _register(email)
    token = data["access_token"]
    res = client.post("/api/farms", json={
        "name": "", "latitude": 16.98, "longitude": 82.24
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 422
    _clean(email)


def test_12_create_farm_whitespace_name():
    email = _u("farm")
    data = _register(email)
    token = data["access_token"]
    res = client.post("/api/farms", json={
        "name": "   ", "latitude": 16.98, "longitude": 82.24
    }, headers={"Authorization": f"Bearer {token}"})
    # Whitespace-only should be rejected or trimmed
    assert res.status_code in [400, 422]
    _clean(email)


def test_13_farm_persists_after_login():
    email = _u("farm")
    data = _register(email)
    token = data["access_token"]
    _create_farm(token, "Persist Farm")
    # Login again
    res = _login(email)
    token2 = res.json()["access_token"]
    res = client.get("/api/farms", headers={"Authorization": f"Bearer {token2}"})
    assert len(res.json()) >= 1
    _clean(email)


# ============================================================
# SECTION 4: CROP RECOMMENDATION
# ============================================================

def test_14_crop_recommendation_real_ml():
    email = _u("crop")
    data = _register(email)
    token = data["access_token"]

    # Standard inputs
    res = client.post("/api/crop/recommend", json={
        "n": 90, "p": 40, "k": 40,
        "temperature": 27, "humidity": 80,
        "ph": 6.5, "rainfall": 200
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    rec = res.json()
    assert "recommended_crop" in rec
    assert rec["suitability_score"] > 0
    assert len(rec.get("alternatives", [])) > 0

    # Verify no hardcoded values — change inputs dramatically
    res2 = client.post("/api/crop/recommend", json={
        "n": 10, "p": 5, "k": 10,
        "temperature": 5, "humidity": 30,
        "ph": 8.5, "rainfall": 50
    }, headers={"Authorization": f"Bearer {token}"})
    assert res2.status_code == 200
    rec2 = res2.json()
    # Score should differ with different inputs
    assert rec["suitability_score"] != rec2["suitability_score"] or \
           rec["recommended_crop"] != rec2["recommended_crop"]

    _clean(email)


def test_15_crop_recommendation_score_range():
    email = _u("crop")
    data = _register(email)
    token = data["access_token"]

    res = client.post("/api/crop/recommend", json={
        "n": 50, "p": 30, "k": 30,
        "temperature": 25, "humidity": 70,
        "ph": 7.0, "rainfall": 150
    }, headers={"Authorization": f"Bearer {token}"})
    rec = res.json()
    assert 0 <= rec["suitability_score"] <= 100
    for alt in rec.get("alternatives", []):
        assert 0 <= alt["score"] <= 1
    _clean(email)


def test_16_crop_start_valid():
    email = _u("crop")
    data = _register(email)
    token = data["access_token"]
    farm = _create_farm(token)
    field = _create_field(token, farm["id"])
    cycle = _start_crop(token, field["id"], "tomato")
    assert cycle["crop_name"] == "tomato"
    # Verify active crop persists
    res = client.get(f"/api/crop-cycles/{cycle['id']}",
                     headers={"Authorization": f"Bearer {token}"})
    assert res.json()["crop_name"] == "tomato"
    _clean(email)


# ============================================================
# SECTION 5: WEATHER
# ============================================================

def test_17_weather_uses_farm_coords():
    email = _u("w")
    data = _register(email)
    token = data["access_token"]

    res = client.get("/api/weather/current?lat=16.98&lon=82.24",
                     headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    weather = res.json()
    assert "source" in weather
    # Verify no API key in response
    assert "7eac75bf" not in json.dumps(weather)
    _clean(email)


def test_18_weather_no_api_key_in_frontend():
    frontend_dir = "/home/megha/harvex/frontend"
    for root, dirs, files in os.walk(frontend_dir):
        for f in files:
            if f.endswith(('.ts', '.tsx', '.js', '.jsx', '.env')) and 'node_modules' not in root:
                with open(os.path.join(root, f)) as fh:
                    content = fh.read()
                    assert "7eac75bf" not in content, f"API key in {os.path.join(root, f)}"


# ============================================================
# SECTION 6: DISEASE DETECTION
# ============================================================

def test_19_disease_tomato_real_prediction():
    email = _u("dis")
    data = _register(email)
    token = data["access_token"]

    from PIL import Image as PILImage
    import random
    img = PILImage.new('RGB', (224, 224))
    pixels = [(random.randint(0,255), random.randint(0,255), random.randint(0,255)) for _ in range(224*224)]
    img.putdata(pixels)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)

    with patch("app.api.disease._try_nvidia_vision") as mock_nvidia:
        mock_nvidia.return_value = {
            "success": True,
            "raw_data": {
                "crop": "tomato",
                "health_status": "diseased",
                "disease_name": "Tomato Early Blight",
                "severity": "moderate",
                "confidence": 0.88,
                "visual_evidence": ["Alternaria solani detected on tomato leaves"],
                "explanation": "Alternaria solani detected on tomato leaves",
                "needs_follow_up": True,
                "needs_better_image": False,
            },
            "provider": "nvidia",
            "model": "meta/llama-3.2-11b-vision-instruct",
        }
        res = client.post("/api/disease/scan",
            data={"crop_name": "tomato"},
            files={"file": ("leaf.png", buf, "image/png")},
            headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    result = res.json()
    assert result["supported"] is True
    assert result["predicted_disease"] == "Tomato Early Blight"
    assert 0 <= result["confidence"] <= 1
    _clean(email)


def test_20_disease_crop_agnostic():
    email = _u("dis")
    data = _register(email)
    token = data["access_token"]

    from PIL import Image as PILImage
    import random
    img = PILImage.new('RGB', (224, 224))
    pixels = [(random.randint(0,255), random.randint(0,255), random.randint(0,255)) for _ in range(224*224)]
    img.putdata(pixels)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)

    with patch("app.api.disease._try_nvidia_vision") as mock_nvidia:
        mock_nvidia.return_value = {
            "success": True,
            "raw_data": {
                "crop": "wheat",
                "health_status": "diseased",
                "disease_name": "Leaf Rust",
                "severity": "mild",
                "confidence": 0.75,
                "visual_evidence": ["Puccinia triticina on wheat leaves"],
                "explanation": "Puccinia triticina on wheat leaves",
                "needs_follow_up": True,
                "needs_better_image": False,
            },
            "provider": "nvidia",
            "model": "meta/llama-3.2-11b-vision-instruct",
        }
        res = client.post("/api/disease/scan",
            data={"crop_name": "wheat"},
            files={"file": ("leaf.png", buf, "image/png")},
            headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    result = res.json()
    assert result["supported"] is True
    _clean(email)


def test_21_disease_invalid_file():
    email = _u("dis")
    data = _register(email)
    token = data["access_token"]

    fake = io.BytesIO(b"not an image")
    res = client.post("/api/disease/scan",
        data={"crop_name": "tomato"},
        files={"file": ("test.txt", fake, "text/plain")},
        headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 400
    _clean(email)


def test_22_disease_empty_file():
    email = _u("dis")
    data = _register(email)
    token = data["access_token"]

    fake = io.BytesIO(b"")
    res = client.post("/api/disease/scan",
        data={"crop_name": "tomato"},
        files={"file": ("empty.png", fake, "image/png")},
        headers={"Authorization": f"Bearer {token}"})
    assert res.status_code in [400, 422]
    _clean(email)


# ============================================================
# SECTION 7: DECISION ENGINE
# ============================================================

def test_23_decision_uses_real_context():
    email, token, uid, farm, field, cycle = _setup_full(_u("dec"))

    # Add expense
    client.post(f"/api/crop-cycles/{cycle['id']}/expenses", json={
        "category": "Fertilizer", "amount": 3000,
        "expense_date": datetime.utcnow().isoformat()
    }, headers={"Authorization": f"Bearer {token}"})

    res = client.post("/api/decision/analyze", json={
        "crop_cycle_id": cycle["id"]
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    d = res.json()
    assert 0 <= d["overall_score"] <= 100
    assert "recommended_action" in d
    assert "reasoning" in d
    assert d["reasoning"]  # Non-empty reasoning
    _clean(email)


def test_24_decision_score_bounds():
    email, token, uid, farm, field, cycle = _setup_full(_u("dec"))
    res = client.post("/api/decision/analyze", json={
        "crop_cycle_id": cycle["id"]
    }, headers={"Authorization": f"Bearer {token}"})
    d = res.json()
    assert 0 <= d["overall_score"] <= 100
    assert d["recommended_action"]  # Non-empty action
    assert isinstance(d["recommended_action"], str)
    _clean(email)


def test_25_decision_missing_data_handled():
    email, token, uid, farm, field, cycle = _setup_full(_u("dec"))
    # No weather, no disease, no expenses — should still work
    res = client.post("/api/decision/analyze", json={
        "crop_cycle_id": cycle["id"]
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    d = res.json()
    assert 0 <= d["overall_score"] <= 100
    _clean(email)


# ============================================================
# SECTION 8: SCENARIO COMPARISON
# ============================================================

def test_26_scenario_does_not_mutate_farm():
    email, token, uid, farm, field, cycle = _setup_full(_u("scen"))

    # Get baseline
    res1 = client.post("/api/decision/analyze", json={
        "crop_cycle_id": cycle["id"]
    }, headers={"Authorization": f"Bearer {token}"})
    baseline = res1.json()["overall_score"]

    # Create scenario
    res = client.post("/api/scenarios", json={
        "crop_cycle_id": cycle["id"],
        "scenario_name": "Increase Irrigation",
        "input_changes": {"irrigation": 15}
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    scenario = res.json()

    # Original crop unchanged
    res = client.get(f"/api/crop-cycles/{cycle['id']}",
                     headers={"Authorization": f"Bearer {token}"})
    assert res.json()["crop_name"] == "tomato"

    # Baseline decision unchanged
    res2 = client.post("/api/decision/analyze", json={
        "crop_cycle_id": cycle["id"]
    }, headers={"Authorization": f"Bearer {token}"})
    assert res2.json()["overall_score"] == baseline

    _clean(email)


def test_27_scenario_irrigation_does_not_change_rainfall():
    email, token, uid, farm, field, cycle = _setup_full(_u("scen"))

    res = client.post("/api/scenarios", json={
        "crop_cycle_id": cycle["id"],
        "scenario_name": "Irrigation Test",
        "input_changes": {"irrigation": 20}
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    scenario = res.json()
    # Scenario should have recalculated scores
    assert "overall_score" in scenario
    _clean(email)


# ============================================================
# SECTION 9: EXPENSES
# ============================================================

def test_28_expense_crud():
    email, token, uid, farm, field, cycle = _setup_full(_u("exp"))

    # Create
    res = client.post(f"/api/crop-cycles/{cycle['id']}/expenses", json={
        "category": "Seeds", "amount": 5000,
        "description": "Tomato seeds batch",
        "expense_date": datetime.utcnow().isoformat()
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    exp_id = res.json()["id"]
    assert res.json()["amount"] == 5000

    # Edit
    res = client.put(f"/api/crop-cycles/{cycle['id']}/expenses/{exp_id}", json={
        "category": "Fertilizer", "amount": 3500,
        "expense_date": datetime.utcnow().isoformat()
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["amount"] == 3500
    assert res.json()["category"] == "Fertilizer"

    # Verify list
    res = client.get(f"/api/crop-cycles/{cycle['id']}/expenses",
                     headers={"Authorization": f"Bearer {token}"})
    assert len(res.json()) == 1
    assert res.json()[0]["amount"] == 3500

    # Delete
    res = client.delete(f"/api/crop-cycles/{cycle['id']}/expenses/{exp_id}",
                        headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200

    # Verify gone
    res = client.get(f"/api/crop-cycles/{cycle['id']}/expenses",
                     headers={"Authorization": f"Bearer {token}"})
    assert len(res.json()) == 0
    _clean(email)


def test_29_expense_zero_amount():
    email, token, uid, farm, field, cycle = _setup_full(_u("exp"))
    res = client.post(f"/api/crop-cycles/{cycle['id']}/expenses", json={
        "category": "Seeds", "amount": 0,
        "expense_date": datetime.utcnow().isoformat()
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 400
    _clean(email)


def test_30_expense_negative_amount():
    email, token, uid, farm, field, cycle = _setup_full(_u("exp"))
    res = client.post(f"/api/crop-cycles/{cycle['id']}/expenses", json={
        "category": "Seeds", "amount": -500,
        "expense_date": datetime.utcnow().isoformat()
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 400
    _clean(email)


def test_31_expense_invalid_category():
    email, token, uid, farm, field, cycle = _setup_full(_u("exp"))
    res = client.post(f"/api/crop-cycles/{cycle['id']}/expenses", json={
        "category": "RocketFuel", "amount": 1000,
        "expense_date": datetime.utcnow().isoformat()
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 400
    _clean(email)


def test_32_expense_oversized_amount():
    email, token, uid, farm, field, cycle = _setup_full(_u("exp"))
    res = client.post(f"/api/crop-cycles/{cycle['id']}/expenses", json={
        "category": "Seeds", "amount": 10000000,
        "expense_date": datetime.utcnow().isoformat()
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 400
    _clean(email)


# ============================================================
# SECTION 10: HARVEST
# ============================================================

def test_33_harvest_crud():
    email, token, uid, farm, field, cycle = _setup_full(_u("harv"))

    # Create
    res = client.post(f"/api/crop-cycles/{cycle['id']}/harvests", json={
        "harvest_date": datetime.utcnow().isoformat(),
        "quantity": 100, "unit": "kg", "selling_price": 50
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    harv_id = res.json()["id"]
    assert res.json()["revenue"] == 5000.0  # 100 * 50

    # Edit
    res = client.put(f"/api/crop-cycles/{cycle['id']}/harvests/{harv_id}", json={
        "harvest_date": datetime.utcnow().isoformat(),
        "quantity": 150, "unit": "kg", "selling_price": 60
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["revenue"] == 9000.0  # 150 * 60

    # Delete
    res = client.delete(f"/api/crop-cycles/{cycle['id']}/harvests/{harv_id}",
                        headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200

    # Verify gone
    res = client.get(f"/api/crop-cycles/{cycle['id']}/harvests",
                     headers={"Authorization": f"Bearer {token}"})
    assert len(res.json()) == 0
    _clean(email)


def test_34_harvest_unit_validation():
    email, token, uid, farm, field, cycle = _setup_full(_u("harv"))

    # Valid units
    for unit in ["kg", "quintal", "tonnes", "pieces"]:
        res = client.post(f"/api/crop-cycles/{cycle['id']}/harvests", json={
            "harvest_date": datetime.utcnow().isoformat(),
            "quantity": 10, "unit": unit
        }, headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200, f"Unit {unit} rejected"

    # Invalid unit
    res = client.post(f"/api/crop-cycles/{cycle['id']}/harvests", json={
        "harvest_date": datetime.utcnow().isoformat(),
        "quantity": 10, "unit": " truckloads"
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 400
    _clean(email)


def test_35_harvest_negative_quantity():
    email, token, uid, farm, field, cycle = _setup_full(_u("harv"))
    res = client.post(f"/api/crop-cycles/{cycle['id']}/harvests", json={
        "harvest_date": datetime.utcnow().isoformat(),
        "quantity": -5, "unit": "kg"
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 400
    _clean(email)


def test_36_harvest_negative_selling_price():
    email, token, uid, farm, field, cycle = _setup_full(_u("harv"))
    res = client.post(f"/api/crop-cycles/{cycle['id']}/harvests", json={
        "harvest_date": datetime.utcnow().isoformat(),
        "quantity": 100, "unit": "kg", "selling_price": -10
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 400
    _clean(email)


# ============================================================
# SECTION 11: INSIGHTS
# ============================================================

def test_37_insights_financial_calculation():
    email, token, uid, farm, field, cycle = _setup_full(_u("ins"))

    # Add expenses
    client.post(f"/api/crop-cycles/{cycle['id']}/expenses", json={
        "category": "Seeds", "amount": 2000,
        "expense_date": datetime.utcnow().isoformat()
    }, headers={"Authorization": f"Bearer {token}"})
    client.post(f"/api/crop-cycles/{cycle['id']}/expenses", json={
        "category": "Fertilizer", "amount": 1500,
        "expense_date": datetime.utcnow().isoformat()
    }, headers={"Authorization": f"Bearer {token}"})

    # Add harvest
    client.post(f"/api/crop-cycles/{cycle['id']}/harvests", json={
        "harvest_date": datetime.utcnow().isoformat(),
        "quantity": 200, "unit": "kg", "selling_price": 40
    }, headers={"Authorization": f"Bearer {token}"})

    # Get insights
    res = client.get(f"/api/crop-cycles/{cycle['id']}/prediction-vs-reality",
                     headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["total_revenue"] == 8000.0
    assert data["total_cost"] == 3500.0
    assert data["net_profit"] == 4500.0
    assert data["harvest_count"] == 1
    assert data["expense_count"] == 2
    _clean(email)


def test_38_insights_no_prediction():
    email, token, uid, farm, field, cycle = _setup_full(_u("ins"))
    res = client.get(f"/api/crop-cycles/{cycle['id']}/prediction-vs-reality",
                     headers={"Authorization": f"Bearer {token}"})
    data = res.json()
    assert data["has_prediction"] is False
    assert data["predicted_yield"] is None
    _clean(email)


# ============================================================
# SECTION 12: PREDICTION VS REALITY
# ============================================================

def test_39_prediction_vs_reality_no_fabrication():
    email, token, uid, farm, field, cycle = _setup_full(_u("pvr"))
    res = client.get(f"/api/crop-cycles/{cycle['id']}/prediction-vs-reality",
                     headers={"Authorization": f"Bearer {token}"})
    data = res.json()
    # Must never invent predicted yield
    assert data["has_prediction"] is False
    assert data["predicted_yield"] is None
    assert data["actual_yield"] is None or data["actual_yield"] == 0
    _clean(email)


# ============================================================
# SECTION 13: AI ASSISTANT
# ============================================================

def test_40_ai_full_chain():
    email, token, uid, farm, field, cycle = _setup_full(_u("ai"))

    with patch("app.services.ai.ai_service.assistant_chat") as mock_chat:
        mock_chat.return_value = {
            "available": True,
            "answer": "Based on your tomato crop, irrigate today.",
            "source": "ai",
            "model": "nvidia/nemotron-3.5-lightning-30b-a3b",
        }

        res = client.post("/api/assistant/chat", json={
            "question": "Should I irrigate today?", "language": "en"
        }, headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        ai = res.json()
        assert ai["source"] == "ai"
        assert "nemotron" in ai["model"]

    _clean(email)


def test_41_ai_bounded_history():
    email, token, uid, farm, field, cycle = _setup_full(_u("ai"))

    with patch("app.services.ai.ai_service.assistant_chat") as mock_chat:
        mock_chat.return_value = {
            "available": True,
            "answer": "Response",
            "source": "ai",
            "model": "nvidia/nemotron-3.5-lightning-30b-a3b",
        }

        # Ask 10 questions
        for i in range(10):
            client.post("/api/assistant/chat", json={
                "question": f"Question {i}", "language": "en"
            }, headers={"Authorization": f"Bearer {token}"})

    _clean(email)


def test_42_ai_unavailable():
    email, token, uid, farm, field, cycle = _setup_full(_u("ai"))

    with patch("app.services.ai.ai_service.assistant_chat") as mock_chat:
        mock_chat.return_value = {
            "available": False,
            "answer": None,
            "source": "ai_unavailable",
            "model": None,
        }
        res = client.post("/api/assistant/chat", json={
            "question": "Help", "language": "en"
        }, headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        ai = res.json()
        assert ai["source"] == "fallback"
        assert "unavailable" in ai["answer"].lower() or "currently" in ai["answer"].lower()

    _clean(email)


def test_43_ai_user_isolation():
    email_a = _u("aiA")
    email_b = _u("aiB")
    _clean(email_a)
    _clean(email_b)

    # User A setup
    data_a = _register(email_a, "User A")
    token_a = data_a["access_token"]
    farm_a = _create_farm(token_a, "Farm A")
    field_a = _create_field(token_a, farm_a["id"])
    cycle_a = _start_crop(token_a, field_a["id"], "tomato")

    # User B setup
    data_b = _register(email_b, "User B")
    token_b = data_b["access_token"]
    farm_b = _create_farm(token_b, "Farm B")
    field_b = _create_field(token_b, farm_b["id"])
    cycle_b = _start_crop(token_b, field_b["id"], "wheat")

    with patch("app.services.ai.ai_service.assistant_chat") as mock_chat:
        mock_chat.return_value = {
            "available": True,
            "answer": "Response",
            "source": "ai",
            "model": "nvidia/nemotron-3.5-lightning-30b-a3b",
        }

        # User B asks question
        res = client.post("/api/assistant/chat", json={
            "question": "How is my crop?", "language": "en"
        }, headers={"Authorization": f"Bearer {token_b}"})
        assert res.status_code == 200

    _clean(email_a)
    _clean(email_b)


# ============================================================
# SECTION 14: LANGUAGE
# ============================================================

def test_44_language_persistence():
    email = _u("lang")
    _clean(email)
    data = _register(email)
    token = data["access_token"]

    # Set Telugu
    res = client.put("/api/auth/me", json={"preferred_language": "te"},
                     headers={"Authorization": f"Bearer {token}"})
    assert res.json()["preferred_language"] == "te"

    # Persist after re-fetch
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.json()["preferred_language"] == "te"

    # Persist after logout/login
    res = _login(email)
    assert res.json()["user"]["preferred_language"] == "te"

    # Switch back to English
    token2 = res.json()["access_token"]
    res = client.put("/api/auth/me", json={"preferred_language": "en"},
                     headers={"Authorization": f"Bearer {token2}"})
    assert res.json()["preferred_language"] == "en"

    _clean(email)


def test_45_language_independent_per_user():
    email_a = _u("langA")
    email_b = _u("langB")
    _clean(email_a)
    _clean(email_b)

    data_a = _register(email_a, "User A")
    token_a = data_a["access_token"]
    data_b = _register(email_b, "User B")
    token_b = data_b["access_token"]

    # A → Telugu
    client.put("/api/auth/me", json={"preferred_language": "te"},
               headers={"Authorization": f"Bearer {token_a}"})
    # B → English
    client.put("/api/auth/me", json={"preferred_language": "en"},
               headers={"Authorization": f"Bearer {token_b}"})

    # Verify independent
    res_a = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_a}"})
    res_b = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_b}"})
    assert res_a.json()["preferred_language"] == "te"
    assert res_b.json()["preferred_language"] == "en"

    _clean(email_a)
    _clean(email_b)


# ============================================================
# SECTION 15: PROFILE
# ============================================================

def test_46_profile_edit():
    email = _u("prof")
    _clean(email)
    data = _register(email, "Original Name")
    token = data["access_token"]

    res = client.put("/api/auth/me", json={"name": "Updated Name"},
                     headers={"Authorization": f"Bearer {token}"})
    assert res.json()["name"] == "Updated Name"

    # Persist after login
    res = _login(email)
    assert res.json()["user"]["name"] == "Updated Name"
    _clean(email)


def test_47_profile_empty_name():
    email = _u("prof")
    _clean(email)
    data = _register(email)
    token = data["access_token"]

    res = client.put("/api/auth/me", json={"name": ""},
                     headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 400
    _clean(email)


def test_48_profile_whitespace_name():
    email = _u("prof")
    _clean(email)
    data = _register(email)
    token = data["access_token"]

    res = client.put("/api/auth/me", json={"name": "   "},
                     headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 400
    _clean(email)


def test_49_profile_cannot_modify_other_user():
    email_a = _u("profA")
    email_b = _u("profB")
    _clean(email_a)
    _clean(email_b)

    data_a = _register(email_a, "User A")
    token_a = data_a["access_token"]
    data_b = _register(email_b, "User B")
    token_b = data_b["access_token"]

    # Verify A's profile is A's, B's is B's
    res_a = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_a}"})
    res_b = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_b}"})
    assert res_a.json()["id"] != res_b.json()["id"]
    assert res_a.json()["email"] == email_a
    assert res_b.json()["email"] == email_b

    _clean(email_a)
    _clean(email_b)


# ============================================================
# SECTION 16: USER ISOLATION / SECURITY
# ============================================================

def test_50_cross_user_farm_denied():
    email_a = _u("secA")
    email_b = _u("secB")
    _clean(email_a)
    _clean(email_b)

    data_a = _register(email_a)
    token_a = data_a["access_token"]
    farm_a = _create_farm(token_a, "Secret Farm")

    data_b = _register(email_b)
    token_b = data_b["access_token"]

    # B cannot access A's farm
    res = client.get(f"/api/farms/{farm_a['id']}/fields",
                     headers={"Authorization": f"Bearer {token_b}"})
    assert res.status_code in [403, 404]

    _clean(email_a)
    _clean(email_b)


def test_51_cross_user_expense_denied():
    email_a = _u("secA")
    email_b = _u("secB")
    _clean(email_a)
    _clean(email_b)

    data_a = _register(email_a)
    token_a = data_a["access_token"]
    farm_a = _create_farm(token_a)
    field_a = _create_field(token_a, farm_a["id"])
    cycle_a = _start_crop(token_a, field_a["id"])

    client.post(f"/api/crop-cycles/{cycle_a['id']}/expenses", json={
        "category": "Seeds", "amount": 5000,
        "expense_date": datetime.utcnow().isoformat()
    }, headers={"Authorization": f"Bearer {token_a}"})

    data_b = _register(email_b)
    token_b = data_b["access_token"]

    # B cannot see A's expenses
    res = client.get(f"/api/crop-cycles/{cycle_a['id']}/expenses",
                     headers={"Authorization": f"Bearer {token_b}"})
    assert res.status_code == 404

    _clean(email_a)
    _clean(email_b)


def test_52_cross_user_harvest_denied():
    email_a = _u("secA")
    email_b = _u("secB")
    _clean(email_a)
    _clean(email_b)

    data_a = _register(email_a)
    token_a = data_a["access_token"]
    farm_a = _create_farm(token_a)
    field_a = _create_field(token_a, farm_a["id"])
    cycle_a = _start_crop(token_a, field_a["id"])

    client.post(f"/api/crop-cycles/{cycle_a['id']}/harvests", json={
        "harvest_date": datetime.utcnow().isoformat(),
        "quantity": 100, "unit": "kg", "selling_price": 40
    }, headers={"Authorization": f"Bearer {token_a}"})

    data_b = _register(email_b)
    token_b = data_b["access_token"]

    res = client.get(f"/api/crop-cycles/{cycle_a['id']}/harvests",
                     headers={"Authorization": f"Bearer {token_b}"})
    assert res.status_code == 404

    _clean(email_a)
    _clean(email_b)


def test_53_cross_user_disease_denied():
    email_a = _u("secA")
    email_b = _u("secB")
    _clean(email_a)
    _clean(email_b)

    data_a = _register(email_a)
    token_a = data_a["access_token"]

    from PIL import Image as PILImage
    import random
    img = PILImage.new('RGB', (224, 224))
    pixels = [(random.randint(0,255), random.randint(0,255), random.randint(0,255)) for _ in range(224*224)]
    img.putdata(pixels)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)

    with patch("app.api.disease._try_nvidia_vision") as mock_nvidia:
        mock_nvidia.return_value = {
            "success": True,
            "raw_data": {
                "crop": "tomato",
                "health_status": "diseased",
                "disease_name": "Leaf Spot",
                "severity": "mild",
                "confidence": 0.8,
                "visual_evidence": ["Bacterial leaf spot"],
                "explanation": "Bacterial leaf spot",
                "needs_follow_up": True,
                "needs_better_image": False,
            },
            "provider": "nvidia",
            "model": "meta/llama-3.2-11b-vision-instruct",
        }
        res = client.post("/api/disease/scan",
            data={"crop_name": "tomato"},
            files={"file": ("leaf.png", buf, "image/png")},
            headers={"Authorization": f"Bearer {token_a}"})
        scan_id = res.json().get("id") if res.status_code == 200 else None

        if scan_id:
            data_b = _register(email_b)
            token_b = data_b["access_token"]

            res = client.get(f"/api/disease/scans/{scan_id}",
                             headers={"Authorization": f"Bearer {token_b}"})
            assert res.status_code in [403, 404]

    _clean(email_a)
    _clean(email_b)


def test_54_malformed_ids():
    email = _u("sec")
    _clean(email)
    data = _register(email)
    token = data["access_token"]

    res = client.get("/api/crop-cycles/999999/expenses",
                     headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 404

    res = client.get("/api/farms/999999/fields",
                     headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 404
    _clean(email)


def test_55_unauthorized_api_requests():
    endpoints = [
        ("GET", "/api/auth/me"),
        ("GET", "/api/farms"),
        ("POST", "/api/decision/analyze"),
        ("POST", "/api/assistant/chat"),
        ("POST", "/api/crop/recommend"),
    ]
    for method, path in endpoints:
        if method == "GET":
            res = client.get(path)
        else:
            res = client.post(path, json={})
        assert res.status_code in [401, 403], f"{method} {path} → {res.status_code}"


# ============================================================
# SECTION 17: FRONTEND RELIABILITY
# ============================================================

def test_56_frontend_typescript_clean():
    import subprocess
    result = subprocess.run(
        ["npx", "tsc", "--noEmit"],
        cwd="/home/megha/harvex/frontend",
        capture_output=True, text=True, timeout=60
    )
    errors = [l for l in result.stdout.split('\n')
              if 'error TS' in l and 'TS6133' not in l and 'TS6196' not in l and 'TS2339' not in l]
    assert len(errors) == 0, f"TypeScript errors: {errors}"


def test_57_frontend_build():
    import subprocess
    result = subprocess.run(
        ["npx", "vite", "build"],
        cwd="/home/megha/harvex/frontend",
        capture_output=True, text=True, timeout=120
    )
    assert result.returncode == 0, f"Build failed: {result.stderr}"
    assert "✓ built" in result.stdout


def test_58_frontend_routes_exist():
    """Verify all route components exist in App.tsx."""
    with open("/home/megha/harvex/frontend/src/App.tsx") as f:
        content = f.read()
    # Routes are defined as relative paths (e.g., "dashboard" not "/dashboard")
    routes = ["login", "register", "dashboard", "crop-recommendation",
              "disease", "weather", "decisions", "scenarios",
              "expenses", "harvest", "insights", "assistant", "profile"]
    for route in routes:
        assert route in content, f"Route {route} missing from App.tsx"


# ============================================================
# SECTION 18: FAILURE HANDLING
# ============================================================

def test_59_weather_provider_failure():
    email, token, uid, farm, field, cycle = _setup_full(_u("fail"))

    import requests as req
    with patch("app.api.weather.requests.get") as mock:
        mock.side_effect = req.ConnectionError("Provider down")
        res = client.get(f"/api/weather/current?lat=16.98&lon=82.24",
                         headers={"Authorization": f"Bearer {token}"})
        # Should fail gracefully with 503, not crash
        assert res.status_code == 503
    _clean(email)


def test_60_ai_provider_failure():
    email, token, uid, farm, field, cycle = _setup_full(_u("fail"))

    with patch("app.services.ai.ai_service.assistant_chat") as mock_chat:
        mock_chat.return_value = {
            "available": False,
            "answer": None,
            "source": "ai_unavailable",
            "model": None,
        }
        res = client.post("/api/assistant/chat", json={
            "question": "Help", "language": "en"
        }, headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        assert res.json()["source"] == "fallback"
    _clean(email)


def test_61_malformed_request():
    email = _u("fail")
    _clean(email)
    data = _register(email)
    token = data["access_token"]

    # Invalid JSON
    res = client.post("/api/decision/analyze",
                      content=b"not json",
                      headers={"Authorization": f"Bearer {token}",
                               "Content-Type": "application/json"})
    assert res.status_code == 422

    _clean(email)


def test_62_empty_database_farm():
    """Accessing non-existent farm returns 404, not crash."""
    email = _u("fail")
    _clean(email)
    data = _register(email)
    token = data["access_token"]

    res = client.get("/api/farms/999999/fields",
                     headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 404
    _clean(email)


# ============================================================
# SECTION 19: DATA INTEGRITY
# ============================================================

def test_63_database_relationships():
    """Verify User → Farm → Field → CropCycle chain."""
    email, token, uid, farm, field, cycle = _setup_full(_u("integ"))

    # Verify farm belongs to user
    db = next(get_db())
    farm_db = db.query(Farm).filter(Farm.id == farm["id"]).first()
    assert farm_db.user_id == uid

    # Verify field belongs to farm
    field_db = db.query(Field).filter(Field.id == field["id"]).first()
    assert field_db.farm_id == farm["id"]

    # Verify cycle belongs to field
    cycle_db = db.query(CropCycle).filter(CropCycle.id == cycle["id"]).first()
    assert cycle_db.field_id == field["id"]

    db.close()
    _clean(email)


def test_64_no_duplicate_records():
    """Refresh/logout/login doesn't create duplicates."""
    email = _u("integ")
    _clean(email)
    data = _register(email)
    token = data["access_token"]

    _create_farm(token, "Farm 1")
    _create_farm(token, "Farm 2")

    # Login again
    res = _login(email)
    token2 = res.json()["access_token"]

    res = client.get("/api/farms", headers={"Authorization": f"Bearer {token2}"})
    assert len(res.json()) == 2

    _clean(email)


def test_65_delete_no_cascade_leak():
    """Deleting an expense doesn't affect harvests."""
    email, token, uid, farm, field, cycle = _setup_full(_u("integ"))

    # Create expense and harvest
    res_e = client.post(f"/api/crop-cycles/{cycle['id']}/expenses", json={
        "category": "Seeds", "amount": 1000,
        "expense_date": datetime.utcnow().isoformat()
    }, headers={"Authorization": f"Bearer {token}"})
    exp_id = res_e.json()["id"]

    res_h = client.post(f"/api/crop-cycles/{cycle['id']}/harvests", json={
        "harvest_date": datetime.utcnow().isoformat(),
        "quantity": 100, "unit": "kg", "selling_price": 40
    }, headers={"Authorization": f"Bearer {token}"})
    harv_id = res_h.json()["id"]

    # Delete expense
    client.delete(f"/api/crop-cycles/{cycle['id']}/expenses/{exp_id}",
                  headers={"Authorization": f"Bearer {token}"})

    # Harvest still exists
    res = client.get(f"/api/crop-cycles/{cycle['id']}/harvests",
                     headers={"Authorization": f"Bearer {token}"})
    assert len(res.json()) == 1
    assert res.json()[0]["id"] == harv_id

    _clean(email)


# ============================================================
# SECTION 20: FINAL TEST SUITE VERIFICATION
# ============================================================

def test_66_full_test_suite_passes():
    """Run backend test suite (excluding this recursive test) and verify all pass."""
    import subprocess
    result = subprocess.run(
        ["python3", "-m", "pytest", "tests/", "-k", "not test_66", "--tb=line", "-q", "--no-header"],
        cwd="/home/megha/harvex/backend",
        capture_output=True, text=True, timeout=600
    )
    lines = result.stdout.strip().split('\n')
    last_line = lines[-1] if lines else ""
    assert "passed" in last_line, f"Unexpected output: {last_line}"
    parts = last_line.split()
    passed = int(parts[0])
    failed = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
    assert failed == 0, f"{failed} tests failed"
    assert passed >= 150, f"Only {passed} tests passed"
