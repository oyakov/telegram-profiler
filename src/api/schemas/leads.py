"""Schemas for lead search and management."""

from __future__ import annotations
from typing import Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class LeadProfileFilter(BaseModel):
    """Profile criteria for lead search."""
    # Basic info
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    position: Optional[str] = None

    # Keywords and interests
    keywords: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)

    # Contact info (optional)
    email: Optional[str] = None
    phone: Optional[str] = None

    # Search filters
    min_score: float = 0.0
    min_activity_ratio: float = 0.0  # Minimum % of activity in "our" channel
    max_activity_ratio: float = 100.0

    # Time range
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None

    # Pagination
    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=100)


class LeadSearchCreate(BaseModel):
    """Create a new tracked lead search."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    profile_filter: LeadProfileFilter
    db_name: Optional[str] = None  # Use specified database or current


class LeadSearchUpdate(BaseModel):
    """Update a tracked lead search."""
    name: Optional[str] = None
    description: Optional[str] = None
    profile_filter: Optional[LeadProfileFilter] = None
    is_active: Optional[bool] = None


class LeadSearchResponse(BaseModel):
    """Response for a tracked lead search."""
    id: str
    name: str
    description: Optional[str]
    profile_filter: dict
    is_active: bool
    result_count: int = 0
    last_run_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeadSearchResults(BaseModel):
    """Results from a lead search."""
    search_id: Optional[str] = None  # If from saved search
    total: int
    page: int
    page_size: int
    pages: int
    contacts: list[dict]  # Simplified contact responses
