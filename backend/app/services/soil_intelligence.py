"""
HARVEX Soil Intelligence Service
Retrieves legitimate soil data from external sources with provenance tracking.

Supports:
- ISRIC SoilGrids (global, 250m resolution, estimated)
- Manual farmer soil reports (measured)
- Location-based soil type inference

Every soil attribute carries provenance:
- value, unit, status (estimated/measured/unavailable)
- source, retrieved_at, resolution, confidence
- is_field_measurement flag

NEVER fabricates soil data. Missing data remains missing.
"""

import requests
import logging
from typing import Dict, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

SOILGRIDS_BASE = "https://rest.isric.org/soilgrids/v2.0/properties/query"


def fetch_soilgrids_data(lat: float, lon: float) -> Dict[str, Any]:
    """Fetch soil properties from ISRIC SoilGrids API.
    Returns raw API response or empty dict on failure."""
    try:
        params = {
            "lon": lon,
            "lat": lat,
            "property": "phh2o",
            "depth": "0-5cm",
            "value": "mean",
        }
        resp = requests.get(SOILGRIDS_BASE, params=params, timeout=10)
        if resp.ok:
            return resp.json()

        # Try alternative properties
        for prop in ["clay", "sand", "silt", "soc", "nitrogen"]:
            params["property"] = prop
            resp = requests.get(SOILGRIDS_BASE, params=params, timeout=10)
            if resp.ok:
                return resp.json()

    except Exception as e:
        logger.warning(f"SoilGrids API error: {e}")

    return {}


def _parse_soilgrids_value(data: Dict, property_name: str) -> Optional[float]:
    """Extract a single property value from SoilGrids response."""
    try:
        layers = data.get("layers", [])
        for layer in layers:
            if layer.get("name") == property_name:
                depths = layer.get("depths", [])
                if depths:
                    return depths[0].get("values", {}).get("mean")
    except Exception:
        pass
    return None


