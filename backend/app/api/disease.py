"""
HARVEX Disease Intelligence — NVIDIA Vision Only.

Pipeline:
  ANY CROP → IMAGE VALIDATION → NVIDIA VISION → STRUCTURED ASSESSMENT
  → VALIDATION → TREATMENT (NVIDIA REASONING) → PERSIST → FOLLOW-UP

No local PyTorch fallback. No mock. No fabrication.
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from PIL import Image
import io
import json
import os
import re
import base64
import logging
from datetime import datetime
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.models import User, DiseaseScan, WeatherRecord, CropCycle, Field, Farm
from app.schemas.schemas import DiseaseScanResponse
from app.core.config import UPLOAD_DIR, MAX_UPLOAD_SIZE_MB

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/disease", tags=["disease"])

MIN_IMAGE_SIZE = 5120       # 5KB
MIN_DIMENSION = 50          # 50x50 px minimum
MAX_DIMENSION = 8192        # 8192 px max side
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}

# Valid enum values for response normalization
VALID_HEALTH_STATUSES = {"healthy", "diseased", "unable_to_determine"}
VALID_SEVERITIES = {"none", "mild", "moderate", "severe", "unknown"}


def _validate_image(file_type: str, image_bytes: bytes, filename: str = None) -> str:
    """Validate uploaded image. Returns the confirmed file extension."""
    # MIME type check
    if file_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Please upload JPEG, PNG, or WEBP image."
        )

    # Extension check
    if filename:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file extension. Use .jpg, .jpeg, .png, or .webp."
            )
    else:
        ext = "jpg"

    # Size checks
    if len(image_bytes) > MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size is {MAX_UPLOAD_SIZE_MB}MB."
        )
    if len(image_bytes) < MIN_IMAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image is too small for reliable analysis. Please upload a clearer leaf photo (minimum 5KB)."
        )

    # Decode and validate image
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.verify()
        # Re-open after verify (verify closes the file)
        img = Image.open(io.BytesIO(image_bytes))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or corrupted image file. Please upload a valid image."
        )

    # Dimension checks
    width, height = img.size
    if width < MIN_DIMENSION or height < MIN_DIMENSION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image too small ({width}x{height}). Minimum {MIN_DIMENSION}x{MIN_DIMENSION} pixels."
        )
    if width > MAX_DIMENSION or height > MAX_DIMENSION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image too large ({width}x{height}). Maximum {MAX_DIMENSION}x{MAX_DIMENSION} pixels."
        )

    # Blank image check — sample corners and center
    try:
        img_rgb = img.convert("RGB")
        pixels_to_check = [
            img_rgb.getpixel((0, 0)),
            img_rgb.getpixel((width - 1, 0)),
            img_rgb.getpixel((0, height - 1)),
            img_rgb.getpixel((width - 1, height - 1)),
            img_rgb.getpixel((width // 2, height // 2)),
        ]
        # Check if all sampled pixels are nearly identical (blank image)
        if len(set(pixels_to_check)) <= 1:
            # All same color — could be blank, but allow it (some leaves are uniform)
            # Only reject if it's pure white or pure black
            if pixels_to_check[0] in ((255, 255, 255), (0, 0, 0)):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Image appears to be blank (solid color). Please upload a photo of a plant leaf."
                )
    except HTTPException:
        raise
    except Exception:
        pass  # If pixel check fails, continue — don't block on this

    return ext


def _normalize_severity(severity: str) -> str:
    """Normalize severity to allowed values."""
    if not severity:
        return "unknown"
    s = severity.strip().lower()
    if s in VALID_SEVERITIES:
        return s
    # Map common variants
    mapping = {
        "high": "severe", "low": "mild", "critical": "severe",
        "medium": "moderate", "moderate": "moderate",
    }
    return mapping.get(s, "unknown")


def _normalize_health_status(status_val: str) -> str:
    """Normalize health_status to allowed values."""
    if not status_val:
        return "unable_to_determine"
    s = status_val.strip().lower().replace(" ", "_")
    if s in VALID_HEALTH_STATUSES:
        return s
    mapping = {
        "healthy": "healthy", "diseased": "diseased",
        "uncertain": "unable_to_determine",
        "insufficient_image_quality": "unable_to_determine",
        "unable_to_determine": "unable_to_determine",
    }
    return mapping.get(s, "unable_to_determine")


def _parse_disease_response(raw_content: str) -> dict | None:
    """Parse NVIDIA response into structured disease data. Returns None if parsing fails."""
    if not raw_content or len(raw_content.strip()) < 10:
        return None

    parsed = None

    # Strategy 1: Direct JSON parse
    try:
        parsed = json.loads(raw_content)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Extract from markdown code fences
    if not parsed:
        for pattern in [r'```json\s*(.*?)\s*```', r'```\s*(.*?)\s*```']:
            match = re.search(pattern, raw_content, re.DOTALL)
            if match:
                try:
                    parsed = json.loads(match.group(1))
                except json.JSONDecodeError:
                    continue

    # Strategy 3: Find first { ... } block
    if not parsed:
        brace = raw_content.find('{')
        if brace >= 0:
            depth = 0
            for i in range(brace, min(len(raw_content), brace + 5000)):
                if raw_content[i] == '{':
                    depth += 1
                elif raw_content[i] == '}':
                    depth -= 1
                if depth == 0:
                    try:
                        parsed = json.loads(raw_content[brace:i + 1])
                    except json.JSONDecodeError:
                        break
                    break

    if not parsed or not isinstance(parsed, dict):
        return None

    # Validate and normalize required fields
    result = {
        "crop": str(parsed.get("crop", "unknown")),
        "health_status": _normalize_health_status(parsed.get("health_status", parsed.get("plant_health", ""))),
        "disease_name": str(parsed.get("disease_name", "Unable to determine")),
        "severity": _normalize_severity(parsed.get("severity", "unknown")),
        "confidence": None,
        "visual_evidence": parsed.get("visual_evidence", parsed.get("visual_symptoms", [])),
        "explanation": str(parsed.get("explanation", parsed.get("reasoning", ""))),
        "needs_follow_up": bool(parsed.get("needs_follow_up", False)),
        "needs_better_image": bool(parsed.get("needs_better_image", False)),
    }

    # Confidence normalization: accept 0-1 or 0-100, normalize to 0-1
    raw_conf = parsed.get("confidence")
    if raw_conf is not None and isinstance(raw_conf, (int, float)):
        if raw_conf > 1.0:
            result["confidence"] = round(raw_conf / 100.0, 4)
        else:
            result["confidence"] = round(float(raw_conf), 4)
        # Clamp to 0-1
        result["confidence"] = max(0.0, min(1.0, result["confidence"]))
    else:
        result["confidence"] = None

    # Ensure visual_evidence is a list
    if not isinstance(result["visual_evidence"], list):
        result["visual_evidence"] = []

    # If health_status is healthy, normalize disease_name
    if result["health_status"] == "healthy":
        result["disease_name"] = "None"
        if result["severity"] == "unknown":
            result["severity"] = "none"
        if result["confidence"] is None:
            result["confidence"] = 0.95

    return result


def _try_nvidia_vision(crop_name: str, image_bytes: bytes, file_type: str) -> dict:
    """Call NVIDIA Vision AI with robust parsing and retry. Returns structured result or failure dict."""
    from app.services.ai import ai_service

    b64 = base64.b64encode(image_bytes).decode("utf-8")
    mime = file_type or "image/jpeg"
    image_url = f"data:{mime};base64,{b64}"

    result = ai_service.disease_analysis(crop_name, image_url)

    debug_info = result.get("debug", {})

    if result.get("available") and result.get("data"):
        ai_data = result["data"]
        return {
            "success": True,
            "raw_data": ai_data,
            "provider": "nvidia",
            "model": debug_info.get("model", "unknown"),
            "debug": debug_info,
        }

    return {
        "success": False,
        "error_code": result.get("error_code", "AI_VISION_FAILED"),
        "error": result.get("message", result.get("error", "Vision AI analysis failed")),
        "debug": debug_info,
    }


def _get_treatment(crop_name: str, disease_name: str, severity: str, weather: dict = None, confidence: float = None) -> dict | None:
    """Get treatment guidance from NVIDIA reasoning model. Returns None on failure.

    Handles:
    - Diseased: full treatment
    - Healthy: monitoring guidance only
    - Unable to determine: image quality guidance
    """
    from app.services.ai import ai_service
    from app.services.ai.prompts import treatment_prompt

    # Healthy plant flow
    if disease_name in ("None", "none") or (disease_name and disease_name.lower() in ("none", "healthy")):
        return {
            "summary": "No visible disease was identified in this image.",
            "immediate_actions": [],
            "cultural_or_organic_actions": [
                "Continue routine crop monitoring.",
                "Maintain proper irrigation and nutrition.",
                "Watch for any new symptoms in the coming days."
            ],
            "chemical_options": [],
            "precautions": [],
            "follow_up_days": 7,
            "reassessment_reason": "Routine monitoring.",
            "safety_note": "No chemical treatment needed at this time.",
            "uncertainty_note": "",
        }

    # Unable to determine flow
    if disease_name in ("Unable to determine", "unable_to_determine") or severity in ("unknown", "none"):
        return {
            "summary": "The image does not provide enough evidence for a reliable disease-specific recommendation.",
            "immediate_actions": [],
            "cultural_or_organic_actions": [
                "Upload a clear close-up of the affected leaf or plant part.",
                "Ensure good lighting and focus on the symptomatic area.",
                "Consider consulting a local agricultural expert for in-person assessment."
            ],
            "chemical_options": [],
            "precautions": [],
            "follow_up_days": 3,
            "reassessment_reason": "Image quality insufficient for reliable diagnosis.",
            "safety_note": "Do not apply any chemicals without a confirmed diagnosis.",
            "uncertainty_note": "The AI could not reliably identify the disease from this image.",
        }

    # Diseased flow - call NVIDIA reasoning
    try:
        prompt = treatment_prompt(crop_name, disease_name, severity, weather)
        provider = ai_service.get_provider()
        messages = [
            {"role": "system", "content": "You are HARVEX, an agricultural decision-support platform. Provide conservative, safe treatment guidance. Never fabricate pesticide names or dosages. Always include safety notes."},
            {"role": "user", "content": prompt},
        ]
        result = provider.chat(messages, temperature=0.3, max_tokens=1024)
        if result.get("success") and result.get("content"):
            parsed = ai_service._parse_json_response(result["content"]) if hasattr(ai_service, '_parse_json_response') else None
            if parsed and isinstance(parsed, dict):
                # Ensure safety fields exist
                parsed.setdefault("safety_note", "Follow product label and local agricultural guidance.")
                parsed.setdefault("uncertainty_note", "")
                if confidence is not None and confidence < 0.6:
                    parsed["uncertainty_note"] = f"Confidence is low ({confidence:.0%}). Treatment should be conservative. Consider re-examination with a clearer image."
                return parsed
    except Exception as e:
        logger.warning(f"Treatment generation failed: {e}")

    return None


def _get_weather_context(user_id: int, db: Session) -> dict | None:
    """Fetch latest weather context for the user's farms. Returns None if unavailable."""
    try:
        weather = (
            db.query(WeatherRecord)
            .join(Farm, WeatherRecord.farm_id == Farm.id)
            .filter(Farm.user_id == user_id)
            .order_by(WeatherRecord.observed_at.desc())
            .first()
        )
        if weather:
            return {
                "temperature": weather.temperature,
                "humidity": weather.humidity,
                "rainfall": weather.rainfall,
                "wind_speed": weather.wind_speed,
                "condition": weather.weather_condition,
            }
    except Exception as e:
        logger.warning(f"Failed to fetch weather context: {e}")
    return None


