"""FastAPI application — Networking Brain CRM backend."""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
import time
import uuid

from src.api.routers import (
    contacts, messages, telegram, leads,
    search, system, settings, pipeline, tracking
)
import structlog
from src.core.logging import setup_logging
from src.core.config import get_settings
from prometheus_fastapi_instrumentator import Instrumentator

setup_logging()
app_settings = get_settings()
logger = structlog.get_logger()

app = FastAPI(
    title="Networking Brain",
    description="Personal CRM with AI-powered contact extraction and semantic search",
    version="1.1.0",
)

# Instrument Prometheus
Instrumentator().instrument(app).expose(app, include_in_schema=False, endpoint="/metrics")

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error("validation_error", errors=exc.errors(), body=exc.body)
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# API prefix for versioning/organization
API_PREFIX = "/api"

app.include_router(contacts.router, prefix=API_PREFIX)
app.include_router(messages.router, prefix=API_PREFIX)
app.include_router(telegram.router, prefix=API_PREFIX)
app.include_router(leads.router, prefix=API_PREFIX)
app.include_router(search.router, prefix=API_PREFIX)
app.include_router(system.router, prefix=API_PREFIX)
app.include_router(settings.router, prefix=API_PREFIX)
app.include_router(pipeline.router, prefix=API_PREFIX)
app.include_router(tracking.router, prefix=API_PREFIX)

@app.get("/")
async def root():
    return {"message": "Networking Brain API is running", "version": "1.1.0"}
