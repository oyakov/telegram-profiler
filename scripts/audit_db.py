
import asyncio
import os
from sqlalchemy import text
from src.db.database import get_session
from src.core.config import get_settings

async def audit_db():
    settings = get_settings()
    print(f"Auditing database: {settings.postgres_db} on {settings.postgres_host}")
    
    async with get_session() as session:
        # Check system projects
        try:
            res = await session.execute(text("SELECT name, db_name FROM system_projects"))
            projects = res.all()
            print(f"\nSystem Projects: {len(projects)}")
            for p in projects:
                print(f" - {p.name} ({p.db_name})")
        except Exception as e:
            print(f"Error checking system_projects: {e}")

        # Check Tracked Folders
        res = await session.execute(text("SELECT name, COUNT(*) as cnt FROM tracked_folders GROUP BY name"))
        folders = res.all()
        print(f"\nTracked Folders: {len(folders)}")
        for f in folders:
            print(f" - {f.name}")

        # Count key tables
        tables = [
            "tracked_channels", 
            "contacts", 
            "messages", 
            "message_embeddings", 
            "voice_notes",
            "extraction_log"
        ]
        
        print("\nRecord Counts:")
        for table in tables:
            try:
                res = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = res.scalar()
                print(f" - {table}: {count}")
            except Exception as e:
                print(f" - {table}: Error ({e})")

        # Check latest messages
        try:
            res = await session.execute(text("SELECT MAX(timestamp) FROM messages"))
            latest = res.scalar()
            print(f"\nLatest message timestamp: {latest}")
        except Exception:
            pass

        # Check lead stats
        try:
            res = await session.execute(text("SELECT COUNT(*) FROM contacts WHERE is_lead = True"))
            leads = res.scalar()
            print(f"Leads identified: {leads}")
        except Exception:
            pass

if __name__ == "__main__":
    asyncio.run(audit_db())
