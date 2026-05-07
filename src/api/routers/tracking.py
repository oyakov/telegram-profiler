from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.database import get_db
from src.db.models import TrackedChannel, TrackedFolder, Message
from src.api.schemas import DiscoveryJoinRequest

router = APIRouter(prefix="/tracking", tags=["Tracking"])


class CreateFolderRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    tags: List[str] = Field(default_factory=list)


class UpdateFolderRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None


@router.get("/folders")
async def list_folders(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(TrackedFolder).order_by(TrackedFolder.created_at))
    folders = res.scalars().all()
    return {"folders": [
        {
            "id": str(f.id), 
            "name": f.name, 
            "description": f.description, 
            "tags": f.tags or [],
            "is_active": f.is_active
        }
        for f in folders
    ]}


@router.post("/folders")
async def create_folder(req: CreateFolderRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(TrackedFolder).where(TrackedFolder.name == req.name))
    if existing.scalar_one_or_none():
        raise HTTPException(400, f"Folder '{req.name}' already exists")
    folder = TrackedFolder(
        name=req.name, 
        description=req.description or None,
        tags=req.tags
    )
    db.add(folder)
    await db.commit()
    await db.refresh(folder)
    return {
        "id": str(folder.id), 
        "name": folder.name, 
        "description": folder.description, 
        "tags": folder.tags
    }


@router.patch("/folders/{folder_id}")
async def update_folder(folder_id: str, req: UpdateFolderRequest, db: AsyncSession = Depends(get_db)):
    from uuid import UUID
    try:
        f_id = UUID(folder_id)
    except ValueError:
        raise HTTPException(400, "Invalid folder ID format")

    res = await db.execute(select(TrackedFolder).where(TrackedFolder.id == f_id))
    folder = res.scalar_one_or_none()
    if not folder:
        raise HTTPException(404, "Folder not found")
    
    update_data = req.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(folder, key, value)
    
    await db.commit()
    await db.refresh(folder)
    return {
        "id": str(folder.id), 
        "name": folder.name, 
        "description": folder.description, 
        "tags": folder.tags
    }


@router.delete("/folders/{folder_id}")
async def delete_folder(folder_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(TrackedFolder).where(TrackedFolder.id == folder_id))
    folder = res.scalar_one_or_none()
    if not folder:
        raise HTTPException(404, "Folder not found")
    await db.delete(folder)
    await db.commit()
    return {"status": "deleted"}


@router.get("/channels")
async def list_tracked_channels(db: AsyncSession = Depends(get_db)):
    msg_counts = select(
        Message.group_id,
        func.count(Message.id).label("count")
    ).group_by(Message.group_id).subquery()

    query = (
        select(TrackedChannel, TrackedFolder.name.label("folder_name"), msg_counts.c.count)
        .outerjoin(TrackedFolder, TrackedChannel.folder_id == TrackedFolder.id)
        .outerjoin(msg_counts, TrackedChannel.telegram_id == msg_counts.c.group_id)
        .order_by(TrackedFolder.name.nullslast(), TrackedChannel.created_at.desc())
    )

    result = await db.execute(query)
    channels = []
    for chan, folder_name, count in result.all():
        channels.append({
            "id": str(chan.id),
            "telegram_id": chan.telegram_id,
            "title": chan.title,
            "username": chan.username,
            "type": chan.entity_type,
            "is_active": chan.is_active,
            "folder_id": str(chan.folder_id) if chan.folder_id else None,
            "folder_name": folder_name,
            "messages_count": count or 0,
            "last_sync": chan.last_sync_at.isoformat() if chan.last_sync_at else None,
        })
    return {"channels": channels}


@router.delete("/channels/{channel_id}")
async def delete_channel(channel_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(TrackedChannel).where(TrackedChannel.id == channel_id))
    chan = res.scalar_one_or_none()
    if not chan:
        raise HTTPException(404, "Channel not found")
    await db.delete(chan)
    await db.commit()
    return {"status": "deleted"}


@router.post("/channels/{channel_id}/toggle")
async def toggle_channel(channel_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(TrackedChannel).where(TrackedChannel.id == channel_id))
    chan = res.scalar_one_or_none()
    if not chan:
        raise HTTPException(404, "Not found")
    chan.is_active = not chan.is_active
    await db.commit()
    return {"status": "success", "is_active": chan.is_active}
