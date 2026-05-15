"""API key authentication middleware.

When API_KEY is set in the environment, every request to /api/* must carry:
    Authorization: Bearer <api_key>

Leave API_KEY empty for local development (auth is skipped with a warning).
"""

from __future__ import annotations

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.core.config import get_settings

logger = structlog.get_logger()

# Paths that never require a key (health probe, docs)
_EXEMPT = frozenset({"/", "/docs", "/redoc", "/openapi.json", "/metrics"})

_api_key_warned = False


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Require a static Bearer token on all non-exempt paths."""

    async def dispatch(self, request: Request, call_next):
        global _api_key_warned
        settings = get_settings()

        # Auth disabled — warn once per worker process, then pass through
        if not settings.api_key:
            if not _api_key_warned:
                _api_key_warned = True
                logger.warning(
                    "api_key_not_configured",
                    msg="API_KEY is not set — all endpoints are publicly accessible. "
                        "Set API_KEY in your .env for production.",
                )
            return await call_next(request)

        # Exempt paths
        if request.url.path in _EXEMPT:
            return await call_next(request)

        # Validate Bearer token
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            if token == settings.api_key:
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
