"""Embedding generation and search tests."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_generate_embedding():
    """Test single embedding generation."""
    mock_response = AsyncMock()
    mock_response.data = [AsyncMock(embedding=[0.1] * 1024)]

    with patch("src.ai.embeddings._get_embed_client") as mock_client:
        client = AsyncMock()
        client.embeddings.create = AsyncMock(return_value=mock_response)
        mock_client.return_value = (client, "test-model", 1024)

        from src.ai.embeddings import generate_embedding
        result = await generate_embedding("test text")

        assert len(result) == 1024
        assert result[0] == 0.1


@pytest.mark.asyncio
async def test_generate_embeddings_batch():
    """Test batch embedding generation."""
    mock_data = [AsyncMock(embedding=[0.1 * i] * 1024, index=i) for i in range(3)]
    mock_response = AsyncMock()
    mock_response.data = mock_data

    with patch("src.ai.embeddings._get_embed_client") as mock_client:
        client = AsyncMock()
        client.embeddings.create = AsyncMock(return_value=mock_response)
        mock_client.return_value = (client, "test-model", 1024)

        from src.ai.embeddings import generate_embeddings_batch
        result = await generate_embeddings_batch(["text1", "text2", "text3"])

        assert len(result) == 3


def test_cosine_similarity():
    """Test cosine similarity computation."""
    from src.ai.embeddings import cosine_similarity

    # Identical vectors → 1.0
    a = [1.0, 0.0, 0.0]
    assert cosine_similarity(a, a) == pytest.approx(1.0)

    # Orthogonal vectors → 0.0
    b = [0.0, 1.0, 0.0]
    assert cosine_similarity(a, b) == pytest.approx(0.0)

    # Opposite vectors → -1.0
    c = [-1.0, 0.0, 0.0]
    assert cosine_similarity(a, c) == pytest.approx(-1.0)

    # Zero vector → 0.0
    z = [0.0, 0.0, 0.0]
    assert cosine_similarity(a, z) == pytest.approx(0.0)
