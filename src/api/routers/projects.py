from __future__ import annotations
import uuid
import re
from typing import Optional, List, AsyncGenerator
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db, get_session, ensure_database_exists, init_database_schema
from src.db.models import SystemProject
from src.core.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/projects", tags=["Projects"])

async def get_master_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that always yields a session to the master 'crm' database."""
    async with get_session(settings.postgres_db, use_pooling=True) as session:
        yield session

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    telegram_folder_id: Optional[str] = None

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    telegram_folder_id: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True

@router.get("", response_model=List[ProjectResponse])
async def list_projects(db: AsyncSession = Depends(get_master_db)):
    """List all projects."""
    result = await db.execute(select(SystemProject).order_by(SystemProject.created_at))
    return result.scalars().all()

@router.post("", response_model=ProjectResponse)
async def create_project(data: ProjectCreate, db: AsyncSession = Depends(get_master_db)):
    """Create a new project."""
    # Check if project already exists
    existing = await db.execute(select(SystemProject).where(SystemProject.name == data.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Project '{data.name}' already exists")

    project = SystemProject(
        name=data.name,
        description=data.description,
        telegram_folder_id=data.telegram_folder_id
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)

    return project

@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: uuid.UUID, data: ProjectUpdate, db: AsyncSession = Depends(get_master_db)):
    result = await db.execute(select(SystemProject).where(SystemProject.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    update_data = data.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(project, key, value)
    
    await db.commit()
    await db.refresh(project)
    return project

@router.delete("/{project_id}")
async def delete_project(project_id: uuid.UUID, db: AsyncSession = Depends(get_master_db)):
    result = await db.execute(select(SystemProject).where(SystemProject.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await db.delete(project)
    await db.commit()
    return {"status": "success", "message": "Project deleted"}
