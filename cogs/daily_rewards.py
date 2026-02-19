import discord
from discord import app_commands
from discord.ext import commands
from database import Database
from datetime import datetime

class DailyRewards(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
    
    @app_commands.command(name="daily", description="Claim your daily reward!")
    async def daily(self, interaction: discord.Interaction):
        """Claim daily reward and maintain streak"""
        
        # Get user's wrestler
        wrestlers = await self.db.get_wrestlers_by_user(interaction.guild_id, interaction.user.id)
        
        if not wrestlers:
            await interaction.response.send_message(
                "❌ You don't have a wrestler! Use `/create_wrestler` first.",
                ephemeral=True
            )
            return
        
        wrestler = wrestlers[0]  # Use first wrestler
        
        # Get server settings for currency display
        settings = await self.db.get_server_settings(interaction.guild_id)
        currency_symbol = settings.get('currency_symbol', '$')
        currency_name = settings.get('currency_name', 'Cash')
        
        # Try to claim
        result = await self.db.claim_daily_reward(wrestler['id'])
        
        if not result:
            await interaction.response.send_message(
                "❌ Error claiming daily reward!",
                ephemeral=True
            )
            return
        
        # Already claimed today
        if not result['success']:
            embed = discord.Embed(
                title="⏰ Come Back Later!",
                description=f"You've already claimed your daily reward today!",
                color=discord.Color.orange()
            )
            
            embed.add_field(
                name="Next Claim",
                value=f"⏰ {result['next_claim_hours']}h {result['next_claim_minutes']}m",
                inline=True
            )
            
            embed.add_field(
                name="Current Streak",
                value=f"🔥 **{result['current_streak']}** day{'s' if result['current_streak'] != 1 else ''}",
                inline=True
            )
            
            # Show next milestone
            streak = result['current_streak']
            if streak < 3:
                next_milestone = f"Day 3: +25% bonus!"
            elif streak < 7:
                next_milestone = f"Day 7: +100% WEEKLY BONUS!"
            elif streak < 14:
                next_milestone = f"Day 14: Another weekly bonus!"
            else:
                next_milestone = f"Keep the streak alive!"
            
            embed.add_field(
                name="Next Milestone",
                value=next_milestone,
                inline=False
            )
            
            embed.set_footer(text=f"Playing as {wrestler['name']}")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Successfully claimed!
        reward = result['reward']
        streak = result['streak']
        new_balance = result['new_balance']
        
        # Determine title and color
        if result['streak_broken']:
            title = "💔 Streak Broken!"
            color = discord.Color.red()
            desc = f"You missed a day! Streak reset to **1**.\n\n"
        elif streak == 1:
            title = "🎁 Daily Reward"
            color = discord.Color.green()
            desc = ""
        elif result['is_milestone']:
            title = "🎉 MILESTONE REWARD!"
            color = discord.Color.gold()
            desc = f"**{streak}-Day Streak!** 🔥\n\n"
        else:
            title = "🎁 Daily Reward"
            color = discord.Color.green()
            desc = ""
        
        embed = discord.Embed(
            title=title,
            description=desc + f"💰 **+{currency_symbol}{reward:,}**",
            color=color
        )
        
        # Streak display
        streak_text = f"🔥 **{streak}** day{'s' if streak != 1 else ''}"
        if streak % 7 == 0:
            streak_text += " ⭐ WEEKLY BONUS!"
        elif streak >= 3:
            streak_text += " (+25% bonus)"
        
        embed.add_field(
            name="Streak",
            value=streak_text,
            inline=True
        )
        
        embed.add_field(
            name="New Balance",
            value=f"{currency_symbol}{new_balance:,}",
            inline=True
        )
        
        # Next bonus info
        if streak < 3:
            next_bonus = f"Day 3: +25% bonus ({currency_symbol}125)"
        elif streak < 7:
            days_until = 7 - (streak % 7)
            next_bonus = f"Day 7: Weekly bonus ({currency_symbol}200) in {days_until} day{'s' if days_until != 1 else ''}!"
        else:
            days_until = 7 - (streak % 7)
            next_bonus = f"Next weekly: Day {streak + days_until} ({currency_symbol}200)"
        
        embed.add_field(
            name="Next Bonus",
            value=next_bonus,
            inline=False
        )
        
        # Motivational message
        if streak >= 30:
            footer = f"🌟 {wrestler['name']} • LEGENDARY DEDICATION! 30+ day streak!"
        elif streak >= 14:
            footer = f"💪 {wrestler['name']} • Amazing commitment! Keep it up!"
        elif streak >= 7:
            footer = f"🔥 {wrestler['name']} • One week strong!"
        elif streak >= 3:
            footer = f"⚡ {wrestler['name']} • Building momentum!"
        else:
            footer = f"🎯 {wrestler['name']} • Start your streak!"
        
        embed.set_footer(text=footer)
        
        await self.db.update_last_active(interaction.user.id, interaction.guild_id)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(DailyRewards(bot))
