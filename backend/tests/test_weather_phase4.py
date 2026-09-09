"""PHASE 4: Weather Intelligence Tests — 19 tests."""

import pytest
import sys
import os
import json
import time
import requests
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient
from app.core.database import get_db, Base, engine
from app.models.models import User, Farm, WeatherRecord
from app.core.security import create_access_token

# Import the FastAPI app from main.py
import importlib
main_mod = importlib.import_module("main")
app = main_mod.app

client = TestClient(app)


def setup():
    Base.metadata.create_all(bind=engine)
    # Clean weather records between test runs
    db = next(get_db())
    db.query(WeatherRecord).delete()
    db.commit()
    db.close()


setup()


def create_test_user_and_farm():
    db = next(get_db())
    # Clean any weather records to avoid test pollution
    db.query(WeatherRecord).delete()
    db.commit()

    user = db.query(User).filter(User.email == "weather_test@example.com").first()
    if not user:
        user = User(name="Weather Test", email="weather_test@example.com", password_hash="hashed")
        db.add(user)
        db.commit()
        db.refresh(user)

    farm = db.query(Farm).filter(Farm.user_id == user.id).first()
    if not farm:
        farm = Farm(
            name="Test Farm", user_id=user.id,
            latitude=16.9, longitude=82.0,
            location_name="Kakinada, Andhra Pradesh, IN"
        )
        db.add(farm)
        db.commit()
        db.refresh(farm)

    db.close()
    token = create_access_token(data={"sub": str(user.id)})
    return token, user, farm


def create_second_user_and_farm():
    db = next(get_db())
    user = db.query(User).filter(User.email == "weather_test2@example.com").first()
    if not user:
        user = User(name="Weather Test 2", email="weather_test2@example.com", password_hash="hashed")
        db.add(user)
        db.commit()
        db.refresh(user)

    farm = db.query(Farm).filter(Farm.user_id == user.id).first()
    if not farm:
        farm = Farm(
            name="Delhi Farm", user_id=user.id,
            latitude=28.6, longitude=77.2,
            location_name="Delhi, IN"
        )
        db.add(farm)
        db.commit()
        db.refresh(farm)

    db.close()
    token = create_access_token(data={"sub": str(user.id)})
    return token, user, farm


MOCK_OPENWEATHER = {
    "main": {"temp": 32.5, "feels_like": 35.0, "humidity": 65},
    "rain": {"1h": 2.5},
    "wind": {"speed": 4.2},
    "weather": [{"main": "Clouds", "description": "scattered clouds"}],
    "dt": int(time.time()),
}

MOCK_GEOCODE = [{"lat": 16.9, "lon": 82.0, "locality": "Kakinada", "state": "Andhra Pradesh", "country": "IN"}]

MOCK_FORECAST = {
    "list": [
        {
            "dt_txt": "2026-09-09 12:00:00",
            "main": {"temp": 30.0, "humidity": 70},
            "pop": 0.3,
            "rain": {"3h": 1.5},
            "wind": {"speed": 3.0},
            "weather": [{"main": "Rain", "description": "light rain"}],
        },
        {
            "dt_txt": "2026-09-09 15:00:00",
            "main": {"temp": 31.0, "humidity": 65},
            "pop": 0.1,
            "rain": {},
            "wind": {"speed": 2.5},
            "weather": [{"main": "Clouds", "description": "overcast clouds"}],
        },
    ]
}


# --- 1. API key never in frontend bundle ---
def test_1_api_key_not_in_frontend_source():
    """VITE_OPENWEATHER_API_KEY must never appear in frontend source files."""
    frontend_src = "/home/megha/harvex/frontend/src"
    found = []
    for root, dirs, files in os.walk(frontend_src):
        for f in files:
            if f.endswith(('.tsx', '.ts', '.js', '.jsx')):
                path = os.path.join(root, f)
                with open(path, 'r') as fh:
                    content = fh.read()
                    if 'VITE_OPENWEATHER' in content:
                        found.append(path)
    assert len(found) == 0, f"API key reference found in: {found}"


# --- 2. Frontend never directly calls OpenWeather ---
def test_2_frontend_no_direct_openweather_calls():
    """No direct fetch/axios calls to api.openweathermap.org in frontend source."""
    frontend_src = "/home/megha/harvex/frontend/src"
    found = []
    for root, dirs, files in os.walk(frontend_src):
        for f in files:
            if f.endswith(('.tsx', '.ts', '.js', '.jsx')):
                path = os.path.join(root, f)
                with open(path, 'r') as fh:
                    content = fh.read()
                    if 'api.openweathermap.org' in content:
                        found.append(path)
    assert len(found) == 0, f"Direct OpenWeather calls found in: {found}"


