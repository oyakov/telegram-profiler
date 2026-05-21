"""OpenAI-compatible embedding provider."""

import structlog
from typing import List
from openai import AsyncOpenAI
from src.ai.providers.embeddings.base import BaseEmbeddingProvider

logger = structlog.get_logger()

class OpenAICompatibleEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, base_url: str, api_key: str, model_name: str, dimensions: int,
                 timeout: float = 30.0):
        # timeout applies per HTTP request — critical for search latency.
        # Use a short value (e.g. 8 s) for real-time search, longer for batch workers.
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key, timeout=timeout)
        self.model_name = model_name
        self.dimensions = dimensions

    async def generate_embedding(self, text: str) -> List[float]:
        response = await self.client.embeddings.create(
            model=self.model_name,
            input=text,
            dimensions=self.dimensions
        )
        return response.data[0].embedding

    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        all_vectors = []
        batch_size = 100

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = await self.client.embeddings.create(
                model=self.model_name,
                input=batch,
                dimensions=self.dimensions
            )
            sorted_data = sorted(response.data, key=lambda x: x.index)
            all_vectors.extend([d.embedding for d in sorted_data])
            
        return all_vectors
