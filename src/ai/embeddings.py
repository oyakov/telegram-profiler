"""Embedding generation — Google or LM Studio."""

from __future__ import annotations

import structlog
from typing import Union

from openai import AsyncOpenAI

from src.core.config import get_settings

logger = structlog.get_logger()


def _get_embed_client() -> tuple[AsyncOpenAI, str, int]:
    """Return (client, model_name, dimensions) based on provider config."""
    settings = get_settings()

    if settings.embed_provider == "lmstudio":
        client = AsyncOpenAI(
            base_url=settings.lmstudio_base_url,
            api_key="lm-studio",
            timeout=300.0
        )
        model = settings.lmstudio_embed_model
    else:
        client = AsyncOpenAI(
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            api_key=settings.google_api_key,
            timeout=300.0
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

    # Process in sub-batches of 100 (API limit)
    all_vectors = []
    batch_size = 100

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = await client.embeddings.create(
            model=model,
            input=batch,
            dimensions=dimensions,
        )
        # Sort by index to maintain order
        sorted_data = sorted(response.data, key=lambda x: x.index)
        all_vectors.extend([d.embedding for d in sorted_data])

    logger.info("embeddings_batch_generated", count=len(all_vectors), model=model)
    return all_vectors


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    import math

    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)
