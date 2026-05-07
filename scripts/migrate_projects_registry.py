"""Script to migrate existing hardcoded databases to the dynamic system_projects registry."""

import asyncio
import sys
import os
import uuid
import structlog
from sqlalchemy import select

sys.path.append(os.getcwd())

from src.db.database import get_session, init_database_schema
from src.db.models import SystemProject

# Hardcoded list of existing projects found in scripts/reinit_all_dbs.py
EXISTING_PROJECTS = [
    {"db_name": "crm", "name": "🇷🇸 Belgrade Intel", "description": "General intelligence"},
    {"db_name": "crm_crypto", "name": "💰 Crypto Universe", "description": "Crypto & Web3 leads"},
    {"db_name": "crm_bg_rent", "name": "🏠 Rent & Housing", "description": "Real estate tracking"},
    {"db_name": "crm_bg_cars", "name": "🚗 Cars & Logistics", "description": "Vehicle market monitoring"},
    {"db_name": "crm_bg_work", "name": "💼 Jobs & Business", "description": "Networking & HR"},
    {"db_name": "crm_bg_news", "name": "📰 Belgrade News", "description": "Local city updates"},
]

async def migrate():
    print("--- Registering Existing Projects ---")
    
    # Ensure master schema is initialized
    print("[*] Initializing master schema for 'crm'...")
    await init_database_schema("crm")
    
    # We always use the 'crm' database as the master registry
    async with get_session(db_name="crm") as session:
        for p_data in EXISTING_PROJECTS:
            try:
                # Check if already registered
                res = await session.execute(
                    select(SystemProject).where(SystemProject.db_name == p_data["db_name"])
                )
                if res.scalar_one_or_none():
                    print(f"[Skip] Project {p_data['db_name']} already registered.")
                    continue
                
                # Add new entry
                project = SystemProject(
                    id=uuid.uuid4(),
                    db_name=p_data["db_name"],
                    name=p_data["name"],
                    description=p_data["description"],
                    is_active=True
                )
                session.add(project)
                print(f"[OK] Registered: {p_data['name']} ({p_data['db_name']})")
                
            except Exception as e:
                print(f"[Error] Failed to register {p_data['db_name']}: {e}")
        
        await session.commit()
    
    print("\n--- Migration Complete ---")

if __name__ == "__main__":
    asyncio.run(migrate())
