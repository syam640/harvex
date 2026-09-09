"""
NVIDIA Reasoning Provider — bounded AI attempt orchestrator.

Handles: primary model → retry → fallback model → deterministic fallback.
Maximum 3 AI attempts. After that, deterministic ranking with verified data only.
"""

import json
import logging
import re
import time
from typing import Optional, Dict, Any, List, Tuple

logger = logging.getLogger(__name__)


class AIAttemptResult:
    """Result of an AI reasoning attempt."""

    def __init__(
        self,
        success: bool,
        parsed_data: Optional[dict] = None,
        model_used: Optional[str] = None,
        provider: str = "nvidia_nim",
        fallback_used: bool = False,
        parse_method: Optional[str] = None,
        attempt_count: int = 0,
        total_duration_ms: int = 0,
        error: Optional[str] = None,
        validation_issues: Optional[List[str]] = None,
    ):
        self.success = success
        self.parsed_data = parsed_data
        self.model_used = model_used
        self.provider = provider
        self.fallback_used = fallback_used
        self.parse_method = parse_method
        self.attempt_count = attempt_count
        self.total_duration_ms = total_duration_ms
        self.error = error
        self.validation_issues = validation_issues or []


def extract_json_from_ai(raw: str) -> Tuple[Optional[dict], Optional[str]]:
    """Robust JSON extraction from AI response.
    Returns (parsed_dict, parse_method) or (None, None)."""
    if not raw or not raw.strip():
        return None, None

    text = raw.strip()

    # Case 1: Pure JSON
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed, "pure_json"
    except json.JSONDecodeError:
        pass

    # Case 2: Markdown fenced
    if "```" in text:
        fence_pattern = r"```(?:json)?\s*\n?(.*?)```"
        match = re.search(fence_pattern, text, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(1).strip())
                if isinstance(parsed, dict):
                    return parsed, "markdown_fenced"
            except json.JSONDecodeError:
                pass

    # Case 3: Extract JSON from surrounding text
    brace_match = re.search(r"\{[\s\S]*\}", text)
    if brace_match:
        try:
            parsed = json.loads(brace_match.group(0))
            if isinstance(parsed, dict):
                return parsed, "bracket_extraction"
        except json.JSONDecodeError:
            pass

    # Case 4: Try to fix common issues
    cleaned = text.replace("'", '"')
    cleaned = re.sub(r',\s*}', '}', cleaned)
    cleaned = re.sub(r',\s*]', ']', cleaned)
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed, "malformed_fix"
    except json.JSONDecodeError:
        pass

    return None, None


def validate_ai_crop_response(data: dict, valid_crop_ids: list) -> dict:
    """Validate AI crop research response against strict schema and crop catalog.
    Returns validation report."""
    issues = []

    if not isinstance(data, dict):
        return {"valid": False, "issues": ["Response is not a dict"]}

    status_val = data.get("recommendation_status")
    if status_val not in ["success", "partial"]:
        issues.append(f"Invalid recommendation_status: {status_val}")

    candidates = data.get("candidates", [])
    if not isinstance(candidates, list):
        issues.append("candidates is not a list")
        return {"valid": False, "issues": issues}

    if len(candidates) == 0:
        issues.append("candidates list is empty")

    valid_ids_set = set(valid_crop_ids)
    seen_ids = set()
    for i, c in enumerate(candidates):
        crop_id = c.get("crop_id", "")
        if not crop_id:
            issues.append(f"Candidate {i}: missing crop_id")
        elif crop_id not in valid_ids_set:
            issues.append(f"Candidate {i}: unknown crop_id '{crop_id}'")
        if crop_id in seen_ids:
            issues.append(f"Candidate {i}: duplicate crop_id '{crop_id}'")
        seen_ids.add(crop_id)

        # Check for fabricated measurements in reasoning
        reasoning = c.get("reasoning", {})
        if isinstance(reasoning, dict):
            for field in ["soil", "climate", "water", "irrigation", "season", "location", "risk"]:
                text = reasoning.get(field, "")
                if isinstance(text, str):
                    # Check for fabricated NPK/pH values
                    if re.search(r'\b(ph|nitrogen|phosphorus|potassium)\s*[=:]\s*\d+\.?\d*', text.lower()):
                        issues.append(f"Candidate {i}: potential fabricated measurement in {field} reasoning")
                    # Check for fabricated temperature/rainfall
                    if re.search(r'\b(temperature|rainfall|humidity)\s*[=:]\s*\d+\.?\d*', text.lower()):
                        issues.append(f"Candidate {i}: potential fabricated weather value in {field} reasoning")

    if len(candidates) > 20:
        issues.append(f"Too many candidates: {len(candidates)}")

    return {"valid": len(issues) == 0, "issues": issues}


