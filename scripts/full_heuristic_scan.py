"""Fast heuristic scan of all messages for ad detection."""

import asyncio
import os
import sys
from datetime import datetime, timezone
from sqlalchemy import select, func, and_

# Add current directory to path
sys.path.append(os.getcwd())

from src.db.database import get_session
from src.db.models import Message, Contact, ExtractionLog, MessageContact
from src.ai.heuristic_detector import detect_ad_heuristically
from src.ai.deduplication import find_duplicate
from src.pipeline.unified_processor import update_all_lead_scores

async def run_heuristic_scan(batch_size: int = 5000):
    if os.getenv("POSTGRES_HOST") == "postgres":
        os.environ["POSTGRES_HOST"] = "localhost"
        
    print("Starting full heuristic scan of all messages...")
    
    total_processed = 0
    total_ads_found = 0
    
    while True:
        async with get_session() as session:
            # 1. Find messages not yet scanned by HEURISTIC
            scanned_ids = select(ExtractionLog.source_id).where(ExtractionLog.model_used == "heuristic_v1")
            
            import sqlalchemy as sa
            from sqlalchemy.orm import joinedload
            
            query = (
                select(Message)
                .options(joinedload(Message.contact))
                .where(Message.id.cast(sa.String).not_in(scanned_ids))
                .where(Message.content.is_not(None))
                .limit(batch_size)
            )
            
            result = await session.execute(query)
            messages = result.scalars().all()
            
            if not messages:
                break
                
            for msg in messages:
                try:
                    res = detect_ad_heuristically(msg.content)
                    
                    # Log that we processed this message
                    log = ExtractionLog(
                        source_type="unified_message",
                        source_id=str(msg.id),
                        model_used="heuristic_v1",
                        success=True,
                        extracted_data={"is_ad": bool(res)}
                    )
                    session.add(log)
                    
                    if res and res.is_ad:
                        # Use provided username or fallback to sender's username
                        username = res.username or (msg.contact.telegram_username if msg.contact else None)
                        if not username:
                            continue
                            
                        contact = await find_duplicate(session, telegram_username=username)
                        
                        new_ad_entry = {
                            "message_id": str(msg.id),
                            "group_id": msg.group_id,
                            "timestamp": msg.timestamp.isoformat(),
                            "summary": res.summary,
                            "evidence": res.evidence,
                            "quality": 3
                        }
                        
                        if not contact:
                            contact = Contact(
                                first_name=username,
                                telegram_username=username,
                                source="heuristic_ad",
                                is_lead=True,
                                ad_context={"ad_history": [new_ad_entry]},
                                notes=f"Heuristically detected as lead. Match: {res.summary}"
                            )
                            session.add(contact)
                            await session.flush()
                        else:
                            contact.is_lead = True
                            ctx = contact.ad_context or {}
                            history = ctx.get("ad_history", [])
                            if not any(h.get("message_id") == str(msg.id) for h in history):
                                history.append(new_ad_entry)
                                ctx["ad_history"] = history[-100:]
                                contact.ad_context = ctx
                                contact.embedding_dirty = True
                        
                        # Link relationaly
                        link_exists = await session.execute(
                            select(MessageContact).where(
                                and_(
                                    MessageContact.message_id == msg.id,
                                    MessageContact.contact_id == contact.id,
                                    MessageContact.role == "lead"
                                )
                            )
                        )
                        if not link_exists.scalar_one_or_none():
                            session.add(MessageContact(
                                message_id=msg.id,
                                contact_id=contact.id,
                                role="lead"
                            ))
                        
                        total_ads_found += 1
                except Exception as e:
                    print(f"Error processing message {msg.id}: {e}")
                
                total_processed += 1
                if total_processed % 500 == 0:
                    print(f"  Processed {total_processed} messages... ({total_ads_found} ads found)")
            
            await session.commit()

    print(f"\nHeuristic scan complete!")
    print(f"Total processed: {total_processed}")
    print(f"Total ads/leads found: {total_ads_found}")
    
    print("Recalculating lead scores and channel ratios...")
    await update_all_lead_scores()
    print("Done.")

if __name__ == "__main__":
    asyncio.run(run_heuristic_scan())
