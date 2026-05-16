"""Project management service — auto-create projects from Telegram folders, distribute messages."""

import structlog
from uuid import UUID
from typing import Optional
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models import SystemProject, TrackedFolder, TrackedChannel, Message, Contact
from src.db.database import get_session

logger = structlog.get_logger()


async def ensure_projects_from_folders(db: AsyncSession) -> dict:
    """
    On login: create projects for each Telegram folder if settings allow.
    Returns mapping of folder_id -> project_id.
    """
    # TODO: Get folders from Telegram API (requires telethon integration)
    # For now, create a default project if none exists

    result = await db.execute(select(SystemProject))
    existing_projects = result.scalars().all()

    if not existing_projects:
        # Create default project
        default_project = SystemProject(
            name="Default",
            description="Default project for initial sync"
        )
        db.add(default_project)
        await db.commit()
        await db.refresh(default_project)
        return {"default": str(default_project.id)}

    return {"existing": len(existing_projects)}


async def distribute_orphaned_messages(db: AsyncSession) -> dict:
    """
    Find messages with NULL folder_id and distribute them to matching channels/folders.
    Returns counts of distributed messages.
    """
    # Get all orphaned messages (folder_id IS NULL)
    orphaned_res = await db.execute(
        select(Message).where(Message.folder_id.is_(None))
    )
    orphaned_messages = orphaned_res.scalars().all()

    if not orphaned_messages:
        logger.info("distribute_orphaned_messages", status="no_orphaned_messages")
        return {"distributed": 0, "remaining": 0}

    distributed_count = 0

    for msg in orphaned_messages:
        if not msg.group_id:
            # Message has no group/channel association
            continue

        # Find channel that matches this group_id
        channel_res = await db.execute(
            select(TrackedChannel).where(TrackedChannel.telegram_id == msg.group_id)
        )
        channel = channel_res.scalar_one_or_none()

        if channel and channel.folder_id:
            msg.folder_id = channel.folder_id
            # TrackedFolder has no project_id — project assignment is handled separately
            distributed_count += 1
        elif channel:
            # Channel exists but not assigned to folder yet
            # Try to find project by channel or default to first project
            project_res = await db.execute(select(SystemProject).limit(1))
            project = project_res.scalar_one_or_none()
            if project:
                msg.project_id = project.id
                distributed_count += 1

    if distributed_count > 0:
        await db.commit()
        logger.info("distribute_orphaned_messages", distributed=distributed_count)

    remaining_res = await db.execute(
        select(func.count(Message.id)).where(Message.folder_id.is_(None))
    )
    remaining = remaining_res.scalar() or 0

    return {"distributed": distributed_count, "remaining": remaining}


async def assign_contacts_to_projects(db: AsyncSession) -> dict:
    """
    Assign contacts to projects based on their messages.
    Contact belongs to project if its messages belong to that project.
    """
    # Get all contacts without project_id
    contacts_res = await db.execute(
        select(Contact).where(Contact.project_id.is_(None))
    )
    contacts = contacts_res.scalars().all()

    assigned_count = 0

    for contact in contacts:
        # Get most common project from this contact's messages
        count_col = func.count(Message.id).label("msg_count")
        project_res = await db.execute(
            select(Message.project_id, count_col)
            .where(Message.contact_id == contact.id)
            .where(Message.project_id.isnot(None))
            .group_by(Message.project_id)
            .order_by(count_col.desc())
            .limit(1)
        )
        result = project_res.one_or_none()

        if result:
            contact.project_id = result[0]
            assigned_count += 1

    if assigned_count > 0:
        await db.commit()
        logger.info("assign_contacts_to_projects", assigned=assigned_count)

    return {"assigned": assigned_count}


async def create_indexing_tasks(project_id: UUID, db: AsyncSession) -> dict:
    """
    Create Celery tasks for gradual indexing of messages in a project.
    From most recent to oldest across all channels in the project.
    """
    from src.pipeline.celery_app import app as celery_app

    # Get all folders/channels in project
    folders_res = await db.execute(
        select(TrackedFolder).where(TrackedFolder.project_id == project_id)
    )
    folders = folders_res.scalars().all()

    if not folders:
        logger.warning("create_indexing_tasks", status="no_folders", project_id=str(project_id))
        return {"status": "no_folders", "tasks_created": 0}

    # Get all channels in these folders
    folder_ids = [f.id for f in folders]
    channels_res = await db.execute(
        select(TrackedChannel).where(TrackedChannel.folder_id.in_(folder_ids))
    )
    channels = channels_res.scalars().all()

    tasks_created = 0

    for channel in channels:
        # Create task: sync_telegram with this channel
        # Tasks will process messages from newest to oldest
        task = celery_app.send_task(
            'src.pipeline.tasks.deep_track_chunk',
            args=[channel.telegram_id, "channel"],
            kwargs={"limit": 500},
            queue='connectors'
        )
        tasks_created += 1
        logger.info("create_indexing_task", channel=channel.title, task_id=task.id)

    return {"status": "ok", "tasks_created": tasks_created, "channels": len(channels)}