def _get_crop_cycle_context(user_id: int, crop_name: str, db: Session) -> dict | None:
    """Fetch active crop cycle context for the user."""
    try:
        cycle = (
            db.query(CropCycle)
            .join(Field).join(Farm)
            .filter(
                Farm.user_id == user_id,
                CropCycle.status == "active",
                CropCycle.crop_name.ilike(f"%{crop_name}%")
            )
            .first()
        )
        if cycle:
            return {
                "crop_cycle_id": cycle.id,
                "field_id": cycle.field_id,
                "planting_date": cycle.planting_date.isoformat() if cycle.planting_date else None,
            }
    except Exception as e:
        logger.warning(f"Failed to fetch crop cycle context: {e}")
    return None


def _save_disease_scan(
    user_id: int, cycle_id: int, image_bytes: bytes, file_ext: str,
    crop_name: str, disease_data: dict, treatment: dict | None, db: Session
) -> DiseaseScan:
    """Save disease scan result to database with full metadata."""
    if cycle_id is None:
        from app.models.models import CropCycle, Field, Farm
        active_cycle = db.query(CropCycle).join(Field).join(Farm).filter(
            Farm.user_id == user_id,
            CropCycle.status == "active"
        ).first()
        if active_cycle:
            cycle_id = active_cycle.id

    upload_dir = os.path.join(UPLOAD_DIR, str(user_id))
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"disease_scan_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{file_ext}"
    filepath = os.path.join(upload_dir, filename)
    with open(filepath, "wb") as f:
        f.write(image_bytes)

    scan = DiseaseScan(
        crop_cycle_id=cycle_id,
        image_path=filepath,
        crop_name=crop_name,
        predicted_disease=disease_data.get("disease_name", "Unknown"),
        health_status=disease_data.get("health_status", "unable_to_determine"),
        confidence=disease_data.get("confidence"),
        severity=disease_data.get("severity", "unknown"),
        model_version=disease_data.get("model_version", "unknown"),
        provider=disease_data.get("provider", "nvidia"),
        model_name=disease_data.get("model_name", "unknown"),
        visual_evidence=disease_data.get("visual_evidence", []),
        explanation=disease_data.get("explanation", ""),
        follow_up_state="initial",
        treatment_json=treatment,
    )
    return scan


