import structlog
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel
from typing import List
from sqlalchemy import select
from telethon.tl.types import Channel

from src.core.config import get_settings, SettingsService
from src.api.schemas import (
    TelegramSendCode, TelegramVerifyCode, TelegramTwoFA,
    DeepSyncRequest, DiscoveryJoinRequest
)


class FolderImportRequest(BaseModel):
    folder_id: str
    peer_ids: List[str]
from src.services.telegram.client_factory import TelegramClientFactory
from src.services.telegram.auth_service import TelegramAuthService
from src.services.telegram.management_service import TelegramManagementService
from src.services.telegram.entity_service import TelegramEntityService
from src.db.database import get_session
from src.db.models import TrackedFolder, TrackedChannel
from src.pipeline.tasks import deep_sync_telegram

logger = structlog.get_logger()
router = APIRouter(prefix="/telegram", tags=["Telegram"])

def get_telegram_services(request: Request):
    db_name = request.headers.get("X-Database")
    factory = TelegramClientFactory(db_name=db_name)
    return {
        "auth": TelegramAuthService(factory),
        "mgmt": TelegramManagementService(factory),
        "entity": TelegramEntityService(factory),
        "db_name": db_name
    }

@router.get("/auth/status")
async def telegram_auth_status(request: Request):
    """Check if Telegram is currently authorized and return profile info."""
    from src.db.models import UserProfile
    services = get_telegram_services(request)
    try:
        is_auth = await services["auth"].is_authorized()
        profile_data = None
        
        if is_auth:
            async with get_session(db_name=services["db_name"]) as session:
                res = await session.execute(select(UserProfile).limit(1))
                profile = res.scalar_one_or_none()
                if profile:
                    profile_data = {
                        "telegram_id": profile.telegram_id,
                        "first_name": profile.first_name,
                        "last_name": profile.last_name,
                        "username": profile.username,
                        "phone": profile.phone,
                        "bio": profile.bio,
                        "photo": profile.profile_photo_path
                    }
        
        return {"authorized": is_auth, "profile": profile_data}
    except Exception as e:
        return {"authorized": False, "error": str(e)}

@router.post("/auth/send_code")
async def telegram_send_code(req: TelegramSendCode, request: Request):
    """Request a verification code."""
    services = get_telegram_services(request)
    try:
        phone_code_hash = await services["auth"].send_code_request(req.phone)
        return {"status": "success", "phone_code_hash": phone_code_hash}
    except Exception as e:
        raise HTTPException(400, f"Failed to send code: {str(e)}")

@router.post("/auth/verify")
async def telegram_verify_code(req: TelegramVerifyCode, request: Request):
    """Verify the code and log in."""
    services = get_telegram_services(request)
    result = await services["auth"].sign_in(req.phone, req.code, req.phone_code_hash)
    if result["status"] == "error":
        raise HTTPException(400, result.get("message", "Verification failed"))
    
    # Post-login: update profile
    if result["status"] == "success":
        await services["entity"].update_user_profile()
        
    return result

@router.post("/auth/2fa")
async def telegram_verify_2fa(req: TelegramTwoFA, request: Request):
    """Complete 2FA if required."""
    services = get_telegram_services(request)
    result = await services["auth"].sign_in_2fa(req.password)
    if result["status"] == "error":
        raise HTTPException(400, result.get("message", "2FA failed"))
    
    if result["status"] == "success":
        await services["entity"].update_user_profile()
        
    return result

@router.get("/folders")
async def telegram_list_folders(request: Request):
    """List Telegram dialog filters (folders) with channel counts."""
    services = get_telegram_services(request)
    folders = await services["mgmt"].list_folders()
    return {"folders": folders}

@router.post("/folders/import")
async def telegram_import_folder(body: FolderImportRequest, request: Request):
    """Import channels from Telegram folder peers into a DB folder."""
    from uuid import UUID
    services = get_telegram_services(request)
    db_name = services["db_name"]

    try:
        folder_id = UUID(body.folder_id)
    except ValueError:
        raise HTTPException(400, "Invalid folder_id format")

    try:
        channels = await services["mgmt"].import_folder_channels(body.peer_ids)
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch channels from Telegram: {str(e)}")

    added = 0
    moved = 0
    async with get_session(db_name=db_name) as session:
        res = await session.execute(select(TrackedFolder).where(TrackedFolder.id == folder_id))
        folder = res.scalar_one_or_none()
        if not folder:
            raise HTTPException(404, "Folder not found")

        for ch in channels:
            res = await session.execute(
                select(TrackedChannel).where(TrackedChannel.telegram_id == ch["telegram_id"])
            )
            existing_chan = res.scalar_one_or_none()
            if existing_chan:
                existing_chan.folder_id = folder.id
                moved += 1
            else:
                session.add(TrackedChannel(
                    folder_id=folder.id,
                    telegram_id=ch["telegram_id"],
                    title=ch["title"],
                    username=ch["username"],
                    entity_type=ch["entity_type"],
                    is_active=True
                ))
                added += 1
        await session.commit()

    return {"status": "success", "added": added, "moved": moved, "total": len(channels)}

@router.post("/auth/logout")
async def telegram_logout(request: Request):
    """Log out from Telegram."""
    services = get_telegram_services(request)
    try:
        await services["auth"].logout()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(400, f"Logout failed: {str(e)}")

@router.post("/auth/reset-session")
async def telegram_reset_session(request: Request):
    """Reset Telegram session to fix database lock issues."""
    db_name = request.headers.get("X-Database")
    connector = TelegramConnector(db_name=db_name)
    await connector._cleanup_stale_session()
    return {"status": "success", "message": "Session cleaned. Please try again."}

@router.post("/auth/sync")
async def telegram_manual_sync(request: Request, background_tasks: BackgroundTasks):
    """Manually trigger the folder and contact sync."""
    db_name = request.headers.get("X-Database")
    connector = TelegramConnector(db_name=db_name)
    background_tasks.add_task(connector.auto_sync_on_login, force=True)
    return {"status": "dispatched", "message": "Manual sync started in background"}

@router.post("/contacts/sync")
async def telegram_sync_contacts(request: Request):
    """Queue async task to sync contacts from Telegram account."""
    from src.pipeline.tasks import sync_telegram_contacts
    from src.core.config import get_settings
    db_name = request.headers.get("X-Database") or get_settings().postgres_db

    task = sync_telegram_contacts.delay(db_name=db_name)
    return {
        "status": "queued",
        "task_id": task.id,
        "message": "Contact sync started in background. You can check status with the task ID."
    }


@router.get("/contacts/sync/status/{task_id}")
async def get_contact_sync_status(task_id: str):
    """Get status of async contact sync task."""
    from celery.result import AsyncResult
    from src.pipeline.celery_app import celery_app

    task = AsyncResult(task_id, app=celery_app)
    return {
        "task_id": task_id,
        "status": task.status,
        "result": task.result if task.ready() else None
    }

