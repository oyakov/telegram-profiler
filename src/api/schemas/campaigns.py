"""Schemas for campaign management."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CampaignMessageResponse(BaseModel):
    """Response model for a single campaign message."""
    id: UUID
    contact_id: UUID
    status: str  # pending|sent|failed
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CampaignCreate(BaseModel):
    """Request to create a new campaign."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    message: str = Field(..., min_length=1)
    contact_ids: List[UUID] = Field(...)


class CampaignUpdate(BaseModel):
    """Request to update a campaign (only draft)."""
    name: Optional[str] = None
    description: Optional[str] = None
    message: Optional[str] = None


class CampaignResponse(BaseModel):
    """Response model for campaign detail."""
    id: UUID
    name: str
    description: Optional[str] = None
    message: str
    status: str  # draft|scheduled|sending|completed|failed
    total_contacts: int
    sent_count: int
    failed_count: int
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CampaignListResponse(BaseModel):
    """Response model for campaign in list."""
    id: UUID
    name: str
    status: str
    total_contacts: int
    sent_count: int
    failed_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CampaignDetailResponse(CampaignResponse):
    """Extended response with all fields."""
    messages: Optional[List[CampaignMessageResponse]] = None


class CampaignPreviewRequest(BaseModel):
    """Request to preview a message with variable substitution."""
    message: str = Field(..., min_length=1)
    sample_contact: dict[str, str] = Field(default_factory=dict)  # first_name, last_name, email, etc.


class CampaignPreviewResponse(BaseModel):
    """Response with preview of rendered message."""
    original: str
    rendered: str


class CampaignListRequest(BaseModel):
    """Query parameters for campaign list."""
    status: Optional[str] = None  # Filter by status
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
