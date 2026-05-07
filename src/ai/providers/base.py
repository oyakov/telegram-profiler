"""Base provider interface for LLM operations."""

from abc import ABC, abstractmethod
from typing import Any

class BaseLLMProvider(ABC):
    @abstractmethod
    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict | None = None,
    ) -> dict[str, Any]:
        """Send a chat completion request."""
        pass

    @abstractmethod
    async def structured_extraction(
        self,
        system_prompt: str,
        user_content: str,
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        """Extract structured JSON from text using the LLM."""
        pass