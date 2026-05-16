"""API key authentication middleware.

When API_KEY is set in the environment, every request to /api/* must carry:
    Authorization: Bearer <api_key>

Leave API_KEY empty for local development (auth is skipped with a warning).
"""

from __future__ import annotations

import hmac
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.core.config import get_settings

logger = structlog.get_logger()

# Only the liveness probe is unconditionally exempt.
# /docs, /redoc, /openapi.json, /metrics are gated when API_KEY is set so that
# internal API schema and Prometheus data aren't publicly accessible.
_ALWAYS_EXEMPT = frozenset({"/", "/api/stats/health"})


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Require a static Bearer token on all non-exempt paths."""

    async def dispatch(self, request: Request, call_next):
        settings = get_settings()

        # Liveness probe — always pass through
        if request.url.path in _ALWAYS_EXEMPT:
            return await call_next(request)

        # Auth disabled — pass through (local dev only)
        if not settings.api_key:
            return await call_next(request)

        # Validate Bearer token using constant-time comparison to prevent timing attacks
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            if hmac.compare_digest(token, settings.api_key):
                return await call_next(request)

        logger.warning(
            "unauthorized_request",
            path=request.url.path,
            ip=getattr(request.client, "host", "unknown"),
        )
        return JSONResponse(
            status_code=401,
            content={"detail": "Unauthorized"},
            headers={"WWW-Authenticate": "Bearer"},
        )
