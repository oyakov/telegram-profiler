import asyncio
import os
import sys
from sqlalchemy import select, func

# Add current directory to path
sys.path.append(os.getcwd())

from src.db.database import get_session
from src.db.models import Message, Contact, MessageContact

async def get_active_posters():
    # Ensure POSTGRES_HOST is set to localhost if running from host
    if os.getenv("POSTGRES_HOST") == "postgres":
        os.environ["POSTGRES_HOST"] = "localhost"
        
    async with get_session() as session:
        # Query to count messages per contact via MessageContact link
        # This includes messages where they are the sender
        query = (
            select(
                Contact.first_name, 
                Contact.last_name, 
                Contact.telegram_username, 
                func.count(MessageContact.message_id).label("message_count"),
                func.count(func.distinct(Message.group_id)).label("channel_count")
            )
            .join(MessageContact, Contact.id == MessageContact.contact_id)
            .join(Message, MessageContact.message_id == Message.id)
            .where(MessageContact.role == "sender")
            .where(Message.group_id.is_not(None))
            .group_by(Contact.id)
            .order_by(func.count(MessageContact.message_id).desc())
            .limit(20)
        )
        
        result = await session.execute(query)
        rows = result.all()
        
        print("\nTop 20 Most Active Posters (Across All Channels):")
        print("-" * 80)
        print(f"{'Name':<30} | {'Username':<20} | {'Messages':<10} | {'Channels':<10}")
        print("-" * 80)
        for first_name, last_name, username, msg_count, chan_count in rows:
            full_name = f"{first_name or ''} {last_name or ''}".strip() or "Unknown"
            username_str = f"@{username}" if username else "N/A"
            print(f"{full_name[:30]:<30} | {username_str:<20} | {msg_count:<10} | {chan_count:<10}")
        print("-" * 80)

if __name__ == "__main__":
    asyncio.run(get_active_posters())
