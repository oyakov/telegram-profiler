import asyncio
import os
import sys
from sqlalchemy import select, func

# Add current directory to path
sys.path.append(os.getcwd())

from src.db.database import get_session
from src.db.models import Contact, Message, MessageContact

async def analyze_results():
    if os.getenv("POSTGRES_HOST") == "postgres":
        os.environ["POSTGRES_HOST"] = "localhost"
        
    async with get_session() as session:
        # 1. Overall stats
        total_ads = await session.execute(select(func.count(MessageContact.id)).where(MessageContact.role == "lead"))
        total_buyers = await session.execute(select(func.count(Contact.id)).where(Contact.is_lead == True))
        
        print(f"--- PRELIMINARY ANALYSIS ---")
        print(f"Total Leads/Ads Found: {total_ads.scalar()}")
        print(f"Total Unique Leads: {total_buyers.scalar()}")
        print("-" * 50)

        # 2. Top Leads in OUR channel (Coefficient > 0)
        print("\nTop Leads in OUR channel (Русские в Белграде):")
        query_ours = (
            select(Contact.first_name, Contact.telegram_username, Contact.lead_score, Contact.our_channel_ratio)
            .where(Contact.is_lead == True)
            .where(Contact.our_channel_ratio > 0)
            .order_by(Contact.lead_score.desc())
            .limit(10)
        )
        res_ours = await session.execute(query_ours)
        for name, username, score, ratio in res_ours:
            print(f"  - {name} (@{username or 'N/A'}): Score {score}, Ratio {ratio}%")

        # 3. Top Leads NOT in our channel (Potential Targets)
        print("\nTop Leads NOT in your channel (Sales Targets):")
        query_targets = (
            select(Contact.first_name, Contact.telegram_username, Contact.lead_score, Contact.our_channel_ratio)
            .where(Contact.is_lead == True)
            .where(Contact.our_channel_ratio == 0)
            .order_by(Contact.lead_score.desc())
            .limit(15)
        )
        res_targets = await session.execute(query_targets)
        for name, username, score, ratio in res_targets:
            print(f"  - {name} (@{username or 'N/A'}): Score {score}, Ratio {ratio}%")

if __name__ == "__main__":
    asyncio.run(analyze_results())
