import discord
from discord import app_commands
from discord.ext import commands
from database import Database
from utils.constants import PERSONAS, MOVE_CATEGORIES
from datetime import datetime
from typing import Optional, List, Dict
import json


# ==================== AUTOCOMPLETE ====================

async def wrestler_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    db = Database()
    wrestlers = await db.get_wrestlers_by_user(interaction.guild_id, interaction.user.id)
    if not wrestlers:
        return [app_commands.Choice(name="(You have no wrestlers)", value="none")]
    filtered = [w for w in wrestlers if current.lower() in w['name'].lower()][:25]
    return [app_commands.Choice(name=w['name'], value=w['name']) for w in filtered]


# ==================== CONSTANTS ====================

# Persona mappings by alignment
ALIGNMENT_PERSONAS = {
    "Face": ["American Power", "Fighter", "Junior", "Orthodox", "Panther", "Wrestling"],
    "Heel": ["Heel", "Mysterious", "Vicious", "Shooter"],
    "Tweener": ["Giant", "Grappler", "Ground", "Luchador", "Power", "Technician"]
}

# Move keywords
HEEL_KEYWORDS = ['choke', 'sleeper', 'guillotine', 'rear naked', 'trap', 'heel', 'behind']
FACE_KEYWORDS = ['splash', 'press', 'crossbody', 'moonsault', 'elbow drop']
TECHNICAL_KEYWORDS = ['lock', 'bar', 'crab', 'stretch', 'figure']
POWER_KEYWORDS = ['slam', 'bomb', 'press', 'gorilla', 'military']
AERIAL_KEYWORDS = ['diving', 'springboard', 'moonsault', 'splash', 'shooting star', 'top rope']

# Costs
TURN_COST = 1000
RENAME_COST = 2000


# ==================== HELPER FUNCTIONS ====================

def get_trait_adjustments(new_alignment: str) -> Dict[str, int]:
    """Get personality trait adjustments for alignment"""
    if new_alignment == "Face":
        return {
            "Prideful_Egotistical": 50,
            "Respectful_Disrespectful": 50,
            "Perseverant_Desperate": 50,
            "Loyal_Treacherous": 50,
            "Bold_Cowardly": 30,
            "Disciplined_Aggressive": 30
        }
    elif new_alignment == "Heel":
        return {
            "Prideful_Egotistical": -50,
            "Respectful_Disrespectful": -50,
            "Perseverant_Desperate": -50,
            "Loyal_Treacherous": -50,
            "Bold_Cowardly": -30,
            "Disciplined_Aggressive": -50
        }
    else:  # Tweener
        return {
            "Prideful_Egotistical": 0,
            "Respectful_Disrespectful": 0,
            "Perseverant_Desperate": 0,
            "Loyal_Treacherous": 0,
            "Bold_Cowardly": 0,
            "Disciplined_Aggressive": 0
        }


def is_heel_move(move_name: str) -> bool:
    """Check if a move is a Heel move"""
    return any(keyword in move_name.lower() for keyword in HEEL_KEYWORDS)


def filter_moves_by_alignment(available_moves: List[str], alignment: str, archetype: str = "Balanced") -> List[str]:
    """Filter moves based on alignment and archetype"""
    
    scored_moves = []
    
    for move in available_moves:
        move_lower = move.lower()
        score = 0
        
        # Alignment scoring
        if alignment == "Heel":
            if any(kw in move_lower for kw in HEEL_KEYWORDS):
                score += 3
        elif alignment == "Face":
            if any(kw in move_lower for kw in FACE_KEYWORDS):
                score += 3
            if any(kw in move_lower for kw in HEEL_KEYWORDS):
                score -= 2
        
        # Archetype scoring
        if archetype == "Technical":
            if any(kw in move_lower for kw in TECHNICAL_KEYWORDS):
                score += 2
        elif archetype == "Powerhouse":
            if any(kw in move_lower for kw in POWER_KEYWORDS):
                score += 2
        elif archetype == "High Flyer":
            if any(kw in move_lower for kw in AERIAL_KEYWORDS):
                score += 2
        
        scored_moves.append((move, score))
    
    scored_moves.sort(key=lambda x: x[1], reverse=True)
    result = [move for move, score in scored_moves[:6]]
    
    if len(result) < 5 and len(available_moves) > len(result):
        remaining = [m for m in available_moves if m not in result]
        result.extend(remaining[:5-len(result)])
    
    return result


