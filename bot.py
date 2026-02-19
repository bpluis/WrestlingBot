import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio
from database import Database

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Initialize database
db = Database()

@bot.event
async def on_ready():
    """Called when bot is ready"""
    print(f'✅ Logged in as {bot.user.name} ({bot.user.id})')
    print('━' * 50)
    
    # Initialize database
    await db.initialize()
    print('✅ Database initialized')
    
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f'✅ Synced {len(synced)} slash commands')
    except Exception as e:
        print(f'❌ Failed to sync commands: {e}')
    
    # Set bot status
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="WWE matches | /help"
        )
    )
    print('━' * 50)
    print('🏆 Wrestling Bot is ready!')

@bot.event
async def on_guild_join(guild):
    """Called when bot joins a new server"""
    print(f'📥 Joined new server: {guild.name} (ID: {guild.id})')

@bot.event
async def on_guild_remove(guild):
    """Called when bot leaves a server"""
    print(f'📤 Left server: {guild.name} (ID: {guild.id})')

async def load_cogs():
    """Load all cog files"""
    cogs = ['cogs.admin', 'cogs.wrestler', 'cogs.currency', 'cogs.shop', 'cogs.matches', 'cogs.championships', 'cogs.events', 'cogs.level_system', 'cogs.daily_rewards','cogs.queue','cogs.inactivity','cogs.rivalries']
    
    for cog in cogs:
        try:
            await bot.load_extension(cog)
            print(f'✅ Loaded {cog}')
        except Exception as e:
            print(f'❌ Failed to load {cog}: {e}')

async def main():
    """Main bot startup"""
    async with bot:
        await load_cogs()
        await bot.start(TOKEN)

if __name__ == '__main__':
    asyncio.run(main())
