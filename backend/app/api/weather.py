from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
import requests
from datetime import datetime, timedelta
from typing import Optional
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import User, WeatherRecord, Farm
from app.schemas.schemas import WeatherResponse
from app.core.config import OPENWEATHER_API_KEY

router = APIRouter(prefix="/api/weather", tags=["weather"])

OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"
OPENWEATHER_GEO_URL = "https://api.openweathermap.org/geo/1.0"

# --- Agricultural signal thresholds (documented, central) ---
THRESHOLDS = {
    "fungal_risk": {
        "high_humidity": 80,
        "medium_humidity": 60,
    },
    "irrigation_need": {
        "high_rain": 10,
        "medium_rain": 25,
    },
    "heat_stress": {
        "high_temp": 35,
        "medium_temp": 30,
    },
    "rain_risk": {
        "high_rain": 50,
        "medium_rain": 20,
    },
}

CACHE_MINUTES = 30
FORECAST_CACHE_MINUTES = 60


def _compute_agricultural_signals(
    temp: float, humidity: float, rainfall: float, wind_speed: float,
    irrigation: float = 0,
) -> dict:
    """Deterministic agricultural signals with explainable reasons.

    rainfall = natural precipitation (mm)
    irrigation = farmer-supplied water (mm), separate from rainfall

    Rain risk uses rainfall only (natural weather).
    Irrigation need uses rainfall + irrigation (total water input).
    """
    t = THRESHOLDS
    signals = {}
    total_water = rainfall + irrigation

    # Fungal risk
    if humidity > t["fungal_risk"]["high_humidity"]:
        signals["fungal_risk"] = {
            "level": "High",
            "reason": f"Humidity {humidity:.0f}% exceeds {t['fungal_risk']['high_humidity']}% threshold. Fungal diseases thrive in high humidity.",
        }
    elif humidity > t["fungal_risk"]["medium_humidity"]:
        signals["fungal_risk"] = {
            "level": "Medium",
            "reason": f"Humidity {humidity:.0f}% is moderate ({t['fungal_risk']['medium_humidity']}–{t['fungal_risk']['high_humidity']}%). Monitor for fungal symptoms.",
        }
    else:
        signals["fungal_risk"] = {
            "level": "Low",
            "reason": f"Humidity {humidity:.0f}% is below {t['fungal_risk']['medium_humidity']}%. Low fungal disease risk.",
        }

    # Irrigation need — based on total water (rainfall + irrigation)
    if total_water < t["irrigation_need"]["high_rain"]:
        signals["irrigation_need"] = {
            "level": "High",
            "reason": f"Total water {total_water:.1f}mm (rainfall {rainfall:.1f}mm + irrigation {irrigation:.1f}mm) is below {t['irrigation_need']['high_rain']}mm. Irrigation strongly recommended.",
        }
    elif total_water < t["irrigation_need"]["medium_rain"]:
        signals["irrigation_need"] = {
            "level": "Medium",
            "reason": f"Total water {total_water:.1f}mm (rainfall {rainfall:.1f}mm + irrigation {irrigation:.1f}mm) is moderate ({t['irrigation_need']['high_rain']}–{t['irrigation_need']['medium_rain']}mm). Monitor soil moisture.",
        }
    else:
        signals["irrigation_need"] = {
            "level": "Low",
            "reason": f"Total water {total_water:.1f}mm (rainfall {rainfall:.1f}mm + irrigation {irrigation:.1f}mm) exceeds {t['irrigation_need']['medium_rain']}mm. Sufficient moisture.",
        }

    # Heat stress
    if temp > t["heat_stress"]["high_temp"]:
        signals["heat_stress"] = {
            "level": "High",
            "reason": f"Temperature {temp:.1f}°C exceeds {t['heat_stress']['high_temp']}°C. Risk of heat stress for most crops.",
        }
    elif temp > t["heat_stress"]["medium_temp"]:
        signals["heat_stress"] = {
            "level": "Medium",
            "reason": f"Temperature {temp:.1f}°C is elevated ({t['heat_stress']['medium_temp']}–{t['heat_stress']['high_temp']}°C). Some crops may be affected.",
        }
    else:
        signals["heat_stress"] = {
            "level": "Low",
            "reason": f"Temperature {temp:.1f}°C is within safe range (below {t['heat_stress']['medium_temp']}°C).",
        }

    # Rain risk
    if rainfall > t["rain_risk"]["high_rain"]:
        signals["rain_risk"] = {
            "level": "High",
            "reason": f"Rainfall {rainfall:.1f}mm exceeds {t['rain_risk']['high_rain']}mm. Heavy rain expected; avoid field operations.",
        }
    elif rainfall > t["rain_risk"]["medium_rain"]:
        signals["rain_risk"] = {
            "level": "Medium",
            "reason": f"Rainfall {rainfall:.1f}mm is moderate ({t['rain_risk']['medium_rain']}–{t['rain_risk']['high_rain']}mm). Plan field work accordingly.",
        }
    else:
        signals["rain_risk"] = {
            "level": "Low",
            "reason": f"Rainfall {rainfall:.1f}mm is below {t['rain_risk']['medium_rain']}mm. Low rain risk.",
        }

    return signals