def get_all_moves(move_type: str) -> List[str]:
    """Get all moves of a type (Finishers or Signatures)"""
    all_moves = []
    for category_data in MOVE_CATEGORIES.values():
        all_moves.extend(category_data['moves'][move_type])
    return all_moves


def calculate_new_traits(current_traits: dict, new_alignment: str) -> dict:
    """Calculate new personality traits based on alignment"""
    adjustments = get_trait_adjustments(new_alignment)
    new_traits = {}
    
    for trait, adjustment in adjustments.items():
        if adjustment == 0:
            new_traits[trait] = 0
        else:
            current = current_traits.get(trait, 0)
            new_value = current + adjustment
            new_traits[trait] = max(-100, min(100, new_value))
    
    return new_traits


def get_persona_bonuses_diff(old_persona: str, new_persona: str) -> Dict[str, int]:
    """Get the difference in persona bonuses"""
    old_bonuses = PERSONAS.get(old_persona, {}).get('bonus_attrs', {})
    new_bonuses = PERSONAS.get(new_persona, {}).get('bonus_attrs', {})
    
    all_attrs = set(old_bonuses.keys()) | set(new_bonuses.keys())
    diff = {}
    
    for attr in all_attrs:
        old_val = old_bonuses.get(attr, 0)
        new_val = new_bonuses.get(attr, 0)
        change = new_val - old_val
        if change != 0:
            diff[attr] = change
    
    return diff


# ==================== VIEW CLASSES ====================

class AlignmentSelectView(discord.ui.View):
    def __init__(self, cog, wrestler: dict, settings: dict):
        super().__init__(timeout=300)
        self.cog = cog
        self.wrestler = wrestler
        self.settings = settings
        
        current_alignment = wrestler['alignment']
        
        if current_alignment != "Face":
            self.add_item(AlignmentButton("Face", discord.ButtonStyle.green, "😇"))
        if current_alignment != "Heel":
            self.add_item(AlignmentButton("Heel", discord.ButtonStyle.red, "😈"))
        if current_alignment != "Tweener":
            self.add_item(AlignmentButton("Tweener", discord.ButtonStyle.gray, "⚖️"))


class AlignmentButton(discord.ui.Button):
    def __init__(self, alignment: str, style: discord.ButtonStyle, emoji: str):
        super().__init__(label=alignment, style=style, emoji=emoji)
        self.alignment = alignment
    
    async def callback(self, interaction: discord.Interaction):
        await self.view.cog.show_persona_selection(
            interaction, self.view.wrestler, self.view.settings, self.alignment
        )


class PersonaSelectView(discord.ui.View):
    def __init__(self, cog, wrestler: dict, settings: dict, new_alignment: str):
        super().__init__(timeout=300)
        self.cog = cog
        self.wrestler = wrestler
        self.settings = settings
        self.new_alignment = new_alignment


class PersonaSelect(discord.ui.Select):
    def __init__(self, personas: List[str]):
        options = [
            discord.SelectOption(
                label=persona,
                description=PERSONAS[persona]['description'][:100]
            )
            for persona in personas
        ]
        super().__init__(placeholder="Choose new persona...", options=options, min_values=1, max_values=1)
    
    async def callback(self, interaction: discord.Interaction):
        new_persona = self.values[0]
        await self.view.cog.check_move_changes(
            interaction, self.view.wrestler, self.view.settings, self.view.new_alignment, new_persona
        )


