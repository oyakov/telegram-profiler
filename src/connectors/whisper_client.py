"""Whisper ASR client — sends audio to the Whisper REST API."""

from __future__ import annotations

import asyncio
import structlog
from pathlib import Path
from typing import Optional

import httpx

from src.core.config import get_settings

logger = structlog.get_logger()


class WhisperClient:
    """HTTP client for the Whisper ASR web service."""

    def __init__(self, base_url: Optional[str] = None):
        settings = get_settings()
        self.base_url = (base_url or settings.whisper_url).rstrip("/")

    async def transcribe(
        self,
        file_path: str | Path,
        language: Optional[str] = None,
    ) -> str:
        """Transcribe an audio file to text.

        Args:
            file_path: Path to the audio file (wav, mp3, ogg, etc.)
            language: Language code (e.g. 'en', 'ru'). None = auto-detect.

        Returns:
            Transcribed text string.
        """
        settings = get_settings()
        lang = language or settings.whisper_language
        if lang == "auto":
            lang = None

        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        url = f"{self.base_url}/asr"
        params = {"output": "json"}
        if lang:
            params["language"] = lang

        # Read file bytes in a thread-pool executor to avoid blocking the event loop
        loop = asyncio.get_running_loop()
        audio_bytes = await loop.run_in_executor(None, file_path.read_bytes)

        async with httpx.AsyncClient(timeout=300.0) as client:
            files = {"audio_file": (file_path.name, audio_bytes, "audio/mpeg")}
            response = await client.post(url, params=params, files=files)

            response.raise_for_status()
            data = response.json()

        text = data.get("text", "").strip()
        logger.info(
            "whisper_transcription",
            file=file_path.name,
            language=lang or "auto",
            text_length=len(text),
        )

        return text

    async def health_check(self) -> bool:
        """Check if the Whisper service is available."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/")
                return response.status_code == 200
        except Exception:
            return False
