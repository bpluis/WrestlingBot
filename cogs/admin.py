import discord
from discord import app_commands
from discord.ext import commands
from database import Database
from typing import Optional, List

# Autocomplete for wrestlers
async def wrestler_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    db = Database()
    wrestlers = await db.get_all_wrestlers(interaction.guild_id)
    if not wrestlers:
        return [app_commands.Choice(name="(No wrestlers found)", value="none")]
    filtered = [w for w in wrestlers if current.lower() in w['name'].lower()][:25]
    return [app_commands.Choice(name=w['name'], value=w['name']) for w in filtered]


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
    
    # Create command group
    admin_group = app_commands.Group(name="admin", description="Admin commands for server management")
    
    @admin_group.command(name="setup", description="Initial server setup")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup(
        self,
        interaction: discord.Interaction,
        currency_name: str,
        currency_symbol: str,
        announcement_channel: discord.TextChannel,
        booker_role: Optional[discord.Role] = None
    ):
        """Initial server setup"""
        
        # Check if already setup
        settings = await self.db.get_server_settings(interaction.guild_id)
        if settings and settings.get('setup_completed'):
            await interaction.response.send_message(
                "⚠️ Server already configured! Use other `/admin` commands to modify settings.",
                ephemeral=True
            )
            return
        
        # Create settings
        await self.db.create_server_settings(
            interaction.guild_id,
            currency_name,
            currency_symbol,
            announcement_channel.id,
            booker_role.id if booker_role else None
        )
        
        embed = discord.Embed(
            title="✅ Server Setup Complete!",
            description="Your wrestling league is ready!",
            color=discord.Color.green()
        )
        
        embed.add_field(name="Currency", value=f"{currency_symbol}{currency_name}", inline=True)
        embed.add_field(name="Announcement Channel", value=announcement_channel.mention, inline=True)
        if booker_role:
            embed.add_field(name="Booker Role", value=booker_role.mention, inline=True)
        
        embed.add_field(
            name="Next Steps",
            value="• Users can now `/wrestler create`\n"
                  "• Create championships with `/championship create`\n"
                  "• Create events with `/event template`",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
    
    @admin_group.command(name="set_booker", description="Assign booker role")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_booker(self, interaction: discord.Interaction, role: discord.Role):
        """Set the booker role for event/match management"""
        
        await self.db.set_booker_role(interaction.guild_id, role.id)
        
        await interaction.response.send_message(
            f"✅ **{role.name}** can now manage events and record matches!",
            ephemeral=True
        )
    
    @admin_group.command(name="remove_booker", description="Remove booker role")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_booker(self, interaction: discord.Interaction):
        """Remove the booker role (admin only can manage)"""
        
        await self.db.set_booker_role(interaction.guild_id, None)
        
        await interaction.response.send_message(
            "✅ Booker role removed. Only admins can manage events now.",
            ephemeral=True
        )
    
    @admin_group.command(name="set_currency", description="Change currency settings")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_currency(
        self,
        interaction: discord.Interaction,
        currency_name: str,
        currency_symbol: str
    ):
        """Update currency name and symbol"""
        
        await self.db.update_currency_settings(
            interaction.guild_id,
            currency_name,
            currency_symbol
        )
        
        await interaction.response.send_message(
            f"✅ Currency updated to: **{currency_symbol}{currency_name}**",
            ephemeral=True
        )
    
    @admin_group.command(name="set_shop_channel", description="Restrict shop to specific channel")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_shop_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Set which channel the shop can be used in"""
        
        await self.db.set_shop_channel(interaction.guild_id, channel.id)
        
        await interaction.response.send_message(
            f"✅ Shop restricted to {channel.mention}",
            ephemeral=True
        )
    
    @admin_group.command(name="bonus", description="Give currency bonus to wrestler")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.autocomplete(wrestler_name=wrestler_autocomplete)
    async def bonus(
        self,
        interaction: discord.Interaction,
        wrestler_name: str,
        amount: int,
        reason: Optional[str] = None
    ):
        """Give currency bonus to a wrestler"""
        
        # Get wrestler
        all_wrestlers = await self.db.get_all_wrestlers(interaction.guild_id)
        wrestler = next((w for w in all_wrestlers if w['name'].lower() == wrestler_name.lower()), None)
        
        if not wrestler:
            await interaction.response.send_message(
                f"❌ Wrestler '{wrestler_name}' not found!",
                ephemeral=True
            )
            return
        
        # Get settings
        settings = await self.db.get_server_settings(interaction.guild_id)
        symbol = settings['currency_symbol']
        
        # Update currency
        await self.db.update_wrestler_currency(wrestler['id'], amount)
        new_balance = wrestler['currency'] + amount
        
        embed = discord.Embed(
            title="💰 Admin Bonus Given!",
            description=f"**{wrestler['name']}** received a bonus",
            color=discord.Color.gold()
        )
        
        embed.add_field(name="Amount", value=f"{symbol}{amount:,}", inline=True)
        embed.add_field(name="New Balance", value=f"{symbol}{new_balance:,}", inline=True)
        
        if reason:
            embed.add_field(name="Reason", value=reason, inline=False)
        
        embed.set_footer(text=f"Given by {interaction.user.display_name}")
        
        await interaction.response.send_message(embed=embed)
    
    @admin_group.command(name="wrestler_limit", description="Set wrestler creation limit")
    @app_commands.checks.has_permissions(administrator=True)
    async def wrestler_limit(
        self,
        interaction: discord.Interaction,
        limit: int,
        user: Optional[discord.Member] = None
    ):
        """Set wrestler limit globally or for specific user"""
        
        if limit < 1:
            await interaction.response.send_message(
                "❌ Limit must be at least 1!",
                ephemeral=True
            )
            return
        
        if user:
            # Set limit for specific user
            try:
                await self.db.set_user_wrestler_limit(interaction.guild_id, user.id, limit)
                
                await interaction.response.send_message(
                    f"✅ **{user.display_name}** can now create up to **{limit}** wrestler(s)!",
                    ephemeral=True
                )
            except Exception as e:
                await interaction.response.send_message(
                    f"❌ Error setting user limit: {str(e)}",
                    ephemeral=True
                )
        else:
            # Set global default
            await self.db.set_default_wrestler_limit(interaction.guild_id, limit)
            
            await interaction.response.send_message(
                f"✅ Default wrestler limit set to **{limit}** for all users!",
                ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(Admin(bot))
