"""Unit tests for TelegramAuthService — PII sanitization in error logs."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.telegram.auth_service import TelegramAuthService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_factory_mock():
    """Return a TelegramClientFactory-shaped mock that always returns a mock client."""
    factory = MagicMock()
    client = AsyncMock()
    client.is_connected = MagicMock(return_value=True)
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    factory.get_client = AsyncMock(return_value=client)
    return factory, client


# ---------------------------------------------------------------------------
# sign_in — error logging should NOT contain phone number or session details
# ---------------------------------------------------------------------------

class TestSignInPIISanitization:
    @pytest.mark.asyncio
    async def test_sign_in_returns_generic_error_message(self):
        """sign_in must NOT echo exception text (which may contain phone) back to caller."""
        factory, client = _make_factory_mock()
        client.sign_in = AsyncMock(
            side_effect=Exception("SessionPasswordNeededError — internal_hash=abc123")
        )
        client.get_me = AsyncMock()

        svc = TelegramAuthService(factory)
        result = await svc.sign_in(
            phone="+9999999999", code="12345", phone_code_hash="hash_xyz"
        )

        assert result["status"] == "error"
        # The raw exception message must NOT appear in the response
        assert "internal_hash=abc123" not in result.get("message", "")
        assert "SessionPasswordNeededError" not in result.get("message", "")
        assert "+9999999999" not in result.get("message", "")

    @pytest.mark.asyncio
    async def test_sign_in_flood_wait_returns_generic_message(self):
        """FloodWait errors often contain countdown seconds — must not leak."""
        factory, client = _make_factory_mock()
        client.sign_in = AsyncMock(
            side_effect=Exception("A wait of 3600 seconds is required (caused by SignInRequest)")
        )

        svc = TelegramAuthService(factory)
        result = await svc.sign_in(
            phone="+1234567890", code="00000", phone_code_hash="phash"
        )

        assert result["status"] == "error"
        assert "3600" not in result.get("message", "")
        assert "SignInRequest" not in result.get("message", "")

    @pytest.mark.asyncio
    async def test_sign_in_success_returns_user_id(self):
        """Happy-path: successful sign-in returns status=success with user_id."""
        factory, client = _make_factory_mock()
        me = MagicMock()
        me.id = 123456789
        client.sign_in = AsyncMock(return_value=me)
        client.get_me = AsyncMock(return_value=me)
        factory.save_session = AsyncMock()

        svc = TelegramAuthService(factory)
        result = await svc.sign_in(
            phone="+1234567890", code="11111", phone_code_hash="good_hash"
        )

        assert result["status"] == "success"
        assert result["user_id"] == 123456789


# ---------------------------------------------------------------------------
# sign_in_2fa — similar guarantees
# ---------------------------------------------------------------------------

class TestSignIn2FAPIISanitization:
    @pytest.mark.asyncio
    async def test_sign_in_2fa_returns_generic_on_bad_password(self):
        """sign_in_2fa must not echo PasswordHashInvalidError details to caller."""
        factory, client = _make_factory_mock()
        client.sign_in = AsyncMock(
            side_effect=Exception("PasswordHashInvalidError — hash=abc123secret")
        )

        svc = TelegramAuthService(factory)
        result = await svc.sign_in_2fa("wrongpassword")

        assert result["status"] == "error"
        assert "hash=abc123secret" not in result.get("message", "")
        assert "PasswordHashInvalidError" not in result.get("message", "")

    @pytest.mark.asyncio
    async def test_sign_in_2fa_success(self):
        factory, client = _make_factory_mock()
        me = MagicMock()
        me.id = 987654321
        client.sign_in = AsyncMock(return_value=me)
        client.get_me = AsyncMock(return_value=me)
        factory.save_session = AsyncMock()

        svc = TelegramAuthService(factory)
        result = await svc.sign_in_2fa("correct_password")

        assert result["status"] == "success"
        assert result["user_id"] == 987654321
