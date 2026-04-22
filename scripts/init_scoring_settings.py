import asyncio
import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.db.database import get_session
from src.core.settings_service import SettingsService

async def init_settings():
    print("Initializing lead scoring settings...")
    async with get_session() as session:
        settings = SettingsService(session)
        
        # High value keywords for scoring
        await settings.set(
            "scoring_high_value_keywords", 
            ['dev', 'invest', 'agency', 'partnership', 'ai', 'software', 'hiring'],
            value_type="json",
            description="Keywords in ad summary that increase lead score",
            category="scoring"
        )
        
        # Our main channel ID
        await settings.set(
            "scoring_our_channel_id",
            "1753396658",
            description="The Telegram channel ID that counts as 'ours' for ratio calculation",
            category="scoring"
        )
        
        # Multipliers and weights
        await settings.set(
            "scoring_weight_keyword_bonus",
            5.0,
            value_type="float",
            description="Points added for each high-value keyword found",
            category="scoring"
        )
        
        await settings.set(
            "scoring_multiplier_recent_week",
            3.0,
            value_type="float",
            description="Multiplier for ads placed within the last 7 days",
            category="scoring"
        )
        
        await settings.set(
            "scoring_multiplier_recent_month",
            2.0,
            value_type="float",
            description="Multiplier for ads placed within the last 30 days",
            category="scoring"
        )
        
        print("Settings initialized successfully.")

if __name__ == "__main__":
    asyncio.run(init_settings())