# --- 3. Backend fetches weather correctly ---
@patch("app.api.weather.requests.get")
def test_3_backend_fetches_weather_correctly(mock_get):
    token, user, farm = create_test_user_and_farm()

    mock_resp = MagicMock()
    mock_resp.json.return_value = MOCK_OPENWEATHER
    mock_resp.raise_for_status = MagicMock()
    mock_resp.status_code = 200
    mock_get.return_value = mock_resp

    with patch("app.api.weather.OPENWEATHER_API_KEY", "test_key"):
        with patch("app.api.weather._build_location_response") as mock_geo:
            mock_geo.return_value = {"name": "Kakinada, IN", "lat": 16.9, "lon": 82.0}
            resp = client.get(
                f"/api/weather/current?lat={farm.latitude}&lon={farm.longitude}",
                headers={"Authorization": f"Bearer {token}"},
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["current"]["temperature"] == 32.5
    assert data["current"]["humidity"] == 65
    assert data["current"]["rainfall"] == 2.5
    assert data["current"]["wind_speed"] == 4.2
    assert data["current"]["condition"] == "Clouds"
    assert data["source"] == "OpenWeather"
    assert data["cached"] is False


# --- 4. Correct farm coordinates are used ---
@patch("app.api.weather.requests.get")
def test_4_farm_coordinates_are_used(mock_get):
    token, user, farm = create_test_user_and_farm()

    mock_resp = MagicMock()
    mock_resp.json.return_value = MOCK_OPENWEATHER
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    with patch("app.api.weather.OPENWEATHER_API_KEY", "test_key"):
        with patch("app.api.weather._build_location_response") as mock_geo:
            mock_geo.return_value = {"name": "Kakinada, IN", "lat": 16.9, "lon": 82.0}
            # Pass different lat/lon than farm — farm coords should be used
            resp = client.get(
                "/api/weather/current?lat=99.9&lon=99.9",
                headers={"Authorization": f"Bearer {token}"},
            )

    assert resp.status_code == 200
    # The API call should use farm coordinates, not 99.9/99.9
    call_args = mock_get.call_args
    params = call_args[1]["params"] if "params" in call_args[1] else call_args[0][1]
    assert params["lat"] == farm.latitude
    assert params["lon"] == farm.longitude


# --- 5. Weather cache is location-specific ---
@patch("app.api.weather.requests.get")
def test_5_cache_is_location_specific(mock_get):
    token, user, farm = create_test_user_and_farm()
    db = next(get_db())

    # Clean up any existing records for this farm
    db.query(WeatherRecord).filter(WeatherRecord.farm_id == farm.id).delete()
    db.commit()

    # Create weather record for farm location
    record = WeatherRecord(
        farm_id=farm.id, latitude=farm.latitude, longitude=farm.longitude,
        temperature=28.0, humidity=55.0, rainfall=0.0, wind_speed=2.0,
        weather_condition="Clear", source="OpenWeather", observed_at=datetime.utcnow(),
    )
    db.add(record)
    db.commit()
    db.close()

    # Mock reverse geocoding too
    mock_geo_resp = MagicMock()
    mock_geo_resp.ok = True
    mock_geo_resp.json.return_value = [{"locality": "Kakinada", "state": "AP", "country": "IN"}]
    mock_get.return_value = mock_geo_resp

    # Request with same location — should hit cache
    resp = client.get(
        f"/api/weather/current?lat={farm.latitude}&lon={farm.longitude}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["cached"] is True
    assert data["current"]["temperature"] == 28.0


# --- 6. Farm A cannot receive Farm B weather ---
@patch("app.api.weather.requests.get")
def test_6_farm_isolation(mock_get):
    token_a, user_a, farm_a = create_test_user_and_farm()
    token_b, user_b, farm_b = create_second_user_and_farm()
    db = next(get_db())

    # Create weather for farm A
    record_a = WeatherRecord(
        farm_id=farm_a.id, latitude=farm_a.latitude, longitude=farm_a.longitude,
        temperature=35.0, humidity=80.0, rainfall=10.0, wind_speed=1.0,
        weather_condition="Rain", source="OpenWeather", observed_at=datetime.utcnow(),
    )
    db.add(record_a)

    # Create weather for farm B
    record_b = WeatherRecord(
        farm_id=farm_b.id, latitude=farm_b.latitude, longitude=farm_b.longitude,
        temperature=15.0, humidity=30.0, rainfall=0.0, wind_speed=5.0,
        weather_condition="Clear", source="OpenWeather", observed_at=datetime.utcnow(),
    )
    db.add(record_b)
    db.commit()
    db.close()

    # User A gets their farm's weather
    resp_a = client.get(
        f"/api/weather/current?lat={farm_a.latitude}&lon={farm_a.longitude}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_a.json()["current"]["temperature"] == 35.0

    # User B gets their farm's weather, NOT farm A's
    resp_b = client.get(
        f"/api/weather/current?lat={farm_b.latitude}&lon={farm_b.longitude}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp_b.json()["current"]["temperature"] == 15.0


# --- 7. Current weather fields are correctly mapped ---
@patch("app.api.weather.requests.get")
def test_7_current_weather_fields_mapped(mock_get):
    token, user, farm = create_test_user_and_farm()

    mock_resp = MagicMock()
    mock_resp.json.return_value = MOCK_OPENWEATHER
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    with patch("app.api.weather.OPENWEATHER_API_KEY", "test_key"):
        with patch("app.api.weather._build_location_response") as mock_geo:
            mock_geo.return_value = {"name": "Kakinada, IN", "lat": 16.9, "lon": 82.0}
            resp = client.get(
                f"/api/weather/current?lat={farm.latitude}&lon={farm.longitude}",
                headers={"Authorization": f"Bearer {token}"},
            )

    data = resp.json()
    current = data["current"]
    assert "temperature" in current
    assert "feels_like" in current
    assert "humidity" in current
    assert "rainfall" in current
    assert "wind_speed" in current
    assert "condition" in current
    assert "description" in current
    assert "observed_at" in current
    assert current["feels_like"] == 35.0


# --- 8. Forecast fields are correctly mapped ---
@patch("app.api.weather.requests.get")
def test_8_forecast_fields_mapped(mock_get):
    token, user, farm = create_test_user_and_farm()

    mock_resp = MagicMock()
    mock_resp.json.return_value = MOCK_FORECAST
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    with patch("app.api.weather.OPENWEATHER_API_KEY", "test_key"):
        resp = client.get(
            f"/api/weather/forecast?lat={farm.latitude}&lon={farm.longitude}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    data = resp.json()
    forecast = data["forecast"]
    assert len(forecast) == 2
    entry = forecast[0]
    assert entry["temperature"] == 30.0
    assert entry["humidity"] == 70
    assert entry["rain_probability"] == 30.0
    assert entry["rainfall"] == 1.5
    assert entry["wind_speed"] == 3.0
    assert entry["condition"] == "Rain"


# --- 9. Missing forecast is handled honestly ---
@patch("app.api.weather.requests.get")
def test_9_missing_forecast_handled_honestly(mock_get):
    token, user, farm = create_test_user_and_farm()

    # API returns empty list
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"list": []}
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    with patch("app.api.weather.OPENWEATHER_API_KEY", "test_key"):
        resp = client.get(
            f"/api/weather/forecast?lat={farm.latitude}&lon={farm.longitude}",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["forecast"] == []


# --- 10. Provider failure with no cache returns unavailable ---
def test_10_provider_failure_no_cache_returns_unavailable():
    token, user, farm = create_test_user_and_farm()

    # Clean any cached records
    db = next(get_db())
    db.query(WeatherRecord).filter(WeatherRecord.farm_id == farm.id).delete()
    db.commit()
    db.close()

    with patch("app.api.weather.requests.get") as mock_get:
        mock_get.side_effect = requests.ConnectionError("Connection refused")
        with patch("app.api.weather.OPENWEATHER_API_KEY", "test_key"):
            resp = client.get(
                f"/api/weather/current?lat={farm.latitude}&lon={farm.longitude}",
                headers={"Authorization": f"Bearer {token}"},
            )

    assert resp.status_code == 503


# --- 11. Agricultural signals are deterministic ---
@patch("app.api.weather.requests.get")
def test_11_agricultural_signals_deterministic(mock_get):
    from app.api.weather import _compute_agricultural_signals

    signals1 = _compute_agricultural_signals(38.0, 90.0, 5.0, 2.0)
    signals2 = _compute_agricultural_signals(38.0, 90.0, 5.0, 2.0)

    assert signals1 == signals2
    assert signals1["fungal_risk"]["level"] == "High"
    assert signals1["heat_stress"]["level"] == "High"
    assert signals1["irrigation_need"]["level"] == "High"

    # Different inputs → different outputs
    signals3 = _compute_agricultural_signals(20.0, 30.0, 60.0, 5.0)
    assert signals3["fungal_risk"]["level"] == "Low"
    assert signals3["heat_stress"]["level"] == "Low"
    assert signals3["irrigation_need"]["level"] == "Low"


# --- 12. Agricultural signals have reason strings ---
def test_12_signals_have_reasons():
    from app.api.weather import _compute_agricultural_signals

    signals = _compute_agricultural_signals(38.0, 90.0, 5.0, 2.0)
    for key, val in signals.items():
        assert "level" in val, f"{key} missing level"
        assert "reason" in val, f"{key} missing reason"
        assert len(val["reason"]) > 10, f"{key} reason too short"


# --- 13. No hardcoded weather values in backend ---
def test_13_no_hardcoded_weather_values():
    """Backend weather endpoint must not contain hardcoded temperature/rainfall."""
    with open("/home/megha/harvex/backend/app/api/weather.py", 'r') as f:
        content = f.read()

    # Check no hardcoded weather values (except thresholds)
    import re
    hardcoded_temp = re.findall(r'(?:temperature|temp)\s*=\s*\d+\.?\d*\s*[^_]', content)
    # Filter out threshold references
    hardcoded_temp = [h for h in hardcoded_temp if "threshold" not in h.lower() and "temp>" not in h.lower()]
    assert len(hardcoded_temp) == 0, f"Hardcoded temperature found: {hardcoded_temp}"


# --- 14. No hardcoded weather values in frontend ---
def test_14_no_hardcoded_weather_in_frontend():
    """Frontend Weather page must not contain hardcoded temperature/rainfall."""
    with open("/home/megha/harvex/frontend/src/pages/Weather.tsx", 'r') as f:
        content = f.read()

    import re
    hardcoded = re.findall(r'(?:temperature|temp|rainfall|humidity)\s*[=:]\s*\d+\.?\d+', content, re.IGNORECASE)
    assert len(hardcoded) == 0, f"Hardcoded weather values found: {hardcoded}"


# --- 15. WeatherResponse schema has all required fields ---
def test_15_weather_response_schema_fields():
    from app.schemas.schemas import WeatherResponse
    fields = WeatherResponse.model_fields.keys()
    assert "location" in fields
    assert "latitude" in fields
    assert "longitude" in fields
    assert "current" in fields
    assert "forecast" in fields
    assert "agricultural_signals" in fields
    assert "source" in fields
    assert "cached" in fields
    assert "cache_age_minutes" in fields
    assert "fetched_at" in fields


# --- 16. Geocoding goes through backend ---
@patch("app.api.weather.requests.get")
def test_16_geocoding_through_backend(mock_get):
    token, user, farm = create_test_user_and_farm()

    mock_resp = MagicMock()
    mock_resp.json.return_value = MOCK_GEOCODE
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp

    with patch("app.api.weather.OPENWEATHER_API_KEY", "test_key"):
        resp = client.post(
            "/api/weather/geocode",
            json={"city": "Kakinada"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["results"]) == 1
    assert data["results"][0]["lat"] == 16.9


# --- 17. Set farm location endpoint works ---
def test_17_set_farm_location():
    token, user, farm = create_test_user_and_farm()

    resp = client.post(
        "/api/weather/set-farm-location?lat=17.5&lon=83.0",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["lat"] == 17.5
    assert data["lon"] == 83.0

    # Reset
    db = next(get_db())
    farm_obj = db.query(Farm).filter(Farm.id == farm.id).first()
    farm_obj.latitude = 16.9
    farm_obj.longitude = 82.0
    db.commit()
    db.close()


# --- 18. Weather cache uses location tolerance ---
def test_18_cache_location_tolerance():
    """Nearby coordinates (within 0.005 tolerance) should share cache."""
    db = next(get_db())
    user = db.query(User).filter(User.email == "weather_test@example.com").first()
    farm = db.query(Farm).filter(Farm.user_id == user.id).first()

    # Clean up any stale records for this farm
    db.query(WeatherRecord).filter(WeatherRecord.farm_id == farm.id).delete()
    db.commit()

    # Create record at exact farm coords
    record = WeatherRecord(
        farm_id=farm.id, latitude=16.9, longitude=82.0,
        temperature=25.0, humidity=50.0, rainfall=0.0, wind_speed=1.0,
        weather_condition="Clear", source="OpenWeather", observed_at=datetime.utcnow(),
    )
    db.add(record)
    db.commit()

    # Query with slightly different coords (within tolerance) — should hit cache
    from app.api.weather import _get_cache_key
    filters = _get_cache_key(farm.id, 16.902, 82.002)
    cached = db.query(WeatherRecord).filter(*filters).first()
    assert cached is not None
    assert cached.temperature == 25.0

    # Query with very different coords — should miss cache
    filters_far = _get_cache_key(farm.id, 20.0, 80.0)
    cached_far = db.query(WeatherRecord).filter(*filters_far).first()
    assert cached_far is None

    db.close()


# --- 19. Dashboard and Weather page use same weather API ---
def test_19_same_weather_api_for_dashboard_and_weather():
    """Both Dashboard and Weather use weatherAPI.getCurrent from api.ts."""
    with open("/home/megha/harvex/frontend/src/pages/Dashboard.tsx", 'r') as f:
        dashboard = f.read()
    with open("/home/megha/harvex/frontend/src/pages/Weather.tsx", 'r') as f:
        weather = f.read()

    assert "weatherAPI.getCurrent" in dashboard, "Dashboard does not use weatherAPI.getCurrent"
    assert "weatherAPI.getCurrent" in weather, "Weather page does not use weatherAPI.getCurrent"
