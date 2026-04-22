"""Script to enrich profile info (bio, photo) for top active users."""

import asyncio
import os
import sys
from sqlalchemy import select, func

# Add current directory to path
sys.path.append(os.getcwd())

from src.db.database import get_session
from src.db.models import Message, Contact, MessageContact
from src.connectors.telegram_connector import TelegramConnector

async def enrich_top_users(limit: int = 20):
    # Ensure POSTGRES_HOST is set to localhost if running from host
    if os.getenv("POSTGRES_HOST") == "postgres":
        os.environ["POSTGRES_HOST"] = "localhost"
        
    print(f"Identifying top {limit} active users for enrichment...")
    
    async with get_session() as session:
        query = (
            select(Contact.id, Contact.first_name, Contact.telegram_id)
            .join(MessageContact, Contact.id == MessageContact.contact_id)
            .where(MessageContact.role == "sender")
            .where(Contact.telegram_id.is_not(None))
            .where(Contact.telegram_id != "system")
            .group_by(Contact.id)
            .order_by(func.count(MessageContact.message_id).desc())
            .limit(limit)
        )
        
        result = await session.execute(query)
        users = result.all()
        
    if not users:
        print("No users found to enrich.")
        return

    print(f"Found {len(users)} users. Starting enrichment...")
    connector = TelegramConnector()
    
    for user_id, first_name, tg_id in users:
        print(f"Enriching {first_name} (TG: {tg_id})...")
        try:
            success = await connector.enrich_contact(str(user_id))
            if success:
                print(f"  [SUCCESS] Bio and photo updated.")
            else:
                print(f"  [FAILED] User not found or connection error.")
        except Exception as e:
            print(f"  [ERROR] {e}")
        
        # Sleep a bit to avoid flood limits
        await asyncio.sleep(1)

    print("\nEnrichment complete.")

if __name__ == "__main__":
    asyncio.run(enrich_top_users())
