import discord
from discord import app_commands
from discord.ext import commands
from database import Database
from typing import Optional

# Autocomplete for wrestlers
async def wrestler_autocomplete(interaction: discord.Interaction, current: str):
    db = Database()
    wrestlers = await db.get_all_wrestlers(interaction.guild_id)
    if not wrestlers:
        return [app_commands.Choice(name="(No wrestlers found)", value="none")]
    filtered = [w for w in wrestlers if current.lower() in w['name'].lower()][:25]
    return [app_commands.Choice(name=w['name'], value=w['name']) for w in filtered]


class LevelSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
    
    @app_commands.command(name="level", description="View wrestler level and progress")
    @app_commands.autocomplete(wrestler_name=wrestler_autocomplete)
    async def level(self, interaction: discord.Interaction, wrestler_name: Optional[str] = None):
        """View level progress for a wrestler"""
        
        all_wrestlers = await self.db.get_all_wrestlers(interaction.guild_id)
        
        # If no name provided, get user's wrestler
        if not wrestler_name:
            wrestler = next((w for w in all_wrestlers if w['user_id'] == interaction.user.id), None)
            if not wrestler:
                await interaction.response.send_message(
                    "❌ You don't have a wrestler! Use /create_wrestler first.",
                    ephemeral=True
                )
                return
        else:
            wrestler = next((w for w in all_wrestlers if w['name'].lower() == wrestler_name.lower()), None)
            if not wrestler:
                await interaction.response.send_message(
                    f"❌ Wrestler '{wrestler_name}' not found!",
                    ephemeral=True
                )
                return
        
        # Level thresholds
        thresholds = [0, 250, 850, 1950, 3750, 6450, 10250, 15450, 22450, 31950]
        level_caps = {1: 70, 2: 75, 3: 80, 4: 85, 5: 90, 6: 92, 7: 95, 8: 97, 9: 99, 10: 100}
        
        current_level = wrestler.get('level', 1)
        current_xp = wrestler.get('xp', 0)
        
        # Calculate XP needed for next level
        if current_level < 10:
            xp_needed = thresholds[current_level]
            xp_progress = current_xp
            progress_pct = (xp_progress / xp_needed * 100) if xp_needed > 0 else 100
        else:
            xp_needed = 0
            xp_progress = current_xp
            progress_pct = 100
        
        # Create embed
        embed = discord.Embed(
            title=f"📊 {wrestler['name']}",
            description=f"**Level {current_level}**" + (" ⭐ LEGEND" if current_level == 10 else ""),
            color=discord.Color.gold() if current_level == 10 else discord.Color.blue()
        )
        
        # XP Progress
        if current_level < 10:
            progress_bar = self.create_progress_bar(progress_pct)
            embed.add_field(
                name="Experience",
                value=f"{progress_bar}\n{xp_progress:,} / {xp_needed:,} XP ({progress_pct:.1f}%)",
                inline=False
            )
        else:
            embed.add_field(
                name="Experience",
                value=f"✅ MAX LEVEL | Total XP: {current_xp:,}",
                inline=False
            )
        
        # Attribute Cap
        cap = level_caps.get(current_level, 70)
        embed.add_field(
            name="Attribute Cap",
            value=f"**{cap}** (max upgrade limit)",
            inline=True
        )
        
        # Record
        embed.add_field(
            name="Record",
            value=f"{wrestler['wins']}-{wrestler['losses']}",
            inline=True
        )
        
        # Unlocks
        unlocks_text = self.get_unlocks_text(wrestler)
        embed.add_field(
            name="Unlocks",
            value=unlocks_text,
            inline=False
        )
        
        # Next unlock
        if current_level < 10:
            next_unlock = self.get_next_unlock(current_level + 1)
            embed.add_field(
                name=f"Next (Level {current_level + 1})",
                value=next_unlock,
                inline=False
            )
        
        embed.set_footer(text=f"{wrestler['archetype']} • {wrestler['weight_class']}")
        
        await interaction.response.send_message(embed=embed)
    
    def create_progress_bar(self, percentage: float) -> str:
        """Create a visual progress bar"""
        filled = int(percentage / 10)
        empty = 10 - filled
        return f"[{'█' * filled}{'░' * empty}]"
    
    def get_unlocks_text(self, wrestler) -> str:
        """Get unlocks based on level"""
        level = wrestler.get('level', 1)
        unlocks = []
        
        # Check what's unlocked
        if level >= 2:
            unlocks.append("✅ $500 Bonus")
        else:
            unlocks.append("🔒 $500 Bonus (Level 2)")
        
        if level >= 3:
            unlocks.append("✅ Signature Slot")
        else:
            unlocks.append("🔒 Signature Slot (Level 3)")
        
        if level >= 4:
            unlocks.append("✅ Sideplates")
        else:
            unlocks.append("🔒 Sideplates (Level 4)")
        
        if level >= 5:
            unlocks.append("✅ Finisher Slot")
        else:
            unlocks.append("🔒 Finisher Slot (Level 5)")
        
        if level >= 6:
            unlocks.append("✅ $1,000 Bonus")
        else:
            unlocks.append("🔒 $1,000 Bonus (Level 6)")
        
        if level >= 7:
            unlocks.append("✅ Superfinisher")
        else:
            unlocks.append("🔒 Superfinisher (Level 7)")
        
        if level >= 8:
            unlocks.append("✅ Custom Entrance")
        else:
            unlocks.append("🔒 Custom Entrance (Level 8)")
        
        if level >= 9:
            unlocks.append("✅ Hall of Fame")
        else:
            unlocks.append("🔒 Hall of Fame (Level 9)")
        
        if level >= 10:
            unlocks.append("✅ Stable Creation")
        else:
            unlocks.append("🔒 Stable Creation (Level 10)")
        
        # Show first 5 unlocks to avoid clutter
        return "\n".join(unlocks[:6])
    
    def get_next_unlock(self, next_level: int) -> str:
        """Get what unlocks at the next level"""
        unlocks = {
            2: "💰 +$500 Bonus",
            3: "🎯 Signature Slot Unlock",
            4: "🎨 Sideplates",
            5: "🔥 Finisher Slot Unlock",
            6: "💰 +$1,000 Bonus",
            7: "⚡ Superfinisher Unlock",
            8: "🎬 Custom Entrance Boost",
            9: "🏛️ Hall of Fame Eligibility",
            10: "⭐ Legend Status + Stable Creation"
        }
        return unlocks.get(next_level, "Max Level")


async def setup(bot):
    await bot.add_cog(LevelSystem(bot))
