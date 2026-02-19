"""
Configuration file for Wrestling League Bot
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Bot Configuration
class Config:
    # Discord Bot Token (from .env)
    DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
    
    # Bot Settings
    BOT_PREFIX = '!'
    BOT_STATUS = "WWE matches | /help"
    
    # Database
    DATABASE_PATH = "wrestling_bot.db"
    
    # Default Server Settings
    DEFAULT_CURRENCY_NAME = "Dollars"
    DEFAULT_CURRENCY_SYMBOL = "$"
    DEFAULT_CURRENCY_MIN = 5
    DEFAULT_CURRENCY_MAX = 15
    DEFAULT_CURRENCY_COOLDOWN = 60  # seconds
    DEFAULT_MAX_WRESTLERS = 3
    
    # Feature Flags (for future phases)
    ENABLE_CHAMPIONSHIPS = False  # Phase 2
    ENABLE_MATCH_HISTORY = False  # Phase 2
    ENABLE_LEADERBOARDS = False   # Phase 2
    ENABLE_EVENTS = False          # Phase 3
    ENABLE_LEVELS = False          # Phase 3
    ENABLE_DAILY_REWARDS = False   # Phase 3

# Validate configuration
def validate_config():
    """Check if required config values are set"""
    if not Config.DISCORD_TOKEN:
        raise ValueError(
            "DISCORD_TOKEN not found! Please create a .env file with your bot token.\n"
            "See .env.template for an example."
        )
    
    print("✅ Configuration loaded successfully")

if __name__ == "__main__":
    validate_config()
