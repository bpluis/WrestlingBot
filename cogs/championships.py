import discord
from discord import app_commands
from discord.ext import commands
from database import Database
from datetime import datetime
from typing import Optional, List

# Weight class options
WEIGHT_CLASSES = ["All", "Cruiser", "Light", "Heavy", "Superheavy", "Ultraheavy"]

# Gender options
GENDER_OPTIONS = ["Male", "Female", "Mixed"]

# Permission check helper
async def is_admin_or_booker(interaction: discord.Interaction, db: Database) -> bool:
    """Check if user is admin or has booker role"""
    if interaction.user.guild_permissions.administrator:
        return True
    
    settings = await db.get_server_settings(interaction.guild_id)
    if settings and settings.get('booker_role_id'):
        booker_role_id = settings['booker_role_id']
        return any(role.id == booker_role_id for role in interaction.user.roles)
    
    return False

# Autocomplete for championships
async def championship_autocomplete(
    interaction: discord.Interaction,
    current: str
) -> List[app_commands.Choice[str]]:
    """Autocomplete for championship names"""
    db = Database()
    championships = await db.get_all_championships(interaction.guild_id)
    
    if not championships:
        return [app_commands.Choice(name="(No championships found)", value="none")]
    
    filtered = [
        c for c in championships 
        if current.lower() in c['name'].lower()
    ][:25]
    
    return [
        app_commands.Choice(name=c['name'], value=c['name'])
        for c in filtered
    ]

# Autocomplete for wrestlers
async def wrestler_autocomplete(
    interaction: discord.Interaction,
    current: str
) -> List[app_commands.Choice[str]]:
    """Autocomplete for wrestler names"""
    db = Database()
    wrestlers = await db.get_all_wrestlers(interaction.guild_id)
    
    if not wrestlers:
        return [app_commands.Choice(name="(No wrestlers found)", value="none")]
    
    filtered = [
        w for w in wrestlers 
        if current.lower() in w['name'].lower()
    ][:25]
    
    return [
        app_commands.Choice(name=w['name'], value=w['name'])
        for w in filtered
    ]


