"""Tests for AI analysis utilities (cosine similarity, embeddings)."""

import math
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.ai.analysis import cosine_similarity, generate_embedding


# ──────────────────────────────────────────────
# cosine_similarity — pure math, no mocks needed
# ──────────────────────────────────────────────

def test_cosine_similarity_identical_vectors():
    v = [1.0, 0.5, 0.0, -0.5]
    assert cosine_similarity(v, v) == pytest.approx(1.0, abs=1e-9)


def test_cosine_similarity_orthogonal_vectors():
    v1 = [1.0, 0.0]
    v2 = [0.0, 1.0]
    assert cosine_similarity(v1, v2) == pytest.approx(0.0, abs=1e-9)


def test_cosine_similarity_opposite_vectors():
    v1 = [1.0, 0.0]
    v2 = [-1.0, 0.0]
    assert cosine_similarity(v1, v2) == pytest.approx(-1.0, abs=1e-9)


def test_cosine_similarity_zero_vector_returns_zero():
    """Division by zero guard: returns 0.0 instead of raising."""
    v1 = [0.0, 0.0]
    v2 = [1.0, 0.5]
    assert cosine_similarity(v1, v2) == 0.0
    assert cosine_similarity(v2, v1) == 0.0


def test_cosine_similarity_known_value():
    # [1, 0] vs [1, 1]/√2  →  dot=1, |a|=1, |b|=√2  →  1/√2 ≈ 0.7071
    v1 = [1.0, 0.0]
    v2 = [1.0, 1.0]
    expected = 1.0 / math.sqrt(2)
    assert cosine_similarity(v1, v2) == pytest.approx(expected, rel=1e-6)


# ──────────────────────────────────────────────
# generate_embedding — mock the OpenAI client
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_embedding_returns_vector():
    """generate_embedding should return the vector from the provider."""
    fake_vector = [0.1] * 768

    mock_provider = AsyncMock()
    mock_provider.generate_embedding = AsyncMock(return_value=fake_vector)

    with patch("src.ai.analysis.get_embedding_provider", return_value=mock_provider):
        result = await generate_embedding("hello world")

    assert result == fake_vector
    mock_provider.generate_embedding.assert_awaited_once_with("hello world")


@pytest.mark.asyncio
async def test_generate_embedding_passes_text_to_api():
    """generate_embedding should forward the text to the provider."""
    fake_vector = [0.0] * 512

    mock_provider = AsyncMock()
    mock_provider.generate_embedding = AsyncMock(return_value=fake_vector)

    with patch("src.ai.analysis.get_embedding_provider", return_value=mock_provider):
        await generate_embedding("specific query text")

    mock_provider.generate_embedding.assert_awaited_once_with("specific query text")
