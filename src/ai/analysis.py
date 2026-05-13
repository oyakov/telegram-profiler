"""Unified AI text analysis utilities — embeddings, deduplication, heuristics."""

from __future__ import annotations

import re
import structlog
import math
from typing import Optional

from openai import AsyncOpenAI
from pydantic import BaseModel
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.db.models import Contact

logger = structlog.get_logger()


# ========== Embedding Generation ==========


def _get_embed_client() -> tuple[AsyncOpenAI, str, int]:
    """Return (client, model_name, dimensions) based on provider config."""
    settings = get_settings()

    if settings.embed_provider == "lmstudio":
        client = AsyncOpenAI(
            base_url=settings.lmstudio_base_url,
            api_key="lm-studio",
            timeout=300.0,
        )
        model = settings.lmstudio_embed_model
    else:
        client = AsyncOpenAI(
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            api_key=settings.google_api_key,
            timeout=300.0,
        )
        model = settings.google_embed_model

    return client, model, settings.embed_dimensions


async def generate_embedding(text: str) -> list[float]:
    """Generate a single embedding vector for the given text."""
    client, model, dimensions = _get_embed_client()

    response = await client.embeddings.create(
        model=model,
        input=text,
        dimensions=dimensions,
    )

    vector = response.data[0].embedding
    logger.debug("embedding_generated", model=model, dimensions=len(vector))
    return vector


async def generate_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a batch of texts."""
    if not texts:
        return []

    client, model, dimensions = _get_embed_client()

    all_vectors = []
    batch_size = 100

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = await client.embeddings.create(
            model=model,
            input=batch,
            dimensions=dimensions,
        )
        sorted_data = sorted(response.data, key=lambda x: x.index)
        all_vectors.extend([d.embedding for d in sorted_data])

    logger.info("embeddings_batch_generated", count=len(all_vectors), model=model)
    return all_vectors


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)


# ========== Heuristic Detection ==========


class HeuristicAdResult(BaseModel):
    """Result of heuristic ad detection."""

    is_ad: bool
    username: Optional[str] = None
    summary: str = ""
    evidence: str = ""
    confidence: float = 0.0


# Keywords indicating commercial activity
AD_KEYWORDS = [
    r"реклам[аыу]",
    r"продам",
    r"услуги",
    r"предлагаю",
    r"ищу",
    r"куплю",
    r"цена",
    r"прайс",
    r"стоимость",
    r"контакты",
    r"пишите",
    r"в лс",
    r"директ",
    r"заказ",
    r"аренда",
    r"сдам",
    r"обучение",
    r"курс",
    r"подбор",
    r"помощь",
    r"viber",
    r"whatsapp",
    r"телефон",
    r"номер",
]

# High value business keywords
BUSINESS_KEYWORDS = [
    r"dev",
    r"software",
    r"ai",
    r"agency",
    r"invest",
    r"partnership",
    r"hiring",
    r"разработка",
    r"программист",
    r"инвестиции",
    r"партнерство",
    r"вакансия",
]


def detect_ad_heuristically(text: str) -> Optional[HeuristicAdResult]:
    """Detect ads using keyword heuristics (no LLM required)."""
    if not text or len(text) < 20:
        return None

    text_lower = text.lower()

    # Look for @username or t.me links
    usernames = re.findall(r"@([a-zA-Z0-9_]{5,32})", text)
    links = re.findall(r"t\.me/([a-zA-Z0-9_]{5,32})", text)

    contacts = list(set(usernames + links))
    primary_contact = contacts[0] if contacts else None

    # Count keyword hits
    ad_matches = [kw for kw in AD_KEYWORDS if re.search(kw, text_lower)]
    biz_matches = [kw for kw in BUSINESS_KEYWORDS if re.search(kw, text_lower)]

    # Decision logic
    if (primary_contact and len(ad_matches) >= 1) or (len(ad_matches) >= 3):
        confidence = 0.5 + (0.1 * len(ad_matches)) + (0.2 * len(biz_matches))
        if primary_contact:
            confidence += 0.2

        confidence = min(0.95, confidence)

        summary = " ".join(ad_matches[:3]) + (" (Business)" if biz_matches else "")
        evidence = text[:100] + "..."

        return HeuristicAdResult(
            is_ad=True,
            username=primary_contact,
            summary=f"Heuristic Match: {summary}",
            evidence=evidence,
            confidence=confidence,
        )

    return None
