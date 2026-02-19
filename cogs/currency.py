import discord
from discord.ext import commands
from database import Database
from datetime import datetime, timedelta
import random

class Currency(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Award currency for chatting"""
        
        # Ignore bots and DMs
        if message.author.bot or not message.guild:
            return
        
        # Ignore commands
        if message.content.startswith(('/', '!')):
            return
        
        # Get server settings
        settings = await self.db.get_server_settings(message.guild.id)
        if not settings or not settings['setup_completed']:
            return
        
        # Check if currency is enabled in this channel
        currency_channels = settings['currency_channels']
        if currency_channels:  # If list is not empty, only specific channels
            if message.channel.id not in currency_channels:
                return
        
        # Check cooldown
        last_earned = await self.db.get_last_currency_earned(message.guild.id, message.author.id)
        
        if last_earned:
            last_time = datetime.fromisoformat(last_earned)
            cooldown_seconds = settings['currency_cooldown']
            
            if datetime.utcnow() - last_time < timedelta(seconds=cooldown_seconds):
                return  # Still on cooldown
        
        # Award currency to all user's wrestlers
        wrestlers = await self.db.get_wrestlers_by_user(message.guild.id, message.author.id)
        
        if not wrestlers:
            return  # No wrestlers to award
        
        # Generate random currency amount
        amount = random.randint(settings['currency_min'], settings['currency_max'])
        
        # Award to all wrestlers
        for wrestler in wrestlers:
            await self.db.update_wrestler_currency(wrestler['id'], amount)
        
        # Update cooldown
        await self.db.update_currency_cooldown(message.guild.id, message.author.id)
        
        # Optional: Send a subtle notification (can be disabled)
        # Uncomment below if you want currency notifications
        # currency_symbol = settings['currency_symbol']
        # await message.add_reaction('💰')

async def setup(bot):
    await bot.add_cog(Currency(bot))