def _get_cache_key(farm_id: int, lat: float, lon: float) -> dict:
    """Cache key includes farm_id AND rounded coordinates (±0.01 tolerance)."""
    return {
        WeatherRecord.farm_id == farm_id,
        WeatherRecord.latitude >= round(lat, 2) - 0.005,
        WeatherRecord.latitude <= round(lat, 2) + 0.005,
        WeatherRecord.longitude >= round(lon, 2) - 0.005,
        WeatherRecord.longitude <= round(lon, 2) + 0.005,
    }


def _check_api_key():
    if not OPENWEATHER_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Weather API key not configured. Please set OPENWEATHER_API_KEY.",
        )


def _build_location_response(db: Session, farm: Farm, lat: float, lon: float) -> dict:
    """Reverse geocode to get location name for display."""
    try:
        resp = requests.get(
            f"{OPENWEATHER_GEO_URL}/reverse",
            params={"lat": lat, "lon": lon, "limit": 1, "appid": OPENWEATHER_API_KEY},
            timeout=5,
        )
        if resp.ok:
            data = resp.json()
            if data and len(data) > 0:
                item = data[0]
                parts = [item.get("locality", ""), item.get("state", ""), item.get("country", "")]
                name = ", ".join(p for p in parts if p)
                return {"name": name or f"{lat:.4f}, {lon:.4f}", "lat": lat, "lon": lon}
    except Exception:
        pass
    return {"name": f"{lat:.4f}, {lon:.4f}", "lat": lat, "lon": lon}