class MoveSelectView(discord.ui.View):
    """View for selecting BOTH Signature and Finisher"""
    def __init__(self, cog, wrestler: dict, settings: dict, new_alignment: str, new_persona: str,
                 signature_must_change: bool, finisher_must_change: bool,
                 signature_moves: List[str], finisher_moves: List[str]):
        super().__init__(timeout=300)
        self.cog = cog
        self.wrestler = wrestler
        self.settings = settings
        self.new_alignment = new_alignment
        self.new_persona = new_persona
        self.signature_must_change = signature_must_change
        self.finisher_must_change = finisher_must_change
        self.new_signature = None
        self.new_finisher = None
        
        # Add signature dropdown if needed
        if signature_must_change or len(signature_moves) > 0:
            self.add_item(SignatureSelect(signature_moves, signature_must_change))
        
        # Add finisher dropdown if needed
        if finisher_must_change or len(finisher_moves) > 0:
            self.add_item(FinisherSelect(finisher_moves, finisher_must_change))
        
        # Add "Keep Current" button if both optional
        if not signature_must_change and not finisher_must_change:
            self.add_item(KeepMovesButton())
        
        # Add Continue button
        self.add_item(ContinueButton())


class SignatureSelect(discord.ui.Select):
    def __init__(self, moves: List[str], required: bool):
        options = [discord.SelectOption(label=move, value=move) for move in moves[:25]]
        label = "Choose new signature" if required else "Choose new signature (optional)"
        super().__init__(placeholder=label, options=options, min_values=1 if required else 0, max_values=1)
        self.required = required
    
    async def callback(self, interaction: discord.Interaction):
        if self.values:
            self.view.new_signature = self.values[0]
        await interaction.response.defer()


class FinisherSelect(discord.ui.Select):
    def __init__(self, moves: List[str], required: bool):
        options = [discord.SelectOption(label=move, value=move) for move in moves[:25]]
        label = "Choose new finisher" if required else "Choose new finisher (optional)"
        super().__init__(placeholder=label, options=options, min_values=1 if required else 0, max_values=1, row=1)
        self.required = required
    
    async def callback(self, interaction: discord.Interaction):
        if self.values:
            self.view.new_finisher = self.values[0]
        await interaction.response.defer()


class KeepMovesButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Keep Current Moves", style=discord.ButtonStyle.gray, row=2)
    
    async def callback(self, interaction: discord.Interaction):
        await self.view.cog.show_turn_confirmation(
            interaction, self.view.wrestler, self.view.settings,
            self.view.new_alignment, self.view.new_persona, None, None
        )


class ContinueButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Continue", style=discord.ButtonStyle.green, emoji="✅", row=2)
    
    async def callback(self, interaction: discord.Interaction):
        # Validate required selections
        if self.view.signature_must_change and not self.view.new_signature:
            await interaction.response.send_message("❌ You must select a new signature!", ephemeral=True)
            return
        if self.view.finisher_must_change and not self.view.new_finisher:
            await interaction.response.send_message("❌ You must select a new finisher!", ephemeral=True)
            return
        
        await self.view.cog.show_turn_confirmation(
            interaction, self.view.wrestler, self.view.settings,
            self.view.new_alignment, self.view.new_persona,
            self.view.new_signature, self.view.new_finisher
        )


