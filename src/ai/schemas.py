"""Extraction schemas for AI-powered data extraction."""

from __future__ import annotations

from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

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
    content_summary: str = Field(
        ..., description="Summary of what they are offering or looking for"
    )
    category: str = Field(
        ...,
        description="Niche: IT, RealEstate, Legal, Business, Services, Crypto, Travel, Other",
    )
    lead_type: str = Field(
        ..., description="Role: Supplier (offering/selling) or Consumer (looking for/buying)"
    )
    lead_quality: int = Field(5, description="Quality score 1-10")
    confidence: float = Field(0.0, description="Confidence score 0.0-1.0")
    evidence_quote: str = Field(..., description="Original text fragment as evidence")


class ChannelDeepAnalysis(BaseExtraction):
    """Structured data for deep analysis of channel messages."""

    topics: list[str] = Field(
        default_factory=list, description="Main topics discussed in the message"
    )
    mentioned_companies: list[str] = Field(
        default_factory=list, description="Names of companies mentioned"
    )
    mentioned_products: list[str] = Field(
        default_factory=list, description="Names of products or services mentioned"
    )
    sentiment: str = Field(
        ...,
        description="Overall sentiment: positive, negative, neutral, or mixed",
    )


class ExtractionResult(BaseModel, Generic[T]):
    """Wrapper around extraction results with metadata."""

    items: list[T] = Field(default_factory=list)
    summary: Optional[str] = None
    is_relevant: bool = True


# ========== System Prompts ==========

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