@router.post("/scan", response_model=DiseaseScanResponse)
async def scan_disease(
    file: UploadFile = File(...),
    crop_name: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Crop-agnostic disease detection using NVIDIA Vision AI exclusively.

    Pipeline: validate image → NVIDIA Vision → parse with retry → validate → treatment → persist.
    On any NVIDIA failure: returns honest error, no fallback.
    """
    image_bytes = await file.read()
    crop_lower = crop_name.strip().lower()

    # Step 1: Validate image
    file_ext = _validate_image(file.content_type, image_bytes, file.filename)

    # Step 2: NVIDIA Vision AI (only path)
    nvidia_result = _try_nvidia_vision(crop_name, image_bytes, file.content_type)
    debug_info = nvidia_result.get("debug", {})

    logger.info(
        f"Disease scan: crop={crop_name}, "
        f"success={nvidia_result['success']}, "
        f"parse_method={debug_info.get('parse_method', 'N/A')}, "
        f"retry_used={debug_info.get('retry_used', False)}, "
        f"latency={debug_info.get('latency', 0)}s"
    )

    if not nvidia_result["success"]:
        error_code = nvidia_result.get("error_code", "UNKNOWN")
        error_msg = nvidia_result.get("error", "Analysis failed")

        error_messages = {
            "AI_VISION_NOT_CONFIGURED": "Disease analysis is not configured. Please contact support.",
            "AI_VISION_RATE_LIMITED": "NVIDIA Vision AI is temporarily rate-limited. Please try again in a few minutes.",
            "AI_VISION_MAX_RETRIES_EXCEEDED": "NVIDIA Vision AI is temporarily rate-limited. Please try again in a few minutes.",
            "AI_VISION_TIMEOUT": "NVIDIA Vision AI timed out. Please try again with a clearer image.",
            "AI_VISION_CONNECTION_ERROR": "NVIDIA Vision AI is temporarily unavailable. Please try again later.",
            "AI_VISION_AUTH_FAILED": "NVIDIA Vision AI authentication failed. Please contact support.",
            "AI_VISION_EMPTY": "NVIDIA Vision AI returned an empty response. Please try again.",
            "AI_VISION_PARSE_FAILED": "The AI response could not be converted into a reliable structured assessment. Please retry the image analysis.",
            "AI_VISION_RETRY_FAILED": "NVIDIA Vision AI could not produce a valid structured response after retry. Please try again.",
        }
        friendly_msg = error_messages.get(error_code, f"Unable to analyze the image: {error_msg}. Please try again.")

        return DiseaseScanResponse(
            supported=True,
            crop=crop_name,
            health_status="unable_to_determine",
            predicted_disease="Unable to determine",
            display_name="Unable to determine",
            confidence=None,
            severity="unknown",
            model_version="unavailable",
            provider="nvidia",
            model_name="unavailable",
            visual_evidence=[],
            explanation=friendly_msg,
            needs_follow_up=False,
            needs_better_image=False,
            top_predictions=[],
            quality_check={"quality": "unavailable", "provider": "nvidia", "error": error_code},
            actions={},
            treatment=None,
            description=friendly_msg,
            progression="",
            crop_impact="",
        )

    # Step 3: Parse and validate NVIDIA response
    raw_data = nvidia_result.get("raw_data", {})
    from app.services.ai.ai_service import _validate_disease_result
    disease_data = _validate_disease_result(raw_data, crop_name)

    if not disease_data:
        # Fallback: could not extract structured data
        disease_data = {
            "crop": crop_name,
            "health_status": "unable_to_determine",
            "disease_name": "Unable to determine",
            "severity": "unknown",
            "confidence": None,
            "visual_evidence": [],
            "explanation": "Could not parse the AI response into a structured assessment.",
            "needs_follow_up": False,
            "needs_better_image": True,
        }

    # Step 4: Get weather and crop context
    weather_ctx = _get_weather_context(current_user.id, db)
    crop_ctx = _get_crop_cycle_context(current_user.id, crop_name, db)
    cycle_id = crop_ctx.get("crop_cycle_id") if crop_ctx else None

    # Step 5: Get treatment
    treatment = _get_treatment(
        crop_name,
        disease_data["disease_name"],
        disease_data["severity"],
        weather=weather_ctx,
        confidence=disease_data.get("confidence"),
    )

    # Step 6: Persist
    file_ext_final = file_ext or "jpg"
    scan = _save_disease_scan(
        current_user.id, cycle_id, image_bytes, file_ext_final,
        crop_name, disease_data, treatment, db
    )
    db.add(scan)
    db.commit()

    # Step 7: Build response
    display_name = disease_data["disease_name"]
    if display_name in ("None", "none"):
        display_name = "Healthy"

    description = disease_data["explanation"]
    if disease_data["needs_better_image"]:
        description = "The image does not contain enough clear visual information for reliable plant-health assessment. Please upload a clear close-up image of the affected leaf or plant part."

    return DiseaseScanResponse(
        supported=True,
        crop=crop_name,
        health_status=disease_data["health_status"],
        predicted_disease=disease_data["disease_name"],
        display_name=display_name,
        confidence=disease_data["confidence"],
        severity=disease_data["severity"],
        model_version="nvidia-vision-v1",
        provider="nvidia",
        model_name=debug_info.get("model", nvidia_result.get("model", "meta/llama-3.2-11b-vision-instruct")),
        visual_evidence=disease_data["visual_evidence"],
        explanation=description,
        needs_follow_up=disease_data["needs_follow_up"],
        needs_better_image=disease_data["needs_better_image"],
        top_predictions=[],
        quality_check={"quality": "good", "provider": "nvidia", "parse_method": debug_info.get("parse_method"), "retry_used": debug_info.get("retry_used", False)},
        actions={},
        treatment=treatment,
        description=description,
        progression="",
        crop_impact="",
    )


@router.get("/history/{crop_cycle_id}")
def get_disease_history(
    crop_cycle_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get disease scan history for a crop cycle."""
    scans = (
        db.query(DiseaseScan)
        .filter(DiseaseScan.crop_cycle_id == crop_cycle_id)
        .order_by(DiseaseScan.created_at.desc())
        .limit(10)
        .all()
    )

    history = []
    for scan in scans:
        history.append({
            "id": scan.id,
            "crop": scan.crop_name or scan.predicted_disease,
            "predicted_disease": scan.predicted_disease,
            "health_status": scan.health_status,
            "confidence": scan.confidence,
            "severity": scan.severity,
            "model_version": scan.model_version,
            "provider": scan.provider,
            "visual_evidence": scan.visual_evidence or [],
            "explanation": scan.explanation,
            "created_at": scan.created_at.isoformat() if scan.created_at else None,
        })

    return {"history": history}


@router.get("/timeline/{crop_cycle_id}")
def get_health_timeline(
    crop_cycle_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get health timeline with trend analysis for a crop cycle."""
    scans = (
        db.query(DiseaseScan)
        .filter(DiseaseScan.crop_cycle_id == crop_cycle_id)
        .order_by(DiseaseScan.created_at.asc())
        .all()
    )

    if not scans:
        return {
            "timeline": [],
            "trend": "stable",
            "summary": "No disease scans recorded yet."
        }

    timeline = []
    for scan in scans:
        timeline.append({
            "id": scan.id,
            "date": scan.created_at.strftime("%Y-%m-%d") if scan.created_at else "Unknown",
            "disease": scan.predicted_disease,
            "health_status": scan.health_status,
            "confidence": scan.confidence,
            "severity": scan.severity,
        })

    severity_order = {"none": 0, "mild": 1, "moderate": 2, "severe": 3, "unknown": 0}
    if len(scans) >= 2:
        latest_severity = scans[-1].severity or "unknown"
        previous_severity = scans[-2].severity or "unknown"
        if severity_order.get(latest_severity, 0) > severity_order.get(previous_severity, 0):
            trend = "worsening"
        elif severity_order.get(latest_severity, 0) < severity_order.get(previous_severity, 0):
            trend = "improving"
        else:
            trend = "stable"
    else:
        trend = "stable"

    total_scans = len(scans)
    diseases_found = set(
        s.predicted_disease for s in scans
        if s.predicted_disease and s.predicted_disease not in ("None", "Unable to determine")
    )

    summary = f"Total scans: {total_scans}. "
    if diseases_found:
        summary += f"Diseases detected: {', '.join(diseases_found)}. "
    summary += f"Health trend: {trend}."

    return {
        "timeline": timeline,
        "trend": trend,
        "summary": summary,
    }


@router.get("/compare/{scan_id}")
def compare_scans(
    scan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Compare a follow-up scan with the previous scan.

    Returns comparison of:
    - health_status changes
    - disease_name changes
    - severity changes
    - observed changes description
    """
    current_scan = db.query(DiseaseScan).filter(DiseaseScan.id == scan_id).first()
    if not current_scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    # Verify ownership
    if current_scan.crop_cycle_id:
        cycle = db.query(CropCycle).filter(CropCycle.id == current_scan.crop_cycle_id).first()
        if cycle:
            field = db.query(Field).filter(Field.id == cycle.field_id).first()
            if field:
                farm = db.query(Farm).filter(Farm.id == field.farm_id).first()
                if farm and farm.user_id != current_user.id:
                    raise HTTPException(status_code=403, detail="Not authorized")

    # Find previous scan for same crop cycle
    previous_scan = (
        db.query(DiseaseScan)
        .filter(
            DiseaseScan.crop_cycle_id == current_scan.crop_cycle_id,
            DiseaseScan.id < scan_id
        )
        .order_by(DiseaseScan.created_at.desc())
        .first()
    )

    if not previous_scan:
        return {
            "current_scan_id": scan_id,
            "previous_scan_id": None,
            "comparison": None,
            "message": "No previous scan available for comparison.",
        }

    # Compare
    severity_order = {"none": 0, "mild": 1, "moderate": 2, "severe": 3, "unknown": 0}
    prev_sev = severity_order.get(previous_scan.severity or "unknown", 0)
    curr_sev = severity_order.get(current_scan.severity or "unknown", 0)

    # Determine change
    if current_scan.health_status == "unable_to_determine" or previous_scan.health_status == "unable_to_determine":
        change = "uncertain"
        description = "Unable to reliably determine change from the available images."
    elif current_scan.predicted_disease != previous_scan.predicted_disease:
        change = "changed"
        description = f"Disease changed from {previous_scan.predicted_disease} to {current_scan.predicted_disease}. New or changed findings were observed."
    elif curr_sev < prev_sev:
        change = "improving"
        description = f"Observed symptoms appear reduced compared with the previous scan. Severity changed from {previous_scan.severity} to {current_scan.severity}."
    elif curr_sev > prev_sev:
        change = "worsening"
        description = f"Observed symptoms appear more severe than the previous scan. Severity changed from {previous_scan.severity} to {current_scan.severity}. Further assessment and agricultural guidance are recommended."
    else:
        change = "stable"
        description = f"Condition appears similar to the previous scan. Severity remains {current_scan.severity}."

    return {
        "current_scan_id": scan_id,
        "previous_scan_id": previous_scan.id,
        "comparison": {
            "change": change,
            "description": description,
            "previous": {
                "disease": previous_scan.predicted_disease,
                "health_status": previous_scan.health_status,
                "severity": previous_scan.severity,
                "confidence": previous_scan.confidence,
                "date": previous_scan.created_at.isoformat() if previous_scan.created_at else None,
            },
            "current": {
                "disease": current_scan.predicted_disease,
                "health_status": current_scan.health_status,
                "severity": current_scan.severity,
                "confidence": current_scan.confidence,
                "date": current_scan.created_at.isoformat() if current_scan.created_at else None,
            },
        },
    }


@router.get("/scans/{scan_id}")
def get_scan_detail(
    scan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed disease scan result including treatment."""
    scan = db.query(DiseaseScan).filter(DiseaseScan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    # Verify ownership
    if scan.crop_cycle_id:
        cycle = db.query(CropCycle).filter(CropCycle.id == scan.crop_cycle_id).first()
        if cycle:
            field = db.query(Field).filter(Field.id == cycle.field_id).first()
            if field:
                farm = db.query(Farm).filter(Farm.id == field.farm_id).first()
                if farm and farm.user_id != current_user.id:
                    raise HTTPException(status_code=403, detail="Not authorized")

    return {
        "id": scan.id,
        "crop": scan.crop_name,
        "health_status": scan.health_status,
        "predicted_disease": scan.predicted_disease,
        "confidence": scan.confidence,
        "severity": scan.severity,
        "visual_evidence": scan.visual_evidence or [],
        "explanation": scan.explanation,
        "treatment": scan.treatment_json,
        "follow_up_state": scan.follow_up_state,
        "model_version": scan.model_version,
        "provider": scan.provider,
        "model_name": scan.model_name,
        "created_at": scan.created_at.isoformat() if scan.created_at else None,
    }
