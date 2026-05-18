"""Schemas for campaign management."""

from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


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
    description: Optional[str] = Field(default=None, max_length=2048)
    message: str = Field(..., min_length=1, max_length=4096)
    contact_ids: List[UUID] = Field(...)


class CampaignUpdate(BaseModel):
    """Request to update a campaign (only draft)."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2048)
    message: Optional[str] = Field(default=None, min_length=1, max_length=4096)


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


_PREVIEW_CONTACT_FIELDS = frozenset({"first_name", "last_name", "email", "phone", "company", "position"})
_PREVIEW_FIELD_MAX_LEN = 255


class CampaignPreviewRequest(BaseModel):
    """Request to preview a message with variable substitution."""
    message: str = Field(..., min_length=1, max_length=4096)
    # Only whitelisted contact fields are accepted; values are length-capped by the validator.
    sample_contact: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def sanitize_sample_contact(cls, data: dict) -> dict:
        """Strip unknown keys and cap value lengths in sample_contact."""
        sc = data.get("sample_contact", {}) or {}
        if sc:
            data["sample_contact"] = {
                k: str(v)[:_PREVIEW_FIELD_MAX_LEN]
                for k, v in sc.items()
                if k in _PREVIEW_CONTACT_FIELDS
            }
        return data


class CampaignPreviewResponse(BaseModel):
    """Response with preview of rendered message."""
    original: str
    rendered: str


class CampaignListRequest(BaseModel):
    """Query parameters for campaign list."""
    status: Optional[str] = None  # Filter by status
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