def _fetch_current_weather_from_api(lat: float, lon: float) -> dict:
    """Fetch current weather from OpenWeather API."""
    response = requests.get(
        f"{OPENWEATHER_BASE_URL}/weather",
        params={"lat": lat, "lon": lon, "appid": OPENWEATHER_API_KEY, "units": "metric"},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()

    temp = data["main"]["temp"]
    feels_like = data["main"].get("feels_like", temp)
    humidity = data["main"]["humidity"]
    rainfall = data.get("rain", {}).get("1h", 0.0)
    wind_speed = data["wind"]["speed"]
    condition = data["weather"][0]["main"]
    description = data["weather"][0].get("description", condition.lower())
    observed_at = datetime.fromtimestamp(data["dt"])

    return {
        "temperature": temp,
        "feels_like": feels_like,
        "humidity": humidity,
        "rainfall": rainfall,
        "wind_speed": wind_speed,
        "condition": condition,
        "description": description,
        "observed_at": observed_at,
    }


def _fetch_forecast_from_api(lat: float, lon: float) -> list:
    """Fetch 5-day / 3-hour forecast from OpenWeather API. Returns list of forecast entries."""
    response = requests.get(
        f"{OPENWEATHER_BASE_URL}/forecast",
        params={"lat": lat, "lon": lon, "appid": OPENWEATHER_API_KEY, "units": "metric"},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()

    entries = []
    for item in data.get("list", []):
        entries.append({
            "time": item["dt_txt"],
            "temperature": item["main"]["temp"],
            "humidity": item["main"]["humidity"],
            "rain_probability": item.get("pop", 0) * 100,
            "rainfall": item.get("rain", {}).get("3h", 0.0),
            "wind_speed": item["wind"]["speed"],
            "condition": item["weather"][0]["main"],
            "description": item["weather"][0].get("description", ""),
        })
    return entries


# --- ENDPOINTS ---


@router.get("/current", response_model=WeatherResponse)
def get_current_weather(
    lat: float = Query(..., description="Farm latitude"),
    lon: float = Query(..., description="Farm longitude"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get current weather for the given farm coordinates."""
    _check_api_key()

    # Find farm with matching coordinates
    farm = db.query(Farm).filter(
        Farm.user_id == current_user.id,
        Farm.latitude.isnot(None),
        Farm.longitude.isnot(None),
    ).first()

    # Use farm coordinates if available, else use the provided lat/lon
    use_lat = farm.latitude if farm else lat
    use_lon = farm.longitude if farm else lon

    # Check cache with location tolerance
    cached = None
    if farm:
        cache_filters = _get_cache_key(farm.id, use_lat, use_lon)
        cached = db.query(WeatherRecord).filter(*cache_filters).order_by(
            WeatherRecord.created_at.desc()
        ).first()

    if cached and cached.created_at:
        age = datetime.utcnow() - cached.created_at
        if age < timedelta(minutes=CACHE_MINUTES):
            signals = _compute_agricultural_signals(
                cached.temperature or 0, cached.humidity or 0,
                cached.rainfall or 0, cached.wind_speed or 0,
            )
            location = _build_location_response(db, farm, use_lat, use_lon) if farm else {"name": f"{use_lat:.4f}, {use_lon:.4f}", "lat": use_lat, "lon": use_lon}
            return WeatherResponse(
                location=location,
                latitude=use_lat,
                longitude=use_lon,
                current={
                    "temperature": cached.temperature,
                    "feels_like": cached.temperature,
                    "humidity": cached.humidity,
                    "rainfall": cached.rainfall,
                    "wind_speed": cached.wind_speed,
                    "condition": cached.weather_condition,
                    "description": cached.weather_condition,
                    "observed_at": (cached.observed_at or cached.created_at).isoformat(),
                },
                forecast=[],
                agricultural_signals=signals,
                source="Cached",
                cached=True,
                cache_age_minutes=int(age.total_seconds() / 60),
                fetched_at=datetime.utcnow().isoformat(),
            )

    # Fetch from OpenWeather
    try:
        weather_data = _fetch_current_weather_from_api(use_lat, use_lon)
    except requests.Timeout:
        # Try cache even if expired
        if cached:
            signals = _compute_agricultural_signals(
                cached.temperature or 0, cached.humidity or 0,
                cached.rainfall or 0, cached.wind_speed or 0,
            )
            location = _build_location_response(db, farm, use_lat, use_lon) if farm else {"name": f"{use_lat:.4f}, {use_lon:.4f}", "lat": use_lat, "lon": use_lon}
            return WeatherResponse(
                location=location,
                latitude=use_lat,
                longitude=use_lon,
                current={
                    "temperature": cached.temperature,
                    "feels_like": cached.temperature,
                    "humidity": cached.humidity,
                    "rainfall": cached.rainfall,
                    "wind_speed": cached.wind_speed,
                    "condition": cached.weather_condition,
                    "description": cached.weather_condition,
                    "observed_at": (cached.observed_at or cached.created_at).isoformat(),
                },
                forecast=[],
                agricultural_signals=signals,
                source="Cached (API timeout)",
                cached=True,
                cache_age_minutes=int((datetime.utcnow() - cached.created_at).total_seconds() / 60),
                fetched_at=datetime.utcnow().isoformat(),
            )
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Weather service timed out. Please try again.")
    except requests.ConnectionError:
        if cached:
            signals = _compute_agricultural_signals(
                cached.temperature or 0, cached.humidity or 0,
                cached.rainfall or 0, cached.wind_speed or 0,
            )
            location = _build_location_response(db, farm, use_lat, use_lon) if farm else {"name": f"{use_lat:.4f}, {use_lon:.4f}", "lat": use_lat, "lon": use_lon}
            return WeatherResponse(
                location=location,
                latitude=use_lat,
                longitude=use_lon,
                current={
                    "temperature": cached.temperature,
                    "feels_like": cached.temperature,
                    "humidity": cached.humidity,
                    "rainfall": cached.rainfall,
                    "wind_speed": cached.wind_speed,
                    "condition": cached.weather_condition,
                    "description": cached.weather_condition,
                    "observed_at": (cached.observed_at or cached.created_at).isoformat(),
                },
                forecast=[],
                agricultural_signals=signals,
                source="Cached (connection failed)",
                cached=True,
                cache_age_minutes=int((datetime.utcnow() - cached.created_at).total_seconds() / 60),
                fetched_at=datetime.utcnow().isoformat(),
            )
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Cannot connect to weather service. Check internet connection.")
    except requests.HTTPError as e:
        if cached:
            signals = _compute_agricultural_signals(
                cached.temperature or 0, cached.humidity or 0,
                cached.rainfall or 0, cached.wind_speed or 0,
            )
            location = _build_location_response(db, farm, use_lat, use_lon) if farm else {"name": f"{use_lat:.4f}, {use_lon:.4f}", "lat": use_lat, "lon": use_lon}
            return WeatherResponse(
                location=location,
                latitude=use_lat,
                longitude=use_lon,
                current={
                    "temperature": cached.temperature,
                    "feels_like": cached.temperature,
                    "humidity": cached.humidity,
                    "rainfall": cached.rainfall,
                    "wind_speed": cached.wind_speed,
                    "condition": cached.weather_condition,
                    "description": cached.weather_condition,
                    "observed_at": (cached.observed_at or cached.created_at).isoformat(),
                },
                forecast=[],
                agricultural_signals=signals,
                source="Cached (API error)",
                cached=True,
                cache_age_minutes=int((datetime.utcnow() - cached.created_at).total_seconds() / 60),
                fetched_at=datetime.utcnow().isoformat(),
            )
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Weather service error: {e.response.status_code}")
    except Exception:
        if cached:
            signals = _compute_agricultural_signals(
                cached.temperature or 0, cached.humidity or 0,
                cached.rainfall or 0, cached.wind_speed or 0,
            )
            location = _build_location_response(db, farm, use_lat, use_lon) if farm else {"name": f"{use_lat:.4f}, {use_lon:.4f}", "lat": use_lat, "lon": use_lon}
            return WeatherResponse(
                location=location,
                latitude=use_lat,
                longitude=use_lon,
                current={
                    "temperature": cached.temperature,
                    "feels_like": cached.temperature,
                    "humidity": cached.humidity,
                    "rainfall": cached.rainfall,
                    "wind_speed": cached.wind_speed,
                    "condition": cached.weather_condition,
                    "description": cached.weather_condition,
                    "observed_at": (cached.observed_at or cached.created_at).isoformat(),
                },
                forecast=[],
                agricultural_signals=signals,
                source="Cached (service error)",
                cached=True,
                cache_age_minutes=int((datetime.utcnow() - cached.created_at).total_seconds() / 60),
                fetched_at=datetime.utcnow().isoformat(),
            )
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Weather service unavailable. Please try again later.")

    # Save to cache
    if farm:
        record = WeatherRecord(
            farm_id=farm.id,
            latitude=use_lat,
            longitude=use_lon,
            temperature=weather_data["temperature"],
            humidity=weather_data["humidity"],
            rainfall=weather_data["rainfall"],
            wind_speed=weather_data["wind_speed"],
            weather_condition=weather_data["condition"],
            source="OpenWeather",
            observed_at=weather_data["observed_at"],
        )
        db.add(record)
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.warning(f"Failed to cache weather record: {e}")

    signals = _compute_agricultural_signals(
        weather_data["temperature"], weather_data["humidity"],
        weather_data["rainfall"], weather_data["wind_speed"],
    )
    location = _build_location_response(db, farm, use_lat, use_lon) if farm else {"name": f"{use_lat:.4f}, {use_lon:.4f}", "lat": use_lat, "lon": use_lon}

    return WeatherResponse(
        location=location,
        latitude=use_lat,
        longitude=use_lon,
        current={
            "temperature": weather_data["temperature"],
            "feels_like": weather_data["feels_like"],
            "humidity": weather_data["humidity"],
            "rainfall": weather_data["rainfall"],
            "wind_speed": weather_data["wind_speed"],
            "condition": weather_data["condition"],
            "description": weather_data["description"],
            "observed_at": weather_data["observed_at"].isoformat(),
        },
        forecast=[],
        agricultural_signals=signals,
        source="OpenWeather",
        cached=False,
        cache_age_minutes=0,
        fetched_at=datetime.utcnow().isoformat(),
    )


@router.get("/forecast")
def get_forecast(
    lat: float = Query(...),
    lon: float = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get 5-day / 3-hour forecast for the given coordinates."""
    _check_api_key()

    farm = db.query(Farm).filter(
        Farm.user_id == current_user.id,
        Farm.latitude.isnot(None),
        Farm.longitude.isnot(None),
    ).first()

    use_lat = farm.latitude if farm else lat
    use_lon = farm.longitude if farm else lon

    # Check forecast cache
    cached = None
    if farm:
        cache_filters = _get_cache_key(farm.id, use_lat, use_lon)
        cached = db.query(WeatherRecord).filter(*cache_filters).order_by(
            WeatherRecord.created_at.desc()
        ).first()

    if cached and cached.forecast_json and cached.created_at:
        age = datetime.utcnow() - cached.created_at
        if age < timedelta(minutes=FORECAST_CACHE_MINUTES):
            return {
                "forecast": cached.forecast_json,
                "cached": True,
                "cache_age_minutes": int(age.total_seconds() / 60),
                "fetched_at": cached.created_at.isoformat(),
            }

    try:
        forecast_data = _fetch_forecast_from_api(use_lat, use_lon)
    except Exception:
        if cached and cached.forecast_json:
            age = datetime.utcnow() - cached.created_at
            return {
                "forecast": cached.forecast_json,
                "cached": True,
                "cache_age_minutes": int(age.total_seconds() / 60),
                "fetched_at": cached.created_at.isoformat(),
                "source": "Cached (API unavailable)",
            }
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Forecast unavailable. Please try again later.")

    # Update forecast cache on existing weather record
    if cached:
        cached.forecast_json = forecast_data
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.warning(f"Failed to update forecast cache: {e}")

    return {
        "forecast": forecast_data,
        "cached": False,
        "cache_age_minutes": 0,
        "fetched_at": datetime.utcnow().isoformat(),
        "source": "OpenWeather",
    }


class GeocodeRequest(BaseModel):
    city: str


@router.post("/geocode")
def geocode_city(
    req: GeocodeRequest,
    current_user: User = Depends(get_current_user),
):
    """Forward geocode a city name to coordinates. All through backend (no API key in frontend)."""
    _check_api_key()

    try:
        resp = requests.get(
            f"{OPENWEATHER_GEO_URL}/direct",
            params={"q": req.city, "limit": 5, "appid": OPENWEATHER_API_KEY},
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Geocoding service unavailable.")

    results = []
    for item in data:
        parts = [item.get("locality", ""), item.get("state", ""), item.get("country", "")]
        name = ", ".join(p for p in parts if p)
        results.append({
            "name": name or f"{item['lat']}, {item['lon']}",
            "lat": item["lat"],
            "lon": item["lon"],
        })

    return {"results": results}


@router.post("/set-farm-location")
def set_farm_location(
    lat: float = Query(...),
    lon: float = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save geolocation to the user's active farm. Explicit user action only."""
    farm = db.query(Farm).filter(Farm.user_id == current_user.id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="No farm found. Create a farm first.")

    farm.latitude = lat
    farm.longitude = lon
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update farm location.")

    return {"message": "Farm location updated", "farm_id": farm.id, "lat": lat, "lon": lon}
