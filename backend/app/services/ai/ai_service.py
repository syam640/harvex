"""Unified AI service — the single entry point for all AI operations in HARVEX."""

import json
import logging
import re
from typing import Optional
from app.services.ai.nvidia_provider import NVIDIAProvider
from app.services.ai.schemas import (
    CropRecommendationResult, DiseaseAnalysisResult, TreatmentResult,
    RiskAnalysisResult, IrrigationResult, FinancialResult,
    WhatIfResult, FarmInsightResult, AIUnavailableResponse,
)
from app.services.ai.prompts import (
    system_prompt, crop_recommendation_prompt, disease_analysis_prompt,
    treatment_prompt, risk_analysis_prompt, irrigation_prompt,
    financial_analysis_prompt, what_if_prompt, farm_insight_prompt,
    assistant_prompt,
)

logger = logging.getLogger(__name__)

_provider: Optional[NVIDIAProvider] = None


def get_provider() -> NVIDIAProvider:
    global _provider
    if _provider is None:
        _provider = NVIDIAProvider()
    return _provider


def _parse_json_response(content: str) -> Optional[dict]:
    if not content:
        return None
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    for pattern in [r'```json\s*(.*?)\s*```', r'```\s*(.*?)\s*```']:
        match = re.search(pattern, content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except (json.JSONDecodeError, IndexError):
                continue
    brace = content.find('{')
    if brace >= 0:
        depth = 0
        for i in range(brace, len(content)):
            if content[i] == '{': depth += 1
            elif content[i] == '}': depth -= 1
            if depth == 0:
                try:
                    return json.loads(content[brace:i+1])
                except json.JSONDecodeError:
                    break
    return None


def _ai_unavailable(error_code: str = "AI_PROVIDER_UNAVAILABLE", error: str = None) -> dict:
    return {
        "available": False,
        "error_code": error_code,
        "message": "AI analysis is temporarily unavailable. Core farm intelligence remains available.",
        "detail": error,
    }


def crop_recommendation(context: dict) -> dict:
    provider = get_provider()
    if not provider.is_available():
        return _ai_unavailable("AI_NOT_CONFIGURED")
    messages = [
        {"role": "system", "content": system_prompt("en")},
        {"role": "user", "content": crop_recommendation_prompt(context)},
    ]
    result = provider.chat(messages, temperature=0.5, max_tokens=1024)
    if not result["success"]:
        return _ai_unavailable(result.get("error_code", "AI_FAILED"), result.get("error"))
    parsed = _parse_json_response(result["content"])
    if not parsed:
        return _ai_unavailable("AI_INVALID_RESPONSE", "Could not parse crop recommendation")
    try:
        validated = CropRecommendationResult(**parsed)
        return {"available": True, "data": validated.model_dump()}
    except Exception:
        return {"available": True, "data": parsed}


def disease_analysis(crop: str, image_url: str, context: dict = None) -> dict:
    """Disease analysis with robust JSON extraction and one controlled retry."""
    import time
    from app.services.ai.prompts import disease_analysis_prompt, disease_analysis_retry_prompt

    provider = get_provider()
    if not provider.is_available():
        return _ai_unavailable("AI_NOT_CONFIGURED")

    prompt = disease_analysis_prompt(crop, context)
    retry_prompt = disease_analysis_retry_prompt(crop, context)

    # Attempt 1
    start = time.time()
    result = provider.vision(image_url, prompt, max_tokens=1024)
    elapsed = round(time.time() - start, 2)

    if not result["success"]:
        return {
            **_ai_unavailable(result.get("error_code", "AI_VISION_FAILED"), result.get("error")),
            "debug": {
                "provider": "nvidia",
                "model": provider.vision_model,
                "latency": elapsed,
                "parse_method": "N/A",
                "initial_parse_success": False,
                "retry_used": False,
                "final_parse_success": False,
                "provider_error": result.get("error"),
            }
        }

    raw_content = result.get("content", "")
    parse_info = _extract_json_with_debug(raw_content)

    if parse_info["success"]:
        return {
            "available": True,
            "data": parse_info["data"],
            "debug": {
                "provider": "nvidia",
                "model": provider.vision_model,
                "latency": elapsed,
                "parse_method": parse_info["method"],
                "initial_parse_success": True,
                "retry_used": False,
                "final_parse_success": True,
                "provider_error": None,
                "raw_content_length": len(raw_content),
            }
        }

    # Attempt 2: Retry with explicit JSON request
    start2 = time.time()
    retry_result = provider.vision(image_url, retry_prompt, max_tokens=1024)
    elapsed2 = round(time.time() - start2, 2)
    total_elapsed = round(elapsed + elapsed2, 2)

    if not retry_result["success"]:
        return {
            **_ai_unavailable("AI_VISION_RETRY_FAILED", "Retry also failed"),
            "debug": {
                "provider": "nvidia",
                "model": provider.vision_model,
                "latency": total_elapsed,
                "parse_method": parse_info["method"],
                "initial_parse_success": False,
                "retry_used": True,
                "final_parse_success": False,
                "provider_error": retry_result.get("error"),
                "raw_content_length": len(raw_content),
            }
        }

    retry_content = retry_result.get("content", "")
    retry_parse = _extract_json_with_debug(retry_content)

    if retry_parse["success"]:
        return {
            "available": True,
            "data": retry_parse["data"],
            "debug": {
                "provider": "nvidia",
                "model": provider.vision_model,
                "latency": total_elapsed,
                "parse_method": retry_parse["method"],
                "initial_parse_success": False,
                "retry_used": True,
                "final_parse_success": True,
                "provider_error": None,
                "raw_content_length": len(retry_content),
            }
        }

    # Both attempts failed - return Unable to determine
    return {
        "available": False,
        "error_code": "AI_VISION_PARSE_FAILED",
        "message": "The AI response could not be converted into a reliable structured assessment. Please retry the image analysis.",
        "debug": {
            "provider": "nvidia",
            "model": provider.vision_model,
            "latency": total_elapsed,
            "parse_method": retry_parse["method"],
            "initial_parse_success": False,
            "retry_used": True,
            "final_parse_success": False,
            "provider_error": None,
            "raw_content_length": len(retry_content),
            "raw_content_preview": retry_content[:200] if retry_content else None,
        }
    }


def _extract_json_with_debug(content: str) -> dict:
    """Extract JSON from response with debug information.

    Returns:
        {"success": bool, "data": dict, "method": str}
    """
    if not content or len(content.strip()) < 10:
        return {"success": False, "data": None, "method": "empty"}

    # Strategy 1: Direct JSON parse
    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            return {"success": True, "data": parsed, "method": "pure_json"}
    except json.JSONDecodeError:
        pass

    # Strategy 2: Markdown code fences ```json ... ```
    for pattern in [r'```json\s*(.*?)\s*```', r'```\s*(.*?)\s*```']:
        match = re.search(pattern, content, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(1))
                if isinstance(parsed, dict):
                    return {"success": True, "data": parsed, "method": "markdown_fenced"}
            except json.JSONDecodeError:
                continue

    # Strategy 3: Find first { ... } block (JSON surrounded by text)
    brace = content.find('{')
    if brace >= 0:
        depth = 0
        for i in range(brace, min(len(content), brace + 5000)):
            if content[i] == '{':
                depth += 1
            elif content[i] == '}':
                depth -= 1
            if depth == 0:
                try:
                    parsed = json.loads(content[brace:i + 1])
                    if isinstance(parsed, dict):
                        return {"success": True, "data": parsed, "method": "bracket_extraction"}
                except json.JSONDecodeError:
                    break

    return {"success": False, "data": None, "method": "failed"}


def _validate_disease_result(data: dict, crop_name: str = None) -> dict:
    """Validate and normalize disease analysis result.

    Returns normalized dict with all required fields.
    Never infers disease from free text.
    """
    if not data or not isinstance(data, dict):
        return None

    result = {
        "crop": str(data.get("crop", crop_name or "unknown")),
        "health_status": "unable_to_determine",
        "disease_name": "Unable to determine",
        "severity": "unknown",
        "confidence": None,
        "visual_evidence": data.get("visual_evidence", []),
        "explanation": str(data.get("explanation", "")),
        "needs_follow_up": bool(data.get("needs_follow_up", False)),
        "needs_better_image": bool(data.get("needs_better_image", False)),
    }

    # Normalize health_status
    hs = str(data.get("health_status", "")).strip().lower().replace(" ", "_")
    if hs in ("healthy", "diseased", "unable_to_determine"):
        result["health_status"] = hs
    elif hs in ("uncertain", "insufficient_image_quality"):
        result["health_status"] = "unable_to_determine"
    else:
        result["health_status"] = "unable_to_determine"

    # Normalize disease_name
    dn = data.get("disease_name")
    if dn and str(dn).strip() and str(dn).strip().lower() not in ("none", "null", "n/a", ""):
        result["disease_name"] = str(dn).strip()
    elif result["health_status"] == "healthy":
        result["disease_name"] = "None"
    else:
        result["disease_name"] = "Unable to determine"

    # Normalize severity
    sev = str(data.get("severity", "")).strip().lower()
    valid_severities = {"none", "mild", "moderate", "severe", "unknown"}
    if sev in valid_severities:
        result["severity"] = sev
    else:
        severity_map = {"high": "severe", "low": "mild", "critical": "severe", "medium": "moderate"}
        result["severity"] = severity_map.get(sev, "unknown")

    # Normalize confidence: accept 0-1 or 0-100, normalize to 0-1
    raw_conf = data.get("confidence")
    if raw_conf is not None and isinstance(raw_conf, (int, float)):
        conf = float(raw_conf)
        if conf > 1.0:
            conf = conf / 100.0
        conf = max(0.0, min(1.0, conf))
        result["confidence"] = round(conf, 4)
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


def treatment_analysis(crop: str, disease: str, severity: str, weather: dict = None) -> dict:
    provider = get_provider()
    if not provider.is_available():
        return _ai_unavailable("AI_NOT_CONFIGURED")
    messages = [
        {"role": "system", "content": system_prompt("en")},
        {"role": "user", "content": treatment_prompt(crop, disease, severity, weather)},
    ]
    result = provider.chat(messages, temperature=0.4, max_tokens=1024)
    if not result["success"]:
        return _ai_unavailable(result.get("error_code", "AI_FAILED"), result.get("error"))
    parsed = _parse_json_response(result["content"])
    if not parsed:
        return _ai_unavailable("AI_INVALID_RESPONSE", "Could not parse treatment analysis")
    try:
        validated = TreatmentResult(**parsed)
        return {"available": True, "data": validated.model_dump()}
    except Exception:
        return {"available": True, "data": parsed}


def risk_analysis(crop: str, crop_stage: str, weather: dict, disease_info: dict = None) -> dict:
    provider = get_provider()
    if not provider.is_available():
        return _ai_unavailable("AI_NOT_CONFIGURED")
    messages = [
        {"role": "system", "content": system_prompt("en")},
        {"role": "user", "content": risk_analysis_prompt(crop, crop_stage, weather, disease_info)},
    ]
    result = provider.chat(messages, temperature=0.4, max_tokens=1024)
    if not result["success"]:
        return _ai_unavailable(result.get("error_code", "AI_FAILED"), result.get("error"))
    parsed = _parse_json_response(result["content"])
    if not parsed:
        return _ai_unavailable("AI_INVALID_RESPONSE", "Could not parse risk analysis")
    try:
        validated = RiskAnalysisResult(**parsed)
        return {"available": True, "data": validated.model_dump()}
    except Exception:
        return {"available": True, "data": parsed}


def irrigation_analysis(crop: str, crop_stage: str, weather: dict, soil_type: str = None) -> dict:
    provider = get_provider()
    if not provider.is_available():
        return _ai_unavailable("AI_NOT_CONFIGURED")
    messages = [
        {"role": "system", "content": system_prompt("en")},
        {"role": "user", "content": irrigation_prompt(crop, crop_stage, weather, soil_type)},
    ]
    result = provider.chat(messages, temperature=0.4, max_tokens=1024)
    if not result["success"]:
        return _ai_unavailable(result.get("error_code", "AI_FAILED"), result.get("error"))
    parsed = _parse_json_response(result["content"])
    if not parsed:
        return _ai_unavailable("AI_INVALID_RESPONSE", "Could not parse irrigation analysis")
    try:
        validated = IrrigationResult(**parsed)
        return {"available": True, "data": validated.model_dump()}
    except Exception:
        return {"available": True, "data": parsed}


def financial_analysis(expenses: list, harvests: list, crop: str) -> dict:
    provider = get_provider()
    if not provider.is_available():
        return _ai_unavailable("AI_NOT_CONFIGURED")
    messages = [
        {"role": "system", "content": system_prompt("en")},
        {"role": "user", "content": financial_analysis_prompt(expenses, harvests, crop)},
    ]
    result = provider.chat(messages, temperature=0.3, max_tokens=1024)
    if not result["success"]:
        return _ai_unavailable(result.get("error_code", "AI_FAILED"), result.get("error"))
    parsed = _parse_json_response(result["content"])
    if not parsed:
        return _ai_unavailable("AI_INVALID_RESPONSE", "Could not parse financial analysis")
    try:
        validated = FinancialResult(**parsed)
        return {"available": True, "data": validated.model_dump()}
    except Exception:
        return {"available": True, "data": parsed}


def what_if_analysis(current_decision: dict, scenario_changes: dict, context: dict) -> dict:
    provider = get_provider()
    if not provider.is_available():
        return _ai_unavailable("AI_NOT_CONFIGURED")
    messages = [
        {"role": "system", "content": system_prompt("en")},
        {"role": "user", "content": what_if_prompt(current_decision, scenario_changes, context)},
    ]
    result = provider.chat(messages, temperature=0.4, max_tokens=1024)
    if not result["success"]:
        return _ai_unavailable(result.get("error_code", "AI_FAILED"), result.get("error"))
    parsed = _parse_json_response(result["content"])
    if not parsed:
        return _ai_unavailable("AI_INVALID_RESPONSE", "Could not parse what-if analysis")
    try:
        validated = WhatIfResult(**parsed)
        return {"available": True, "data": validated.model_dump()}
    except Exception:
        return {"available": True, "data": parsed}


def farm_insights(context: dict, expenses_summary: dict = None, harvest_summary: dict = None) -> dict:
    provider = get_provider()
    if not provider.is_available():
        return _ai_unavailable("AI_NOT_CONFIGURED")
    messages = [
        {"role": "system", "content": system_prompt("en")},
        {"role": "user", "content": farm_insight_prompt(context, expenses_summary, harvest_summary)},
    ]
    result = provider.chat(messages, temperature=0.5, max_tokens=1024)
    if not result["success"]:
        return _ai_unavailable(result.get("error_code", "AI_FAILED"), result.get("error"))
    parsed = _parse_json_response(result["content"])
    if not parsed:
        return _ai_unavailable("AI_INVALID_RESPONSE", "Could not parse farm insights")
    try:
        validated = FarmInsightResult(**parsed)
        return {"available": True, "data": validated.model_dump()}
    except Exception:
        return {"available": True, "data": parsed}


def assistant_chat(context: dict, question: str, history: list = None, language: str = "en") -> dict:
    provider = get_provider()
    if not provider.is_available():
        return {
            "available": False,
            "answer": "AI Assistant is currently unavailable. Core HARVEX farm intelligence is still available.",
            "source": "fallback",
            "model": None,
        }
    messages = [
        {"role": "system", "content": system_prompt(language)},
        {"role": "user", "content": assistant_prompt(context, question)},
    ]
    result = provider.chat(messages, temperature=0.7, max_tokens=1024)
    if not result["success"]:
        return {
            "available": False,
            "answer": "AI Assistant is currently unavailable. Core HARVEX farm intelligence is still available.",
            "source": "fallback",
            "model": None,
            "error": result.get("error"),
        }
    return {
        "available": True,
        "answer": result["content"],
        "source": "ai",
        "model": result.get("model"),
        "response_time": result.get("response_time"),
    }


def check_provider_status() -> dict:
    provider = get_provider()
    return {
        "provider": "nvidia_nim",
        "available": provider.is_available(),
        "text_model": provider.text_model,
        "vision_model": provider.vision_model,
        "configured": bool(provider.text_api_key),
    }
