"""
HARVEX Vision Output Hardening Tests.

Tests robust JSON extraction, schema validation, retry logic, and failure states.

Run:  python3 -m pytest tests/test_vision_hardening.py -v
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from app.services.ai.ai_service import _extract_json_with_debug, _validate_disease_result


# ============================================================
# 1. PURE JSON
# ============================================================

def test_pure_json():
    """Pure JSON response is parsed correctly."""
    content = '{"crop":"tomato","health_status":"diseased","disease_name":"Early Blight","severity":"moderate","confidence":0.85,"visual_evidence":["brown spots"],"explanation":"Visible symptoms","needs_follow_up":true,"needs_better_image":false}'
    result = _extract_json_with_debug(content)
    assert result["success"] is True
    assert result["method"] == "pure_json"
    assert result["data"]["health_status"] == "diseased"
    assert result["data"]["disease_name"] == "Early Blight"


# ============================================================
# 2. MARKDOWN JSON
# ============================================================

def test_markdown_json():
    """JSON wrapped in markdown code fences is parsed."""
    content = '```json\n{"crop":"tomato","health_status":"healthy","disease_name":null,"severity":"None","confidence":0.95,"visual_evidence":[],"explanation":"No symptoms","needs_follow_up":false,"needs_better_image":false}\n```'
    result = _extract_json_with_debug(content)
    assert result["success"] is True
    assert result["method"] == "markdown_fenced"
    assert result["data"]["health_status"] == "healthy"


# ============================================================
# 3. FENCED JSON (no language tag)
# ============================================================

def test_fenced_json():
    """JSON wrapped in plain code fences is parsed."""
    content = '```\n{"crop":"rice","health_status":"diseased","disease_name":"Blast","severity":"mild","confidence":0.7,"visual_evidence":["leaf lesions"],"explanation":"Symptoms visible","needs_follow_up":true,"needs_better_image":false}\n```'
    result = _extract_json_with_debug(content)
    assert result["success"] is True
    assert result["method"] == "markdown_fenced"


# ============================================================
# 4. JSON WITH SURROUNDING TEXT
# ============================================================

def test_json_with_surrounding_text():
    """JSON surrounded by text is extracted via bracket matching."""
    content = 'Here is my analysis:\n{"crop":"chilli","health_status":"healthy","disease_name":null,"severity":"None","confidence":0.9,"visual_evidence":[],"explanation":"Plant healthy","needs_follow_up":false,"needs_better_image":false}\nPlease let me know if you need more info.'
    result = _extract_json_with_debug(content)
    assert result["success"] is True
    assert result["method"] == "bracket_extraction"
    assert result["data"]["crop"] == "chilli"


# ============================================================
# 5. MALFORMED JSON
# ============================================================

def test_malformed_json():
    """Malformed JSON returns failure."""
    content = '{"crop":"tomato","health_status":"diseased",,,"disease_name":"Blight"}'
    result = _extract_json_with_debug(content)
    assert result["success"] is False
    assert result["method"] == "failed"


# ============================================================
# 6. FREE TEXT (no JSON)
# ============================================================

def test_free_text():
    """Free text with no JSON returns failure."""
    content = 'The plant appears to have early blight based on the brown spots visible on the leaves. I recommend monitoring and applying fungicide if symptoms worsen.'
    result = _extract_json_with_debug(content)
    assert result["success"] is False
    assert result["method"] == "failed"


# ============================================================
# 7. MISSING CONFIDENCE
# ============================================================

def test_missing_confidence():
    """Missing confidence field is normalized to null."""
    data = {
        "crop": "tomato",
        "health_status": "diseased",
        "disease_name": "Blight",
        "severity": "mild",
        "visual_evidence": ["spots"],
        "explanation": "Symptoms visible",
    }
    result = _validate_disease_result(data, "tomato")
    assert result["confidence"] is None


# ============================================================
# 8. CONFIDENCE > 1 (0-100 scale)
# ============================================================

def test_confidence_over_1():
    """Confidence > 1 is normalized to 0-1 scale."""
    data = {
        "crop": "tomato",
        "health_status": "diseased",
        "disease_name": "Blight",
        "severity": "moderate",
        "confidence": 85,
        "visual_evidence": ["spots"],
        "explanation": "Visible",
    }
    result = _validate_disease_result(data, "tomato")
    assert result["confidence"] == 0.85


# ============================================================
# 9. CONFIDENCE < 0
# ============================================================

def test_confidence_negative():
    """Negative confidence is clamped to 0."""
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
# 10. INVALID HEALTH STATUS
# ============================================================

def test_invalid_health_status():
    """Invalid health_status is normalized to unable_to_determine."""
    data = {
        "crop": "tomato",
        "health_status": "maybe_healthy",
        "disease_name": "Blight",
        "severity": "mild",
        "confidence": 0.8,
        "visual_evidence": [],
        "explanation": "",
    }
    result = _validate_disease_result(data, "tomato")
    assert result["health_status"] == "unable_to_determine"


# ============================================================
# 11. HEALTHY RESULT NORMALIZATION
# ============================================================

def test_healthy_normalization():
    """Healthy result normalizes disease_name to None and severity to none."""
    data = {
        "crop": "tomato",
        "health_status": "healthy",
        "disease_name": "None",
        "severity": "unknown",
        "confidence": 0.95,
        "visual_evidence": [],
        "explanation": "Plant looks healthy",
    }
    result = _validate_disease_result(data, "tomato")
    assert result["health_status"] == "healthy"
    assert result["disease_name"] == "None"
    assert result["severity"] == "none"
    assert result["confidence"] == 0.95


# ============================================================
# 12. UNABLE TO DETERMINE NORMALIZATION
# ============================================================

def test_unable_to_determine_normalization():
    """Unable to determine normalizes all fields appropriately."""
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


# ============================================================
# 13. EMPTY RESPONSE
# ============================================================

def test_empty_response():
    """Empty response returns failure."""
    result = _extract_json_with_debug("")
    assert result["success"] is False
    assert result["method"] == "empty"

    result = _extract_json_with_debug(None)
    assert result["success"] is False
    assert result["method"] == "empty"


# ============================================================
# 14. NVIDIA TIMEOUT
# ============================================================

def test_nvidia_timeout():
    """NVIDIA timeout returns proper error."""
    from app.services.ai.ai_service import disease_analysis

    with patch("app.services.ai.ai_service.get_provider") as mock_get:
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.vision.return_value = {
            "success": False,
            "content": None,
            "model": "meta/llama-3.2-11b-vision-instruct",
            "error": "Vision request timed out",
            "error_code": "AI_VISION_MAX_RETRIES_EXCEEDED",
        }
        mock_get.return_value = mock_provider

        result = disease_analysis("tomato", "data:image/jpeg;base64,abc123")
        assert result["available"] is False
        assert result["error_code"] == "AI_VISION_MAX_RETRIES_EXCEEDED"


# ============================================================
# 15. NVIDIA RATE LIMIT
# ============================================================

def test_nvidia_rate_limit():
    """NVIDIA rate limit returns proper error."""
    from app.services.ai.ai_service import disease_analysis

    with patch("app.services.ai.ai_service.get_provider") as mock_get:
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.vision.return_value = {
            "success": False,
            "content": None,
            "model": "meta/llama-3.2-11b-vision-instruct",
            "error": "Rate limited",
            "error_code": "AI_VISION_RATE_LIMITED",
        }
        mock_get.return_value = mock_provider

        result = disease_analysis("tomato", "data:image/jpeg;base64,abc123")
        assert result["available"] is False
        assert result["error_code"] == "AI_VISION_RATE_LIMITED"


# ============================================================
# 16. NVIDIA 401 AUTH FAILURE
# ============================================================

def test_nvidia_auth_failure():
    """NVIDIA 401 returns proper error."""
    from app.services.ai.ai_service import disease_analysis

    with patch("app.services.ai.ai_service.get_provider") as mock_get:
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.vision.return_value = {
            "success": False,
            "content": None,
            "model": "meta/llama-3.2-11b-vision-instruct",
            "error": "Invalid Vision API key",
            "error_code": "AI_VISION_AUTH_FAILED",
        }
        mock_get.return_value = mock_provider

        result = disease_analysis("tomato", "data:image/jpeg;base64,abc123")
        assert result["available"] is False
        assert result["error_code"] == "AI_VISION_AUTH_FAILED"


# ============================================================
# SAFETY TEST: Free text must NOT become diagnosis
# ============================================================

def test_free_text_safety():
    """Free text describing disease MUST NOT automatically become diagnosis.

    This is the critical safety test. The model must return structured JSON.
    Free text like 'Looks like early blight...' must NOT be parsed into
    disease_name='Early Blight' without proper JSON structure.
    """
    free_text = "Looks like early blight based on the concentric rings visible on the leaves. I would recommend applying copper-based fungicide."

    # JSON extraction must fail
    result = _extract_json_with_debug(free_text)
    assert result["success"] is False

    # If we try to validate None as a disease result, it should return None
    validated = _validate_disease_result(result["data"], "tomato")
    assert validated is None


# ============================================================
# RETRY LOGIC TEST
# ============================================================

def test_retry_logic():
    """When first attempt returns free text, retry request is sent."""
    from app.services.ai.ai_service import disease_analysis

    free_text = "The plant appears healthy with no visible disease symptoms."

    valid_json = {
        "crop": "tomato",
        "health_status": "healthy",
        "disease_name": None,
        "severity": "None",
        "confidence": 0.9,
        "visual_evidence": [],
        "explanation": "No symptoms visible",
        "needs_follow_up": False,
        "needs_better_image": False,
    }

    with patch("app.services.ai.ai_service.get_provider") as mock_get:
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.vision_model = "meta/llama-3.2-11b-vision-instruct"

        # First call returns free text, second call returns valid JSON
        mock_provider.vision.side_effect = [
            {"success": True, "content": free_text, "model": "meta/llama-3.2-11b-vision-instruct", "response_time": 10.0},
            {"success": True, "content": json.dumps(valid_json), "model": "meta/llama-3.2-11b-vision-instruct", "response_time": 10.0},
        ]
        mock_get.return_value = mock_provider

        result = disease_analysis("tomato", "data:image/jpeg;base64,abc123")
        assert result["available"] is True
        assert result["data"]["health_status"] == "healthy"
        assert result["debug"]["retry_used"] is True
        assert result["debug"]["initial_parse_success"] is False
        assert result["debug"]["final_parse_success"] is True
        assert mock_provider.vision.call_count == 2


# ============================================================
# DOUBLE RETRY FAILURE TEST
# ============================================================

def test_double_retry_failure():
    """When both attempts fail, returns Unable to determine."""
    from app.services.ai.ai_service import disease_analysis

    free_text_1 = "The plant looks diseased."
    free_text_2 = "I think there might be some spots."

    with patch("app.services.ai.ai_service.get_provider") as mock_get:
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.vision_model = "meta/llama-3.2-11b-vision-instruct"

        mock_provider.vision.side_effect = [
            {"success": True, "content": free_text_1, "model": "meta/llama-3.2-11b-vision-instruct", "response_time": 10.0},
            {"success": True, "content": free_text_2, "model": "meta/llama-3.2-11b-vision-instruct", "response_time": 10.0},
        ]
        mock_get.return_value = mock_provider

        result = disease_analysis("tomato", "data:image/jpeg;base64,abc123")
        assert result["available"] is False
        assert result["error_code"] == "AI_VISION_PARSE_FAILED"
        assert result["debug"]["retry_used"] is True
        assert result["debug"]["final_parse_success"] is False
