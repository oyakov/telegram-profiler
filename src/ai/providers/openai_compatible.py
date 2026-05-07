"""OpenAI-compatible LLM provider."""

import asyncio
import json
import time
import structlog
from typing import Any

from openai import AsyncOpenAI
from src.ai.providers.base import BaseLLMProvider

logger = structlog.get_logger()

# Global semaphore to limit concurrent requests to LLM provider
_llm_semaphore = asyncio.Semaphore(10)

class OpenAICompatibleProvider(BaseLLMProvider):
    def __init__(self, base_url: str, api_key: str, model_name: str, provider_name: str, default_temperature: float = 0.1, default_max_tokens: int = 4096):
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        self.model_name = model_name
        self.provider_name = provider_name
        self.default_temperature = default_temperature
        self.default_max_tokens = default_max_tokens

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict | None = None,
    ) -> dict[str, Any]:
        temp = temperature if temperature is not None else self.default_temperature
        max_tok = max_tokens if max_tokens is not None else self.default_max_tokens

        kwargs: dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temp,
            "max_tokens": max_tok,
        }
        if response_format:
            kwargs["response_format"] = response_format

        start = time.monotonic()
        async with _llm_semaphore:
            response = await self.client.chat.completions.create(**kwargs)
        elapsed_ms = int((time.monotonic() - start) * 1000)

        choice = response.choices[0]
        usage = response.usage

        result = {
            "content": choice.message.content,
            "model": self.model_name,
            "provider": self.provider_name,
            "prompt_tokens": usage.prompt_tokens if usage else None,
            "completion_tokens": usage.completion_tokens if usage else None,
            "processing_time_ms": elapsed_ms,
        }

        logger.info(
            "llm_completion",
            model=self.model_name,
            provider=self.provider_name,
            prompt_tokens=result["prompt_tokens"],
            completion_tokens=result["completion_tokens"],
            elapsed_ms=elapsed_ms,
        )

        return result

    async def structured_extraction(
        self,
        system_prompt: str,
        user_content: str,
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        response = await self.chat_completion(
            messages=messages,
            temperature=temperature,
            response_format={"type": "json_object"},
        )

        content = response["content"]

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
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