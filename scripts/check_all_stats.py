import asyncio
import os
import sys
from sqlalchemy import select, func

# Add project root to sys.path
sys.path.append(os.getcwd())

from src.db.database import get_session
from src.db.models import Message, Contact, SyncState

async def check_stats(db_name):
    print(f"\n--- STATS FOR {db_name} ---")
    async with get_session(db_name=db_name) as session:
        # Total messages
        msg_count = (await session.execute(select(func.count(Message.id)))).scalar()
        
        # Total contacts
        contact_count = (await session.execute(select(func.count(Contact.id)))).scalar()
        
        # Leads (ad buyers)
        lead_count = (await session.execute(select(func.count(Contact.id)).where(Contact.is_lead == True))).scalar()
        
        # Connector status
        state_res = await session.execute(select(SyncState).where(SyncState.connector == "telegram"))
        state = state_res.scalar_one_or_none()
        status_str = f"{state.status} (Last: {state.last_sync_at})" if state else "unknown"

        # Top channels
        query = (
            select(Message.group_name, func.count(Message.id))
            .group_by(Message.group_name)
            .order_by(func.count(Message.id).desc())
            .limit(5)
        )
        top_channels = (await session.execute(query)).all()
        
        print(f"Status:         {status_str}")
        print(f"Total Messages: {msg_count}")
        print(f"Total Contacts: {contact_count}")
        print(f"Total Leads:    {lead_count}")
        print("\nTop 5 Channels/Groups:")
        for name, count in top_channels:
            print(f"  - {name or 'Unknown'}: {count}")

async def main():
    await check_stats("crm")
    await check_stats("crm_crypto")

if __name__ == "__main__":
    asyncio.run(main())