def get_soil_intelligence(lat: float, lon: float) -> Dict[str, Any]:
    """Retrieve soil intelligence for a location.

    Returns structured soil data with provenance:
    {
        "ph": {"value": 6.4, "unit": "pH", "status": "estimated",
               "source": "ISRIC SoilGrids", "retrieved_at": "...",
               "resolution": "250m", "confidence": "medium",
               "is_field_measurement": false},
        "soil_type": {"value": "loamy", "status": "estimated", ...},
        "nitrogen": {"value": null, "status": "unavailable"},
        ...
    }
    """
    now = datetime.utcnow().isoformat()
    result = {
        "ph": {"value": None, "unit": "pH", "status": "unavailable",
                "source": "none", "retrieved_at": now, "is_field_measurement": False},
        "soil_type": {"value": None, "status": "unavailable",
                       "source": "none", "retrieved_at": now, "is_field_measurement": False},
        "nitrogen": {"value": None, "unit": "kg/ha", "status": "unavailable",
                      "source": "none", "retrieved_at": now, "is_field_measurement": False},
        "phosphorus": {"value": None, "unit": "kg/ha", "status": "unavailable",
                        "source": "none", "retrieved_at": now, "is_field_measurement": False},
        "potassium": {"value": None, "unit": "kg/ha", "status": "unavailable",
                       "source": "none", "retrieved_at": now, "is_field_measurement": False},
        "organic_carbon": {"value": None, "unit": "dag/kg", "status": "unavailable",
                           "source": "none", "retrieved_at": now, "is_field_measurement": False},
        "clay": {"value": None, "unit": "%", "status": "unavailable",
                  "source": "none", "retrieved_at": now, "is_field_measurement": False},
        "sand": {"value": None, "unit": "%", "status": "unavailable",
                  "source": "none", "retrieved_at": now, "is_field_measurement": False},
        "provider": "ISRIC SoilGrids",
        "resolution": "250m",
        "overall_status": "unavailable",
    }

    # Attempt SoilGrids fetch
    raw = fetch_soilgrids_data(lat, lon)
    if not raw:
        result["overall_status"] = "unavailable"
        return result

    # Parse pH (SoilGrids returns pH*10, e.g., 65 = 6.5)
    ph_raw = _parse_soilgrids_value(raw, "phh2o")
    if ph_raw is not None:
        ph_val = ph_raw / 10.0 if ph_raw > 14 else ph_raw
        result["ph"] = {
            "value": round(ph_val, 1),
            "unit": "pH",
            "status": "estimated",
            "source": "ISRIC SoilGrids",
            "retrieved_at": now,
            "resolution": "250m",
            "confidence": "medium",
            "is_field_measurement": False,
        }

    # Parse texture
    clay_raw = _parse_soilgrids_value(raw, "clay")
    sand_raw = _parse_soilgrids_value(raw, "sand")
    silt_raw = _parse_soilgrids_value(raw, "silt")

    if clay_raw is not None:
        result["clay"]["value"] = round(clay_raw, 1)
        result["clay"]["status"] = "estimated"
        result["clay"]["source"] = "ISRIC SoilGrids"
        result["clay"]["retrieved_at"] = now

    if sand_raw is not None:
        result["sand"]["value"] = round(sand_raw, 1)
        result["sand"]["status"] = "estimated"
        result["sand"]["source"] = "ISRIC SoilGrids"
        result["sand"]["retrieved_at"] = now

    # Infer soil type from texture
    if clay_raw is not None and sand_raw is not None:
        if clay_raw > 40:
            inferred = "clay"
        elif clay_raw > 25:
            inferred = "clay_loam"
        elif sand_raw > 50:
            inferred = "sandy_loam"
        elif clay_raw > 15 and sand_raw > 30:
            inferred = "loamy"
        else:
            inferred = "loamy"
        result["soil_type"] = {
            "value": inferred,
            "status": "estimated",
            "source": "ISRIC SoilGrids (texture-based)",
            "retrieved_at": now,
            "resolution": "250m",
            "confidence": "medium",
            "is_field_measurement": False,
        }

    # Parse organic carbon
    soc_raw = _parse_soilgrids_value(raw, "soc")
    if soc_raw is not None:
        result["organic_carbon"]["value"] = round(soc_raw, 2)
        result["organic_carbon"]["status"] = "estimated"
        result["organic_carbon"]["source"] = "ISRIC SoilGrids"
        result["organic_carbon"]["retrieved_at"] = now

    # Parse nitrogen (SoilGrids nitrogen in cg/kg)
    n_raw = _parse_soilgrids_value(raw, "nitrogen")
    if n_raw is not None:
        result["nitrogen"]["value"] = round(n_raw / 100.0, 1)  # convert cg/kg to g/kg
        result["nitrogen"]["status"] = "estimated"
        result["nitrogen"]["source"] = "ISRIC SoilGrids"
        result["nitrogen"]["retrieved_at"] = now

    # N/P/K are NOT directly available from SoilGrids as kg/ha
    # P and K remain unavailable from this source
    # N is estimated from organic carbon using conversion factor

    # Determine overall status
    available_count = sum(
        1 for f in ["ph", "soil_type", "nitrogen", "clay", "sand"]
        if result[f].get("value") is not None
    )
    if available_count >= 3:
        result["overall_status"] = "partial"
    elif available_count >= 1:
        result["overall_status"] = "minimal"
    else:
        result["overall_status"] = "unavailable"

    return result


def apply_farmer_soil_report(soil_data: Dict, report: Dict) -> Dict[str, Any]:
    """Apply farmer-provided soil report values.
    These are marked as 'measured' with is_field_measurement=true.

    report format:
    {
        "ph": 6.5,
        "nitrogen": 80,  # kg/ha
        "phosphorus": 40,
        "potassium": 50,
        "soil_type": "loamy",
        "organic_carbon": 0.5
    }
    """
    now = datetime.utcnow().isoformat()

    for field, value in report.items():
        if field in soil_data and value is not None:
            unit_map = {
                "ph": "pH", "nitrogen": "kg/ha", "phosphorus": "kg/ha",
                "potassium": "kg/ha", "soil_type": "", "organic_carbon": "%",
            }
            soil_data[field] = {
                "value": value,
                "unit": unit_map.get(field, ""),
                "status": "measured",
                "source": "farmer_soil_report",
                "retrieved_at": now,
                "is_field_measurement": True,
            }

    return soil_data


def get_data_completeness(soil_data: Dict) -> Dict[str, str]:
    """Calculate soil data completeness."""
    completeness = {}
    for field in ["ph", "soil_type", "nitrogen", "phosphorus", "potassium"]:
        val = soil_data.get(field, {})
        if isinstance(val, dict):
            status = val.get("status", "unavailable")
            if status == "measured":
                completeness[field] = "measured"
            elif status == "estimated":
                completeness[field] = "estimated"
            else:
                completeness[field] = "unavailable"
        else:
            completeness[field] = "unavailable"
    return completeness