def _call_nvidia_model(provider, messages: list, model: str, timeout: int = 60) -> dict:
    """Call NVIDIA model directly with a specific model override."""
    import requests as req

    if not provider.text_api_key:
        return {"success": False, "content": None, "model": model,
                "error": "API key not configured", "error_code": "NOT_CONFIGURED"}

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.3,
        "top_p": 0.95,
        "max_tokens": 2048,
        "stream": False,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    headers = {
        "Authorization": f"Bearer {provider.text_api_key}",
        "Content-Type": "application/json",
    }

    start = time.time()
    try:
        resp = req.post(
            f"{provider.text_base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=timeout,
        )
        elapsed = round(time.time() - start, 2)

        if resp.status_code == 401:
            return {"success": False, "content": None, "model": model,
                    "error": "Invalid API key", "error_code": "AUTH_FAILED"}
        if resp.status_code == 429:
            return {"success": False, "content": None, "model": model,
                    "error": "Rate limited", "error_code": "RATE_LIMITED"}
        if resp.status_code >= 500:
            return {"success": False, "content": None, "model": model,
                    "error": f"Server error {resp.status_code}", "error_code": "SERVER_ERROR"}

        resp.raise_for_status()
        data = resp.json()
        choice = data.get("choices", [{}])[0]
        content = choice.get("message", {}).get("content", "")

        if content and len(content.strip()) > 3:
            return {"success": True, "content": content.strip(), "model": model,
                    "response_time": elapsed}
        else:
            return {"success": False, "content": None, "model": model,
                    "error": "Empty response", "error_code": "EMPTY_RESPONSE"}

    except req.exceptions.Timeout:
        return {"success": False, "content": None, "model": model,
                "error": "Request timed out", "error_code": "TIMEOUT"}
    except req.exceptions.ConnectionError:
        return {"success": False, "content": None, "model": model,
                "error": "Connection failed", "error_code": "CONNECTION_ERROR"}
    except Exception as e:
        return {"success": False, "content": None, "model": model,
                "error": str(e), "error_code": "UNKNOWN_ERROR"}


def run_crop_reasoning(
    provider,
    messages: list,
    primary_model: str,
    fallback_model: str,
    valid_crop_ids: list,
    timeout: int = 60,
    max_retries: int = 2,
) -> AIAttemptResult:
    """Execute bounded AI reasoning: primary → retry → fallback → deterministic.

    Maximum 3 AI calls total:
      Attempt 1: primary model
      Attempt 2: primary model retry (if attempt 1 failed validation)
      Attempt 3: fallback model (if attempts 1+2 both failed)

    After 3 failures, returns unsuccessful for deterministic fallback.
    """
    overall_start = time.time()
    attempt_count = 0

    # --- ATTEMPT 1: Primary model ---
    attempt_count += 1
    result = _call_nvidia_model(provider, messages, primary_model, timeout)
    if result["success"]:
        parsed, parse_method = extract_json_from_ai(result["content"])
        if parsed:
            validation = validate_ai_crop_response(parsed, valid_crop_ids)
            if validation["valid"]:
                elapsed = int((time.time() - overall_start) * 1000)
                return AIAttemptResult(
                    success=True, parsed_data=parsed,
                    model_used=primary_model, fallback_used=False,
                    parse_method=parse_method, attempt_count=attempt_count,
                    total_duration_ms=elapsed,
                )
            else:
                logger.warning(f"Primary model attempt {attempt_count} validation failed: {validation['issues']}")
        else:
            logger.warning(f"Primary model attempt {attempt_count} JSON extraction failed")

    # --- ATTEMPT 2: Primary model retry (reuse existing messages, stricter) ---
    attempt_count += 1
    result2 = _call_nvidia_model(provider, messages, primary_model, timeout)
    if result2["success"]:
        parsed2, parse_method2 = extract_json_from_ai(result2["content"])
        if parsed2:
            validation2 = validate_ai_crop_response(parsed2, valid_crop_ids)
            if validation2["valid"]:
                elapsed = int((time.time() - overall_start) * 1000)
                return AIAttemptResult(
                    success=True, parsed_data=parsed2,
                    model_used=primary_model, fallback_used=False,
                    parse_method=parse_method2, attempt_count=attempt_count,
                    total_duration_ms=elapsed,
                )
            else:
                logger.warning(f"Primary retry attempt {attempt_count} validation failed: {validation2['issues']}")
        else:
            logger.warning(f"Primary retry attempt {attempt_count} JSON extraction failed")

    # --- ATTEMPT 3: Fallback model ---
    if fallback_model and fallback_model != primary_model:
        attempt_count += 1
        result3 = _call_nvidia_model(provider, messages, fallback_model, timeout)
        if result3["success"]:
            parsed3, parse_method3 = extract_json_from_ai(result3["content"])
            if parsed3:
                validation3 = validate_ai_crop_response(parsed3, valid_crop_ids)
                if validation3["valid"]:
                    elapsed = int((time.time() - overall_start) * 1000)
                    return AIAttemptResult(
                        success=True, parsed_data=parsed3,
                        model_used=fallback_model, fallback_used=True,
                        parse_method=parse_method3, attempt_count=attempt_count,
                        total_duration_ms=elapsed,
                    )
                else:
                    logger.warning(f"Fallback model attempt {attempt_count} validation failed: {validation3['issues']}")
            else:
                logger.warning(f"Fallback model attempt {attempt_count} JSON extraction failed")
    else:
        logger.info("No fallback model configured, skipping fallback attempt")

    # --- ALL AI ATTEMPTS FAILED ---
    elapsed = int((time.time() - overall_start) * 1000)
    return AIAttemptResult(
        success=False,
        attempt_count=attempt_count,
        total_duration_ms=elapsed,
        error="All AI attempts failed",
    )
