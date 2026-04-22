"""Unified LLM client — switches between Google Gemini and LM Studio."""

from __future__ import annotations

import asyncio
import json
import time
import structlog
from typing import Any

from openai import AsyncOpenAI

from src.core.config import get_settings

logger = structlog.get_logger()

# Global semaphore to limit concurrent requests to LLM provider
# Limits to 10 concurrent calls by default to prevent rate limiting
_llm_semaphore = asyncio.Semaphore(10)


def _get_client() -> tuple[AsyncOpenAI, str]:
    """Return (client, model_name) based on provider config."""
    settings = get_settings()

    if settings.llm_provider == "lmstudio":
        client = AsyncOpenAI(
            base_url=settings.lmstudio_base_url,
            api_key="lm-studio",  # LM Studio doesn't validate keys
        )
        model = settings.lmstudio_llm_model
    else:
        # Google Gemini via OpenAI-compatible endpoint
        client = AsyncOpenAI(
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            api_key=settings.google_api_key,
        )
        model = settings.google_llm_model

    return client, model


async def chat_completion(
    messages: list[dict[str, str]],
    temperature: float | None = None,
    max_tokens: int | None = None,
    response_format: dict | None = None,
) -> dict[str, Any]:
    """Send a chat completion request. Returns parsed response with usage stats."""
    settings = get_settings()
    client, model = _get_client()

    temp = temperature if temperature is not None else settings.llm_temperature
    max_tok = max_tokens if max_tokens is not None else settings.llm_max_tokens

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temp,
        "max_tokens": max_tok,
    }
    if response_format:
        kwargs["response_format"] = response_format

    start = time.monotonic()
    async with _llm_semaphore:
        response = await client.chat.completions.create(**kwargs)
    elapsed_ms = int((time.monotonic() - start) * 1000)

    choice = response.choices[0]
    usage = response.usage

    result = {
        "content": choice.message.content,
        "model": model,
        "provider": settings.llm_provider,
        "prompt_tokens": usage.prompt_tokens if usage else None,
        "completion_tokens": usage.completion_tokens if usage else None,
        "processing_time_ms": elapsed_ms,
    }

    logger.info(
        "llm_completion",
        model=model,
        provider=settings.llm_provider,
        prompt_tokens=result["prompt_tokens"],
        completion_tokens=result["completion_tokens"],
        elapsed_ms=elapsed_ms,
    )

    return result


async def structured_extraction(
    system_prompt: str,
    user_content: str,
    temperature: float = 0.1,
) -> dict[str, Any]:
    """Extract structured JSON from text using the LLM.

    Returns the parsed JSON and usage metadata.
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    response = await chat_completion(
        messages=messages,
        temperature=temperature,
        response_format={"type": "json_object"},
    )

    content = response["content"]

    # Parse the JSON response
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        # Try to extract JSON from markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        parsed = json.loads(content)

    return {
        "data": parsed,
        "model": response["model"],
        "provider": response["provider"],
        "prompt_tokens": response["prompt_tokens"],
        "completion_tokens": response["completion_tokens"],
        "processing_time_ms": response["processing_time_ms"],
    }
