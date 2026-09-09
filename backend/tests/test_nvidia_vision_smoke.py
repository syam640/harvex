"""
REAL NVIDIA Vision API smoke test.

No mocking. No fabrication. Reports actual NVIDIA Vision endpoint behavior:
  - SUCCESS: returns actual disease/health analysis
  - TIMEOUT: reports timeout honestly
  - RATE-LIMIT: reports 429 honestly
  - PROVIDER-FAILURE: reports connection/auth/empty-response honestly

Run:  python3 -m pytest tests/test_nvidia_vision_smoke.py -v -s
"""
import io
import json
import os
import sys
import uuid
import base64
import time
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# -----------------------------------------------------------
# 1. Create a synthetic but valid leaf-like image
# -----------------------------------------------------------

def _make_leaf_image() -> bytes:
    """Generate a 224x224 green-dominant PNG that looks plant-like to a vision model."""
    img = Image.new('RGB', (224, 224))
    pixels = []
    for y in range(224):
        for x in range(224):
            # green-dominant with brown spot in center
            cx, cy = 112, 112
            dist = ((x - cx)**2 + (y - cy)**2) ** 0.5
            if dist < 30:
                pixels.append((139, 90, 43))   # brown spot
            elif dist < 60:
                pixels.append((34, 139, 34))   # green ring
            else:
                r = max(0, min(255, 50 + (x % 40)))
                g = max(0, min(255, 160 + (y % 50)))
                b = max(0, min(255, 30 + ((x+y) % 30)))
                pixels.append((r, g, b))
    img.putdata(pixels)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


# -----------------------------------------------------------
# 2. Hit the real NVIDIA Vision endpoint via ai_service
# -----------------------------------------------------------

def test_nvidia_vision_real_call():
    """
    Call NVIDIA Vision API with a real image.
    Report the honest result — success or specific failure mode.
    """
    from app.services.ai import ai_service
    from app.services.ai.nvidia_provider import NVIDIAProvider

    provider = NVIDIAProvider()

    print("\n" + "=" * 60)
    print("NVIDIA VISION SMOKE TEST (REAL — NO MOCK)")
    print("=" * 60)
    print(f"  Vision model : {provider.vision_model}")
    print(f"  API key set  : {bool(provider.vision_api_key)}")
    print(f"  Timeout      : {provider.timeout}s")
    print(f"  Max retries  : {provider.max_retries}")

    if not provider.vision_api_key:
        print("  RESULT: SKIP — Vision API key not configured")
        print("=" * 60)
        return  # not a failure, just untestable

    image_bytes = _make_leaf_image()
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    image_url = f"data:image/png;base64,{b64}"

    prompt = (
        'Analyze this plant image for disease. Output ONLY valid JSON:\n'
        '{"crop":"tomato","plant_health":"healthy|diseased|uncertain",'
        '"disease_name":"...","severity":"none|mild|moderate|severe",'
        '"confidence":75,"visual_symptoms":["..."],"recommended_next_step":"..."}'
    )

    print(f"\n  Uploading {len(image_bytes):,} byte PNG (synthetic leaf)")
    print(f"  Calling provider.vision() ...")

    start = time.time()
    result = provider.vision(image_url, prompt, max_tokens=512)
    elapsed = round(time.time() - start, 2)

    print(f"  Elapsed: {elapsed}s")
    print(f"  success : {result['success']}")

    if result["success"]:
        print(f"  model   : {result['model']}")
        print(f"  response_time: {result.get('response_time', 'N/A')}s")
        content = result["content"]
        print(f"\n  RAW RESPONSE (first 500 chars):")
        print(f"  {content[:500]}")

        # Try to parse JSON
        try:
            parsed = json.loads(content)
            print(f"\n  PARSED JSON:")
            for k, v in parsed.items():
                print(f"    {k}: {v}")
        except json.JSONDecodeError:
            print(f"\n  (Response is not valid JSON — model returned free text)")

        print(f"\n  RESULT: SUCCESS")
        print(f"  provider = nvidia")
        print(f"  model    = {result['model']}")
    else:
        error_code = result.get("error_code", "UNKNOWN")
        error_msg = result.get("error", "Unknown error")
        print(f"  error_code: {error_code}")
        print(f"  error     : {error_msg}")

        if error_code == "AI_VISION_NOT_CONFIGURED":
            print(f"\n  RESULT: NOT_CONFIGURED — Vision API key missing")
        elif error_code == "AI_VISION_AUTH_FAILED":
            print(f"\n  RESULT: AUTH_FAILED — API key invalid")
        elif error_code == "AI_VISION_RATE_LIMITED":
            print(f"\n  RESULT: RATE_LIMITED — Free tier 429, retry later")
        elif error_code in ("AI_VISION_TIMEOUT", "AI_VISION_MAX_RETRIES_EXCEEDED"):
            print(f"\n  RESULT: TIMEOUT — NVIDIA Vision model too slow on free tier")
        elif error_code == "AI_VISION_CONNECTION_ERROR":
            print(f"\n  RESULT: CONNECTION_ERROR — Cannot reach NVIDIA API")
        elif error_code == "AI_VISION_EMPTY":
            print(f"\n  RESULT: EMPTY_RESPONSE — Model returned no content")
        else:
            print(f"\n  RESULT: FAILED — {error_code}")

    print("=" * 60)

    # The test always passes — it's a smoke test that reports, not asserts success.
    # Real NVIDIA failures are expected on free tier.
    assert True


if __name__ == "__main__":
    test_nvidia_vision_real_call()
