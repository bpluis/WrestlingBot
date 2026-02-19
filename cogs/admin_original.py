import discord
from discord import app_commands
from discord.ext import commands
from database import Database
from utils.helpers import create_pending_upgrades_embed
from typing import Optional

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
    
    @app_commands.command(name="setup", description="Initial server setup for the Wrestling Bot")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup(
        self,
        interaction: discord.Interaction,
        currency_name: str,
        currency_symbol: str,
        currency_min: int,
        currency_max: int,
        announcement_channel: discord.TextChannel,
        max_wrestlers: int = 3
    ):
        """Setup the bot for this server"""
        
        await interaction.response.defer(ephemeral=True)
        
        # Validate inputs
        if currency_min < 1 or currency_max < currency_min:
            await interaction.followup.send(
                "❌ Invalid currency range! Min must be >= 1 and Max must be >= Min.",
                ephemeral=True
            )
            return
        
        if max_wrestlers < 1:
            await interaction.followup.send(
                "❌ Max wrestlers must be at least 1!",
                ephemeral=True
            )
            return
        
        # Setup server with all channels enabled by default
        await self.db.setup_server(
            guild_id=interaction.guild_id,
            currency_name=currency_name,
            currency_symbol=currency_symbol,
            currency_min=currency_min,
            currency_max=currency_max,
            announcement_channel_id=announcement_channel.id,
            currency_channels=[],  # Empty = all channels
            max_wrestlers_per_user=max_wrestlers
        )
        
        embed = discord.Embed(
            title="✅ Server Setup Complete!",
            description="Your Wrestling League is ready to go!",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="💰 Currency Settings",
            value=(
                f"**Name:** {currency_name}\n"
                f"**Symbol:** {currency_symbol}\n"
                f"**Range:** {currency_symbol}{currency_min}-{currency_max} per message\n"
                f"**Cooldown:** 60 seconds"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📢 Announcement Channel",
            value=announcement_channel.mention,
            inline=True
        )
        
        embed.add_field(
            name="🏆 Wrestler Limit",
            value=f"{max_wrestlers} per user",
            inline=True
        )
        
        embed.add_field(
            name="💬 Currency Channels",
            value="All channels (use `/set_currency_channels` to customize)",
            inline=False
        )
        
        embed.set_footer(text="Users can now create wrestlers with /create_wrestler!")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="set_currency_channels", description="Set which channels earn currency (Admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_currency_channels(
        self,
        interaction: discord.Interaction,
        channel1: Optional[discord.TextChannel] = None,
        channel2: Optional[discord.TextChannel] = None,
        channel3: Optional[discord.TextChannel] = None,
        channel4: Optional[discord.TextChannel] = None,
        channel5: Optional[discord.TextChannel] = None
    ):
        """Set specific channels where users can earn currency"""
        
        channels = [ch for ch in [channel1, channel2, channel3, channel4, channel5] if ch is not None]
        
        if not channels:
            await interaction.response.send_message(
                "❌ You must select at least one channel! Or use `/enable_all_channels` to enable all channels.",
                ephemeral=True
            )
            return
        
        channel_ids = [ch.id for ch in channels]
        await self.db.update_server_setting(interaction.guild_id, 'currency_channels', channel_ids)
        
        channel_mentions = ", ".join([ch.mention for ch in channels])
        
        await interaction.response.send_message(
            f"✅ Currency earning enabled in: {channel_mentions}",
            ephemeral=True
        )
    
    @app_commands.command(name="enable_all_channels", description="Enable currency earning in ALL channels (Admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def enable_all_channels(self, interaction: discord.Interaction):
        """Enable currency in all channels"""
        
        await self.db.update_server_setting(interaction.guild_id, 'currency_channels', [])
        
        await interaction.response.send_message(
            "✅ Currency earning enabled in **all channels**!",
            ephemeral=True
        )
    
    @app_commands.command(name="set_max_wrestlers", description="Set default max wrestlers per user (Admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_max_wrestlers(self, interaction: discord.Interaction, max_wrestlers: int):
        """Set server-wide max wrestlers per user"""
        
        if max_wrestlers < 1:
            await interaction.response.send_message(
                "❌ Max wrestlers must be at least 1!",
                ephemeral=True
            )
            return
        
        await self.db.update_server_setting(interaction.guild_id, 'max_wrestlers_per_user', max_wrestlers)
        
        await interaction.response.send_message(
            f"✅ Default wrestler limit set to **{max_wrestlers}** per user!",
            ephemeral=True
        )
    
    @app_commands.command(name="set_user_limit", description="Set custom wrestler limit for a specific user (Admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_user_limit(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        limit: int
    ):
        """Set custom wrestler limit for a user"""
        
        if limit < 0:
            await interaction.response.send_message(
                "❌ Limit must be 0 or higher! (0 = unlimited)",
                ephemeral=True
            )
            return
        
        # 0 means unlimited - store as 999
        actual_limit = 999 if limit == 0 else limit
        await self.db.set_user_wrestler_limit(interaction.guild_id, user.id, actual_limit)
        
        limit_text = "unlimited" if limit == 0 else str(limit)
        await interaction.response.send_message(
            f"✅ {user.mention} can now create **{limit_text}** wrestlers!",
            ephemeral=True
        )
    
    @app_commands.command(name="view_upgrades", description="View all pending wrestler upgrades (Admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def view_upgrades(self, interaction: discord.Interaction):
        """View pending upgrades that need to be applied in WWE 2K"""
        
        upgrades = await self.db.get_pending_upgrades(interaction.guild_id)
        
        embed = create_pending_upgrades_embed(upgrades)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="clear_upgrades", description="Mark all upgrades as processed (Admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def clear_upgrades(self, interaction: discord.Interaction):
        """Clear the upgrade queue after applying them in-game"""
        
        upgrades = await self.db.get_pending_upgrades(interaction.guild_id)
        
        if not upgrades:
            await interaction.response.send_message(
                "✅ No pending upgrades to clear!",
                ephemeral=True
            )
            return
        
        # Create confirmation view
        class ConfirmView(discord.ui.View):
            def __init__(self, db, guild_id):
                super().__init__(timeout=60)
                self.db = db
                self.guild_id = guild_id
                self.value = None
            
            @discord.ui.button(label="Confirm Clear", style=discord.ButtonStyle.danger)
            async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
                await self.db.clear_processed_upgrades(self.guild_id)
                await interaction.response.edit_message(
                    content=f"✅ Cleared {len(upgrades)} upgrade(s) from the queue!",
                    embed=None,
                    view=None
                )
                self.value = True
                self.stop()
            
            @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
            async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.response.edit_message(
                    content="❌ Cancelled. Upgrades were not cleared.",
                    embed=None,
                    view=None
                )
                self.value = False
                self.stop()
        
        view = ConfirmView(self.db, interaction.guild_id)
        
        embed = discord.Embed(
            title="⚠️ Confirm Clear Upgrades",
            description=f"Are you sure you want to mark **{len(upgrades)} upgrade(s)** as processed?",
            color=discord.Color.orange()
        )
        embed.add_field(
            name="Note",
            value="Only do this after you've applied these upgrades in WWE 2K!",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Admin(bot))
