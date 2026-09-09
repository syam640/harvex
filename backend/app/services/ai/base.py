"""Abstract AI provider interface."""

from abc import ABC, abstractmethod
from typing import Optional


class AIProviderBase(ABC):
    """Base class for AI providers. All providers must implement these methods."""

    @abstractmethod
    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        response_format: Optional[dict] = None,
    ) -> dict:
        """
        Send a chat completion request.

        Returns:
            {
                "success": True/False,
                "content": "...",
                "reasoning": "...",  # if model supports thinking
                "model": "...",
                "error": "...",  # if failed
                "error_code": "..."  # if failed
            }
        """
        pass

    @abstractmethod
    def vision(
        self,
        image_url: str,
        prompt: str,
        max_tokens: int = 1024,
    ) -> dict:
        """
        Send a vision request with an image.

        Returns:
            {
                "success": True/False,
                "content": "...",
                "model": "...",
                "error": "..."
            }
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is configured and reachable."""
        pass
