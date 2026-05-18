"""Telegram authentication service implementation."""

import asyncio
import structlog
from typing import Optional
from telethon.errors import (
    AuthRestartError, 
    AuthKeyUnregisteredError, 
    SessionPasswordNeededError
)
from src.services.telegram.base import TelegramAuthInterface
from src.services.telegram.client_factory import TelegramClientFactory

logger = structlog.get_logger()

class TelegramAuthService(TelegramAuthInterface):
    """Handles Telegram authentication and session management."""

    def __init__(self, client_factory: TelegramClientFactory):
        self.factory = client_factory

    async def is_authorized(self) -> bool:
        """Check if the current session is authorized."""
        client = await self.factory.get_client()
        try:
            await client.connect()
            return await client.is_user_authorized()
        except Exception as e:
            logger.error("telegram_auth_check_failed", error_type=type(e).__name__)
            return False
        finally:
            await client.disconnect()

    async def send_code_request(self, phone: str) -> str:
        """Send a login code request to the given phone number."""
        for attempt in range(2):
            client = await self.factory.get_client()
            try:
                await client.connect()
                if not client.is_connected():
                    raise Exception("Failed to connect to Telegram servers")

                result = await client.send_code_request(phone)
                await self.factory.save_session()
                return result.phone_code_hash
            except (AuthRestartError, AuthKeyUnregisteredError) as e:
                logger.warning("telegram_stale_session_detected", phone=phone, attempt=attempt)
                await self.factory.delete_session()
                self.factory.clear_cache()
                if attempt == 1:
                    raise Exception("Telegram session is invalid. Please try again.") from e
            finally:
                await client.disconnect()

    async def sign_in(self, phone: str, code: str, phone_code_hash: str) -> dict:
        """Sign in with phone, code, and hash."""
        client = await self.factory.get_client()
        try:
            await client.connect()
            if not client.is_connected():
                return {"status": "error", "message": "Failed to connect to Telegram servers"}

            await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
            
            me = await client.get_me()
            await self.factory.save_session(user_id=str(me.id))
            
            return {"status": "success", "user_id": me.id}
        except SessionPasswordNeededError:
            return {"status": "requires_2fa"}
        except Exception as e:
            # Log error_type only — str(e) may include the phone number or
            # Telethon FloodWait details which constitute PII in log aggregators.
            logger.error("sign_in_error", error_type=type(e).__name__)
            return {"status": "error", "message": "Authentication failed. Please try again."}
        finally:
            await client.disconnect()

    async def sign_in_2fa(self, password: str) -> dict:
        """Sign in with 2FA password."""
        client = await self.factory.get_client()
        try:
            await client.connect()
            await client.sign_in(password=password)
            
            me = await client.get_me()
            await self.factory.save_session(user_id=str(me.id))
            
            return {"status": "success", "user_id": me.id}
        except Exception as e:
            # Log type only — 2FA errors can carry session/hash identifiers.
            logger.error("sign_in_2fa_error", error_type=type(e).__name__)
            return {"status": "error", "message": "2FA authentication failed. Please try again."}
        finally:
            await client.disconnect()

    async def logout(self):
        """Log out and delete session."""
        client = await self.factory.get_client()
        try:
            await client.connect()
            await client.log_out()
        finally:
            await self.factory.delete_session()
            await client.disconnect()
