import structlog
import os
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select
from telethon.tl.types import Channel

from src.core.config import get_settings
from src.api.schemas import (
    TelegramSendCode, TelegramVerifyCode, TelegramTwoFA, 
    DeepSyncRequest, DiscoveryJoinRequest
)
from src.connectors.telegram_connector import TelegramConnector
from src.db.database import get_session
from src.core.config import SettingsService
from src.db.models import TrackedFolder, TrackedChannel
from src.pipeline.tasks import deep_sync_telegram

logger = structlog.get_logger()
router = APIRouter(prefix="/telegram", tags=["Telegram"])

@router.get("/search")
async def telegram_search(query: str, request: Request, limit: int = 50):
    """Search for public communities by keyword."""
    db_name = request.headers.get("X-Database")
    connector = TelegramConnector(db_name=db_name)
    results = await connector.search_communities(query, limit=limit)
    return {"results": results}

@router.post("/join")
async def telegram_join(req: DiscoveryJoinRequest, request: Request):
    """Join a community, add to whitelist, and optionally trigger deep sync."""
    db_name = request.headers.get("X-Database")
    connector = TelegramConnector(db_name=db_name)
    
    # 1. Join
    success, entity = await connector.join_community(req.chat_id, username=req.username)
    if not success or not entity:
        raise HTTPException(400, "Failed to join community. See logs for details.")
    
    # 2. Add to TrackedChannels automatically
    async with get_session(db_name=db_name) as session:
        # Get target folder
        folder_name = os.getenv("TARGET_FOLDER", "BG Intel")
        if db_name == "crm_crypto": folder_name = "Crypto"
        
        res = await session.execute(select(TrackedFolder).where(TrackedFolder.name == folder_name))
        folder = res.scalar_one_or_none()
        if not folder:
            folder = TrackedFolder(name=folder_name)
            session.add(folder); await session.flush()
            
        tg_id = str(entity.id)
        res = await session.execute(select(TrackedChannel).where(TrackedChannel.telegram_id == tg_id))
        chan = res.scalar_one_or_none()
        
        if not chan:
            e_type = "channel" if isinstance(entity, Channel) and entity.broadcast else "group"
            chan = TrackedChannel(
                telegram_id=tg_id,
                folder_id=folder.id,
                title=getattr(entity, 'title', 'Unknown'),
                username=getattr(entity, 'username', None),
                entity_type=e_type
            )
            session.add(chan)
            logger.info("telegram_auto_tracked", chat_id=tg_id, folder=folder_name, db=db_name)
            await session.commit()
    
    # 3. Trigger Deep Sync if requested
    if req.deep_sync_days > 0:
        # Use the canonical ID
        deep_sync_telegram.delay(
            chat_ids=[entity.id],
            limit=5000, 
            days=req.deep_sync_days,
            db_name=db_name
        )
        
    return {
        "status": "success", 
        "joined_id": entity.id, 
        "whitelisted": True,
        "sync_queued": req.deep_sync_days > 0
    }

@router.post("/deep-sync")
async def telegram_deep_sync(req: DeepSyncRequest, request: Request):
    """Trigger a deep history sync for specific channels."""
    db_name = request.headers.get("X-Database")
    task = deep_sync_telegram.delay(
        chat_ids=req.chat_ids,
        limit=req.limit,
        days=req.days,
        db_name=db_name
    )
    return {"status": "queued", "task_id": task.id}

@router.get("/auth/status")
async def telegram_auth_status(request: Request):
    """Check if Telegram is currently authorized."""
    db_name = request.headers.get("X-Database")
    connector = TelegramConnector(db_name=db_name)
    try:
        is_auth = await connector.is_authorized()
        return {"authorized": is_auth}
    except Exception as e:
        return {"authorized": False, "error": str(e)}

@router.post("/auth/send_code")
async def telegram_send_code(req: TelegramSendCode, request: Request):
    """Request a verification code."""
    db_name = request.headers.get("X-Database")
    settings = get_settings()
    if not settings.telegram_api_id or not settings.telegram_api_hash:
        raise HTTPException(400, "TELEGRAM_API_ID or TELEGRAM_API_HASH is not configured")
    
    connector = TelegramConnector(db_name=db_name)
    try:
        phone_code_hash = await connector.send_code_request(req.phone)
        return {"status": "success", "phone_code_hash": phone_code_hash}
    except Exception as e:
        raise HTTPException(400, f"Failed to send code: {str(e)}")

@router.post("/auth/verify")
async def telegram_verify_code(req: TelegramVerifyCode, request: Request):
    """Verify the code and log in."""
    db_name = request.headers.get("X-Database")
    connector = TelegramConnector(db_name=db_name)
    result = await connector.sign_in(req.phone, req.code, req.phone_code_hash)
    if result["status"] == "error":
        raise HTTPException(400, result.get("message", "Verification failed"))
    return result

@router.post("/auth/2fa")
async def telegram_verify_2fa(req: TelegramTwoFA, request: Request):
    """Complete 2FA if required."""
    db_name = request.headers.get("X-Database")
    connector = TelegramConnector(db_name=db_name)
    result = await connector.sign_in_2fa(req.password)
    if result["status"] == "error":
        raise HTTPException(400, result.get("message", "2FA failed"))
    return result

@router.get("/folders")
async def telegram_list_folders(request: Request):
    """List Telegram dialog filters (folders) with channel counts."""
    db_name = request.headers.get("X-Database")
    connector = TelegramConnector(db_name=db_name)
    folders = await connector.list_telegram_folders()
    return {"folders": folders}


@router.post("/folders/import")
async def telegram_import_folder(request: Request):
    """Import channels from Telegram folder peers into a DB folder."""
    from pydantic import BaseModel
    from sqlalchemy import select
    from src.db.database import get_session
    from src.db.models import TrackedFolder, TrackedChannel

    body = await request.json()
    folder_id = body.get("folder_id")
    peer_ids = body.get("peer_ids", [])
    db_name = request.headers.get("X-Database")

    if not folder_id or not peer_ids:
        raise HTTPException(400, "folder_id and peer_ids are required")

    connector = TelegramConnector(db_name=db_name)
    channels = await connector.import_folder_channels(peer_ids)

    added = 0
    skipped = 0
    async with get_session(db_name=db_name) as session:
        res = await session.execute(select(TrackedFolder).where(TrackedFolder.id == folder_id))
        folder = res.scalar_one_or_none()
        if not folder:
            raise HTTPException(404, "Folder not found")

        for ch in channels:
            existing = await session.execute(
                select(TrackedChannel).where(TrackedChannel.telegram_id == ch["telegram_id"])
            )
            existing_chan = existing.scalar_one_or_none()
            if existing_chan:
                existing_chan.folder_id = folder.id
                skipped += 1
            else:
                new_chan = TrackedChannel(
                    folder_id=folder.id,
                    telegram_id=ch["telegram_id"],
                    title=ch["title"],
                    username=ch["username"],
                    entity_type=ch["entity_type"],
                )
                session.add(new_chan)
                added += 1
        await session.commit()

    return {"status": "success", "added": added, "moved": skipped, "total": len(channels)}


@router.post("/auth/logout")
async def telegram_logout(request: Request):
    """Log out from Telegram."""
    db_name = request.headers.get("X-Database")
    connector = TelegramConnector(db_name=db_name)
    try:
        await connector.logout()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(400, f"Logout failed: {str(e)}")

