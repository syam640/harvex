"""NVIDIA NIM AI provider — OpenAI-compatible API."""

import time
import logging
import requests
from typing import Optional
from app.services.ai.base import AIProviderBase
from app.core.config import (
    NVIDIA_API_KEY, NVIDIA_BASE_URL, NVIDIA_TEXT_MODEL,
    NVIDIA_VISION_API_KEY, NVIDIA_VISION_MODEL,
    AI_REQUEST_TIMEOUT, AI_MAX_RETRIES,
)

logger = logging.getLogger(__name__)


class NVIDIAProvider(AIProviderBase):
    """NVIDIA NIM provider using OpenAI-compatible API."""

    def __init__(self):
        self.text_api_key = NVIDIA_API_KEY
        self.text_base_url = NVIDIA_BASE_URL
        self.text_model = NVIDIA_TEXT_MODEL
        self.vision_api_key = NVIDIA_VISION_API_KEY
        self.vision_model = NVIDIA_VISION_MODEL
        self.timeout = AI_REQUEST_TIMEOUT
        self.max_retries = AI_MAX_RETRIES

    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        response_format: Optional[dict] = None,
    ) -> dict:
        """Send chat completion via NVIDIA NIM."""
        if not self.text_api_key:
            return {
                "success": False,
                "content": None,
                "reasoning": None,
                "model": self.text_model,
                "error": "NVIDIA API key not configured",
                "error_code": "AI_PROVIDER_NOT_CONFIGURED",
            }

        payload = {
            "model": self.text_model,
            "messages": messages,
            "temperature": temperature,
            "top_p": 0.95,
            "max_tokens": max_tokens,
            "stream": False,
            "chat_template_kwargs": {"enable_thinking": False},
        }
        if response_format:
            payload["response_format"] = response_format

        headers = {
            "Authorization": f"Bearer {self.text_api_key}",
            "Content-Type": "application/json",
        }

        last_error = None
        for attempt in range(self.max_retries + 1):
            start = time.time()
            try:
                resp = requests.post(
                    f"{self.text_base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                )
                elapsed = round(time.time() - start, 2)

                if resp.status_code == 401:
                    return {
                        "success": False, "content": None, "reasoning": None,
                        "model": self.text_model,
                        "error": "Invalid NVIDIA API key",
                        "error_code": "AI_AUTH_FAILED",
                    }
                if resp.status_code == 429:
                    if attempt < self.max_retries:
                        time.sleep(2 ** attempt)
                        continue
                    return {
                        "success": False, "content": None, "reasoning": None,
                        "model": self.text_model,
                        "error": "Rate limited by NVIDIA",
                        "error_code": "AI_RATE_LIMITED",
                    }
                if resp.status_code >= 500:
                    last_error = f"Server error {resp.status_code}"
                    if attempt < self.max_retries:
                        time.sleep(2 ** attempt)
                        continue
                    return {
                        "success": False, "content": None, "reasoning": None,
                        "model": self.text_model,
                        "error": last_error,
                        "error_code": "AI_SERVER_ERROR",
                    }

                resp.raise_for_status()
                data = resp.json()

                choice = data.get("choices", [{}])[0]
                message = choice.get("message", {})
                content = message.get("content", "")
                reasoning = getattr(message, "reasoning_content", None)

                if content and len(content.strip()) > 3:
                    return {
                        "success": True,
                        "content": content.strip(),
                        "reasoning": reasoning,
                        "model": self.text_model,
                        "error": None,
                        "error_code": None,
                        "response_time": elapsed,
                    }
                else:
                    return {
                        "success": False, "content": None, "reasoning": None,
                        "model": self.text_model,
                        "error": "Empty response from model",
                        "error_code": "AI_EMPTY_RESPONSE",
                    }

            except requests.exceptions.Timeout:
                last_error = "Request timed out"
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)
                    continue
            except requests.exceptions.ConnectionError:
                return {
                    "success": False, "content": None, "reasoning": None,
                    "model": self.text_model,
                    "error": "Cannot connect to NVIDIA API",
                    "error_code": "AI_CONNECTION_ERROR",
                }
            except Exception as e:
                last_error = str(e)
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)
                    continue

        return {
            "success": False, "content": None, "reasoning": None,
            "model": self.text_model,
            "error": last_error or "Unknown error",
            "error_code": "AI_MAX_RETRIES_EXCEEDED",
        }

    def vision(
        self,
        image_url: str,
        prompt: str,
        max_tokens: int = 1024,
    ) -> dict:
        """Send vision request via NVIDIA NIM."""
        if not self.vision_api_key:
            return {
                "success": False,
                "content": None,
                "model": self.vision_model,
                "error": "NVIDIA Vision API key not configured",
                "error_code": "AI_VISION_NOT_CONFIGURED",
            }

        payload = {
            "model": self.vision_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url},
                        },
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                }
            ],
            "max_tokens": max_tokens,
            "temperature": 0.3,
            "stream": False,
        }

        headers = {
            "Authorization": f"Bearer {self.vision_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        last_error = None
        vision_timeout = min(self.timeout, 90)  # Vision models need more time
        for attempt in range(self.max_retries + 1):
            start = time.time()
            try:
                resp = requests.post(
                    f"{self.text_base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=vision_timeout,
                )
                elapsed = round(time.time() - start, 2)

                if resp.status_code == 401:
                    return {
                        "success": False, "content": None,
                        "model": self.vision_model,
                        "error": "Invalid Vision API key",
                        "error_code": "AI_VISION_AUTH_FAILED",
                    }
                if resp.status_code == 429:
                    if attempt < self.max_retries:
                        time.sleep(2 ** attempt)
                        continue
                    return {
                        "success": False, "content": None,
                        "model": self.vision_model,
                        "error": "Rate limited",
                        "error_code": "AI_VISION_RATE_LIMITED",
                    }

                resp.raise_for_status()
                data = resp.json()

                choice = data.get("choices", [{}])[0]
                content = choice.get("message", {}).get("content", "")

                if content and len(content.strip()) > 3:
                    return {
                        "success": True,
                        "content": content.strip(),
                        "model": self.vision_model,
                        "error": None,
                        "error_code": None,
                        "response_time": elapsed,
                    }
                else:
                    return {
                        "success": False, "content": None,
                        "model": self.vision_model,
                        "error": "Vision model returned empty response",
                        "error_code": "AI_VISION_EMPTY",
                    }

            except requests.exceptions.Timeout:
                last_error = "Vision request timed out"
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)
                    continue
            except requests.exceptions.ConnectionError:
                return {
                    "success": False, "content": None,
                    "model": self.vision_model,
                    "error": "Cannot connect to NVIDIA Vision API",
                    "error_code": "AI_VISION_CONNECTION_ERROR",
                }
            except Exception as e:
                last_error = str(e)
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)
                    continue

        return {
            "success": False, "content": None,
            "model": self.vision_model,
            "error": last_error or "Unknown error",
            "error_code": "AI_VISION_MAX_RETRIES_EXCEEDED",
        }

    def is_available(self) -> bool:
        """Check if NVIDIA API is configured."""
        return bool(self.text_api_key)