class Championships(commands.Cog):  # Keep same name
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
    
    # Add command group
    championship_group = app_commands.Group(name="championship", description="Championship management")
    
    @championship_group.command(name="create", description="Create a new championship (Admin/Booker only)")
    @app_commands.choices(
        gender=[
            app_commands.Choice(name="Male Only", value="Male"),
            app_commands.Choice(name="Female Only", value="Female"),
            app_commands.Choice(name="Mixed (Any Gender)", value="Mixed")
        ],
        weight_class=[
            app_commands.Choice(name="All Weight Classes", value="All"),
            app_commands.Choice(name="Cruiserweight", value="Cruiser"),
            app_commands.Choice(name="Light Heavyweight", value="Light"),
            app_commands.Choice(name="Heavyweight", value="Heavy"),
            app_commands.Choice(name="Super Heavyweight", value="Superheavy"),
            app_commands.Choice(name="Ultra Heavyweight", value="Ultraheavy")
        ],
        tag_team=[
            app_commands.Choice(name="Singles Championship", value="No"),
            app_commands.Choice(name="Tag Team Championship", value="Yes")
        ]
    )
    async def create_championship(
        self,
        interaction: discord.Interaction,
        name: str,
        gender: app_commands.Choice[str],
        weight_class: app_commands.Choice[str],
        tag_team: app_commands.Choice[str],
        description: Optional[str] = None
    ):
        """Create a new championship"""
        
        # Check permissions
        if not await is_admin_or_booker(interaction, self.db):
            await interaction.response.send_message(
                "❌ You need administrator permissions or the Booker role to create championships!",
                ephemeral=True
            )
            return
        
        # Check if championship already exists
        existing = await self.db.get_championship_by_name(interaction.guild_id, name)
        if existing:
            await interaction.response.send_message(
                f"❌ A championship named **{name}** already exists!",
                ephemeral=True
            )
            return
        
        # Create championship
        is_tag = tag_team.value == "Yes"
        champ_id = await self.db.create_championship(
            guild_id=interaction.guild_id,
            name=name,
            description=description,
            gender_requirement=gender.value,
            weight_class_requirement=weight_class.value,
            is_tag_team=is_tag
        )
        
        # Create announcement embed
        embed = discord.Embed(
            title="🏆 New Championship Created!",
            description=f"**{name}**",
            color=discord.Color.gold()
        )
        
        if description:
            embed.add_field(
                name="Description",
                value=description,
                inline=False
            )
        
        embed.add_field(
            name="Type",
            value="Tag Team Championship" if is_tag else "Singles Championship",
            inline=True
        )
        
        embed.add_field(
            name="Gender Requirement",
            value=gender.value,
            inline=True
        )
        
        embed.add_field(
            name="Weight Class",
            value=weight_class.value,
            inline=True
        )
        
        embed.add_field(
            name="Status",
            value="🔓 Vacant - No current champion",
            inline=False
        )
        
        embed.set_footer(text=f"Championship ID: {champ_id}")
        embed.timestamp = datetime.utcnow()
        
        await interaction.response.send_message(embed=embed)
    
    @championship_group.command(name="assign", description="Assign champion(s) to vacant title (Admin/Booker)")
    @app_commands.autocomplete(
        championship=championship_autocomplete,
        wrestler1=wrestler_autocomplete,
        wrestler2=wrestler_autocomplete
    )
    async def assign_champion(
        self,
        interaction: discord.Interaction,
        championship: str,
        wrestler1: str,
        wrestler2: Optional[str] = None
    ):
        """Manually assign champion(s). Use wrestler2 for tag team titles."""
        
        # Check permissions
        if not await is_admin_or_booker(interaction, self.db):
            await interaction.response.send_message(
                "❌ You need administrator permissions or the Booker role to assign champions!",
                ephemeral=True
            )
            return
        
        # Get championship
        champ = await self.db.get_championship_by_name(interaction.guild_id, championship)
        if not champ:
            await interaction.response.send_message(
                f"❌ Championship '{championship}' not found!",
                ephemeral=True
            )
            return
        
        # Get wrestlers
        all_wrestlers = await self.db.get_all_wrestlers(interaction.guild_id)
        wrestler1_obj = next((w for w in all_wrestlers if w['name'].lower() == wrestler1.lower()), None)
        
        if not wrestler1_obj:
            await interaction.response.send_message(
                f"❌ Wrestler '{wrestler1}' not found!",
                ephemeral=True
            )
            return
        
        # Check if tag team title requires 2 wrestlers
        if champ['is_tag_team'] and not wrestler2:
            await interaction.response.send_message(
                f"❌ **{championship}** is a tag team championship!\n"
                f"You must specify both wrestlers:\n"
                f"`/assign_champion championship:\"{championship}\" wrestler1:\"Name1\" wrestler2:\"Name2\"`",
                ephemeral=True
            )
            return
        
        # Get second wrestler for tag teams
        wrestler2_obj = None
        if wrestler2:
            wrestler2_obj = next((w for w in all_wrestlers if w['name'].lower() == wrestler2.lower()), None)
            if not wrestler2_obj:
                await interaction.response.send_message(
                    f"❌ Wrestler '{wrestler2}' not found!",
                    ephemeral=True
                )
                return
            
            # Verify it's a tag team title
            if not champ['is_tag_team']:
                await interaction.response.send_message(
                    f"❌ **{championship}** is NOT a tag team championship!\n"
                    f"Only assign one wrestler for singles titles.",
                    ephemeral=True
                )
                return
        
        # Check if title is vacant (check new field first, fallback to old)
        current_champion_ids = champ.get('current_champion_ids')
        is_vacant = True
        
        if current_champion_ids:
            import json
            champ_ids = json.loads(current_champion_ids) if isinstance(current_champion_ids, str) else current_champion_ids
            if champ_ids and len(champ_ids) > 0:
                is_vacant = False
                # Get current champion names
                champ_names = []
                for champ_id in champ_ids:
                    c = await self.db.get_wrestler_by_id(champ_id, interaction.guild_id)
                    if c:
                        champ_names.append(c['name'])
        elif champ.get('current_champion_id'):
            # Fallback to old single champion field
            is_vacant = False
            current_champ = await self.db.get_wrestler_by_id(champ['current_champion_id'], interaction.guild_id)
            champ_names = [current_champ['name']]
        
        if not is_vacant:
            await interaction.response.send_message(
                f"❌ **{championship}** is currently held by **{' & '.join(champ_names)}**!\n"
                f"Use `/vacate_championship` first or record a title match.",
                ephemeral=True
            )
            return
        
        # Assign champion(s)
        if champ['is_tag_team']:
            # Tag team - create reigns for both
            await self.db.start_title_reign(
                championship_id=champ['id'],
                wrestler_id=wrestler1_obj['id'],
                wrestler_name=wrestler1_obj['name']
            )
            await self.db.start_title_reign(
                championship_id=champ['id'],
                wrestler_id=wrestler2_obj['id'],
                wrestler_name=wrestler2_obj['name']
            )
            
            # Update current champions
            await self.db.update_current_champions(champ['id'], [wrestler1_obj['id'], wrestler2_obj['id']])
            
            champion_names = f"{wrestler1_obj['name']} & {wrestler2_obj['name']}"
            title_text = "NEW CHAMPIONS!"
        else:
            # Singles - one reign
            await self.db.start_title_reign(
                championship_id=champ['id'],
                wrestler_id=wrestler1_obj['id'],
                wrestler_name=wrestler1_obj['name']
            )
            
            # Update current champion
            await self.db.update_current_champions(champ['id'], [wrestler1_obj['id']])
            
            champion_names = wrestler1_obj['name']
            title_text = "NEW CHAMPION!"
        
        # Announcement
        embed = discord.Embed(
            title=f"👑 {title_text}",
            description=f"**{champion_names}** {'are' if champ['is_tag_team'] else 'is'} now the **{championship}**!",
            color=discord.Color.gold()
        )
        
        embed.set_footer(text="Championship assigned by admin")
        embed.timestamp = datetime.utcnow()
        
        await interaction.response.send_message(embed=embed)
    
    @championship_group.command(name="vacate", description="Vacate a championship (Admin/Booker only)")
    @app_commands.autocomplete(championship=championship_autocomplete)
    async def vacate_championship(
        self,
        interaction: discord.Interaction,
        championship: str,
        reason: Optional[str] = None
    ):
        """Vacate a championship (injury, retirement, etc.)"""
        
        try:
            # Check permissions
            if not await is_admin_or_booker(interaction, self.db):
                await interaction.response.send_message(
                    "❌ You need administrator permissions or the Booker role to vacate championships!",
                    ephemeral=True
                )
                return
            
            print(f"[DEBUG] Vacating championship: {championship}")
            
            # Get championship
            champ = await self.db.get_championship_by_name(interaction.guild_id, championship)
            if not champ:
                await interaction.response.send_message(
                    f"❌ Championship '{championship}' not found!",
                    ephemeral=True
                )
                return
            
            print(f"[DEBUG] Championship found: {champ}")
            
            # Check if there's a current champion
            if not champ['current_champion_id']:
                await interaction.response.send_message(
                    f"❌ **{championship}** is already vacant!",
                    ephemeral=True
                )
                return
            
            print(f"[DEBUG] Current champion ID: {champ['current_champion_id']}")
            
            # Get current champion info
            current_champ = await self.db.get_wrestler_by_id(champ['current_champion_id'], interaction.guild_id)
            print(f"[DEBUG] Current champion: {current_champ['name']}")
            
            # End current reign
            await self.db.end_title_reign(champ['id'])
            print(f"[DEBUG] Reign ended")
            # Clear current champion(s)
            await self.db.update_current_champions(champ['id'], [])
            print(f"[DEBUG] Champions cleared")
            
            # Update championship to vacant
            await self.db.update_current_champion(champ['id'], None)
            print(f"[DEBUG] Champion updated to None")
            
            # Announcement
            embed = discord.Embed(
                title="🔓 Championship Vacated",
                description=f"**{current_champ['name']}** has vacated the **{championship}**",
                color=discord.Color.orange()
            )
            
            if reason:
                embed.add_field(
                    name="Reason",
                    value=reason,
                    inline=False
                )
            
            embed.add_field(
                name="Status",
                value="The championship is now vacant",
                inline=False
            )
            
            embed.timestamp = datetime.utcnow()
            
            print(f"[DEBUG] Sending response...")
            await interaction.response.send_message(embed=embed)
            print(f"[DEBUG] SUCCESS!")
            
        except Exception as e:
            print(f"[ERROR] vacate_championship failed: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            
            try:
                await interaction.response.send_message(
                    f"❌ **Error:** {type(e).__name__}: {str(e)}",
                    ephemeral=True
                )
            except:
                try:
                    await interaction.followup.send(
                        f"❌ **Error:** {type(e).__name__}: {str(e)}",
                        ephemeral=True
                    )
                except:
                    print("[ERROR] Could not send error message to user")
    
    @app_commands.command(name="champions", description="View all current champions")
    async def champions(self, interaction: discord.Interaction):
        """Show all current champions"""
        
        championships = await self.db.get_all_championships(interaction.guild_id)
        
        if not championships:
            await interaction.response.send_message(
                "❌ No championships have been created yet!",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="👑 Current Champions",
            color=discord.Color.gold()
        )
        
        has_champions = False
        
        for champ in championships:
            if champ['current_champion_id']:
                has_champions = True
                # Get champion info
                champion = await self.db.get_wrestler_by_id(champ['current_champion_id'], interaction.guild_id)
                
                # Get current reign info
                reign = await self.db.get_current_reign(champ['id'])
                
                if reign:
                    # Calculate days held
                    won_date = datetime.fromisoformat(reign['won_date'])
                    days_held = (datetime.utcnow() - won_date).days
                    
                    value = (
                        f"👑 **{champion['name']}**\n"
                        f"📅 Reign: {days_held} days\n"
                        f"🛡️ Defenses: {reign['successful_defenses']}"
                    )
                else:
                    value = f"👑 **{champion['name']}**"
                
                embed.add_field(
                    name=f"🏆 {champ['name']}",
                    value=value,
                    inline=False
                )
        
        # Show vacant titles
        vacant = [c for c in championships if not c['current_champion_id']]
        if vacant:
            vacant_list = "\n".join([f"🔓 {c['name']}" for c in vacant])
            embed.add_field(
                name="Vacant Championships",
                value=vacant_list,
                inline=False
            )
        
        if not has_champions and not vacant:
            embed.description = "No championships or champions yet!"
        
        await interaction.response.send_message(embed=embed)
    
    @championship_group.command(name="history", description="View title history")
    @app_commands.autocomplete(championship=championship_autocomplete)
    async def title_history(
        self,
        interaction: discord.Interaction,
        championship: str
    ):
        """View all reigns for a championship"""
        
        # Get championship
        champ = await self.db.get_championship_by_name(interaction.guild_id, championship)
        if not champ:
            await interaction.response.send_message(
                f"❌ Championship '{championship}' not found!",
                ephemeral=True
            )
            return
        
        # Get all reigns
        reigns = await self.db.get_championship_reigns(champ['id'])
        
        if not reigns:
            await interaction.response.send_message(
                f"📜 **{championship}** has no title history yet.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title=f"📜 {championship} - Title History",
            color=discord.Color.gold()
        )
        
        for reign in reigns:
            # Format dates
            won_date = datetime.fromisoformat(reign['won_date']).strftime("%Y-%m-%d")
            
            if reign['is_current']:
                status = "👑 **CURRENT CHAMPION**"
                days = (datetime.utcnow() - datetime.fromisoformat(reign['won_date'])).days
            else:
                lost_date = datetime.fromisoformat(reign['lost_date']).strftime("%Y-%m-%d")
                status = f"Lost: {lost_date}"
                days = reign['days_held']
            
            value = (
                f"{status}\n"
                f"📅 Won: {won_date}\n"
                f"⏱️ Days held: {days}\n"
                f"🛡️ Successful defenses: {reign['successful_defenses']}"
            )
            
            embed.add_field(
                name=f"Reign #{reign['reign_number']}: {reign['wrestler_name']}",
                value=value,
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    @championship_group.command(name="list", description="List all championships")
    async def list_championships(self, interaction: discord.Interaction):
        """List all championships"""
    
        championships = await self.db.get_all_championships(interaction.guild_id)
    
        if not championships:
                await interaction.response.send_message(
                "❌ No championships created yet!",
                ephemeral=True
                )
                return
    
        embed = discord.Embed(
            title="🏆 Championships",
            color=discord.Color.gold()
        )
    
        for champ in championships:
            # Get current champion(s)
            if champ.get('current_champion_ids'):
                import json
                champ_ids = json.loads(champ['current_champion_ids']) if isinstance(champ['current_champion_ids'], str) else champ['current_champion_ids']
            
                # Get wrestler names
                all_wrestlers = await self.db.get_all_wrestlers(interaction.guild_id)
                champ_names = []
                for c_id in champ_ids:
                    w = next((wr for wr in all_wrestlers if wr['id'] == c_id), None)
                    if w:
                        champ_names.append(w['name'])
            
                if champ_names:
                    champion_text = " & ".join(champ_names) if len(champ_names) > 1 else champ_names[0]
            else:
                champion_text = "*Vacant*"
        else:
            champion_text = "*Vacant*"
        
        embed.add_field(
            name=champ['name'],
            value=f"👑 {champion_text}",
            inline=False
        )
    
        await interaction.response.send_message(embed=embed)


    @championship_group.command(name="current", description="View current champions")
    async def current(self, interaction: discord.Interaction):
        """Show all current champions"""
        import json  # ← NACH OBEN VERSCHIEBEN
    
        championships = await self.db.get_all_championships(interaction.guild_id)
    
        embed = discord.Embed(
            title="👑 Current Champions",
            color=discord.Color.gold()
        )
    
        has_champions = False
    
        for champ in championships:
            champ_ids_raw = champ.get('current_champion_ids')
        
            # DIESE ZEILE ÄNDERN - Check ob nicht leer/null/"[]"
            if champ_ids_raw and champ_ids_raw not in [None, '', '[]', 'null']:
                champ_ids = json.loads(champ_ids_raw) if isinstance(champ_ids_raw, str) else champ_ids_raw
            
                # Zusätzlicher Check ob Liste nicht leer
                if champ_ids and len(champ_ids) > 0:  # ← NEU!
                    # Get wrestler names
                    all_wrestlers = await self.db.get_all_wrestlers(interaction.guild_id)
                    champ_names = []
                    for c_id in champ_ids:
                        w = next((wr for wr in all_wrestlers if wr['id'] == c_id), None)
                        if w:
                            champ_names.append(w['name'])
                
                    if champ_names:
                        has_champions = True
                        embed.add_field(
                            name=f"🏆 {champ['name']}",
                            value=" & ".join(champ_names) if len(champ_names) > 1 else champ_names[0],
                            inline=False
                        )
                    else:
                        # IDs da aber Wrestler nicht gefunden (retired!)
                        embed.add_field(
                            name=f"🏆 {champ['name']}",
                            value="*Vacant* (Champion retired)",
                            inline=False
                        )
                else:
                    # Leere Liste
                    embed.add_field(
                        name=f"🏆 {champ['name']}",
                        value="*Vacant*",
                        inline=False
                    )
            else:
                # Null oder "[]"
                embed.add_field(
                    name=f"🏆 {champ['name']}",
                    value="*Vacant*",
                    inline=False
                )
    
        if not has_champions:
            embed.description = "No current champions. All titles are vacant!"
    
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Championships(bot))
