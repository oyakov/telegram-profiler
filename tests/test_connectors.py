"""Connector tests — Excel parsing, Whisper client."""

from __future__ import annotations

import os
import tempfile

import pandas as pd
import pytest
from unittest.mock import AsyncMock, patch


def test_excel_column_mapping():
    """Test auto-detection of column names."""
    from src.connectors.excel_connector import COLUMN_MAP

    assert COLUMN_MAP["email"] == "email"
    assert COLUMN_MAP["firstname"] == "first_name"
    assert COLUMN_MAP["company"] == "company"
    assert COLUMN_MAP["имя"] == "first_name"  # Russian
    assert COLUMN_MAP["телефон"] == "phone"


def test_excel_parse_csv():
    """Test CSV file parsing with column auto-detection."""
    df = pd.DataFrame({
        "first_name": ["Alice", "Bob"],
        "last_name": ["Smith", "Jones"],
        "email": ["alice@test.com", "bob@test.com"],
        "company": ["Acme", "TechCo"],
    })

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
        df.to_csv(f, index=False)
        temp_path = f.name

    try:
        parsed = pd.read_csv(temp_path)
        parsed.columns = [c.strip().lower().replace(" ", "_") for c in parsed.columns]
        assert "first_name" in parsed.columns
        assert "email" in parsed.columns
        assert len(parsed) == 2
    finally:
        os.unlink(temp_path)


def test_excel_parse_xlsx():
    """Test XLSX file parsing."""
    df = pd.DataFrame({
        "Name": ["Charlie"],
        "Email": ["charlie@test.com"],
        "Company": ["StartupXYZ"],
    })

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        df.to_excel(f.name, index=False)
        temp_path = f.name

    try:
        parsed = pd.read_excel(temp_path)
        parsed.columns = [c.strip().lower().replace(" ", "_") for c in parsed.columns]
        assert "name" in parsed.columns
        assert "email" in parsed.columns
        assert len(parsed) == 1
    finally:
        os.unlink(temp_path)


def test_whisper_client_init():
    """Test WhisperClient initialization."""
    from src.connectors.whisper_client import WhisperClient

    client = WhisperClient(base_url="http://localhost:9000")
    assert client.base_url == "http://localhost:9000"


@pytest.mark.asyncio
async def test_whisper_health_check_mock():
    """Test Whisper health check with mocked HTTP."""
    from src.connectors.whisper_client import WhisperClient

    client = WhisperClient(base_url="http://test:9000")

    mock_response = AsyncMock()
    mock_response.status_code = 200

    mock_http = AsyncMock()
    mock_http.get = AsyncMock(return_value=mock_response)
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_http):
        result = await client.health_check()
        assert result is True


def test_sync_result_dataclass():
    """Test SyncResult dataclass."""
    from src.connectors.base import SyncResult

    result = SyncResult(connector="test")
    assert result.status == "success"
    assert result.messages_fetched == 0
    assert result.errors == []

    result.errors.append("test error")
    result.status = "error"
    assert result.status == "error"
    assert len(result.errors) == 1
