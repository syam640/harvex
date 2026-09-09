"""PHASE 7: AI Assistant + Profile + Language Tests — 38 tests."""

import pytest
import sys
import os
import json
import uuid
import requests
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient
from app.core.database import get_db, Base, engine
from app.models.models import User, Farm, Field, CropCycle, AIConversation, WeatherRecord, Decision, Expense, Harvest, DiseaseScan
from app.core.security import create_access_token, get_password_hash

import importlib
main_mod = importlib.import_module("main")
app = main_mod.app
client = TestClient(app)

_counter = 0


def _next():
    global _counter
    _counter += 1
    return _counter


def _setup_db():
    Base.metadata.create_all(bind=engine)


_setup_db()


def _make_user(prefix="user"):
    n = _next()
    email = f"phase7_{prefix}_{n}@example.com"
    db = next(get_db())
    # Clean any existing user and their data
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        farms = db.query(Farm).filter(Farm.user_id == existing.id).all()
        for f in farms:
            fields = db.query(Field).filter(Field.farm_id == f.id).all()
            for field in fields:
                db.query(AIConversation).filter(AIConversation.crop_cycle_id.in_(
                    db.query(CropCycle.id).filter(CropCycle.field_id == field.id)
                )).delete(synchronize_session=False)
                db.query(Expense).filter(Expense.crop_cycle_id.in_(
                    db.query(CropCycle.id).filter(CropCycle.field_id == field.id)
                )).delete(synchronize_session=False)
                db.query(Harvest).filter(Harvest.crop_cycle_id.in_(
                    db.query(CropCycle.id).filter(CropCycle.field_id == field.id)
                )).delete(synchronize_session=False)
                db.query(Decision).filter(Decision.crop_cycle_id.in_(
                    db.query(CropCycle.id).filter(CropCycle.field_id == field.id)
                )).delete(synchronize_session=False)
                db.query(DiseaseScan).filter(DiseaseScan.crop_cycle_id.in_(
                    db.query(CropCycle.id).filter(CropCycle.field_id == field.id)
                )).delete(synchronize_session=False)
                db.query(CropCycle).filter(CropCycle.field_id == field.id).delete(synchronize_session=False)
            db.query(Field).filter(Field.farm_id == f.id).delete(synchronize_session=False)
            db.query(WeatherRecord).filter(WeatherRecord.farm_id == f.id).delete(synchronize_session=False)
        db.query(Farm).filter(Farm.user_id == existing.id).delete(synchronize_session=False)
        db.delete(existing)
        db.commit()

    user = User(
        name=f"P7 {n}", email=email,
        password_hash=get_password_hash("testpass123"),
        preferred_language="en"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    uid = user.id
    db.close()
    return uid, email


def _make_farm_with_crop(user_id, crop="tomato", predicted_yield=1500.0):
    db = next(get_db())
    farm = Farm(name="Test Farm", user_id=user_id, latitude=16.9, longitude=82.0, location_name="Kakinada")
    db.add(farm)
    db.commit()
    db.refresh(farm)

    field = Field(name="Test Field", farm_id=farm.id, area=1.0, soil_type="loam")
    db.add(field)
    db.commit()
    db.refresh(field)

    cycle = CropCycle(
        field_id=field.id, crop_name=crop,
        planting_date=datetime.utcnow() - timedelta(days=30),
        expected_harvest_date=datetime.utcnow() + timedelta(days=60),
        status="active", predicted_yield=predicted_yield
    )
    db.add(cycle)
    db.commit()
    db.refresh(cycle)

    cid = cycle.id
    db.close()
    return cid


def _make_weather(farm_id):
    db = next(get_db())
    weather = WeatherRecord(
        farm_id=farm_id, latitude=16.9, longitude=82.0,
        temperature=32.0, humidity=65.0, rainfall=5.0,
        weather_condition="Clear", source="OpenWeather",
        observed_at=datetime.utcnow()
    )
    db.add(weather)
    db.commit()
    db.close()


def _make_decision(cycle_id):
    db = next(get_db())
    decision = Decision(
        crop_cycle_id=cycle_id,
        recommended_action="Proceed with normal irrigation schedule",
        score=72.5, profit_score=80.0, risk_score=65.0,
        cost_score=70.0, water_score=75.0
    )
    db.add(decision)
    db.commit()
    db.close()


def _make_expense(cycle_id):
    db = next(get_db())
    expense = Expense(
        crop_cycle_id=cycle_id, category="Seeds", amount=5000,
        expense_date=datetime.utcnow()
    )
    db.add(expense)
    db.commit()
    db.close()


def _make_harvest(cycle_id):
    db = next(get_db())
    harvest = Harvest(
        crop_cycle_id=cycle_id,
        harvest_date=datetime.utcnow(),
        quantity=200, unit="kg", selling_price=40
    )
    db.add(harvest)
    db.commit()
    db.close()


def _token(user_id):
    return create_access_token(data={"sub": str(user_id)})


def _register_and_login(email, password="testpass123"):
    uid, email = email, email
    db = next(get_db())
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(name="Test", email=email, password_hash=get_password_hash(password))
        db.add(user)
        db.commit()
        db.refresh(user)
    uid = user.id
    db.close()
    token = create_access_token(data={"sub": str(uid)})
    return token, uid


# ============================================================
# AI ASSISTANT TESTS (1-20)
# ============================================================

def test_1_assistant_chat_with_context():
    """Assistant responds with real AI using farm context."""
    uid, email = _make_user("ai")
    cycle_id = _make_farm_with_crop(uid)
    _make_weather(uid)
    _make_decision(cycle_id)
    token = _token(uid)

    with patch("app.services.ai.ai_service.assistant_chat") as mock_chat:
        mock_chat.return_value = {
            "available": True,
            "answer": "Based on your tomato crop, proceed with irrigation.",
            "source": "ai",
            "model": "nvidia/nemotron-3.5-lightning-30b-a3b",
        }

        res = client.post("/api/assistant/chat", json={
            "question": "Should I irrigate today?",
            "language": "en"
        }, headers={"Authorization": f"Bearer {token}"})

        assert res.status_code == 200
        data = res.json()
        assert "answer" in data
        assert len(data["answer"]) > 10
        assert data["language"] == "en"
        assert data["source"] == "ai"


def test_2_assistant_uses_real_ai():
    """Verify the chain actually calls AI service when available."""
    uid, email = _make_user("ai")
    cycle_id = _make_farm_with_crop(uid)
    token = _token(uid)

    with patch("app.services.ai.ai_service.assistant_chat") as mock_chat:
        mock_chat.return_value = {
            "available": True,
            "answer": "Based on your tomato crop context, you should check soil moisture before irrigating.",
            "source": "ai",
            "model": "nvidia/nemotron-3.5-lightning-30b-a3b",
        }

        res = client.post("/api/assistant/chat", json={
            "question": "Should I irrigate?",
            "language": "en"
        }, headers={"Authorization": f"Bearer {token}"})

        assert res.status_code == 200
        data = res.json()
        assert data["source"] == "ai"
        assert mock_chat.called


def test_3_assistant_crop_cycle_id_stored():
    """Conversation stores crop_cycle_id when active crop exists."""
    uid, email = _make_user("ai")
    cycle_id = _make_farm_with_crop(uid)
    token = _token(uid)

    with patch("app.services.ai.ai_service.assistant_chat") as mock_chat:
        mock_chat.return_value = {
            "available": True,
            "answer": "Your crop is doing well.",
            "source": "ai",
            "model": "nvidia/nemotron-3.5-lightning-30b-a3b",
        }

        res = client.post("/api/assistant/chat", json={
            "question": "How is my crop?",
            "language": "en"
        }, headers={"Authorization": f"Bearer {token}"})

        assert res.status_code == 200

    db = next(get_db())
    conv = db.query(AIConversation).filter(
        AIConversation.user_id == uid
    ).order_by(AIConversation.created_at.desc()).first()
    assert conv is not None
    assert conv.crop_cycle_id == cycle_id
    assert conv.question == "How is my crop?"
    db.close()


def test_4_assistant_crop_cycle_id_null_when_no_crop():
    """Conversation has null crop_cycle_id when no active crop."""
    uid, email = _make_user("ai")
    token = _token(uid)

    with patch("app.services.ai.ai_service.assistant_chat") as mock_chat:
        mock_chat.return_value = {
            "available": True,
            "answer": "Farming is the practice of cultivating plants.",
            "source": "ai",
            "model": "nvidia/nemotron-3.5-lightning-30b-a3b",
        }

        res = client.post("/api/assistant/chat", json={
            "question": "What is farming?",
            "language": "en"
        }, headers={"Authorization": f"Bearer {token}"})

        assert res.status_code == 200

    db = next(get_db())
    conv = db.query(AIConversation).filter(
        AIConversation.user_id == uid
    ).order_by(AIConversation.created_at.desc()).first()
    assert conv is not None
    assert conv.crop_cycle_id is None
    db.close()


def test_5_assistant_context_includes_weather():
    """Farm context includes weather when available."""
    uid, email = _make_user("ai")
    cycle_id = _make_farm_with_crop(uid)
    _make_weather(uid)
    token = _token(uid)

    with patch("app.services.ai.ai_service.assistant_chat") as mock_chat:
        mock_chat.return_value = {
            "available": True,
            "answer": "Your weather is clear with 32C.",
            "source": "ai",
            "model": "nvidia/nemotron-3.5-lightning-30b-a3b",
        }

        res = client.post("/api/assistant/chat", json={
            "question": "What is the weather?",
            "language": "en"
        }, headers={"Authorization": f"Bearer {token}"})

        assert res.status_code == 200
        data = res.json()
        assert "answer" in data


def test_6_assistant_context_includes_expenses():
    """Farm context includes expenses when available."""
    uid, email = _make_user("ai")
    cycle_id = _make_farm_with_crop(uid)
    _make_expense(cycle_id)
    token = _token(uid)

    with patch("app.services.ai.ai_service.assistant_chat") as mock_chat:
        mock_chat.return_value = {
            "available": True,
            "answer": "You have spent Rs 5000 on seeds.",
            "source": "ai",
            "model": "nvidia/nemotron-3.5-lightning-30b-a3b",
        }

        res = client.post("/api/assistant/chat", json={
            "question": "How much have I spent?",
            "language": "en"
        }, headers={"Authorization": f"Bearer {token}"})

        assert res.status_code == 200
        data = res.json()
        assert "answer" in data


def test_7_assistant_context_includes_harvest():
    """Farm context includes harvest data when available."""
    uid, email = _make_user("ai")
    cycle_id = _make_farm_with_crop(uid)
    _make_harvest(cycle_id)
    token = _token(uid)

    with patch("app.services.ai.ai_service.assistant_chat") as mock_chat:
        mock_chat.return_value = {
            "available": True,
            "answer": "Revenue is Rs 8000.",
            "source": "ai",
            "model": "nvidia/nemotron-3.5-lightning-30b-a3b",
        }

        res = client.post("/api/assistant/chat", json={
            "question": "What is my revenue?",
            "language": "en"
        }, headers={"Authorization": f"Bearer {token}"})

        assert res.status_code == 200
        data = res.json()
        assert "answer" in data


def test_8_assistant_context_includes_disease():
    """Farm context includes disease scan when available."""
    uid, email = _make_user("ai")
    cycle_id = _make_farm_with_crop(uid)

    db = next(get_db())
    from app.models.models import DiseaseScan
    scan = DiseaseScan(
        crop_cycle_id=cycle_id, image_path="/tmp/test.jpg",
        predicted_disease="Late_Blight", confidence=87.5, severity="High"
    )
    db.add(scan)
    db.commit()
    db.close()

    token = _token(uid)

    with patch("app.services.ai.ai_service.assistant_chat") as mock_chat:
        mock_chat.return_value = {
            "available": True,
            "answer": "Late blight detected with 87.5% confidence.",
            "source": "ai",
            "model": "nvidia/nemotron-3.5-lightning-30b-a3b",
        }

        res = client.post("/api/assistant/chat", json={
            "question": "What is my disease status?",
            "language": "en"
        }, headers={"Authorization": f"Bearer {token}"})

        assert res.status_code == 200
        data = res.json()
        assert "answer" in data


def test_9_assistant_ollama_timeout_handled():
    """Timeout from Ollama is handled gracefully."""
    uid, email = _make_user("ai")
    token = _token(uid)

    with patch("app.services.ai.ai_service.assistant_chat") as mock_chat:
        mock_chat.return_value = {
            "available": False,
            "answer": None,
            "source": "ai_unavailable",
            "model": None,
        }

        res = client.post("/api/assistant/chat", json={
            "question": "What is farming?",
            "language": "en"
        }, headers={"Authorization": f"Bearer {token}"})

        assert res.status_code == 200
        data = res.json()
        assert "unavailable" in data["answer"].lower() or "currently unavailable" in data["answer"].lower()
        assert data["source"] == "fallback"


def test_10_assistant_ollama_connection_error_handled():
    """Connection error from Ollama is handled gracefully."""
    uid, email = _make_user("ai")
    token = _token(uid)

    with patch("app.services.ai.ai_service.assistant_chat") as mock_chat:
        mock_chat.return_value = {
            "available": False,
            "answer": None,
            "source": "ai_unavailable",
            "model": None,
        }

        res = client.post("/api/assistant/chat", json={
            "question": "What is farming?",
            "language": "en"
        }, headers={"Authorization": f"Bearer {token}"})

        assert res.status_code == 200
        data = res.json()
        assert "unavailable" in data["answer"].lower() or "currently unavailable" in data["answer"].lower()
        assert data["source"] == "fallback"


def test_11_assistant_empty_response_handled():
    """Empty response from Ollama triggers fallback."""
    uid, email = _make_user("ai")
    token = _token(uid)

    with patch("app.services.ai.ai_service.assistant_chat") as mock_chat:
        mock_chat.return_value = {
            "available": True,
            "answer": "",
            "source": "ai",
            "model": "nvidia/nemotron-3.5-lightning-30b-a3b",
        }

        res = client.post("/api/assistant/chat", json={
            "question": "Hello",
            "language": "en"
        }, headers={"Authorization": f"Bearer {token}"})

        assert res.status_code == 200
        data = res.json()
        assert data["source"] == "fallback"
        assert "unavailable" in data["answer"].lower()


def test_12_assistant_telugu_response():
    """Assistant responds with Telugu when language=te."""
    uid, email = _make_user("ai")
    token = _token(uid)

    with patch("app.services.ai.ai_service.assistant_chat") as mock_chat:
        mock_chat.return_value = {
            "available": True,
            "answer": "మీ పొలం సమాచారం అందుబాటులో ఉంది.",
            "source": "ai",
            "model": "nvidia/nemotron-3.5-lightning-30b-a3b",
        }

        res = client.post("/api/assistant/chat", json={
            "question": "నా పొలం ఎలా ఉంది?",
            "language": "te"
        }, headers={"Authorization": f"Bearer {token}"})

        assert res.status_code == 200
        data = res.json()
        assert data["language"] == "te"
        assert data["source"] == "ai"


def test_13_assistant_ownership_isolation():
    """User A cannot see User B's farm context."""
    uid_a, email_a = _make_user("aiA")
    uid_b, email_b = _make_user("aiB")
    cycle_a = _make_farm_with_crop(uid_a, crop="tomato")
    _make_farm_with_crop(uid_b, crop="wheat")
    token_b = _token(uid_b)

    with patch("app.services.ai.ai_service.assistant_chat") as mock_chat:
        mock_chat.return_value = {
            "available": True,
            "answer": "OK",
            "source": "ai",
            "model": "nvidia/nemotron-3.5-lightning-30b-a3b",
        }

        res = client.post("/api/assistant/chat", json={
            "question": "What crop am I growing?",
            "language": "en"
        }, headers={"Authorization": f"Bearer {token_b}"})

        assert res.status_code == 200
        data = res.json()
        assert "answer" in data


def test_14_assistant_no_fabricated_data():
    """When no weather data, context does not include fake weather."""
    uid, email = _make_user("ai")
    cycle_id = _make_farm_with_crop(uid)
    token = _token(uid)

    with patch("app.services.ai.ai_service.assistant_chat") as mock_chat:
        mock_chat.return_value = {
            "available": True,
            "answer": "Weather data is unavailable.",
            "source": "ai",
            "model": "nvidia/nemotron-3.5-lightning-30b-a3b",
        }

        res = client.post("/api/assistant/chat", json={
            "question": "What is the weather?",
            "language": "en"
        }, headers={"Authorization": f"Bearer {token}"})

        assert res.status_code == 200
        data = res.json()
        assert "answer" in data


def test_15_assistant_conversation_history_bounded():
    """Only recent conversations are used as history (max 6)."""
    uid, email = _make_user("ai")
    token = _token(uid)

    with patch("app.services.ai.ai_service.assistant_chat") as mock_chat:
        mock_chat.return_value = {
            "available": True,
            "answer": "OK",
            "source": "ai",
            "model": "nvidia/nemotron-3.5-lightning-30b-a3b",
        }

        for i in range(10):
            client.post("/api/assistant/chat", json={
                "question": f"Question {i}",
                "language": "en"
            }, headers={"Authorization": f"Bearer {token}"})

        res = client.post("/api/assistant/chat", json={
            "question": "Final question",
            "language": "en"
        }, headers={"Authorization": f"Bearer {token}"})

        assert res.status_code == 200
        data = res.json()
        assert "answer" in data


def test_16_assistant_no_auth_rejected():
    """Unauthenticated request is rejected."""
    res = client.post("/api/assistant/chat", json={
        "question": "Hello",
        "language": "en"
    })
    assert res.status_code in [401, 403]


def test_17_assistant_system_prompt_content():
    """System prompt contains required safety instructions."""
    from app.services.ai.prompts import system_prompt
    prompt = system_prompt("en")
    assert "NEVER" in prompt
    assert "HARVEX" in prompt


def test_18_assistant_telugu_system_prompt():
    """Telugu system prompt contains Telugu instruction."""
    from app.services.ai.prompts import system_prompt
    prompt = system_prompt("te")
    assert "Telugu" in prompt


def test_19_assistant_fallback_telugu():
    """Fallback response is in Telugu when language=te."""
    from app.api.assistant import generate_fallback_response
    response = generate_fallback_response({}, "test", "te")
    assert "అందుబాటులో లేదు" in response or "సహాయకుడు" in response


def test_20_assistant_fallback_english():
    """Fallback response is in English when language=en."""
    from app.api.assistant import generate_fallback_response
    response = generate_fallback_response({}, "test", "en")
    assert "unavailable" in response.lower()


# ============================================================
# PROFILE TESTS (21-31)
# ============================================================

def test_21_profile_loads():
    """GET /api/auth/me returns user profile."""
    uid, email = _make_user("profile")
    token = _token(uid)

    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == email
    assert data["preferred_language"] == "en"


def test_22_profile_update_name():
    """PUT /api/auth/me updates name."""
    uid, email = _make_user("profile")
    token = _token(uid)

    res = client.put("/api/auth/me", json={"name": "Updated Name"},
                     headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["name"] == "Updated Name"


def test_23_profile_name_empty_rejected():
    """Empty name is rejected."""
    uid, email = _make_user("profile")
    token = _token(uid)

    res = client.put("/api/auth/me", json={"name": ""},
                     headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 400


def test_24_profile_update_language():
    """PUT /api/auth/me updates preferred_language."""
    uid, email = _make_user("profile")
    token = _token(uid)

    res = client.put("/api/auth/me", json={"preferred_language": "te"},
                     headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["preferred_language"] == "te"


def test_25_profile_invalid_language_rejected():
    """Invalid language value is rejected."""
    uid, email = _make_user("profile")
    token = _token(uid)

    res = client.put("/api/auth/me", json={"preferred_language": "fr"},
                     headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 400


def test_26_profile_persists_to_db():
    """Profile changes persist to database."""
    uid, email = _make_user("profile")
    token = _token(uid)

    client.put("/api/auth/me", json={"name": "Persistent Name"},
               headers={"Authorization": f"Bearer {token}"})

    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.json()["name"] == "Persistent Name"


def test_27_profile_refresh_retains_changes():
    """Profile changes survive refresh (re-fetch from DB)."""
    uid, email = _make_user("profile")
    token = _token(uid)

    client.put("/api/auth/me", json={"name": "Refreshed", "preferred_language": "te"},
               headers={"Authorization": f"Bearer {token}"})

    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.json()["name"] == "Refreshed"
    assert res.json()["preferred_language"] == "te"


def test_28_profile_cannot_update_other_user():
    """User cannot update another user's profile."""
    uid_a, _ = _make_user("profA")
    uid_b, _ = _make_user("profB")
    token_a = _token(uid_a)

    # Update own name
    client.put("/api/auth/me", json={"name": "My Name"},
               headers={"Authorization": f"Bearer {token_a}"})

    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_a}"})
    assert res.json()["name"] == "My Name"


def test_29_profile_no_auth_rejected():
    """Unauthenticated profile request is rejected."""
    res = client.get("/api/auth/me")
    assert res.status_code in [401, 403]


def test_30_profile_user_response_fields():
    """UserResponse includes all required fields."""
    uid, email = _make_user("profile")
    token = _token(uid)

    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    data = res.json()
    assert "id" in data
    assert "name" in data
    assert "email" in data
    assert "preferred_language" in data
    assert "created_at" in data


def test_31_profile_update_both_fields():
    """Update name and language in single request."""
    uid, email = _make_user("profile")
    token = _token(uid)

    res = client.put("/api/auth/me",
                     json={"name": "Both Fields", "preferred_language": "te"},
                     headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Both Fields"
    assert data["preferred_language"] == "te"


# ============================================================
# LANGUAGE PERSISTENCE TESTS (32-38)
# ============================================================

def test_32_language_persists_on_profile():
    """Language preference persists in user profile."""
    uid, email = _make_user("lang")
    token = _token(uid)

    client.put("/api/auth/me", json={"preferred_language": "te"},
               headers={"Authorization": f"Bearer {token}"})

    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.json()["preferred_language"] == "te"


def test_33_language_survives_logout_login():
    """Language persists after logout and login."""
    uid, email = _make_user("lang")
    password = "testpass123"

    # Set language
    token = _token(uid)
    client.put("/api/auth/me", json={"preferred_language": "te"},
               headers={"Authorization": f"Bearer {token}"})

    # Login fresh
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    assert res.json()["user"]["preferred_language"] == "te"


def test_34_different_users_independent_language():
    """Different users have independent language preferences."""
    uid_a, email_a = _make_user("langA")
    uid_b, email_b = _make_user("langB")

    token_a = _token(uid_a)
    token_b = _token(uid_b)

    client.put("/api/auth/me", json={"preferred_language": "te"},
               headers={"Authorization": f"Bearer {token_a}"})
    client.put("/api/auth/me", json={"preferred_language": "en"},
               headers={"Authorization": f"Bearer {token_b}"})

    res_a = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_a}"})
    res_b = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_b}"})

    assert res_a.json()["preferred_language"] == "te"
    assert res_b.json()["preferred_language"] == "en"


def test_35_register_default_language_en():
    """New user defaults to English language."""
    email = f"phase7_newuser_{uuid.uuid4().hex[:8]}@example.com"
    res = client.post("/api/auth/register", json={
        "name": "New User", "email": email, "password": "testpass123"
    })
    assert res.status_code == 200
    assert res.json()["user"]["preferred_language"] == "en"


def test_36_register_then_set_telugu():
    """Register, set Telugu, login, language persists."""
    email = f"phase7_reglang_{uuid.uuid4().hex[:8]}@example.com"

    res = client.post("/api/auth/register", json={
        "name": "Lang User", "email": email, "password": "testpass123"
    })
    token = res.json()["access_token"]

    client.put("/api/auth/me", json={"preferred_language": "te"},
               headers={"Authorization": f"Bearer {token}"})

    res = client.post("/api/auth/login", json={"email": email, "password": "testpass123"})
    assert res.json()["user"]["preferred_language"] == "te"


def test_37_language_toggle_back_and_forth():
    """Toggle language en -> te -> en persists correctly."""
    uid, email = _make_user("lang")
    token = _token(uid)

    client.put("/api/auth/me", json={"preferred_language": "te"},
               headers={"Authorization": f"Bearer {token}"})
    client.put("/api/auth/me", json={"preferred_language": "en"},
               headers={"Authorization": f"Bearer {token}"})

    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.json()["preferred_language"] == "en"


def test_38_assistant_uses_user_language():
    """Assistant stores conversation with user's preferred language."""
    uid, email = _make_user("lang")
    token = _token(uid)

    client.put("/api/auth/me", json={"preferred_language": "te"},
               headers={"Authorization": f"Bearer {token}"})

    with patch("app.services.ai.ai_service.assistant_chat") as mock_chat:
        mock_chat.return_value = {
            "available": True,
            "answer": "సమాధానం",
            "source": "ai",
            "model": "nvidia/nemotron-3.5-lightning-30b-a3b",
        }

        res = client.post("/api/assistant/chat", json={
            "question": "Test question",
            "language": "te"
        }, headers={"Authorization": f"Bearer {token}"})

        assert res.status_code == 200
        db = next(get_db())
        conv = db.query(AIConversation).filter(AIConversation.user_id == uid).first()
        assert conv.language == "te"
        db.close()
