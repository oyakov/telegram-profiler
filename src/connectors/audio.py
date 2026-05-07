"""Audio processing utilities for voice transcription."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from src.connectors.whisper_client import WhisperClient


class AudioProcessor:
    """Unified audio processing for voice notes and recordings."""

    def __init__(self, base_url: Optional[str] = None):
        self.whisper = WhisperClient(base_url=base_url)

    async def transcribe(
        self,
        file_path: str | Path,
        language: Optional[str] = None,
    ) -> str:
        """Transcribe audio file to text."""
        return await self.whisper.transcribe(file_path, language=language)

    async def health_check(self) -> bool:
        """Check if audio services are available."""
        return await self.whisper.health_check()