class TurnConfirmView(discord.ui.View):
    def __init__(self, cog, wrestler: dict, settings: dict, new_alignment: str, new_persona: str,
                 new_signature: Optional[str], new_finisher: Optional[str]):
        super().__init__(timeout=300)
        self.cog = cog
        self.wrestler = wrestler
        self.settings = settings
        self.new_alignment = new_alignment
        self.new_persona = new_persona
        self.new_signature = new_signature
        self.new_finisher = new_finisher
    
    @discord.ui.button(label="Confirm Turn", style=discord.ButtonStyle.green, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.execute_turn(
            interaction, self.wrestler, self.settings,
            self.new_alignment, self.new_persona, self.new_signature, self.new_finisher
        )
        self.stop()
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❌ Turn cancelled.", embed=None, view=None)
        self.stop()


# ==================== MAIN COG ====================

class WrestlerChanges(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
    
    wrestler_group = app_commands.Group(name="wrestler", description="Wrestler management")
    
    @wrestler_group.command(name="turn", description="Turn your wrestler (Face/Heel/Tweener)")
    @app_commands.autocomplete(wrestler=wrestler_autocomplete)
    async def turn(self, interaction: discord.Interaction, wrestler: str):
        """Start the turn process"""
        
        wrestlers = await self.db.get_wrestlers_by_user(interaction.guild_id, interaction.user.id)
        wrestler_obj = next((w for w in wrestlers if w['name'].lower() == wrestler.lower()), None)
        
        if not wrestler_obj:
            await interaction.response.send_message(f"❌ Wrestler '{wrestler}' not found!", ephemeral=True)
            return
        
        settings = await self.db.get_server_settings(interaction.guild_id)
        cooldown_days = settings.get('turn_cooldown_days', 30)
        
        cooldown = await self.db.check_turn_cooldown(wrestler_obj['id'], cooldown_days)
        if not cooldown['can_turn']:
            await interaction.response.send_message(
                f"❌ **{wrestler_obj['name']}** turned recently!\n"
                f"Next turn available in: **{cooldown['days_remaining']}** days",
                ephemeral=True
            )
            return
        
        if wrestler_obj['currency'] < TURN_COST:
            symbol = settings['currency_symbol']
            await interaction.response.send_message(
                f"❌ Not enough {settings['currency_name']}!\n"
                f"Cost: {symbol}{TURN_COST:,}\nYou have: {symbol}{wrestler_obj['currency']:,}",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title=f"🎭 Turn {wrestler_obj['name']}",
            description=f"Current: **{wrestler_obj['alignment']}** ({wrestler_obj['persona']})",
            color=discord.Color.blue()
        )
        embed.add_field(name="Cost", value=f"{settings['currency_symbol']}{TURN_COST:,}", inline=True)
        embed.add_field(name="What changes:", value="• Alignment\n• Persona\n• Traits\n• Possibly Moves", inline=False)
        
        view = AlignmentSelectView(self, wrestler_obj, settings)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    async def show_persona_selection(self, interaction: discord.Interaction, wrestler: dict, 
                                     settings: dict, new_alignment: str):
        """Show persona selection"""
        personas = ALIGNMENT_PERSONAS.get(new_alignment, [])
        
        embed = discord.Embed(
            title=f"🎭 Choose Persona ({new_alignment})",
            description=f"Select a persona:",
            color=discord.Color.blue()
        )
        
        view = PersonaSelectView(self, wrestler, settings, new_alignment)
        view.add_item(PersonaSelect(personas))
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def check_move_changes(self, interaction: discord.Interaction, wrestler: dict,
                                 settings: dict, new_alignment: str, new_persona: str):
        """Check if signature AND finisher need changing"""
        
        current_signature = wrestler.get('signature', 'None')
        current_finisher = wrestler.get('finisher', 'None')
        archetype = wrestler.get('archetype', 'Balanced')
        
        signature_is_heel = is_heel_move(current_signature)
        finisher_is_heel = is_heel_move(current_finisher)
        
        # Determine what needs changing
        signature_must_change = new_alignment == "Face" and signature_is_heel
        finisher_must_change = new_alignment == "Face" and finisher_is_heel
        
        # Get available moves
        all_signatures = get_all_moves('Signatures')
        all_finishers = get_all_moves('Finishers')
        
        # Filter signatures
        if signature_must_change:
            signature_moves = [m for m in all_signatures if not is_heel_move(m)]
            signature_moves = filter_moves_by_alignment(signature_moves, new_alignment, archetype)
        elif new_alignment == "Heel":
            signature_moves = filter_moves_by_alignment(all_signatures, new_alignment, archetype)
        else:
            signature_moves = []
        
        # Filter finishers
        if finisher_must_change:
            finisher_moves = [m for m in all_finishers if not is_heel_move(m)]
            finisher_moves = filter_moves_by_alignment(finisher_moves, new_alignment, archetype)
        elif new_alignment == "Heel":
            finisher_moves = filter_moves_by_alignment(all_finishers, new_alignment, archetype)
        else:
            finisher_moves = []
        
        # Build description
        desc_parts = []
        if signature_must_change:
            desc_parts.append(f"❌ **{current_signature}** (Signature) is a Heel move - MUST change!")
        elif new_alignment == "Heel" and signature_moves:
            desc_parts.append(f"Current Signature: **{current_signature}**\nOptional: Choose Heel-style signature")
        
        if finisher_must_change:
            desc_parts.append(f"❌ **{current_finisher}** (Finisher) is a Heel move - MUST change!")
        elif new_alignment == "Heel" and finisher_moves:
            desc_parts.append(f"Current Finisher: **{current_finisher}**\nOptional: Choose Heel-style finisher")
        
        if not desc_parts:
            # No move changes needed
            await self.show_turn_confirmation(interaction, wrestler, settings, new_alignment, new_persona, None, None)
            return
        
        embed = discord.Embed(
            title="💥 Move Changes",
            description="\n\n".join(desc_parts),
            color=discord.Color.red() if (signature_must_change or finisher_must_change) else discord.Color.dark_red()
        )
        
        view = MoveSelectView(
            self, wrestler, settings, new_alignment, new_persona,
            signature_must_change, finisher_must_change,
            signature_moves, finisher_moves
        )
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def show_turn_confirmation(self, interaction: discord.Interaction, wrestler: dict,
                                     settings: dict, new_alignment: str, new_persona: str,
                                     new_signature: Optional[str], new_finisher: Optional[str]):
        """Show final confirmation"""
        
        old_alignment = wrestler['alignment']
        old_persona = wrestler['persona']
        
        old_traits = json.loads(wrestler['personality_traits']) if wrestler.get('personality_traits') else {}
        new_traits = calculate_new_traits(old_traits, new_alignment)
        persona_diff = get_persona_bonuses_diff(old_persona, new_persona)
        
        embed = discord.Embed(
            title=f"✅ Confirm Turn",
            description=f"**{wrestler['name']}**",
            color=discord.Color.green()
        )
        
        embed.add_field(name="Alignment", value=f"{old_alignment} → **{new_alignment}**", inline=True)
        embed.add_field(name="Persona", value=f"{old_persona} → **{new_persona}**", inline=True)
        embed.add_field(name="Cost", value=f"{settings['currency_symbol']}{TURN_COST:,}", inline=True)
        
        if new_signature:
            embed.add_field(name="Signature", value=f"{wrestler.get('signature', 'None')} → **{new_signature}**", inline=False)
        if new_finisher:
            embed.add_field(name="Finisher", value=f"{wrestler.get('finisher', 'None')} → **{new_finisher}**", inline=False)
        
        if persona_diff:
            bonus_text = []
            for attr, change in list(persona_diff.items())[:5]:
                bonus_text.append(f"• {attr}: {change:+d}")
            embed.add_field(name="Attribute Changes", value="\n".join(bonus_text), inline=False)
        
        view = TurnConfirmView(self, wrestler, settings, new_alignment, new_persona, new_signature, new_finisher)
        
        try:
            await interaction.edit_original_response(embed=embed, view=view)
        except:
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    async def execute_turn(self, interaction: discord.Interaction, wrestler: dict, settings: dict,
                          new_alignment: str, new_persona: str, new_signature: Optional[str], new_finisher: Optional[str]):
        """Execute the turn"""
        
        await interaction.response.defer(ephemeral=True)
        
        old_alignment = wrestler['alignment']
        old_persona = wrestler['persona']
        old_signature = wrestler.get('signature', 'None')
        old_finisher = wrestler.get('finisher', 'None')
        
        await self.db.update_wrestler_currency(wrestler['id'], -TURN_COST)
        
        old_traits = json.loads(wrestler['personality_traits']) if wrestler.get('personality_traits') else {}
        new_traits = calculate_new_traits(old_traits, new_alignment)
        
        await self.db.update_wrestler_alignment_and_persona(wrestler['id'], new_alignment, new_persona, new_traits)
        
        # Update moves if changed
        if new_signature:
            await self.db.update_wrestler_signature(wrestler['id'], new_signature)
        if new_finisher:
            await self.db.update_wrestler_finisher(wrestler['id'], new_finisher)
        
        await self.db.record_turn(wrestler['id'], old_alignment, new_alignment, old_persona, new_persona)
        
        await self.send_turn_announcements(
            interaction.guild, wrestler, settings, old_alignment, new_alignment,
            old_persona, new_persona, old_traits, new_traits,
            old_signature, new_signature, old_finisher, new_finisher
        )
        
        await interaction.followup.send(
            f"✅ **{wrestler['name']}** has turned {new_alignment}!\nAnnouncements posted!",
            ephemeral=True
        )
    
    async def send_turn_announcements(self, guild: discord.Guild, wrestler: dict, settings: dict,
                                      old_alignment: str, new_alignment: str, old_persona: str, new_persona: str,
                                      old_traits: dict, new_traits: dict, old_signature: str, new_signature: Optional[str],
                                      old_finisher: str, new_finisher: Optional[str]):
        """Send announcements"""
        
        # PUBLIC ANNOUNCEMENT
        announcement_channel_id = settings.get('announcement_channel_id')
        if announcement_channel_id:
            channel = guild.get_channel(announcement_channel_id)
            if channel:
                embed = discord.Embed(
                    title="🚨 BREAKING NEWS!",
                    description=f"**{wrestler['name'].upper()} HAS TURNED {new_alignment.upper()}!**",
                    color=discord.Color.red() if new_alignment == "Heel" else discord.Color.green()
                )
                
                if new_alignment == "Heel":
                    embed.add_field(name="", value=f"The {old_alignment.lower()} has shocked the world!", inline=False)
                elif new_alignment == "Face":
                    embed.add_field(name="", value=f"The {old_alignment.lower()} is fighting for the people!", inline=False)
                else:
                    embed.add_field(name="", value=f"{wrestler['name']} walks alone now.", inline=False)
                
                embed.add_field(name="Alignment", value=f"{old_alignment} → {new_alignment}", inline=True)
                embed.add_field(name="New Persona", value=new_persona, inline=True)
                
                if new_signature:
                    embed.add_field(name="New Signature", value=new_signature, inline=True)
                if new_finisher:
                    embed.add_field(name="New Finisher", value=new_finisher, inline=True)
                
                try:
                    await channel.send(embed=embed)
                except:
                    pass
        
        # IN-GAME SUMMARY
        changes_channel_id = settings.get('wrestler_changes_channel_id')
        if changes_channel_id:
            channel = guild.get_channel(changes_channel_id)
            if channel:
                embed = discord.Embed(
                    title="⚙️ IN-GAME CHANGES REQUIRED",
                    description=f"**Wrestler:** {wrestler['name']}\n**Turn:** {old_alignment} → {new_alignment}",
                    color=discord.Color.blue()
                )
                
                # Attributes
                persona_diff = get_persona_bonuses_diff(old_persona, new_persona)
                if persona_diff:
                    attr_lines = []
                    for attr, change in persona_diff.items():
                        attr_lines.append(f"  {attr}: {change:+d}")
                    embed.add_field(name="📊 ATTRIBUTES", value="\n".join(attr_lines), inline=False)
                
                # Moves
                if new_signature or new_finisher:
                    move_text = ""
                    if new_signature:
                        move_text += f"**Signature:** {old_signature} → {new_signature}\n"
                    if new_finisher:
                        move_text += f"**Finisher:** {old_finisher} → {new_finisher}"
                    embed.add_field(name="💥 MOVES", value=move_text, inline=False)
                
                # Traits
                trait_lines = []
                for trait in old_traits:
                    old_val = old_traits.get(trait, 0)
                    new_val = new_traits.get(trait, 0)
                    trait_lines.append(f"{trait.replace('_', '/')}: {old_val:+d} → {new_val:+d}")
                embed.add_field(name="🎭 PERSONALITY", value="\n".join(trait_lines), inline=False)
                
                try:
                    await channel.send(embed=embed)
                except:
                    pass
    
    # RENAME COMMAND (unchanged)
    @wrestler_group.command(name="rename", description="Rename your wrestler")
    @app_commands.autocomplete(wrestler=wrestler_autocomplete)
    async def rename(self, interaction: discord.Interaction, wrestler: str, new_name: str):
        wrestlers = await self.db.get_wrestlers_by_user(interaction.guild_id, interaction.user.id)
        wrestler_obj = next((w for w in wrestlers if w['name'].lower() == wrestler.lower()), None)
        
        if not wrestler_obj:
            await interaction.response.send_message(f"❌ '{wrestler}' not found!", ephemeral=True)
            return
        
        if len(new_name) > 50 or len(new_name) < 2:
            await interaction.response.send_message("❌ Name must be 2-50 characters!", ephemeral=True)
            return
        
        all_wrestlers = await self.db.get_all_wrestlers(interaction.guild_id)
        if any(w['name'].lower() == new_name.lower() for w in all_wrestlers):
            await interaction.response.send_message(f"❌ '{new_name}' already taken!", ephemeral=True)
            return
        
        settings = await self.db.get_server_settings(interaction.guild_id)
        cooldown = await self.db.check_rename_cooldown(wrestler_obj['id'], settings.get('turn_cooldown_days', 30))
        if not cooldown['can_rename']:
            await interaction.response.send_message(
                f"❌ Renamed recently! Wait **{cooldown['days_remaining']}** days",
                ephemeral=True
            )
            return
        
        if wrestler_obj['currency'] < RENAME_COST:
            await interaction.response.send_message(
                f"❌ Need {settings['currency_symbol']}{RENAME_COST:,}!",
                ephemeral=True
            )
            return
        
        await self.db.update_wrestler_currency(wrestler_obj['id'], -RENAME_COST)
        await self.db.rename_wrestler(wrestler_obj['id'], new_name, wrestler_obj['name'])
        
        await interaction.response.send_message(
            f"✅ **{wrestler_obj['name']}** → **{new_name}**!",
            ephemeral=True
        )
    
    # TURN HISTORY (unchanged)
    @wrestler_group.command(name="turn_history", description="View turn history")
    @app_commands.autocomplete(wrestler=wrestler_autocomplete)
    async def turn_history(self, interaction: discord.Interaction, wrestler: str):
        wrestlers = await self.db.get_wrestlers_by_user(interaction.guild_id, interaction.user.id)
        wrestler_obj = next((w for w in wrestlers if w['name'].lower() == wrestler.lower()), None)
        
        if not wrestler_obj:
            await interaction.response.send_message(f"❌ '{wrestler}' not found!", ephemeral=True)
            return
        
        history = await self.db.get_turn_history(wrestler_obj['id'])
        if not history:
            await interaction.response.send_message(f"📜 **{wrestler_obj['name']}** has never turned!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title=f"🎭 Turn History - {wrestler_obj['name']}",
            description=f"Current: **{wrestler_obj['alignment']}** ({wrestler_obj['persona']})",
            color=discord.Color.blue()
        )
        
        for turn in history[:10]:
            date = datetime.fromisoformat(turn['turn_date']).strftime("%Y-%m-%d")
            embed.add_field(
                name=f"{turn['old_alignment']} → {turn['new_alignment']}",
                value=f"{turn['old_persona']} → {turn['new_persona']}\n{date}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(WrestlerChanges(bot))
