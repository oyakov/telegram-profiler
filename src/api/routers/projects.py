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

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    db_name: str
    description: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True

def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    return re.sub(r'[-\s]+', '_', text).strip('_')

@router.get("", response_model=List[ProjectResponse])
async def list_projects(db: AsyncSession = Depends(get_master_db)):
    """List all projects. Forces connection to master 'crm' database."""
    result = await db.execute(select(SystemProject).order_by(SystemProject.created_at))
    return result.scalars().all()

@router.post("", response_model=ProjectResponse)
async def create_project(data: ProjectCreate, db: AsyncSession = Depends(get_master_db)):
    """Create a new project and initialize its database."""
    slug = slugify(data.name)
    db_name = f"crm_{slug}"
    
    # Check if project or DB already exists
    existing = await db.execute(select(SystemProject).where(SystemProject.db_name == db_name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Project with name '{data.name}' already exists (db: {db_name})")
    
    # 1. Register in system_projects
    project = SystemProject(
        name=data.name,
        db_name=db_name,
        description=data.description
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    
    # 2. Physically create and init the database
    try:
        await ensure_database_exists(db_name)
        await init_database_schema(db_name)
    except Exception as e:
        # Rollback project registration if DB creation fails
        await db.delete(project)
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Failed to initialize database: {str(e)}")
    
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
    
    # Note: We don't automatically DROP the database for safety. 
    # The user can do it manually if needed, or we add a 'force' flag.
    await db.delete(project)
    await db.commit()
    return {"status": "success", "message": "Project record removed. Database remains intact for safety."}
