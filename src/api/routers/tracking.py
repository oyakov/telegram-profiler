from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.database import get_db
from src.db.models import TrackedChannel, TrackedFolder, Message
from src.api.schemas import DiscoveryJoinRequest

router = APIRouter(prefix="/tracking", tags=["Tracking"])

@router.get("/folders")
async def list_folders(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(TrackedFolder))
    return {"folders": res.scalars().all()}

@router.get("/channels")
async def list_tracked_channels(db: AsyncSession = Depends(get_db)):
    # Join with message count to show progress
    msg_counts = select(
        Message.group_id, 
        func.count(Message.id).label("count")
    ).group_by(Message.group_id).subquery()
    
    query = (
        select(TrackedChannel, msg_counts.c.count)
        .outerjoin(msg_counts, TrackedChannel.telegram_id == msg_counts.c.group_id)
        .order_by(TrackedChannel.created_at.desc())
    )
    
    result = await db.execute(query)
    channels = []
    for chan, count in result.all():
        channels.append({
            "id": chan.id,
            "telegram_id": chan.telegram_id,
            "title": chan.title,
            "username": chan.username,
            "type": chan.entity_type,
            "is_active": chan.is_active,
            "messages_count": count or 0,
            "last_sync": chan.last_sync_at.isoformat() if chan.last_sync_at else None
        })
    return {"channels": channels}

@router.post("/channels/{channel_id}/toggle")
async def toggle_channel(channel_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(TrackedChannel).where(TrackedChannel.id == channel_id))
    chan = res.scalar_one_or_none()
    if not chan: raise HTTPException(404, "Not found")
    chan.is_active = not chan.is_active
    await db.commit()
    return {"status": "success", "is_active": chan.is_active}
