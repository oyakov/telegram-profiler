import asyncio
import os
import sys
import csv
from datetime import datetime
from sqlalchemy import select, func

# Add current directory to path
sys.path.append(os.getcwd())

from src.db.database import get_session
from src.db.models import Contact

async def export_targets():
    if os.getenv("POSTGRES_HOST") == "postgres":
        os.environ["POSTGRES_HOST"] = "localhost"
        
    print("Exporting top sales targets (Advertisers NOT in our channel)...")
    
    async with get_session() as session:
        # Query for top advertisers with 0% our_channel_ratio
        query = (
            select(
                Contact.first_name, 
                Contact.last_name, 
                Contact.telegram_username, 
                Contact.lead_score,
                Contact.bio,
                Contact.notes
            )
            .where(Contact.is_lead == True)
            .where(Contact.our_channel_ratio == 0)
            .order_by(Contact.lead_score.desc())
            .limit(100)
        )
        
        result = await session.execute(query)
        rows = result.all()
        
    if not rows:
        print("No targets found yet. Scan might still be in early stages.")
        return

    filename = f"sales_targets_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    with open(filename, mode='w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "Username", "Score", "Bio", "Heuristic Notes"])
        for r in rows:
            full_name = f"{r[0] or ''} {r[1] or ''}".strip()
            writer.writerow([full_name, f"@{r[2]}" if r[2] else "N/A", r[3], r[4], r[5]])

    print(f"Successfully exported {len(rows)} targets to {filename}")

if __name__ == "__main__":
    asyncio.run(export_targets())
