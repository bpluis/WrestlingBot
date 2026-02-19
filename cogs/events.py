import discord
from discord import app_commands
from discord.ext import commands
from database import Database
from datetime import datetime
from typing import Optional, List
import json

# Match types
MATCH_TYPES = [
    "Singles", "Tag Team", "Triple Threat", "Fatal 4-Way", "6-Man Tag",
    "Battle Royal", "Royal Rumble", "Ladder Match", "Steel Cage",
    "Hell in a Cell", "Tables Match", "TLC Match", "Last Man Standing", "I Quit Match"
]

# Finish types by match type
FINISH_TYPES_BY_MATCH = {
    "generic": ["Pinfall", "Submission", "DQ", "Count-out", "KO", "No Contest", "Time Limit Draw"],
    "Ladder Match": ["Retrieved Object", "Pinfall", "Submission"],
    "Steel Cage": ["Escaped Cage", "Pinfall", "Submission"],
    "Hell in a Cell": ["Pinfall", "Submission", "KO"],
    "Tables Match": ["Put Opponent Through Table"],
    "TLC Match": ["Retrieved Object"],
    "Last Man Standing": ["Opponent Failed to Answer 10 Count"],
    "I Quit Match": ["Made Opponent Quit"],
    "Battle Royal": ["Eliminated Last Opponent"],
    "Royal Rumble": ["Eliminated Last Opponent"]
}

def get_finish_types_for_match(match_type: str) -> List[str]:
    """Get valid finish types for a specific match type"""
    return FINISH_TYPES_BY_MATCH.get(match_type, FINISH_TYPES_BY_MATCH["generic"])

def format_participants(participant_names: list, match_type: str) -> str:
    """Format participant names based on match type (teams vs individuals)"""
    if match_type == "Tag Team":
        # Split into teams of 2
        if len(participant_names) >= 2:
            mid = len(participant_names) // 2
            team1 = participant_names[:mid]
            team2 = participant_names[mid:]
            return f"{' & '.join(team1)} vs {' & '.join(team2)}"
    elif match_type == "6-Man Tag":
        # Split into teams of 3
        if len(participant_names) >= 3:
            team1 = participant_names[:3]
            team2 = participant_names[3:]
            return f"{' & '.join(team1)} vs {' & '.join(team2)}"
    
    # Default: everyone vs everyone
    return " vs ".join(participant_names)

# Permission check
async def is_admin_or_booker(interaction: discord.Interaction, db: Database) -> bool:
    if interaction.user.guild_permissions.administrator:
        return True
    settings = await db.get_server_settings(interaction.guild_id)
    if settings and settings.get('booker_role_id'):
        return any(role.id == settings['booker_role_id'] for role in interaction.user.roles)
    return False

# Autocompletes
async def template_autocomplete(interaction: discord.Interaction, current: str):
    db = Database()
    templates = await db.get_event_templates(interaction.guild_id)
    filtered = [t for t in templates if current.lower() in t['name'].lower()][:25]
    return [app_commands.Choice(name=f"{t['type']}: {t['name']}", value=t['name']) for t in filtered]

async def event_autocomplete(interaction: discord.Interaction, current: str):
    db = Database()
    events = await db.get_event_instances(interaction.guild_id, status='planned')
    filtered = [e for e in events if current.lower() in e['full_name'].lower()][:25]
    return [app_commands.Choice(name=e['full_name'], value=e['full_name']) for e in filtered]

async def wrestler_autocomplete(interaction: discord.Interaction, current: str):
    db = Database()
    wrestlers = await db.get_all_wrestlers(interaction.guild_id)
    filtered = [w for w in wrestlers if current.lower() in w['name'].lower()][:25]
    return [app_commands.Choice(name=w['name'], value=w['name']) for w in filtered]

async def championship_autocomplete(interaction: discord.Interaction, current: str):
    db = Database()
    championships = await db.get_all_championships(interaction.guild_id)
    filtered = [c for c in championships if current.lower() in c['name'].lower()][:25]
    return [app_commands.Choice(name=c['name'], value=c['name']) for c in filtered]

async def match_type_autocomplete(interaction: discord.Interaction, current: str):
    """Autocomplete for match types"""
    filtered = [mt for mt in MATCH_TYPES if current.lower() in mt.lower()][:25]
    return [app_commands.Choice(name=mt, value=mt) for mt in filtered]


