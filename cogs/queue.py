import discord
from discord import app_commands
from discord.ext import commands
from database import Database
from utils.helpers import create_pending_upgrades_embed
from typing import Optional

class Queue(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
    
    # Command group
    queue_group = app_commands.Group(name="queue", description="Attribute upgrade queue management")
    
    @queue_group.command(name="view", description="View pending attribute upgrades")
    @app_commands.checks.has_permissions(administrator=True)
    async def view(self, interaction: discord.Interaction):
        """View all pending upgrades in queue"""
        
        upgrades = await self.db.get_pending_upgrades(interaction.guild_id)
        upgrades = [u for u in upgrades if not u.get('processed', 0)]
        
        if not upgrades:
            await interaction.response.send_message(
                "✅ No pending upgrades in the queue!",
                ephemeral=True
            )
            return
        
        # Group by wrestler and attribute
        grouped = {}
        for upgrade in upgrades:
            wrestler_name = upgrade['wrestler_name']
            attr_name = upgrade['attribute']  # ← HIER: attribute nicht attribute_name
            
            if wrestler_name not in grouped:
                grouped[wrestler_name] = {}
            
            if attr_name not in grouped[wrestler_name]:
                # Initialize with FIRST entry's old_value
                grouped[wrestler_name][attr_name] = {
                    'start_value': upgrade['old_value'],
                    'end_value': upgrade['new_value'],
                    'total_increase': upgrade['amount']  # ← HIER: amount nicht increase_amount
                }
            else:
                # Update end_value and add to total
                grouped[wrestler_name][attr_name]['end_value'] = upgrade['new_value']
                grouped[wrestler_name][attr_name]['total_increase'] += upgrade['amount']
        
        # Create embed
        embed = discord.Embed(
            title="📋 Pending Attribute Upgrades",
            description="These upgrades need to be applied in-game.",
            color=discord.Color.blue()
        )
        
        for wrestler_name, attributes in grouped.items():
            lines = []
            for attr_name, data in attributes.items():
                lines.append(
                    f"• **{attr_name}**: {data['start_value']} → {data['end_value']} (+{data['total_increase']})"
                )
            
            embed.add_field(
                name=f"🏆 {wrestler_name}",
                value="\n".join(lines),
                inline=False
            )
        
        embed.set_footer(text="Use /queue clear when you've applied these in-game")
        
        await interaction.response.send_message(embed=embed)
    
    @queue_group.command(name="clear", description="Mark all upgrades as applied")
    @app_commands.checks.has_permissions(administrator=True)
    async def clear(self, interaction: discord.Interaction):
        """Mark all pending upgrades as processed"""
        
        # Get count first
        upgrades = await self.db.get_pending_upgrades(interaction.guild_id)
        upgrades = [u for u in upgrades if not u.get('processed', 0)]
        count = len(upgrades)
        
        # Mark as processed
        await self.db.clear_processed_upgrades(interaction.guild_id)
        
        await interaction.response.send_message(
            f"✅ Marked **{count}** upgrade(s) as applied!",
            ephemeral=True
        )
    
async def setup(bot):
    await bot.add_cog(Queue(bot))
