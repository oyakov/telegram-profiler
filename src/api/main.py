"""FastAPI application — Networking Brain CRM backend."""

from __future__ import annotations

import os

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import structlog

from src.api.routers import (
    contacts, messages, telegram, leads,
    search, system, settings, pipeline, tracking, sync, projects
)
from src.api.middleware.auth import APIKeyMiddleware
from src.core.logging import setup_logging
from src.core.config import get_settings
from prometheus_fastapi_instrumentator import Instrumentator

setup_logging()
app_settings = get_settings()
logger = structlog.get_logger()

if not app_settings.api_key:
    logger.warning(
        "api_key_not_configured",
        msg="API_KEY is not set — all endpoints are publicly accessible. "
            "Set API_KEY in your .env for production.",
    )

# --- Rate limiter (shared across routers via app.state) ---
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

app = FastAPI(
    title="Networking Brain",
    description="Personal CRM with AI-powered contact extraction and semantic search",
    version="1.1.0",
    # Always disable auto-generated docs URLs — they are gated by APIKeyMiddleware
    # when API_KEY is set, so there's no need to hide them at the FastAPI level.
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- Prometheus (internal only — nginx blocks /metrics from outside) ---
Instrumentator().instrument(app).expose(app, include_in_schema=False, endpoint="/metrics")

# --- Exception handlers ---

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Log full details internally, return generic message to client
    logger.error("validation_error", errors=exc.errors(), path=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Invalid request data"},
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", error=type(exc).__name__, path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

# --- CORS ---
_cors_origins = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:3005,http://localhost:5173").split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "X-Database"],
)

# --- Auth (must be added AFTER CORS so preflight OPTIONS passes through) ---
app.add_middleware(APIKeyMiddleware)

# --- Request logging ---
@app.middleware("http")
async def log_requests(request: Request, call_next):
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        method=request.method,
        path=request.url.path,
        db=request.headers.get("X-Database", "default"),
    )
    response = await call_next(request)
    logger.info("request_finished", status_code=response.status_code)
    return response

# ========== Include Routers ==========

API_PREFIX = "/api"

app.include_router(contacts.router, prefix=API_PREFIX)
app.include_router(messages.router, prefix=API_PREFIX)
app.include_router(telegram.router, prefix=API_PREFIX)
app.include_router(leads.router, prefix=API_PREFIX)
app.include_router(search.router, prefix=API_PREFIX)
app.include_router(system.router, prefix=API_PREFIX)
app.include_router(settings.router, prefix=API_PREFIX)
app.include_router(pipeline.router, prefix=f"{API_PREFIX}/connectors")
app.include_router(tracking.router, prefix=API_PREFIX)
app.include_router(sync.router, prefix=API_PREFIX)
app.include_router(projects.router, prefix=API_PREFIX)

@app.get("/")
async def root():
    return {"status": "ok"}
