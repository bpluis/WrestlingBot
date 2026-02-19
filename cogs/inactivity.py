import discord
from discord import app_commands
from discord.ext import commands, tasks
from database import Database
from datetime import datetime, timedelta
from typing import Optional, List


# Autocomplete for wrestlers
async def wrestler_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    db = Database()
    wrestlers = await db.get_all_wrestlers(interaction.guild_id)
    if not wrestlers:
        return [app_commands.Choice(name="(No wrestlers found)", value="none")]
    filtered = [w for w in wrestlers if current.lower() in w['name'].lower()][:25]
    return [app_commands.Choice(name=w['name'], value=w['name']) for w in filtered]


class Inactivity(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
        self.inactivity_check.start()
    
    def cog_unload(self):
        self.inactivity_check.cancel()
    
    # Command Group
    inactivity_group = app_commands.Group(
        name="inactivity",
        description="Inactivity system management"
    )
    
    # ==================== DAILY TASK ====================
    
    @tasks.loop(hours=24)
    async def inactivity_check(self):
        """Daily check for inactive wrestlers"""
        print("🔄 Running daily inactivity check...")
        for guild in self.bot.guilds:
            try:
                await self._check_guild_inactivity(guild)
            except Exception as e:
                print(f"❌ Inactivity check failed for guild {guild.id}: {e}")
        print("✅ Inactivity check complete!")
    
    @inactivity_check.before_loop
    async def before_inactivity_check(self):
        await self.bot.wait_until_ready()
    
    async def _check_guild_inactivity(self, guild: discord.Guild):
        """Check and process inactivity for a single guild"""
        
        settings = await self.db.get_server_settings(guild.id)
        if not settings or not settings.get('setup_completed'):
            return
        
        inactivity_days = settings.get('inactivity_days', 30)
        warning_days = settings.get('warning_days', 25)
        log_channel_id = settings.get('inactivity_log_channel_id')
        log_channel = guild.get_channel(log_channel_id) if log_channel_id else None
        
        # Get current champions
        champion_wrestler_ids = [c['wrestler_id'] for c in await self.db.get_wrestler_champions(guild.id)]
        
        # ===== SET INACTIVE =====
        inactive_wrestlers = await self.db.get_inactive_wrestlers(guild.id, inactivity_days)
        
        for wrestler in inactive_wrestlers:
            await self.db.set_wrestler_inactive(wrestler['id'])
            
            days_inactive = 0
            if wrestler.get('last_active'):
                last = datetime.fromisoformat(wrestler['last_active'])
                days_inactive = (datetime.utcnow() - last).days
            
            print(f"  💤 {wrestler['name']} set inactive ({days_inactive} days)")
            is_champion = wrestler['id'] in champion_wrestler_ids
            
            if log_channel:
                embed = discord.Embed(
                    title="💤 Wrestler Inactive",
                    description=f"**{wrestler['name']}** has been set to inactive.",
                    color=discord.Color.red() if is_champion else discord.Color.orange()
                )
                embed.add_field(name="Owner", value=f"<@{wrestler['user_id']}>", inline=True)
                embed.add_field(name="Days Inactive", value=f"{days_inactive} days", inline=True)
                
                if is_champion:
                    champ_info = next(
                        (c for c in await self.db.get_wrestler_champions(guild.id) if c['wrestler_id'] == wrestler['id']),
                        None
                    )
                    embed.add_field(
                        name="⚠️ CHAMPION ALERT",
                        value=f"Holds **{champ_info['championship_name']}**!\nConsider `/championship force_vacate`",
                        inline=False
                    )
                
                await log_channel.send(embed=embed)
            
            await self._send_inactive_dm(guild, wrestler, days_inactive)
        
        # ===== WARNINGS =====
        warning_wrestlers = await self.db.get_warning_wrestlers(guild.id, warning_days, inactivity_days)
        
        for wrestler in warning_wrestlers:
            days_inactive = 0
            if wrestler.get('last_active'):
                last = datetime.fromisoformat(wrestler['last_active'])
                days_inactive = (datetime.utcnow() - last).days
            
            days_until_inactive = inactivity_days - days_inactive
            if days_inactive == warning_days:
                await self._send_warning_dm(guild, wrestler, days_until_inactive)
    
    async def _send_warning_dm(self, guild: discord.Guild, wrestler: dict, days_until_inactive: int):
        """Send warning DM - checks if user is still in server!"""
        try:
            member = guild.get_member(wrestler['user_id'])
            if not member:
                print(f"  ⚠️ User {wrestler['user_id']} not in server, skipping DM")
                return
            
            embed = discord.Embed(
                title="⚠️ Inactivity Warning",
                description=f"**{wrestler['name']}** will become inactive in **{days_until_inactive} days**!",
                color=discord.Color.yellow()
            )
            embed.add_field(
                name="How to stay active",
                value="Use any command: `/daily`, `/shop`, `/apply`, etc.",
                inline=False
            )
            embed.set_footer(text=f"Server: {guild.name}")
            await member.send(embed=embed)
            
        except discord.Forbidden:
            print(f"  ⚠️ Cannot DM user {wrestler['user_id']} (DMs disabled)")
        except Exception as e:
            print(f"  ❌ DM error: {e}")
    
    async def _send_inactive_dm(self, guild: discord.Guild, wrestler: dict, days_inactive: int):
        """Send inactive DM - checks if user is still in server!"""
        try:
            member = guild.get_member(wrestler['user_id'])
            if not member:
                print(f"  ⚠️ User {wrestler['user_id']} not in server, skipping DM")
                return
            
            embed = discord.Embed(
                title="💤 Wrestler Now Inactive",
                description=f"**{wrestler['name']}** is now inactive after **{days_inactive} days**.",
                color=discord.Color.red()
            )
            embed.add_field(
                name="What this means",
                value="• Cannot be booked in events\n• Won't appear in /apply\n• Stats preserved",
                inline=False
            )
            embed.add_field(
                name="How to return",
                value="Use any command and you'll be active again automatically!",
                inline=False
            )
            embed.set_footer(text=f"Server: {guild.name}")
            await member.send(embed=embed)
            
        except discord.Forbidden:
            print(f"  ⚠️ Cannot DM user {wrestler['user_id']} (DMs disabled)")
        except Exception as e:
            print(f"  ❌ DM error: {e}")
    
    # ==================== COMMANDS ====================
    
    @inactivity_group.command(name="setup", description="Configure inactivity settings")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup(
        self,
        interaction: discord.Interaction,
        inactivity_days: int,
        warning_days: Optional[int] = None,
        log_channel: Optional[discord.TextChannel] = None
    ):
        """Configure inactivity settings"""
        
        if inactivity_days < 7:
            await interaction.response.send_message(
                "❌ Inactivity days must be at least 7!", ephemeral=True
            )
            return
        
        if warning_days is None:
            warning_days = inactivity_days - 5
        
        if warning_days >= inactivity_days:
            await interaction.response.send_message(
                "❌ Warning days must be less than inactivity days!", ephemeral=True
            )
            return
        
        log_channel_id = log_channel.id if log_channel else None
        await self.db.update_inactivity_settings(
            interaction.guild_id, inactivity_days, warning_days, log_channel_id
        )
        
        embed = discord.Embed(
            title="⚙️ Inactivity Settings Updated",
            color=discord.Color.green()
        )
        embed.add_field(name="Inactive After", value=f"**{inactivity_days}** days", inline=True)
        embed.add_field(name="Warning At", value=f"**{warning_days}** days", inline=True)
        embed.add_field(name="Log Channel", value=log_channel.mention if log_channel else "Not set", inline=True)
        embed.add_field(
            name="How it works",
            value=f"• Day {warning_days}: User gets DM warning ⚠️\n"
                  f"• Day {inactivity_days}: Wrestler set inactive 💤\n"
                  f"• Any command = auto reactivation ✅",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
    
    @inactivity_group.command(name="check", description="Check inactivity status")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.autocomplete(wrestler=wrestler_autocomplete)
    async def check(
        self,
        interaction: discord.Interaction,
        wrestler: Optional[str] = None
    ):
        """Check specific wrestler or full server report"""
        
        settings = await self.db.get_server_settings(interaction.guild_id)
        inactivity_days = settings.get('inactivity_days', 30)
        warning_days = settings.get('warning_days', 25)
        
        if wrestler:
            # ===== SPECIFIC WRESTLER =====
            all_wrestlers = await self.db.get_all_wrestlers(interaction.guild_id)
            wrestler_obj = next((w for w in all_wrestlers if w['name'].lower() == wrestler.lower()), None)
            
            if not wrestler_obj:
                await interaction.response.send_message(f"❌ '{wrestler}' not found!", ephemeral=True)
                return
            
            days_inactive = 0
            if wrestler_obj.get('last_active'):
                last = datetime.fromisoformat(wrestler_obj['last_active'])
                days_inactive = (datetime.utcnow() - last).days
            
            is_inactive = bool(wrestler_obj.get('is_inactive', 0))
            days_until_inactive = max(0, inactivity_days - days_inactive)
            
            if is_inactive:
                status = "💤 INACTIVE"
                color = discord.Color.red()
            elif days_inactive >= warning_days:
                status = "⚠️ WARNING"
                color = discord.Color.yellow()
            else:
                status = "✅ ACTIVE"
                color = discord.Color.green()
            
            embed = discord.Embed(title=f"{status} - {wrestler_obj['name']}", color=color)
            embed.add_field(name="Owner", value=f"<@{wrestler_obj['user_id']}>", inline=True)
            embed.add_field(name="Days Inactive", value=f"{days_inactive} days", inline=True)
            
            if not is_inactive:
                embed.add_field(
                    name="Goes Inactive In",
                    value=f"{days_until_inactive} days" if days_until_inactive > 0 else "Today!",
                    inline=True
                )
            
            if wrestler_obj.get('last_active'):
                last_dt = datetime.fromisoformat(wrestler_obj['last_active'])
                embed.add_field(name="Last Active", value=last_dt.strftime("%Y-%m-%d"), inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        else:
            # ===== FULL SERVER REPORT =====
            await interaction.response.defer(ephemeral=True)
            
            going_inactive = await self.db.get_inactive_wrestlers(interaction.guild_id, inactivity_days)
            warnings = await self.db.get_warning_wrestlers(interaction.guild_id, warning_days, inactivity_days)
            
            embed = discord.Embed(title="📊 Inactivity Report", color=discord.Color.blue())
            embed.add_field(
                name="⚙️ Settings",
                value=f"Inactive after: **{inactivity_days}** days\nWarning at: **{warning_days}** days",
                inline=False
            )
            
            if going_inactive:
                inactive_list = "\n".join([f"• **{w['name']}** (<@{w['user_id']}>)" for w in going_inactive[:10]])
                embed.add_field(name=f"💤 Going Inactive ({len(going_inactive)})", value=inactive_list, inline=False)
            else:
                embed.add_field(name="💤 Going Inactive", value="None ✅", inline=False)
            
            if warnings:
                warning_list = "\n".join([f"• **{w['name']}** (<@{w['user_id']}>)" for w in warnings[:10]])
                embed.add_field(name=f"⚠️ Approaching ({len(warnings)})", value=warning_list, inline=False)
            else:
                embed.add_field(name="⚠️ Approaching Inactivity", value="None ✅", inline=False)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @inactivity_group.command(name="toggle_status", description="Toggle active/inactive status of a wrestler")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.autocomplete(wrestler=wrestler_autocomplete)
    async def toggle_status(
        self,
        interaction: discord.Interaction,
        wrestler: str
    ):
        """Toggle wrestler between active and inactive"""
        
        all_wrestlers = await self.db.get_all_wrestlers(interaction.guild_id)
        wrestler_obj = next((w for w in all_wrestlers if w['name'].lower() == wrestler.lower()), None)
        
        if not wrestler_obj:
            await interaction.response.send_message(f"❌ '{wrestler}' not found!", ephemeral=True)
            return
        
        is_currently_inactive = bool(wrestler_obj.get('is_inactive', 0))
        
        if is_currently_inactive:
            await self.db.set_wrestler_active(wrestler_obj['id'])
            embed = discord.Embed(
                title="✅ Wrestler Activated",
                description=f"**{wrestler_obj['name']}** is now active!",
                color=discord.Color.green()
            )
            embed.add_field(name="Owner", value=f"<@{wrestler_obj['user_id']}>", inline=True)
            embed.add_field(name="Status", value="💤 Inactive → ✅ Active", inline=True)
        else:
            await self.db.set_wrestler_inactive(wrestler_obj['id'])
            embed = discord.Embed(
                title="💤 Wrestler Deactivated",
                description=f"**{wrestler_obj['name']}** is now inactive!",
                color=discord.Color.orange()
            )
            embed.add_field(name="Owner", value=f"<@{wrestler_obj['user_id']}>", inline=True)
            embed.add_field(name="Status", value="✅ Active → 💤 Inactive", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Inactivity(bot))