class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
    event_group = app_commands.Group(name="event", description="Event and show management")
    
    @event_group.command(name="template", description="Create show/event template (Admin/Booker)")
    @app_commands.choices(template_type=[
        app_commands.Choice(name="📺 Show (Weekly)", value="Show"),
        app_commands.Choice(name="🏆 Event (PPV)", value="Event")
    ])
    async def create_template(
        self, interaction: discord.Interaction, template_type: app_commands.Choice[str],
        name: str, description: Optional[str] = None, default_time: Optional[str] = None,
        banner_url: Optional[str] = None
    ):
        if not await is_admin_or_booker(interaction, self.db):
            await interaction.response.send_message("❌ Admin/Booker only!", ephemeral=True)
            return
        
        await interaction.response.send_message(
            "Select announcement channel:",
            view=ChannelSelectView(self, template_type.value, name, description, default_time, banner_url),
            ephemeral=True
        )
    
    @event_group.command(name="create_show", description="Create a show instance (Admin/Booker)")
    @app_commands.autocomplete(template=template_autocomplete)
    async def create_show(
        self, interaction: discord.Interaction, template: str, date: str,
        time: Optional[str] = None, description: Optional[str] = None
    ):
        if not await is_admin_or_booker(interaction, self.db):
            await interaction.response.send_message("❌ Admin/Booker only!", ephemeral=True)
            return
        
        templates = await self.db.get_event_templates(interaction.guild_id)
        temp = next((t for t in templates if t['name'] == template), None)
        
        if not temp:
            await interaction.response.send_message(f"❌ Template '{template}' not found!", ephemeral=True)
            return
        
        event_id, full_name = await self.db.create_event_instance(
            interaction.guild_id, temp['id'], temp['name'], temp['type'],
            date, time or temp['default_time'], description or temp['description'],
            temp['banner_url'], temp['announcement_channel_id']
        )
        
        embed = discord.Embed(
            title="📺 Show Created!",
            description=f"**{full_name}**",
            color=discord.Color.blue()
        )
        embed.add_field(name="Date", value=date, inline=True)
        if time or temp['default_time']:
            embed.add_field(name="Time", value=time or temp['default_time'], inline=True)
        embed.set_footer(text="Use /add_match to build the card")
        
        await interaction.response.send_message(embed=embed)
    
    @event_group.command(name="create_ppv", description="Create an event instance (Admin/Booker)")
    @app_commands.autocomplete(template=template_autocomplete)
    async def create_event(
        self, interaction: discord.Interaction, template: str, date: str,
        time: Optional[str] = None, description: Optional[str] = None
    ):
        if not await is_admin_or_booker(interaction, self.db):
            await interaction.response.send_message("❌ Admin/Booker only!", ephemeral=True)
            return
        
        templates = await self.db.get_event_templates(interaction.guild_id)
        temp = next((t for t in templates if t['name'] == template), None)
        
        if not temp:
            await interaction.response.send_message(f"❌ Template '{template}' not found!", ephemeral=True)
            return
        
        event_id, full_name = await self.db.create_event_instance(
            interaction.guild_id, temp['id'], temp['name'], temp['type'],
            date, time or temp['default_time'], description or temp['description'],
            temp['banner_url'], temp['announcement_channel_id']
        )
        
        embed = discord.Embed(
            title="🏆 EVENT CREATED!",
            description=f"**{full_name}**",
            color=discord.Color.gold()
        )
        embed.add_field(name="Date", value=date, inline=True)
        if time or temp['default_time']:
            embed.add_field(name="Time", value=time or temp['default_time'], inline=True)
        embed.set_footer(text="Use /add_match to build the card")
        
        await interaction.response.send_message(embed=embed)
    
    @event_group.command(name="add_match", description="Add match to event card (Admin/Booker)")
    @app_commands.autocomplete(
        event=event_autocomplete, 
        match_type=match_type_autocomplete,
        wrestler1=wrestler_autocomplete,
        wrestler2=wrestler_autocomplete, wrestler3=wrestler_autocomplete,
        wrestler4=wrestler_autocomplete, wrestler5=wrestler_autocomplete,
        wrestler6=wrestler_autocomplete, championship=championship_autocomplete
    )
    @app_commands.choices(is_main_event=[
        app_commands.Choice(name="Yes - Main Event", value="yes"),
        app_commands.Choice(name="No - Regular Match", value="no")
    ])
    async def add_match(
        self, interaction: discord.Interaction, event: str, match_order: int,
        match_type: str, wrestler1: str, wrestler2: Optional[str] = None,
        wrestler3: Optional[str] = None, wrestler4: Optional[str] = None,
        wrestler5: Optional[str] = None, wrestler6: Optional[str] = None,
        championship: Optional[str] = None,
        is_main_event: Optional[app_commands.Choice[str]] = None
    ):
        if not await is_admin_or_booker(interaction, self.db):
            await interaction.response.send_message("❌ Admin/Booker only!", ephemeral=True)
            return
        
        event_obj = await self.db.get_event_instance_by_name(interaction.guild_id, event)
        if not event_obj:
            await interaction.response.send_message(f"❌ Event '{event}' not found!", ephemeral=True)
            return
        
        all_wrestlers = await self.db.get_all_wrestlers(interaction.guild_id)
        participants = []
        for name in [wrestler1, wrestler2, wrestler3, wrestler4, wrestler5, wrestler6]:
            if name:
                w = next((wrestler for wrestler in all_wrestlers if wrestler['name'].lower() == name.lower()), None)
                if not w:
                    await interaction.response.send_message(f"❌ Wrestler '{name}' not found!", ephemeral=True)
                    return
                # Check if inactive
                if w.get('is_inactive', 0):
                    await interaction.response.send_message(
                        f"❌ **{w['name']}** is inactive and cannot be booked!\n"
                        f"Use `/inactivity toggle_status wrestler:{w['name']}` to reactivate.",
                        ephemeral=True
                    )
                    return
                participants.append(w['id'])
        
        champ_id = None
        if championship:
            champ = await self.db.get_championship_by_name(interaction.guild_id, championship)
            if champ:
                champ_id = champ['id']
        
        is_main = is_main_event and is_main_event.value == "yes"
        
        await self.db.add_event_match(
            event_obj['id'], match_order, match_type,
            participants, champ_id, is_main
        )
        
        participant_names = [name for name in [wrestler1, wrestler2, wrestler3, wrestler4, wrestler5, wrestler6] if name]
        
        embed = discord.Embed(
            title="✅ Match Added!",
            description=f"**{event}**",
            color=discord.Color.green()
        )
        embed.add_field(name="Match Order", value=f"#{match_order}", inline=True)
        embed.add_field(name="Type", value=match_type, inline=True)
        if is_main:
            embed.add_field(name="Status", value="⭐ MAIN EVENT", inline=True)
        embed.add_field(name="Participants", value=", ".join(participant_names), inline=False)
        if championship:
            embed.add_field(name="Championship", value=f"🏆 {championship}", inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @event_group.command(name="add_open", description="Add open spot match (Admin/Booker)")
    @app_commands.autocomplete(event=event_autocomplete,match_type=match_type_autocomplete)
    @app_commands.choices(is_main_event=[
        app_commands.Choice(name="Yes - Main Event", value="yes"),
        app_commands.Choice(name="No - Regular Match", value="no")
    ])
    async def add_open_match(
        self, interaction: discord.Interaction, event: str, match_order: int,
        match_type: str, spots: int, description: Optional[str] = None,
        is_main_event: Optional[app_commands.Choice[str]] = None
    ):
        if not await is_admin_or_booker(interaction, self.db):
            await interaction.response.send_message("❌ Admin/Booker only!", ephemeral=True)
            return
        
        event_obj = await self.db.get_event_instance_by_name(interaction.guild_id, event)
        if not event_obj:
            await interaction.response.send_message(f"❌ Event '{event}' not found!", ephemeral=True)
            return
        
        is_main = is_main_event and is_main_event.value == "yes"
        
        await self.db.add_open_match(
            event_obj['id'], match_order, match_type, spots, description, is_main
        )
        
        embed = discord.Embed(
            title="✅ Open Match Added!",
            description=f"**{event}**",
            color=discord.Color.blue()
        )
        embed.add_field(name="Match Order", value=f"#{match_order}", inline=True)
        embed.add_field(name="Type", value=match_type, inline=True)
        embed.add_field(name="Open Spots", value=f"{spots} spots", inline=True)
        if description:
            embed.add_field(name="Description", value=description, inline=False)
        embed.set_footer(text="Users can apply with /apply")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="apply", description="Apply for an open match spot")
    @app_commands.autocomplete(event=event_autocomplete)
    async def apply(self, interaction: discord.Interaction, event: str):
        event_obj = await self.db.get_event_instance_by_name(interaction.guild_id, event)
        if not event_obj:
            await interaction.response.send_message(f"❌ Event '{event}' not found!", ephemeral=True)
            return
        
        # Get ALL user's wrestlers
        all_wrestlers = await self.db.get_all_wrestlers(interaction.guild_id)
        user_wrestlers = [w for w in all_wrestlers if w['user_id'] == interaction.user.id]
        
        if not user_wrestlers:
            await interaction.response.send_message(
                "❌ You don't have a wrestler! Use /create_wrestler first.",
                ephemeral=True
            )
            return
        
        # Get open matches
        matches = await self.db.get_event_matches(event_obj['id'])
        open_matches = [m for m in matches if m['is_open_spot'] and m['spots_filled'] < m['spots_available']]
        
        if not open_matches:
            await interaction.response.send_message(
                "❌ No open spots available!",
                ephemeral=True
            )
            return
        
        # Filter out wrestlers already on the card
        available_wrestlers = []
        for wrestler in user_wrestlers:
            already_on_card = False
            for match in matches:
                if wrestler['id'] in match['participants']:
                    already_on_card = True
                    break
            if not already_on_card:
                available_wrestlers.append(wrestler)
        
        if not available_wrestlers:
            await interaction.response.send_message(
                "❌ All your wrestlers are already on the card!",
                ephemeral=True
            )
            return
        
        # Show wrestler selection first, then match selection
        await self.db.update_last_active(interaction.user.id, interaction.guild_id)
        await interaction.response.send_message(
            "**Select your wrestler to apply:**",
            view=WrestlerSelectView(self, event_obj['id'], available_wrestlers, open_matches),
            ephemeral=True
            
        )
    
    @event_group.command(name="announce", description="Announce event/show (Admin/Booker)")
    @app_commands.autocomplete(event=event_autocomplete)
    async def announce_event(self, interaction: discord.Interaction, event: str):
        if not await is_admin_or_booker(interaction, self.db):
            await interaction.response.send_message("❌ Admin/Booker only!", ephemeral=True)
            return
        
        event_obj = await self.db.get_event_instance_by_name(interaction.guild_id, event)
        if not event_obj:
            await interaction.response.send_message(f"❌ Event '{event}' not found!", ephemeral=True)
            return
        
        matches = await self.db.get_event_matches(event_obj['id'])
        
        if not matches:
            await interaction.response.send_message(
                "❌ No matches on the card! Use /add_match first.",
                ephemeral=True
            )
            return
        
        # Get channel
        channel = self.bot.get_channel(event_obj['announcement_channel_id'])
        if not channel:
            await interaction.response.send_message(
                "❌ Announcement channel not found!",
                ephemeral=True
            )
            return
        
        # Create announcement
        if event_obj['type'] == "Event":
            # KRASS EVENT ANNOUNCEMENT
            announcement = await self.create_event_announcement(event_obj, matches)
        else:
            # CLEAN SHOW ANNOUNCEMENT
            announcement = await self.create_show_announcement(event_obj, matches)
        
        msg = await channel.send(embed=announcement)
        await msg.add_reaction("👍")
        
        # Save message ID for future updates
        await self.db.update_event_instance_announcement(event_obj['id'], msg.id)
        
        await interaction.response.send_message(
            f"✅ **{event}** announced in {channel.mention}!",
            ephemeral=True
        )
    
    async def create_show_announcement(self, event, matches):
        """Create clean show announcement"""
        desc = f"📅 **{event['date']}**"
        if event['time']:
            desc += f" | ⏰ {event['time']}"
        
        embed = discord.Embed(
            title=f"📺 {event['full_name'].upper()}",
            description=desc,
            color=discord.Color.blue()
        )
        
        if event['banner_url']:
            embed.set_image(url=event['banner_url'])
        
        if event['description']:
            embed.add_field(name="About", value=event['description'], inline=False)
        
        card_text = ""
        all_wrestlers = await self.db.get_all_wrestlers(event['guild_id'])
        championships = await self.db.get_all_championships(event['guild_id'])
        
        for match in matches:
            card_text += f"\n**{match['match_order']}.** "
            
            if match['is_main_event']:
                card_text += "⭐ "
            
            if match['is_open_spot']:
                # Get current participants in the open spot
                participant_names = []
                for p_id in match['participants']:
                    w = next((wrestler for wrestler in all_wrestlers if wrestler['id'] == p_id), None)
                    if w:
                        participant_names.append(w['name'])
                
                spots_filled = len(participant_names)
                spots_total = match['spots_available']
                
                # Show as open spot if not full, otherwise show as regular match
                if spots_filled < spots_total:
                    card_text += f"**{match['match_type']}** - Open Spot ({spots_filled}/{spots_total} filled)\n"
                    if match['open_spot_description']:
                        card_text += f"   *{match['open_spot_description']}*\n"
                    
                    # Show who's already in
                    if participant_names:
                        card_text += f"   → {', '.join(participant_names)}\n"
                else:
                    # All spots filled - show as regular match now!
                    card_text += f"**{format_participants(participant_names, match['match_type'])}**\n"
                    card_text += f"   *{match['match_type']}*\n"
            else:
                participant_names = []
                for p_id in match['participants']:
                    w = next((wrestler for wrestler in all_wrestlers if wrestler['id'] == p_id), None)
                    if w:
                        participant_names.append(w['name'])
                
                card_text += f"**{format_participants(participant_names, match['match_type'])}**\n"
                card_text += f"   *{match['match_type']}*"
                
                if match['championship_id']:
                    champ = next((c for c in championships if c['id'] == match['championship_id']), None)
                    if champ:
                        card_text += f" - 🏆 {champ['name']}"
                card_text += "\n"
        
        embed.add_field(name="━━━━━━━ MATCH CARD ━━━━━━━", value=card_text, inline=False)
        embed.set_footer(text="React with 👍 if attending | Use /apply for open spots")
        
        return embed
    
    async def create_event_announcement(self, event, matches):
        """Create PREMIUM event announcement with beautiful formatting"""
        border = "═" * 35
        
        # Top section with date
        desc = f"```\n{border}\n"
        desc += f"   📅 {event['date']}"
        if event['time']:
            desc += f" | ⏰ {event['time']}"
        desc += f"\n{border}\n```"
        
        embed = discord.Embed(
            title=f"🏆 {event['full_name'].upper()} 🏆",
            description=desc,
            color=discord.Color.gold()
        )
        
        if event['banner_url']:
            embed.set_image(url=event['banner_url'])
        
        # Description with better formatting
        if event['description']:
            embed.add_field(
                name="\u200b",  # Invisible character
                value=f"**✨ {event['description']}**",
                inline=False
            )
        
        # Get data
        all_wrestlers = await self.db.get_all_wrestlers(event['guild_id'])
        championships = await self.db.get_all_championships(event['guild_id'])
        
        main_events = [m for m in matches if m['is_main_event']]
        undercard = [m for m in matches if not m['is_main_event']]
        
        # MAIN EVENTS - Premium formatting
        if main_events:
            main_text = ""
            for i, match in enumerate(main_events):
                if i > 0:
                    main_text += "\n"  # Spacing between matches
                
                if match['is_open_spot']:
                    participant_names = []
                    for p_id in match['participants']:
                        w = next((wrestler for wrestler in all_wrestlers if wrestler['id'] == p_id), None)
                        if w:
                            participant_names.append(w['name'])
                    
                    spots_filled = len(participant_names)
                    spots_total = match['spots_available']
                    
                    if spots_filled < spots_total:
                        main_text += f"🎯 **{match['match_type']}** - Open Spot\n"
                        main_text += f"   *{spots_filled}/{spots_total} filled*"
                        if participant_names:
                            main_text += f" - {', '.join(participant_names)}"
                        main_text += "\n"
                    else:
                        main_text += f"**{format_participants(participant_names, match['match_type'])}**\n"
                        main_text += f"   *{match['match_type']}*\n"
                else:
                    participant_names = []
                    for p_id in match['participants']:
                        w = next((wrestler for wrestler in all_wrestlers if wrestler['id'] == p_id), None)
                        if w:
                            participant_names.append(w['name'])
                    
                    main_text += f"**{format_participants(participant_names, match['match_type'])}**\n"
                    
                    if match['championship_id']:
                        champ = next((c for c in championships if c['id'] == match['championship_id']), None)
                        if champ:
                            main_text += f"   🏆 *{champ['name']}*\n"
                    else:
                        main_text += f"   *{match['match_type']}*\n"
            
            embed.add_field(
                name=f"{'═' * 13} ⭐ MAIN EVENTS ⭐ {'═' * 13}",
                value=main_text,
                inline=False
            )
        
        # UNDERCARD - Much cleaner formatting
        if undercard:
            card_text = ""
            for i, match in enumerate(undercard):
                if i > 0:
                    card_text += "\n"  # Blank line between matches for breathing room
                
                if match['is_open_spot']:
                    participant_names = []
                    for p_id in match['participants']:
                        w = next((wrestler for wrestler in all_wrestlers if wrestler['id'] == p_id), None)
                        if w:
                            participant_names.append(w['name'])
                    
                    spots_filled = len(participant_names)
                    spots_total = match['spots_available']
                    
                    if spots_filled < spots_total:
                        card_text += f"**{match['match_type']}** - Open Spot ({spots_filled}/{spots_total})\n"
                        if participant_names:
                            card_text += f"   → {', '.join(participant_names)}\n"
                    else:
                        card_text += f"**{format_participants(participant_names, match['match_type'])}**\n"
                        card_text += f"   *{match['match_type']}*\n"
                else:
                    participant_names = []
                    for p_id in match['participants']:
                        w = next((wrestler for wrestler in all_wrestlers if wrestler['id'] == p_id), None)
                        if w:
                            participant_names.append(w['name'])
                    
                    card_text += f"**{format_participants(participant_names, match['match_type'])}**\n"
                    
                    # Show match type AND championship on separate line
                    info_line = f"   *{match['match_type']}*"
                    if match['championship_id']:
                        champ = next((c for c in championships if c['id'] == match['championship_id']), None)
                        if champ:
                            info_line += f" • 🏆 {champ['name']}"
                    card_text += info_line + "\n"
            
            embed.add_field(
                name=f"{'═' * 11} UNDERCARD MATCHES {'═' * 11}",
                value=card_text,
                inline=False
            )
        
        # Footer with clean separator
        embed.add_field(
            name=f"{'═' * 35}",
            value="🎫 Apply for Open Spots: `/apply`\n👍 React to confirm attendance!",
            inline=False
        )
        
        return embed
        
        return embed
    
    @event_group.command(name="close", description="Close event - no more matches can be added (Admin/Booker)")
    @app_commands.autocomplete(event=event_autocomplete)
    async def close_event(self, interaction: discord.Interaction, event: str):
        """Close an event"""
        if not await is_admin_or_booker(interaction, self.db):
            await interaction.response.send_message("❌ Admin/Booker only!", ephemeral=True)
            return
        
        event_obj = await self.db.get_event_instance_by_name(interaction.guild_id, event)
        if not event_obj:
            await interaction.response.send_message(f"❌ Event '{event}' not found!", ephemeral=True)
            return
        
        if event_obj['status'] == 'closed':
            await interaction.response.send_message(f"❌ **{event}** is already closed!", ephemeral=True)
            return
        
        # Check if there are pending matches
        matches = await self.db.get_event_matches(event_obj['id'])
        pending_matches = [m for m in matches if m['status'] == 'pending']
        
        if pending_matches:
            pending_list = "\n".join([f"• Match #{m['match_order']}: {m['match_type']}" for m in pending_matches[:5]])
            if len(pending_matches) > 5:
                pending_list += f"\n... and {len(pending_matches) - 5} more"
            
            await interaction.response.send_message(
                f"❌ **Cannot close event!**\n\n"
                f"There are still **{len(pending_matches)} pending match(es)** without results:\n\n"
                f"{pending_list}\n\n"
                f"Please record all matches with `/record_match` first.",
                ephemeral=True
            )
            return
        
        # Close event
        await self.db.update_event_status(event_obj['id'], 'closed')
        
        embed = discord.Embed(
            title="🔒 Event Closed",
            description=f"**{event}** has been closed",
            color=discord.Color.orange()
        )
        embed.add_field(
            name="Status",
            value="No more matches can be added\nUse /record_match to record results",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
    
    @event_group.command(name="cancel", description="Cancel an event (deletes event and matches) (Admin/Booker)")
    @app_commands.autocomplete(event=event_autocomplete)
    async def cancel_event(self, interaction: discord.Interaction, event: str):
        """Cancel an event - deletes it and all associated matches"""
        if not await is_admin_or_booker(interaction, self.db):
            await interaction.response.send_message("❌ Admin/Booker only!", ephemeral=True)
            return
        
        event_obj = await self.db.get_event_instance_by_name(interaction.guild_id, event)
        if not event_obj:
            await interaction.response.send_message(f"❌ Event '{event}' not found!", ephemeral=True)
            return
        
        # Check if any matches have been recorded
        matches = await self.db.get_event_matches(event_obj['id'])
        completed_matches = [m for m in matches if m['status'] == 'completed' or m.get('match_id')]
        
        if completed_matches:
            await interaction.response.send_message(
                f"❌ **Cannot cancel event!**\n\n"
                f"This event has **{len(completed_matches)} completed match(es)**.\n"
                f"Events with recorded results cannot be cancelled.\n\n"
                f"Use `/close_event` instead to finalize the event.",
                ephemeral=True
            )
            return
        
        # Show confirmation view
        await interaction.response.send_message(
            f"⚠️ **Are you sure you want to cancel '{event}'?**\n\n"
            f"This will:\n"
            f"• Delete the event\n"
            f"• Delete all {len(matches)} match(es) on the card\n"
            f"• This action cannot be undone!\n\n"
            f"Click 'Confirm' to proceed.",
            view=CancelEventConfirmView(self, event_obj, matches),
            ephemeral=True
        )
    
    @event_group.command(name="results", description="Post event results (Admin/Booker)")
    @app_commands.autocomplete(event=event_autocomplete)
    async def announce_results(self, interaction: discord.Interaction, event: str):
        """Announce event results after completion"""
        if not await is_admin_or_booker(interaction, self.db):
            await interaction.response.send_message("❌ Admin/Booker only!", ephemeral=True)
            return
        
        event_obj = await self.db.get_event_instance_by_name(interaction.guild_id, event)
        if not event_obj:
            await interaction.response.send_message(f"❌ Event '{event}' not found!", ephemeral=True)
            return
        
        # Get all matches
        matches = await self.db.get_event_matches(event_obj['id'])
        completed_matches = [m for m in matches if m['status'] == 'completed' or m['match_id']]
        
        if not completed_matches:
            await interaction.response.send_message(
                "❌ No completed matches! Record matches first with /record_match",
                ephemeral=True
            )
            return
        
        # Get channel
        channel = self.bot.get_channel(event_obj['announcement_channel_id'])
        if not channel:
            await interaction.response.send_message(
                "❌ Announcement channel not found!",
                ephemeral=True
            )
            return
        
        # Create results announcement
        if event_obj['type'] == "Event":
            embed = await self.create_event_results(event_obj, completed_matches)
        else:
            embed = await self.create_show_results(event_obj, completed_matches)
        
        msg = await channel.send(embed=embed)
        
        await interaction.response.send_message(
            f"✅ Results for **{event}** posted in {channel.mention}!",
            ephemeral=True
        )
    
    async def create_show_results(self, event, matches):
        """Create show results announcement"""
        embed = discord.Embed(
            title=f"📊 {event['full_name'].upper()} - RESULTS",
            description=f"**{event['date']}**",
            color=discord.Color.green()
        )
        
        if event['banner_url']:
            embed.set_thumbnail(url=event['banner_url'])
        
        all_wrestlers = await self.db.get_all_wrestlers(event['guild_id'])
        championships = await self.db.get_all_championships(event['guild_id'])
        
        results_text = ""
        for match in sorted(matches, key=lambda m: m['match_order']):
            if not match.get('match_id'):
                continue
            
            match_record = await self.db.get_match_by_id(match['match_id'])
            if not match_record:
                continue
            
            import json
            winner_ids = json.loads(match_record['winner_ids']) if isinstance(match_record['winner_ids'], str) else match_record['winner_ids']
            
            winner_names = []
            for w_id in winner_ids:
                w = next((wrestler for wrestler in all_wrestlers if wrestler['id'] == w_id), None)
                if w:
                    winner_names.append(w['name'])
            # Get loser names           
            loser_ids = json.loads(match_record['loser_ids']) if isinstance(match_record['loser_ids'], str) else match_record['loser_ids']
            loser_names = []
            for l_id in loser_ids:
                l = next((wrestler for wrestler in all_wrestlers if wrestler['id'] == l_id), None)
                if l:
                    loser_names.append(l['name'])

            results_text += f"\n**{match['match_order']}.** "
            if match['is_main_event']:
                results_text += "⭐ "

            # Show winner vs loser
            if loser_names:
                loser_text = ' & '.join(loser_names)
                results_text += f"**{' & '.join(winner_names)}** defeated {loser_text}\n"
            else:
                results_text += f"**{' & '.join(winner_names)}** won\n"

            results_text += f"   *{match_record['match_type']} - {match_record['finish_type']}*"
            
            if match_record.get('rating'):
                stars = "⭐" * int(match_record['rating'])
                if match_record['rating'] % 1 != 0:
                    stars += "½"
                results_text += f" {stars}"
            
            if match.get('championship_id'):
                champ = next((c for c in championships if c['id'] == match['championship_id']), None)
                if champ:
                    results_text += f" - 👑 **NEW CHAMPION!**"
            
            results_text += "\n"
        
        embed.add_field(name="━━━━━━━ RESULTS ━━━━━━━", value=results_text, inline=False)
        embed.set_footer(text="Thank you for watching!")
        
        return embed
    
    async def create_event_results(self, event, matches):
        """Create KRASS event results"""
        border = "═" * 35
        
        embed = discord.Embed(
            title=f"🏆 {event['full_name'].upper()} - RESULTS 🏆",
            description=f"```\n{border}\n   📅 {event['date']}\n{border}\n```",
            color=discord.Color.gold()
        )
        
        if event['banner_url']:
            embed.set_thumbnail(url=event['banner_url'])
        
        all_wrestlers = await self.db.get_all_wrestlers(event['guild_id'])
        championships = await self.db.get_all_championships(event['guild_id'])
        
        main_events = [m for m in matches if m['is_main_event']]
        undercard = [m for m in matches if not m['is_main_event']]
        
        if main_events:
            main_text = ""
            for match in sorted(main_events, key=lambda m: m['match_order']):
                if not match.get('match_id'):
                    continue
                
                match_record = await self.db.get_match_by_id(match['match_id'])
                if not match_record:
                    continue
                
                import json
                winner_ids = json.loads(match_record['winner_ids']) if isinstance(match_record['winner_ids'], str) else match_record['winner_ids']
                
                winner_names = []
                for w_id in winner_ids:
                    w = next((wrestler for wrestler in all_wrestlers if wrestler['id'] == w_id), None)
                    if w:
                        winner_names.append(w['name'])
                
                main_text += f"\n🏆 **{' & '.join(winner_names)}** WIN"
                
                if match.get('championship_id'):
                    champ = next((c for c in championships if c['id'] == match['championship_id']), None)
                    if champ:
                        main_text += f"\n👑 **NEW {champ['name'].upper()}!**"
                
                if match_record.get('rating'):
                    stars = "⭐" * int(match_record['rating'])
                    if match_record['rating'] % 1 != 0:
                        stars += "½"
                    main_text += f"\n{stars}"
                
                main_text += "\n"
            
            embed.add_field(
                name=f"{'═' * 15} MAIN EVENTS {'═' * 15}",
                value=main_text,
                inline=False
            )
        
        if undercard:
            card_text = ""
            for match in sorted(undercard, key=lambda m: m['match_order']):
                if not match.get('match_id'):
                    continue
                
                match_record = await self.db.get_match_by_id(match['match_id'])
                if not match_record:
                    continue
                
                import json
                winner_ids = json.loads(match_record['winner_ids']) if isinstance(match_record['winner_ids'], str) else match_record['winner_ids']
                
                winner_names = []
                for w_id in winner_ids:
                    w = next((wrestler for wrestler in all_wrestlers if wrestler['id'] == w_id), None)
                    if w:
                        winner_names.append(w['name'])
                
                card_text += f"→ **{' & '.join(winner_names)}** win"
                
                if match_record.get('rating') and match_record['rating'] >= 4.0:
                    stars = "⭐" * int(match_record['rating'])
                    card_text += f" {stars}"
                
                card_text += "\n"
            
            embed.add_field(
                name=f"{'═' * 12} OTHER RESULTS {'═' * 12}",
                value=card_text,
                inline=False
            )
        
        embed.add_field(
            name=f"{'═' * 35}",
            value="Thank you for an incredible night!",
            inline=False
        )
        
        return embed

    @event_group.command(name="record", description="Record match result")
    async def record(self, interaction: discord.Interaction):
        """Guided workflow for recording matches - DROPDOWN ONLY"""
        
        if not await is_admin_or_booker(interaction, self.db):
            await interaction.response.send_message("❌ Admin/Booker only!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="📊 Record Match",
            description="**Step 1/4:** Is this match from an event/show, or standalone?",
            color=discord.Color.blue()
        )
        
        view = Step1_MatchTypeView(self)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
# ========== GUIDED WORKFLOW VIEWS - DROPDOWN ONLY ==========

class Step1_MatchTypeView(discord.ui.View):
    """Step 1: Choose Event Match or Standalone"""
    def __init__(self, parent_cog):
        super().__init__(timeout=300)
        self.parent_cog = parent_cog
    
    @discord.ui.button(label="📅 Event Match", style=discord.ButtonStyle.primary)
    async def event_match_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        """User chose event match"""
        # Get events with pending matches only
        events = await self.parent_cog.db.get_event_instances(interaction.guild_id)
        
        # Filter: only planned/ongoing events
        events = [e for e in events if e['status'] in ['planned', 'ongoing']]
        
        # Filter: only events with pending matches
        events_with_pending = []
        for event in events:
            matches = await self.parent_cog.db.get_event_matches(event['id'])
            pending = [m for m in matches if m['status'] == 'pending']
            if pending:
                events_with_pending.append(event)
        
        if not events_with_pending:
            await interaction.response.edit_message(
                content="❌ No events with pending matches found!\nCreate an event and add matches first.",
                embed=None,
                view=None
            )
            return
        
        # Show event selection
        await interaction.response.edit_message(
            content="**Step 2/4:** Select the event/show:",
            embed=None,
            view=Step2_EventSelectView(self.parent_cog, events_with_pending)
        )
    
    @discord.ui.button(label="🎯 Standalone Match", style=discord.ButtonStyle.secondary)
    async def standalone_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        """User chose standalone - not implemented yet"""
        await interaction.response.edit_message(
            content="⚠️ **Standalone matches not yet implemented in guided workflow.**\n\n"
                    "For now, standalone matches should be recorded manually.\n"
                    "Event matches are fully supported!",
            embed=None,
            view=None
        )


class Step2_EventSelectView(discord.ui.View):
    """Step 2: Select Event"""
    def __init__(self, parent_cog, events):
        super().__init__(timeout=300)
        self.parent_cog = parent_cog
        self.add_item(Step2_EventSelect(parent_cog, events))


class Step2_EventSelect(discord.ui.Select):
    """Dropdown for event selection"""
    def __init__(self, parent_cog, events):
        options = []
        for event in events[:25]:  # Discord limit
            options.append(discord.SelectOption(
                label=event['full_name'],
                description=f"{event['date']} - {event['status']}",
                value=str(event['id'])
            ))
        
        super().__init__(placeholder="Choose event...", options=options, min_values=1, max_values=1)
        self.parent_cog = parent_cog
        self.events = events
    
    async def callback(self, interaction: discord.Interaction):
        event_id = int(self.values[0])
        event = next((e for e in self.events if e['id'] == event_id), None)
        
        if not event:
            await interaction.response.edit_message(content="❌ Event not found!", view=None)
            return
        
        # Get pending matches
        matches = await self.parent_cog.db.get_event_matches(event_id)
        pending_matches = [m for m in matches if m['status'] == 'pending']
        
        if not pending_matches:
            await interaction.response.edit_message(
                content="❌ No pending matches in this event!",
                view=None
            )
            return
        
        # Show match selection
        await interaction.response.edit_message(
            content=f"**Step 3/4:** Select match from **{event['full_name']}**:",
            view=Step3_MatchSelectView(self.parent_cog, event, pending_matches)
        )


class Step3_MatchSelectView(discord.ui.View):
    """Step 3: Select Match from Event"""
    def __init__(self, parent_cog, event, matches):
        super().__init__(timeout=300)
        self.parent_cog = parent_cog
        self.event = event
        self.add_item(Step3_MatchSelect(parent_cog, event, matches))


class Step3_MatchSelect(discord.ui.Select):
    """Dropdown for match selection"""
    def __init__(self, parent_cog, event, matches):
        options = []
        for match in matches[:25]:
            if match['is_open_spot']:
                label = f"Match #{match['match_order']}: {match['match_type']} (Open)"
            else:
                label = f"Match #{match['match_order']}: {match['match_type']}"
            
            desc_parts = []
            desc_parts.append(f"{len(match['participants']) if not match['is_open_spot'] else match['spots_filled']} wrestlers")
            if match.get('championship_id'):
                desc_parts.append("🏆 Title")
            if match['is_main_event']:
                desc_parts.append("⭐ Main Event")
            
            desc = " • ".join(desc_parts)
            
            options.append(discord.SelectOption(
                label=label[:100],
                description=desc[:100],
                value=str(match['id'])
            ))
        
        super().__init__(placeholder="Choose match...", options=options, min_values=1, max_values=1)
        self.parent_cog = parent_cog
        self.event = event
        self.matches = matches
    
    async def callback(self, interaction: discord.Interaction):
        match_id = int(self.values[0])
        match = next((m for m in self.matches if m['id'] == match_id), None)
        
        if not match:
            await interaction.response.edit_message(content="❌ Match not found!", view=None)
            return
        
        # Get participants
        all_wrestlers = await self.parent_cog.db.get_all_wrestlers(interaction.guild_id)
        
        participant_names = []
        participant_ids = []
        for p_id in match['participants']:
            w = next((wrestler for wrestler in all_wrestlers if wrestler['id'] == p_id), None)
            if w:
                participant_names.append(w['name'])
                participant_ids.append(w['id'])
        
        if not participant_names:
            await interaction.response.edit_message(
                content="❌ No participants found for this match!",
                view=None
            )
            return
        
        # Show Step 4: Select winners
        await interaction.response.edit_message(
            content=f"**Step 4/4:** Record result for **{match['match_type']}**\n\nSelect winner(s):",
            view=Step4_WinnerSelectView(self.parent_cog, self.event, match, participant_ids, participant_names)
        )


class Step4_WinnerSelectView(discord.ui.View):
    """Step 4a: Select Winners"""
    def __init__(self, parent_cog, event, match, participant_ids, participant_names):
        super().__init__(timeout=300)
        self.parent_cog = parent_cog
        self.event = event
        self.match = match
        self.participant_ids = participant_ids
        self.participant_names = participant_names
        self.add_item(Step4_WinnerSelect(parent_cog, event, match, participant_ids, participant_names))


class Step4_WinnerSelect(discord.ui.Select):
    """Dropdown for selecting winners (multi-select)"""
    def __init__(self, parent_cog, event, match, participant_ids, participant_names):
        options = []
        for i, name in enumerate(participant_names):
            options.append(discord.SelectOption(
                label=name,
                value=str(i)  # Index in the list
            ))
        
        # Multi-select: min 1, max = all participants (for team wins)
        super().__init__(
            placeholder="Select winner(s)...",
            options=options,
            min_values=1,
            max_values=len(participant_names)
        )
        self.parent_cog = parent_cog
        self.event = event
        self.match = match
        self.participant_ids = participant_ids
        self.participant_names = participant_names
    
    async def callback(self, interaction: discord.Interaction):
        # Get selected winner indices
        winner_indices = [int(v) for v in self.values]
        
        winner_ids = [self.participant_ids[i] for i in winner_indices]
        winner_names = [self.participant_names[i] for i in winner_indices]
        
        # Losers are everyone else
        loser_ids = [pid for i, pid in enumerate(self.participant_ids) if i not in winner_indices]
        loser_names = [name for i, name in enumerate(self.participant_names) if i not in winner_indices]
        
        if not loser_ids:
            await interaction.response.edit_message(
                content="❌ You must have at least one loser! Not all participants can win.",
                view=None
            )
            return
        
        # Show finish type selection
        await interaction.response.edit_message(
            content=f"**Winners:** {', '.join(winner_names)}\n\nSelect finish type:",
            view=Step5_FinishSelectView(
                self.parent_cog, self.event, self.match,
                winner_ids, winner_names, loser_ids, loser_names
            )
        )


class Step5_FinishSelectView(discord.ui.View):
    """Step 4b: Select Finish Type"""
    def __init__(self, parent_cog, event, match, winner_ids, winner_names, loser_ids, loser_names):
        super().__init__(timeout=300)
        self.parent_cog = parent_cog
        self.event = event
        self.match = match
        self.winner_ids = winner_ids
        self.winner_names = winner_names
        self.loser_ids = loser_ids
        self.loser_names = loser_names
        self.add_item(Step5_FinishSelect(parent_cog, event, match, winner_ids, winner_names, loser_ids, loser_names))


class Step5_FinishSelect(discord.ui.Select):
    """Dropdown for finish type"""
    def __init__(self, parent_cog, event, match, winner_ids, winner_names, loser_ids, loser_names):
        finish_types = get_finish_types_for_match(match['match_type'])
        
        options = []
        for finish in finish_types:
            options.append(discord.SelectOption(label=finish, value=finish))
        
        super().__init__(placeholder="How did the match end?", options=options, min_values=1, max_values=1)
        self.parent_cog = parent_cog
        self.event = event
        self.match = match
        self.winner_ids = winner_ids
        self.winner_names = winner_names
        self.loser_ids = loser_ids
        self.loser_names = loser_names
    
    async def callback(self, interaction: discord.Interaction):
        finish_type = self.values[0]
        
        # Show rating selection
        await interaction.response.edit_message(
            content=f"**Finish:** {finish_type}\n\nSelect rating:",
            view=Step6_RatingSelectView(
                self.parent_cog, self.event, self.match,
                self.winner_ids, self.winner_names,
                self.loser_ids, self.loser_names,
                finish_type
            )
        )


class Step6_RatingSelectView(discord.ui.View):
    """Step 4c: Select Rating"""
    def __init__(self, parent_cog, event, match, winner_ids, winner_names, loser_ids, loser_names, finish_type):
        super().__init__(timeout=300)
        self.parent_cog = parent_cog
        self.event = event
        self.match = match
        self.winner_ids = winner_ids
        self.winner_names = winner_names
        self.loser_ids = loser_ids
        self.loser_names = loser_names
        self.finish_type = finish_type
        self.add_item(Step6_RatingSelect(parent_cog, event, match, winner_ids, winner_names, loser_ids, loser_names, finish_type))


class Step6_RatingSelect(discord.ui.Select):
    """Dropdown for rating"""
    def __init__(self, parent_cog, event, match, winner_ids, winner_names, loser_ids, loser_names, finish_type):
        options = [
            discord.SelectOption(label="⭐ 0.5 Stars", value="0.5"),
            discord.SelectOption(label="⭐ 1.0 Stars", value="1.0"),
            discord.SelectOption(label="⭐⭐ 1.5 Stars", value="1.5"),
            discord.SelectOption(label="⭐⭐ 2.0 Stars", value="2.0"),
            discord.SelectOption(label="⭐⭐ 2.5 Stars", value="2.5"),
            discord.SelectOption(label="⭐⭐⭐ 3.0 Stars", value="3.0"),
            discord.SelectOption(label="⭐⭐⭐ 3.5 Stars", value="3.5"),
            discord.SelectOption(label="⭐⭐⭐⭐ 4.0 Stars", value="4.0"),
            discord.SelectOption(label="⭐⭐⭐⭐ 4.5 Stars", value="4.5"),
            discord.SelectOption(label="⭐⭐⭐⭐⭐ 5.0 Stars", value="5.0"),
            discord.SelectOption(label="No Rating", value="0")
        ]
        
        super().__init__(placeholder="Rate the match...", options=options, min_values=1, max_values=1)
        self.parent_cog = parent_cog
        self.event = event
        self.match = match
        self.winner_ids = winner_ids
        self.winner_names = winner_names
        self.loser_ids = loser_ids
        self.loser_names = loser_names
        self.finish_type = finish_type
    
    async def award_xp(self, winner_ids, loser_ids, championship_id, rating):
        """Award XP to all participants based on match conditions"""
        results = []
        
        # Check if main event
        is_main_event = self.match.get('is_main_event', False)

        # Check for rivalry
        all_participants = winner_ids + loser_ids
        rivalry = await self.parent_cog.db.check_rivalry_between_wrestlers(all_participants)
        rivalry_bonus = 0
        
        if rivalry:
            # Update rivalry stats
            await self.parent_cog.db.update_rivalry_after_match(rivalry['id'], winner_ids, loser_ids)
            rivalry_bonus = 0.10  # 10% bonus
            self.has_rivalry = True
        else:
            self.has_rivalry = False
       
        # Award to winners
        for i, winner_id in enumerate(winner_ids):
            xp = 50  # Base win XP
            
            # Main event bonus
            if self.match.get('is_main_event'):
                xp += 25
            
            # Championship bonus
            if championship_id:
                xp += 100
            
            # Rating bonus
            if rating:
                if rating >= 5.0:
                    xp += 50
                elif rating >= 4.5:
                    xp += 40
                elif rating >= 4.0:
                    xp += 30
                elif rating >= 3.5:
                    xp += 20
                elif rating >= 3.0:
                    xp += 10
            
            # Award XP
            result = await self.parent_cog.db.add_xp(winner_id, xp)
            if result:
                result['name'] = self.winner_names[i] if i < len(self.winner_names) else "Wrestler"
                results.append(result)
        
        # Award to losers (participation XP)
        for i, loser_id in enumerate(loser_ids):
            xp = 10  # Base participation
            
            if self.match.get('is_main_event'):
                xp += 25
            
            if championship_id:
                xp += 100  # Still get title match XP
            
            result = await self.parent_cog.db.add_xp(loser_id, xp)
            if result:
                result['name'] = self.loser_names[i] if i < len(self.loser_names) else "Wrestler"
                results.append(result)
        
        return results
    
    async def callback(self, interaction: discord.Interaction):
        rating_value = float(self.values[0]) if self.values[0] != "0" else None
        
        # DEFER immediately - we have long database operations ahead!
        await interaction.response.defer(ephemeral=True)
        
        # NOW RECORD THE MATCH!
        try:
            # Handle championship logic if this is a title match
            championship_id = self.match.get('championship_id')
            title_changed = False
            new_champion_names = None
            
            if championship_id:
                # Get championship
                champ_obj = await self.parent_cog.db.get_championship_by_id(championship_id)
                is_tag_team = champ_obj['is_tag_team'] if champ_obj else False
                
                # Get current champion(s)
                current_champion_ids = []
                if champ_obj and champ_obj.get('current_champion_ids'):
                    current_champion_ids = json.loads(champ_obj['current_champion_ids']) if isinstance(champ_obj['current_champion_ids'], str) else champ_obj['current_champion_ids']
                elif champ_obj and champ_obj.get('current_champion_id'):
                    current_champion_ids = [champ_obj['current_champion_id']]
                
                # Check if ALL current champions lost
                if current_champion_ids:
                    all_champs_lost = all(champ_id in self.loser_ids for champ_id in current_champion_ids)
                    
                    if all_champs_lost:
                        # TITLE CHANGE!
                        title_changed = True
                        
                        # Determine new champions
                        if is_tag_team and len(self.winner_ids) >= 2:
                            new_champ_ids = self.winner_ids[:2]
                            new_champion_names = f"{self.winner_names[0]} & {self.winner_names[1]}"
                        else:
                            new_champ_ids = [self.winner_ids[0]]
                            new_champion_names = self.winner_names[0]
                        
                        # End old reigns
                        for _ in current_champion_ids:
                            await self.parent_cog.db.end_title_reign(championship_id)
                        
                        # Start new reigns
                        for i, new_champ_id in enumerate(new_champ_ids):
                            await self.parent_cog.db.start_title_reign(
                                championship_id=championship_id,
                                wrestler_id=new_champ_id,
                                wrestler_name=self.winner_names[i] if i < len(self.winner_names) else self.winner_names[0]
                            )
                        
                        # Update current champions
                        await self.parent_cog.db.update_current_champions(championship_id, new_champ_ids)
                    
                    elif any(champ_id in self.winner_ids for champ_id in current_champion_ids):
                        # Successful defense
                        await self.parent_cog.db.increment_title_defense(championship_id)
            
            # Record the match
            match_id = await self.parent_cog.db.record_match(
                guild_id=interaction.guild_id,
                winner_ids=self.winner_ids,
                winner_names=self.winner_names,
                loser_ids=self.loser_ids,
                loser_names=self.loser_names,
                match_type=self.match['match_type'],
                finish_type=self.finish_type,
                rating=rating_value,
                championship_id=championship_id,
                event_instance_id=self.event['id'],
                notes=None
            )
            
            # Update wrestler records
            for w_id in self.winner_ids:
                await self.parent_cog.db.update_wrestler_record(w_id, won=True)
            for l_id in self.loser_ids:
                await self.parent_cog.db.update_wrestler_record(l_id, won=False)
            
            # Award XP
            xp_results = await self.award_xp(
                self.winner_ids, self.loser_ids, 
                championship_id, rating_value
            )
            
            # Link to event match
            await self.parent_cog.db.link_match_to_event_match(
                self.event['id'],
                match_id,
                self.match['match_type'],
                self.winner_ids + self.loser_ids
            )
            
            # Success embed
            if title_changed:
                embed = discord.Embed(
                    title="👑 NEW CHAMPION!",
                    description=f"**{new_champion_names}** won the championship!",
                    color=discord.Color.gold()
                )
            else:
                embed = discord.Embed(
                    title="✅ Match Recorded!",
                    color=discord.Color.green()
                )
            
            embed.add_field(name="Event", value=self.event['full_name'], inline=False)
            embed.add_field(name="Match", value=f"#{self.match['match_order']} - {self.match['match_type']}", inline=True)
            embed.add_field(name="Winners", value=", ".join(self.winner_names), inline=False)
            embed.add_field(name="Finish", value=self.finish_type, inline=True)
            
            if rating_value:
                stars = "⭐" * int(rating_value)
                if rating_value % 1 != 0:
                    stars += "½"
                embed.add_field(name="Rating", value=stars, inline=True)
            
            # Show XP and level ups
            if xp_results:
                xp_summary = []
                has_rivalry = getattr(self, 'has_rivalry', False)
                
                for result in xp_results:
                    if result['leveled_up']:
                        xp_summary.append(f"🎉 **{result['name']}** → Level {result['new_level']}!")
                    else:
                        xp_summary.append(f"+{result['xp_gained']} XP for {result['name']}")
                
                if xp_summary:
                    xp_title = "⚔️ Experience (Rivalry +10%)" if has_rivalry else "Experience"
                    embed.add_field(
                        name=xp_title,
                        value="\n".join(xp_summary[:3]),  # Max 3 to avoid clutter
                        inline=False
                    )
            
            await interaction.followup.send(
                embed=embed,
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.followup.send(
                content=f"❌ Error recording match: {str(e)}",
                ephemeral=True
            )
    async def award_xp(self, winner_ids, loser_ids, championship_id, rating):
        """Award XP to all participants based on match conditions"""
        results = []
        
        # Check if main event
        is_main_event = self.match.get('is_main_event', False)
        
        # Award XP to WINNERS
        for winner_id, winner_name in zip(winner_ids, self.winner_names):
            xp = 50  # Base win XP
            
            # Main event bonus
            if is_main_event:
                xp += 25
            
            # Championship bonus
            if championship_id:
                xp += 100  # Title match bonus
            
            # Rating bonus
            if rating:
                if rating >= 5.0:
                    xp += 50
                elif rating >= 4.5:
                    xp += 40
                elif rating >= 4.0:
                    xp += 30
                elif rating >= 3.5:
                    xp += 20
                elif rating >= 3.0:
                    xp += 10
            
            # Rivalry bonus (10%)
            if rivalry:
                xp = int(xp * (1 + rivalry_bonus))
            
            # Award XP and check for level up
            level_result = await self.parent_cog.db.add_xp(winner_id, xp)
            
            results.append({
                'name': winner_name,
                'xp_gained': xp,
                'leveled_up': level_result is not None,
                'new_level': level_result['new_level'] if level_result else None,
                'rivalry_bonus': rivalry is not None  # Flag for display
            })
        
        # Award XP to LOSERS (participation XP)
        for loser_id, loser_name in zip(loser_ids, self.loser_names):
            xp = 10  # Base participation XP
            
            # Main event bonus (still get it for participating)
            if is_main_event:
                xp += 25
            
            # Championship bonus (still valuable experience)
            if championship_id:
                xp += 100
            
            # Rivalry bonus (10%)
            if rivalry:
                xp = int(xp * (1 + rivalry_bonus))
            
            # Award XP and check for level up
            level_result = await self.parent_cog.db.add_xp(loser_id, xp)
            
            results.append({
                'name': loser_name,
                'xp_gained': xp,
                'leveled_up': level_result is not None,
                'new_level': level_result['new_level'] if level_result else None,
                'rivalry_bonus': rivalry is not None  # Flag for display
            })
        
        return results

class ChannelSelectView(discord.ui.View):
    def __init__(self, parent_cog, template_type, name, description, default_time, banner_url):
        super().__init__(timeout=300)
        self.parent_cog = parent_cog
        self.template_type = template_type
        self.name = name
        self.description = description
        self.default_time = default_time
        self.banner_url = banner_url
        self.add_item(ChannelSelect())


class ChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="Select announcement channel...",
            channel_types=[discord.ChannelType.text],
            min_values=1, max_values=1
        )
    
    async def callback(self, interaction: discord.Interaction):
        view: ChannelSelectView = self.view
        channel = self.values[0]
        
        await view.parent_cog.db.create_event_template(
            interaction.guild_id, view.template_type, view.name,
            view.description, view.default_time, channel.id, view.banner_url
        )
        
        embed = discord.Embed(
            title=f"✅ Template Created!",
            description=f"**{view.name}** ({view.template_type})",
            color=discord.Color.green()
        )
        if view.description:
            embed.add_field(name="Description", value=view.description, inline=False)
        if view.default_time:
            embed.add_field(name="Default Time", value=view.default_time, inline=True)
        embed.add_field(name="Channel", value=channel.mention, inline=True)
        
        cmd_name = "create_show" if view.template_type == "Show" else "create_event"
        embed.set_footer(text=f"Use /{cmd_name} to create an instance")
        
        await interaction.response.edit_message(embed=embed, view=None)


class WrestlerSelectView(discord.ui.View):
    """View for selecting which wrestler to apply with"""
    def __init__(self, parent_cog, event_id, available_wrestlers, open_matches):
        super().__init__(timeout=300)
        self.parent_cog = parent_cog
        self.event_id = event_id
        self.available_wrestlers = available_wrestlers
        self.open_matches = open_matches
        self.add_item(WrestlerSelect(available_wrestlers, parent_cog, event_id, open_matches))


class WrestlerSelect(discord.ui.Select):
    """Dropdown to select wrestler"""
    def __init__(self, available_wrestlers, parent_cog, event_id, open_matches):
        options = []
        for wrestler in available_wrestlers:
            options.append(discord.SelectOption(
                label=wrestler['name'],
                description=f"{wrestler['archetype']} - {wrestler['weight_class']}",
                value=str(wrestler['id'])
            ))
        
        super().__init__(placeholder="Choose your wrestler...", options=options, min_values=1, max_values=1)
        self.parent_cog = parent_cog
        self.event_id = event_id
        self.open_matches = open_matches
        self.available_wrestlers = available_wrestlers
    
    async def callback(self, interaction: discord.Interaction):
        wrestler_id = int(self.values[0])
        wrestler = next((w for w in self.available_wrestlers if w['id'] == wrestler_id), None)
        
        if not wrestler:
            await interaction.response.edit_message(content="❌ Wrestler not found!", view=None)
            return
        
        # Now show match selection
        await interaction.response.edit_message(
            content=f"**{wrestler['name']}** - Select match to join:",
            view=ApplyView(self.parent_cog, self.event_id, wrestler, self.open_matches)
        )


class ApplyView(discord.ui.View):
    def __init__(self, parent_cog, event_id, wrestler, open_matches):
        super().__init__(timeout=300)
        self.parent_cog = parent_cog
        self.event_id = event_id
        self.wrestler = wrestler
        self.add_item(ApplySelect(open_matches, parent_cog, wrestler, event_id))


class ApplySelect(discord.ui.Select):
    def __init__(self, open_matches, parent_cog, wrestler, event_instance_id):
        options = []
        for match in open_matches:
            desc = f"{match['match_type']} - {match['spots_filled']}/{match['spots_available']} filled"
            options.append(discord.SelectOption(
                label=f"Match #{match['match_order']}: {match['match_type']}",
                description=desc[:100],
                value=str(match['id'])
            ))
        
        super().__init__(placeholder="Choose a match...", options=options, min_values=1, max_values=1)
        self.parent_cog = parent_cog
        self.wrestler = wrestler
        self.event_instance_id = event_instance_id
    
    async def callback(self, interaction: discord.Interaction):
        match_id = int(self.values[0])
        
        try:
            await self.parent_cog.db.apply_for_match(match_id, self.wrestler['id'], interaction.user.id)
            
            # Get event to update announcement
            event = await self.parent_cog.db.get_event_instance_by_id(self.event_instance_id)
            
            if event and event.get('announcement_message_id') and event.get('announcement_channel_id'):
                # Get channel
                channel = self.parent_cog.bot.get_channel(event['announcement_channel_id'])
                
                if channel:
                    try:
                        # Fetch the original message
                        message = await channel.fetch_message(event['announcement_message_id'])
                        
                        # Recreate the announcement with updated match card
                        matches = await self.parent_cog.db.get_event_matches(self.event_instance_id)
                        
                        if event['type'] == "Event":
                            new_embed = await self.parent_cog.create_event_announcement(event, matches)
                        else:
                            new_embed = await self.parent_cog.create_show_announcement(event, matches)
                        
                        # Edit the announcement
                        await message.edit(embed=new_embed)
                        
                    except discord.NotFound:
                        pass  # Message was deleted, no problem
                    except discord.Forbidden:
                        pass  # No permission to edit, no problem
            
            await interaction.response.edit_message(
                content=f"✅ **{self.wrestler['name']}** has been added to the match!\n🔄 Event announcement updated.",
                view=None
            )
        except ValueError as e:
            await interaction.response.edit_message(
                content=f"❌ {str(e)}",
                view=None
            )


class CancelEventConfirmView(discord.ui.View):
    """Confirmation view for canceling events"""
    def __init__(self, parent_cog, event_obj, matches):
        super().__init__(timeout=60)
        self.parent_cog = parent_cog
        self.event_obj = event_obj
        self.matches = matches
    
    @discord.ui.button(label="✅ Confirm Cancel", style=discord.ButtonStyle.danger)
    async def confirm_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Delete event and matches"""
        try:
            # Delete all event matches first
            for match in self.matches:
                await self.parent_cog.db.delete_event_match(match['id'])
            
            # Delete event instance
            await self.parent_cog.db.delete_event_instance(self.event_obj['id'])
            
            # Try to delete announcement if it exists
            if self.event_obj.get('announcement_message_id') and self.event_obj.get('announcement_channel_id'):
                channel = self.parent_cog.bot.get_channel(self.event_obj['announcement_channel_id'])
                if channel:
                    try:
                        message = await channel.fetch_message(self.event_obj['announcement_message_id'])
                        await message.delete()
                    except:
                        pass  # Message already deleted or no permission
            
            await interaction.response.edit_message(
                content=f"✅ **Event cancelled!**\n\n"
                        f"**{self.event_obj['full_name']}** has been deleted.\n"
                        f"• {len(self.matches)} match(es) removed\n"
                        f"• Announcement deleted (if it existed)",
                view=None
            )
        except Exception as e:
            await interaction.response.edit_message(
                content=f"❌ Error cancelling event: {str(e)}",
                view=None
            )
    
    @discord.ui.button(label="❌ Nevermind", style=discord.ButtonStyle.secondary)
    async def cancel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel the cancellation"""
        await interaction.response.edit_message(
            content="Event cancellation aborted. No changes made.",
            view=None
        )

    @app_commands.command(name="view_card", description="View event match card")
    @app_commands.autocomplete(event=event_autocomplete)
    async def view_card_alias(self, interaction: discord.Interaction, event: str):
        """Top-level alias for /event card"""
        await self.card(interaction, event)
        
async def setup(bot):
    await bot.add_cog(Events(bot))
