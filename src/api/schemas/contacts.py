from __future__ import annotations
from typing import Optional, Any
from pydantic import BaseModel, Field

class ContactCreate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    position: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    telegram_id: Optional[str] = None
    telegram_username: Optional[str] = None
    linkedin_url: Optional[str] = None
    source: str = "manual"
    interests: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    notes: Optional[str] = None
    context: Optional[str] = None


class ContactUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    position: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    telegram_username: Optional[str] = None
    linkedin_url: Optional[str] = None
    interests: Optional[list[str]] = None
    skills: Optional[list[str]] = None
    notes: Optional[str] = None
    context: Optional[str] = None


class ContactResponse(BaseModel):
    id: str
    first_name: Optional[str]
    last_name: Optional[str]
    company: Optional[str]
    position: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    telegram_id: Optional[str]
    telegram_username: Optional[str]
    linkedin_url: Optional[str]
    source: str
    interests: list[str]
    skills: list[str]
    notes: Optional[str]
    context: Optional[str]
    is_lead: bool = False
    lead_score: float = 0.0
    lead_context: dict = {}
    last_interaction: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]

    model_config = {"from_attributes": True}
