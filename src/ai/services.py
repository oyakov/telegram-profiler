"""Unified AI services for extraction and analysis."""

from __future__ import annotations

import asyncio
import structlog
from typing import Any, Optional, Type, TypeVar, Generic, Union

import tiktoken
from pydantic import BaseModel, Field

from src.ai.llm_client import structured_extraction

logger = structlog.get_logger()

T = TypeVar("T")


class BaseExtraction(BaseModel):
    """Base class for all extraction schemas."""
    pass


class ContactExtraction(BaseExtraction):
    """Structured contact information."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    position: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    telegram_username: Optional[str] = None
    linkedin_url: Optional[str] = None
    interests: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    context: Optional[str] = None
    facts: list[str] = Field(default_factory=list)
    confidence: float = 0.0


class LeadExtraction(BaseExtraction):
    """Structured data for lead generation across different niches."""
    username: str = Field(..., description="Telegram username without @")
    display_name: Optional[str] = Field(None, description="Name of the lead or brand")
    content_summary: str = Field(..., description="Summary of what they are offering or looking for")
    category: str = Field(..., description="Niche: IT, RealEstate, Legal, Business, Services, Crypto, Travel, Other")
    lead_type: str = Field(..., description="Role: Supplier (offering/selling) or Consumer (looking for/buying)")
    lead_quality: int = Field(5, description="Quality score 1-10")
    confidence: float = Field(0.0, description="Confidence score 0.0-1.0")
    evidence_quote: str = Field(..., description="Original text fragment as evidence")


class ChannelDeepAnalysis(BaseExtraction):
    """Structured data for deep analysis of channel messages."""
    topics: list[str] = Field(default_factory=list, description="Main topics discussed in the message")
    mentioned_companies: list[str] = Field(default_factory=list, description="Names of companies mentioned")
    mentioned_products: list[str] = Field(default_factory=list, description="Names of products or services mentioned")
    sentiment: str = Field(..., description="Overall sentiment: positive, negative, neutral, or mixed")


class ExtractionResult(BaseModel, Generic[T]):
    """Wrapper around extraction results with metadata."""
    items: list[T] = Field(default_factory=list)
    summary: Optional[str] = None
    is_relevant: bool = True


# --- Prompts ---

CONTACT_SYSTEM_PROMPT = """You are a contact information extraction assistant. Extract ALL contacts mentioned in the text.
For each contact, extract: first_name, last_name, company, position, email, phone, telegram_username (no @), linkedin_url, interests, skills, context, facts, confidence.
Rules: No hallucinations. Only explicit info. Phone numbers with country code. Confidence 0.0-1.0.
Respond with JSON matching the schema: {"items": [{"first_name": ...}], "summary": "...", "is_relevant": true}"""

LEAD_SYSTEM_PROMPT = """You are an elite lead generation assistant for Belgrade/Serbia market. 
Identify individuals or brands that are either OFFERING (Supplier) or LOOKING FOR (Consumer) products/services.
Categories: 
- IT (Software, hardware, dev, design)
- RealEstate (Rent, buy, sell, apartments)
- Legal (VNZH, permits, documents, law)
- Business (Investment, partnerships, B2B)
- Services (Beauty, repair, transport, cleaning)
- Crypto (Exchange, OTC, mining)
- Travel (Tickets, tours, visas)

Extract for each lead: username (no @), display_name, content_summary, category, lead_type (Supplier/Consumer), lead_quality (1-10), confidence (0.0-1.0), evidence_quote.
Respond with JSON matching the schema: {"items": [{"username": ...}], "summary": "...", "is_relevant": boolean}"""

DEEP_ANALYSIS_SYSTEM_PROMPT = """You are a professional market intelligence analyst. Analyze Telegram channel messages for key insights.
Extract: topics, mentioned_companies, mentioned_products, sentiment, and confidence (0.0-1.0).
Respond with JSON matching the schema: {"items": [{"topics": [...], "sentiment": "..."}], "summary": "...", "is_relevant": true}"""


class ExtractionService:
    """Service for running various LLM-based extractions on text."""

    def __init__(self, model: str = "gpt-4o"):
        self.model = model

    def _chunk_text(self, text: str, max_tokens: int = 3000, overlap_tokens: int = 200) -> list[str]:
        """Split text into overlapping chunks using tiktoken."""
        try:
            enc = tiktoken.encoding_for_model(self.model)
        except Exception:
            enc = tiktoken.get_encoding("cl100k_base")

        tokens = enc.encode(text)
        if len(tokens) <= max_tokens:
            return [text]

        chunks = []
        start = 0
        while start < len(tokens):
            end = start + max_tokens
            chunks.append(enc.decode(tokens[start:end]))
            start = end - overlap_tokens
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

        chunks = self._chunk_text(text, max_tokens=max_chunk_tokens)
        all_items = []
        metadata = {
            "chunks": len(chunks),
            "tokens": 0,
            "time_ms": 0,
            "model": self.model,
        }

        async def _extract_chunk(chunk_text: str) -> dict[str, Any]:
            user_content = chunk_text
            if source_context:
                user_content = f"[Source: {source_context}]\n\n{chunk_text}"
            
            return await structured_extraction(
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
                # Dynamic model validation
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
                        # Fix for legacy ad_content_summary -> content_summary
                        if "ad_content_summary" in item_data and "content_summary" not in item_data:
                            item_data["content_summary"] = item_data.pop("ad_content_summary")
                        
                        all_items.append(item_schema(**item_data))
                    except Exception as ve:
                        logger.warning("item_validation_failed", error=str(ve), data=item_data)

                metadata["tokens"] += result.get("prompt_tokens", 0) + result.get("completion_tokens", 0)
                metadata["time_ms"] = max(metadata["time_ms"], result.get("processing_time_ms", 0))
                
            except Exception as e:
                logger.error("extraction_result_parsing_failed", error=str(e), extraction_type=extraction_type)
                continue

        return all_items, metadata
