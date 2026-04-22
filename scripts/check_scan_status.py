import asyncio
import os
import sys
from sqlalchemy import select, func

# Add current directory to path
sys.path.append(os.getcwd())

from src.db.database import get_session
from src.db.models import ExtractionLog, Message, MessageContact, Contact
from src.pipeline.unified_processor import update_all_lead_scores

async def check_progress():
    if os.getenv("POSTGRES_HOST") == "postgres":
        os.environ["POSTGRES_HOST"] = "localhost"
        
    async with get_session() as session:
        # 1. Scan Progress
        processed = await session.execute(select(func.count(ExtractionLog.id)).where(ExtractionLog.model_used == "heuristic_v1"))
        total = await session.execute(select(func.count(Message.id)))
        
        proc_count = processed.scalar() or 0
        total_count = total.scalar() or 0
        
        print(f"--- SCAN PROGRESS ---")
        print(f"Processed: {proc_count} / {total_count} messages ({ (proc_count/total_count*100) if total_count else 0 :.1f}%)")

        # 2. Ads Found
        ads = await session.execute(select(func.count(MessageContact.id)).where(MessageContact.role == "lead"))
        print(f"Ads Identified: {ads.scalar()}")

        # 3. Analyze Top Prospects (Recalculate first)
        print("\nRecalculating scores for current findings...")
        await update_all_lead_scores()
        
        print("\n--- TOP ADVERTISERS IN OUR CHANNEL ---")
        q_ours = (
            select(Contact.first_name, Contact.telegram_username, Contact.lead_score, Contact.our_channel_ratio)
            .where(Contact.is_lead == True)
            .where(Contact.our_channel_ratio > 0)
            .order_by(Contact.lead_score.desc())
            .limit(10)
        )
        res_ours = await session.execute(q_ours)
        for name, username, score, ratio in res_ours:
            print(f"  {score:>6} | {ratio:>5.1f}% | {name} (@{username or 'N/A'})")

        print("\n--- TOP TARGETS (NOT IN OUR CHANNEL YET) ---")
        q_targets = (
            select(Contact.first_name, Contact.telegram_username, Contact.lead_score)
            .where(Contact.is_lead == True)
            .where(Contact.our_channel_ratio == 0)
            .order_by(Contact.lead_score.desc())
            .limit(15)
        )
        res_targets = await session.execute(q_targets)
        for name, username, score in res_targets:
            print(f"  {score:>6} | {name} (@{username or 'N/A'})")

if __name__ == "__main__":
    asyncio.run(check_progress())
