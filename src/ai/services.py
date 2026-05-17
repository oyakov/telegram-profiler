"""Unified AI services for extraction and analysis."""

from __future__ import annotations

import asyncio
import structlog
from typing import Any, Optional

import tiktoken

from src.ai.providers.factory import get_llm_provider
from src.core.config import ConfigurationProvider
from src.ai.schemas import (
    ContactExtraction,
    LeadExtraction,
    ChannelDeepAnalysis,
    CONTACT_SYSTEM_PROMPT,
    LEAD_SYSTEM_PROMPT,
    DEEP_ANALYSIS_SYSTEM_PROMPT,
)

logger = structlog.get_logger()


class ExtractionService:
    """Service for running various LLM-based extractions on text."""

    def __init__(self, session: Optional[Any] = None):
        self.config = ConfigurationProvider(session)
        self._provider = None

    async def _get_provider(self):
        if not self._provider:
            self._provider = get_llm_provider()
        return self._provider

    async def _get_model_name(self):
        provider = await self._get_provider()
        return provider.model_name

    def _chunk_text(self, text: str, model_name: str, max_tokens: int = 3000, overlap_tokens: int = 200) -> list[str]:
        """Split text into overlapping chunks using tiktoken."""
        try:
            enc = tiktoken.encoding_for_model(model_name)
        except Exception:
            enc = tiktoken.get_encoding("cl100k_base")

        tokens = enc.encode(text)
        if len(tokens) <= max_tokens:
            return [text]

        step = max(max_tokens - overlap_tokens, 1)
        chunks = []
        start = 0
        while start < len(tokens):
            end = start + max_tokens
            chunks.append(enc.decode(tokens[start:end]))
            start += step
        return chunks

    async def extract(
        self,
        text: str,
        extraction_type: str = "contacts",
        source_context: str = "",
        max_chunk_tokens: int = 3000,
    ) -> tuple[list[Any], dict[str, Any]]:
        """Run extraction on text for the specified type."""
        
        prompts = {
            "contacts": CONTACT_SYSTEM_PROMPT,
            "leads": LEAD_SYSTEM_PROMPT,
            "deep_analysis": DEEP_ANALYSIS_SYSTEM_PROMPT,
        }
        
        schemas = {
            "contacts": ContactExtraction,
            "leads": LeadExtraction,
            "deep_analysis": ChannelDeepAnalysis,
        }

        system_prompt = prompts.get(extraction_type)
        if not system_prompt:
            raise ValueError(f"Unknown extraction type: {extraction_type}")

        model_name = await self._get_model_name()
        chunks = self._chunk_text(text, model_name, max_tokens=max_chunk_tokens)
        
        all_items = []
        metadata = {
            "chunks": len(chunks),
            "tokens": 0,
            "time_ms": 0,
            "model": model_name,
        }

        provider = await self._get_provider()

        async def _extract_chunk(chunk_text: str) -> dict[str, Any]:
            user_content = chunk_text
            if source_context:
                user_content = f"[Source: {source_context}]\n\n{chunk_text}"
            
            return await provider.structured_extraction(
                system_prompt=system_prompt,
                user_content=user_content,
            )

        # Run all chunks in parallel
        tasks = [_extract_chunk(chunk) for chunk in chunks]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error("extraction_chunk_failed", error=str(result), extraction_type=extraction_type, chunk_index=i)
                continue

            try:
                data = result.get("data", {})
                items_raw = data.get("items", [])
                
                # Fallback for LLMs using older field names
                if not items_raw:
                    for key in ["contacts", "buyers", "leads"]:
                        if key in data:
                            items_raw = data[key]
                            break
                
                item_schema = schemas[extraction_type]
                for item_data in items_raw:
                    try:
                        # Standardize legacy field names
                        if "ad_content_summary" in item_data and "content_summary" not in item_data:
                            item_data["content_summary"] = item_data.pop("ad_content_summary")
                        
                        all_items.append(item_schema(**item_data))
                    except Exception as ve:
                        logger.warning("item_validation_failed", error=str(ve), data=item_data)

                metadata["tokens"] += result.get("prompt_tokens", 0) + result.get("completion_tokens", 0)
                metadata["time_ms"] = max(metadata["time_ms"], result.get("processing_time_ms", 0))
                
            except Exception as e:
                logger.error("extraction_result_parsing_failed", error=str(e), extraction_type=extraction_type)

        return all_items, metadata
