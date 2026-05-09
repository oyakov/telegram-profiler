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
    project_id: str
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

    # Count messages per folder
    msg_counts_res = await db.execute(
        select(Message.folder_id, func.count(Message.id))
        .group_by(Message.folder_id)
    )
    msg_counts = {str(row[0]): row[1] for row in msg_counts_res.all()}

    return {"folders": [
        {
            "id": str(f.id),
            "project_id": str(f.project_id) if f.project_id else None,
            "name": f.name,
            "description": f.description,
            "tags": f.tags or [],
            "is_active": f.is_active,
            "message_count": msg_counts.get(str(f.id), 0)
        }
        for f in folders
    ]}


@router.post("/folders")
async def create_folder(req: CreateFolderRequest, db: AsyncSession = Depends(get_db)):
    from uuid import UUID
    try:
        project_id = UUID(req.project_id)
    except ValueError:
        raise HTTPException(400, "Invalid project_id format")

    # Check project exists
    from src.db.models import SystemProject
    proj_res = await db.execute(select(SystemProject).where(SystemProject.id == project_id))
    if not proj_res.scalar_one_or_none():
        raise HTTPException(404, "Project not found")

    folder = TrackedFolder(
        project_id=project_id,
        name=req.name,
        description=req.description or None,
        tags=req.tags
    )
    db.add(folder)
    await db.commit()
    await db.refresh(folder)
    return {
        "id": str(folder.id),
        "project_id": str(folder.project_id),
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
    query = (
        select(TrackedChannel, TrackedFolder.name.label("folder_name"), TrackedFolder.project_id.label("project_id"))
        .outerjoin(TrackedFolder, TrackedChannel.folder_id == TrackedFolder.id)
        .order_by(TrackedFolder.name.nullslast(), TrackedChannel.created_at.desc())
    )

    result = await db.execute(query)

    # Get message counts by folder
    msg_counts_res = await db.execute(
        select(Message.folder_id, func.count(Message.id))
        .group_by(Message.folder_id)
    )
    msg_counts = {str(row[0]): row[1] for row in msg_counts_res.all()}

    channels = []
    for chan, folder_name, project_id in result.all():
        # Count messages in this channel's folder
        folder_messages = msg_counts.get(str(chan.folder_id), 0) if chan.folder_id else 0

        channels.append({
            "id": str(chan.id),
            "telegram_id": chan.telegram_id,
            "title": chan.title or chan.telegram_id,
            "username": chan.username,
            "type": chan.entity_type,
            "is_active": chan.is_active,
            "folder_id": str(chan.folder_id) if chan.folder_id else None,
            "folder_name": folder_name,
            "project_id": str(project_id) if project_id else None,
            "messages_count": folder_messages,
            "total_synced": chan.total_messages_synced or 0,
            "oldest_msg_date": chan.oldest_message_date.isoformat() if chan.oldest_message_date else None,
            "last_sync": chan.last_sync_at.isoformat() if chan.last_sync_at else None,
        })
    return {"channels": channels}


@router.get("/contacts")
async def list_tracked_contacts(db: AsyncSession = Depends(get_db)):
    from src.db.models import Contact
    res = await db.execute(
        select(Contact)
        .where(Contact.is_tracked == True)
        .order_by(Contact.updated_at.desc())
    )
    contacts = res.scalars().all()
    return {"contacts": [
        {
            "id": str(c.id),
            "telegram_id": c.telegram_id,
            "name": f"{c.first_name} {c.last_name or ''}".strip(),
            "username": c.telegram_username,
            "total_synced": c.total_messages_synced or 0,
            "oldest_msg_date": c.oldest_message_date.isoformat() if c.oldest_message_date else None,
            "last_sync": c.last_enriched_at.isoformat() if c.last_enriched_at else None,
        }
        for c in contacts
    ]}


@router.post("/contacts/{contact_id}/toggle")
async def toggle_contact_tracking(contact_id: str, db: AsyncSession = Depends(get_db)):
    from src.db.models import Contact
    from uuid import UUID
    try:
        c_id = UUID(contact_id)
    except ValueError:
        raise HTTPException(400, "Invalid contact ID format")

    res = await db.execute(select(Contact).where(Contact.id == c_id))
    contact = res.scalar_one_or_none()
    if not contact:
        raise HTTPException(404, "Contact not found")
    
    contact.is_tracked = not contact.is_tracked
    await db.commit()
    return {"status": "success", "is_tracked": contact.is_tracked}


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
