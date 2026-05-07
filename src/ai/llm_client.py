"""Unified LLM client — delegates to provider factory for backward compatibility."""

from __future__ import annotations
from typing import Any
from src.ai.providers.factory import get_llm_provider

async def chat_completion(
    messages: list[dict[str, str]],
    temperature: float | None = None,
    max_tokens: int | None = None,
    response_format: dict | None = None,
) -> dict[str, Any]:
    """Send a chat completion request. Returns parsed response with usage stats."""
    provider = get_llm_provider()
    return await provider.chat_completion(
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format=response_format
    )

async def structured_extraction(
    system_prompt: str,
    user_content: str,
    temperature: float = 0.1,
) -> dict[str, Any]:
    """Extract structured JSON from text using the LLM."""
    provider = get_llm_provider()
    return await provider.structured_extraction(
        system_prompt=system_prompt,
        user_content=user_content,
        temperature=temperature
    )
