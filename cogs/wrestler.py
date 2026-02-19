import discord
from discord import app_commands
from discord.ext import commands
from database import Database
from utils.constants import ARCHETYPES, PERSONAS, MOVE_CATEGORIES, BODY_TYPES, get_base_attributes, get_height_for_archetype
from utils.helpers import (
    create_wrestler_embed, 
    create_full_attributes_embed,
    create_full_wrestler_embed,
    calculate_archetype_and_alignment,
    calculate_personality_traits
)
from typing import Optional, List
import random


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


# Autocomplete for own wrestlers
async def own_wrestler_autocomplete(
    interaction: discord.Interaction,
    current: str
) -> List[app_commands.Choice[str]]:
    """Autocomplete for wrestler_name - shows user's own wrestlers"""
    db = Database()
    
    # Get user's wrestlers
    wrestlers = await db.get_wrestlers_by_user(interaction.guild_id, interaction.user.id)
    
    if not wrestlers:
        return [app_commands.Choice(name="(You have no wrestlers)", value="none")]
    
    # Filter based on current input
    filtered = [
        w for w in wrestlers 
        if current.lower() in w['name'].lower()
    ][:25]  # Discord limit
    
    return [
        app_commands.Choice(name=w['name'], value=w['name'])
        for w in filtered
    ]

# Autocomplete for viewing any wrestler (including other users)
async def any_wrestler_autocomplete(
    interaction: discord.Interaction,
    current: str
) -> List[app_commands.Choice[str]]:
    """Autocomplete for wrestler_name - shows all wrestlers in server"""
    db = Database()
    
    # Get all wrestlers in server
    wrestlers = await db.get_all_wrestlers(interaction.guild_id)
    
    if not wrestlers:
        return [app_commands.Choice(name="(No wrestlers found)", value="none")]
    
    # Filter based on current input
    filtered = [
        w for w in wrestlers 
        if current.lower() in w['name'].lower()
    ][:25]  # Discord limit
    
    return [
        app_commands.Choice(name=f"{w['name']} (ID: {w['user_id']})", value=w['name'])
        for w in filtered
    ]
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
        await interaction.response.defer()
        
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
        
        # DEFER first! ← NEU!
        await interaction.response.defer()
        
        # Now edit via followup or edit_original_response
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
        print(f"[DEBUG] Confirm button clicked!")  

        try:        
            await interaction.response.defer()
            print(f"[DEBUG] Deferred!")

            await self.cog.execute_turn(
                interaction, self.wrestler, self.settings,
                self.new_alignment, self.new_persona, self.new_signature, self.new_finisher
            )
            print(f"[DEBUG] Execute turn completed!") 

            self.stop()
        except Exception as e:
            print(f"[DEBUG ERROR] {e}")  # ← DEBUG
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❌ Turn cancelled.", embed=None, view=None)
        self.stop()

class Wrestler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
    wrestler_group = app_commands.Group(name="wrestler", description="Wrestler management commands")
    
    @wrestler_group.command(name="create", description="Create your wrestler for the league!")
    async def create(self, interaction: discord.Interaction):
        """Start the wrestler creation process"""
        
        # Check if server is setup
        settings = await self.db.get_server_settings(interaction.guild_id)
        if not settings or not settings['setup_completed']:
            await interaction.response.send_message(
                "❌ This server hasn't been set up yet! An admin needs to run `/setup` first.",
                ephemeral=True
            )
            return
        
        # Check wrestler limit
        current_wrestlers = await self.db.get_wrestlers_by_user(interaction.guild_id, interaction.user.id)
        
        # Get wrestler limit (checks user-specific first, then default)
        max_wrestlers = await self.db.get_wrestler_limit(interaction.guild_id, interaction.user.id)
        
        if len(current_wrestlers) >= max_wrestlers:
            await interaction.response.send_message(
                f"❌ You've reached your wrestler limit ({max_wrestlers})! Retire a wrestler first with `/wrestler retire`.",
                ephemeral=True
            )
            return
        
        # Start creation flow
        creation_view = WrestlerCreationView(
            self.db, 
            interaction.user, 
            settings,
            interaction.guild
        )
        
        embed = discord.Embed(
            title="🏆 Create Your Wrestler",
            description="Let's build your superstar! Answer the questions below to shape their identity.\n\n*You can go back or cancel at any time.*",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Question 1/16",
            value="**What is your wrestler's gender?**",
            inline=False
        )
        await self.db.update_last_active(interaction.user.id, interaction.guild_id)
        await interaction.response.send_message(embed=embed, view=creation_view, ephemeral=True)
    
    @wrestler_group.command(name="view", description="View a wrestler's details")
    @app_commands.autocomplete(wrestler_name=any_wrestler_autocomplete)
    async def view(
        self,
        interaction: discord.Interaction,
        wrestler_name: Optional[str] = None,
        user: Optional[discord.Member] = None
    ):
        """View wrestler information"""
        
        if user:
            # If user is specified, search only their wrestlers
            target_user = user
            wrestlers = await self.db.get_wrestlers_by_user(interaction.guild_id, target_user.id)
        else:
            # If no user specified, search own wrestlers first, then all wrestlers
            wrestlers = await self.db.get_wrestlers_by_user(interaction.guild_id, interaction.user.id)
            
            # If wrestler_name is provided and not found in own wrestlers, search all
            if wrestler_name and not any(w['name'].lower() == wrestler_name.lower() for w in wrestlers):
                all_wrestlers = await self.db.get_all_wrestlers(interaction.guild_id)
                wrestler = next((w for w in all_wrestlers if w['name'].lower() == wrestler_name.lower()), None)
                
                if wrestler:
                    # Found in other users, get the owner
                    target_user = await interaction.guild.fetch_member(wrestler['user_id'])
                    wrestlers = [wrestler]
                else:
                    await interaction.response.send_message(
                        f"❌ Wrestler '{wrestler_name}' not found!",
                        ephemeral=True
                    )
                    return
            else:
                target_user = interaction.user
        
        if not wrestlers:
            pronoun = "They" if user else "You"
            await interaction.response.send_message(
                f"❌ {pronoun} don't have any wrestlers yet!",
                ephemeral=True
            )
            return
        
        # If name specified, find that wrestler
        if wrestler_name:
            wrestler = next((w for w in wrestlers if w['name'].lower() == wrestler_name.lower()), None)
            if not wrestler:
                await interaction.response.send_message(
                    f"❌ Wrestler '{wrestler_name}' not found!",
                    ephemeral=True
                )
                return
        else:
            # Show first wrestler if they have multiple
            wrestler = wrestlers[0]
        
        # Get server settings for currency display
        settings = await self.db.get_server_settings(interaction.guild_id)
        wrestler['currency_name'] = settings['currency_name']
        wrestler['currency_symbol'] = settings['currency_symbol']
        
        embed = create_wrestler_embed(wrestler, target_user)
        
        # Add button to view full attributes
        view = ViewAttributesButton(wrestler)

        await self.db.update_last_active(interaction.user.id, interaction.guild_id)
        await interaction.response.send_message(embed=embed, view=view)
    
    @wrestler_group.command(name="list", description="List all your wrestlers")
    async def list(self, interaction: discord.Interaction):
        """List all wrestlers owned by the user"""
        
        wrestlers = await self.db.get_wrestlers_by_user(interaction.guild_id, interaction.user.id)
        
        if not wrestlers:
            await interaction.response.send_message(
                "❌ You don't have any wrestlers yet! Create one with `/create_wrestler`.",
                ephemeral=True
            )
            return
        
        settings = await self.db.get_server_settings(interaction.guild_id)
        
        embed = discord.Embed(
            title=f"🏆 {interaction.user.name}'s Wrestlers",
            description=f"You have **{len(wrestlers)}** wrestler(s)",
            color=discord.Color.blue()
        )
        
        for wrestler in wrestlers:
            alignment = wrestler.get('alignment', 'Tweener')
            alignment_emoji = "😇" if alignment == "Face" else "😈" if alignment == "Heel" else "⚖️"
            value = (
                f"{alignment_emoji} **{alignment}** | **{wrestler['archetype']}**\n"
                f"**Level:** {wrestler['level']} | **W/L:** {wrestler['wins']}/{wrestler['losses']}\n"
                f"**{settings['currency_name']}:** {settings['currency_symbol']}{wrestler['currency']}"
            )
            embed.add_field(
                name=f"{wrestler['name']} ({wrestler['weight_class']})",
                value=value,
                inline=False
            )
        
        await self.db.update_last_active(interaction.user.id, interaction.guild_id)
        await interaction.response.send_message(embed=embed)
    
    @wrestler_group.command(name="retire", description="Retire your wrestler")
    @app_commands.autocomplete(wrestler_name=own_wrestler_autocomplete)
    async def retire(self, interaction: discord.Interaction, wrestler_name: str):
        """Retire a wrestler (frees up unique moves)"""
        
        wrestlers = await self.db.get_wrestlers_by_user(interaction.guild_id, interaction.user.id)
        wrestler = next((w for w in wrestlers if w['name'].lower() == wrestler_name.lower()), None)
        
        if not wrestler:
            await interaction.response.send_message(
                f"❌ You don't have a wrestler named '{wrestler_name}'!",
                ephemeral=True
            )
            return
        
        # Confirmation view
        class ConfirmRetireView(discord.ui.View):
            def __init__(self, db, wrestler_id, wrestler_name):
                super().__init__(timeout=60)
                self.db = db
                self.wrestler_id = wrestler_id
                self.wrestler_name = wrestler_name
                self.value = None
            
            @discord.ui.button(label="Confirm Retirement", style=discord.ButtonStyle.danger)
            async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
                await self.db.retire_wrestler(self.wrestler_id)
                await interaction.response.edit_message(
                    content=f"✅ **{self.wrestler_name}** has been retired. Their moves are now available!",
                    embed=None,
                    view=None
                )
                self.value = True
                self.stop()
            
            @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
            async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.response.edit_message(
                    content="❌ Retirement cancelled.",
                    embed=None,
                    view=None
                )
                self.value = False
                self.stop()
        
        view = ConfirmRetireView(self.db, wrestler['id'], wrestler['name'])
        
        embed = discord.Embed(
            title="⚠️ Confirm Retirement",
            description=f"Are you sure you want to retire **{wrestler['name']}**?",
            color=discord.Color.orange()
        )
        embed.add_field(
            name="This will:",
            value="• Remove them from your active roster\n• Free up their unique moves\n• Preserve their stats in history",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    @wrestler_group.command(name="history", description="View match history")
    @app_commands.autocomplete(wrestler_name=any_wrestler_autocomplete)
    async def history(
       self,interaction: discord.Interaction,wrestler_name: str,limit: Optional[int] = 10
    ):
        all_wrestlers = await self.db.get_all_wrestlers(interaction.guild_id)
        wrestler = next((w for w in all_wrestlers if w['name'].lower() == wrestler_name.lower()), None)
        
        if not wrestler:
            await interaction.response.send_message(f"❌ Wrestler '{wrestler_name}' not found!", ephemeral=True)
            return
        
        matches = await self.db.get_wrestler_matches(wrestler['id'], limit)
        
        if not matches:
            await interaction.response.send_message(f"📊 **{wrestler['name']}** has no match history yet.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title=f"📊 Match History - {wrestler['name']}",
            description=f"**Record:** {wrestler['wins']}-{wrestler['losses']}",
            color=discord.Color.blue()
        )
        
        for match in matches:
            is_winner = wrestler['id'] in match['winner_ids']
            
            if is_winner:
                result_icon = "🏆"
                result_text = "**WIN**"
                opponents = match['loser_names']
            else:
                result_icon = "❌"
                result_text = "LOSS"
                opponents = match['winner_names']
            
            opponent_text = ", ".join(opponents)
            
            try:
                match_date = datetime.fromisoformat(match['match_date'])
                date_str = match_date.strftime("%Y-%m-%d")
            except:
                date_str = match['match_date'][:10]
            
            rating_str = ""
            if match.get('rating'):
                stars = "⭐" * int(match['rating'])
                if match['rating'] % 1 != 0:
                    stars += "½"
                rating_str = f" | {stars}"
            
            value = (
                f"{result_icon} {result_text} vs **{opponent_text}**\n"
                f"*{match['match_type']} • {match['finish_type']}*{rating_str}\n"
                f"📅 {date_str}"
            )
            
            embed.add_field(name="\u200b", value=value, inline=False)
        
        if len(matches) >= limit:
            embed.set_footer(text=f"Showing last {limit} matches")
        
        await interaction.response.send_message(embed=embed)

    @wrestler_group.command(name="titles", description="View championships won by a wrestler")
    @app_commands.autocomplete(wrestler_name=any_wrestler_autocomplete)
    async def titles(
        self,
        interaction: discord.Interaction,
        wrestler_name: str
    ):
        """View all championships held by a wrestler"""
    
        # Get wrestler
        all_wrestlers = await self.db.get_all_wrestlers(interaction.guild_id)
        wrestler_obj = next((w for w in all_wrestlers if w['name'].lower() == wrestler_name.lower()), None)
    
        if not wrestler_obj:
            await interaction.response.send_message(
                f"❌ Wrestler '{wrestler_name}' not found!",
                ephemeral=True
            )
            return
    
        # Get all reigns for this wrestler
        reigns = await self.db.get_wrestler_title_reigns(wrestler_obj['id'])
    
        if not reigns:
            await interaction.response.send_message(
                f"📜 **{wrestler_name}** has never held a championship.",
                ephemeral=True
            )
            return
    
        from datetime import datetime
    
        embed = discord.Embed(
            title=f"🏆 {wrestler_name} - Championship History",
            color=discord.Color.gold()
        )
    
        # Group by championship
        championships = {}
        for reign in reigns:
            champ_name = reign['championship_name']
            if champ_name not in championships:
                championships[champ_name] = []
            championships[champ_name].append(reign)
    
        for champ_name, champ_reigns in championships.items():
            total_reigns = len(champ_reigns)
            total_days = sum(r['days_held'] for r in champ_reigns if not r['is_current'])
        
            # Add current reign days
            current = next((r for r in champ_reigns if r['is_current']), None)
            if current:
                total_days += (datetime.utcnow() - datetime.fromisoformat(current['won_date'])).days
        
            total_defenses = sum(r['successful_defenses'] for r in champ_reigns)
        
            status = "👑 **CURRENT CHAMPION**" if current else ""
        
            value = (
                f"{status}\n"
                f"🏆 Total reigns: **{total_reigns}x**\n"
                f"📅 Total days: {total_days}\n"
                f"🛡️ Total defenses: {total_defenses}"
            )
        
            embed.add_field(
                name=champ_name,
                value=value,
                inline=False
            )
    
        await interaction.response.send_message(embed=embed)
    

    @wrestler_group.command(name="admin_retire", description="[ADMIN] Force retire any wrestler")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.autocomplete(wrestler_name=any_wrestler_autocomplete)
    async def admin_retire(
        self,
        interaction: discord.Interaction,
        wrestler_name: str,
        reason: Optional[str] = None
    ):
        """Force retire any wrestler (admin only)"""
        
        # Get ALL wrestlers (not just user's)
        all_wrestlers = await self.db.get_all_wrestlers(interaction.guild_id)
        wrestler = next((w for w in all_wrestlers if w['name'].lower() == wrestler_name.lower()), None)
        
        if not wrestler:
            await interaction.response.send_message(
                f"❌ Wrestler '{wrestler_name}' not found in this server!",
                ephemeral=True
            )
            return
        
        # Retire the wrestler
        await self.db.retire_wrestler(wrestler['id'])
        
        embed = discord.Embed(
            title="⚰️ Wrestler Retired (Admin)",
            description=f"**{wrestler['name']}** has been forcefully retired by an administrator.",
            color=discord.Color.red()
        )
        
        embed.add_field(name="Owner", value=f"<@{wrestler['user_id']}>", inline=True)
        
        if reason:
            embed.add_field(name="Reason", value=reason, inline=False)
        
        embed.set_footer(text=f"Retired by {interaction.user.display_name}")
        
        await interaction.response.send_message(embed=embed)   

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
            try:
                await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            except:
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    async def execute_turn(self, interaction: discord.Interaction, wrestler: dict, settings: dict,
                          new_alignment: str, new_persona: str, new_signature: Optional[str], new_finisher: Optional[str]):
        print(f"[DEBUG] Wrestler dict keys: {wrestler.keys()}")
        print(f"[DEBUG] personality_traits value: {wrestler.get('personality_traits')}")
        print(f"[DEBUG] personality_traits type: {type(wrestler.get('personality_traits'))}")
        
        """Execute the turn"""
        # Get FRESH wrestler data with all fields
        all_wrestlers = await self.db.get_all_wrestlers(interaction.guild_id)
        wrestler_fresh = next((w for w in all_wrestlers if w['id'] == wrestler['id']), None)
        
        if not wrestler_fresh:
            await interaction.followup.send("❌ Wrestler not found!", ephemeral=True)
            return        
         
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


# Final name view
class FinalNameView(discord.ui.View):
    def __init__(self, parent_view):
        super().__init__(timeout=600)
        self.parent_view = parent_view
        self.add_item(BackButton())
        self.add_item(CancelButton())
    
    @discord.ui.button(label="✏️ Enter Name", style=discord.ButtonStyle.success, row=0)
    async def enter_name(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.parent_view.finalize_creation(interaction)

# View for full attributes button
class ViewAttributesButton(discord.ui.View):
    def __init__(self, wrestler):
        super().__init__(timeout=300)
        self.wrestler = wrestler
    
    @discord.ui.button(label="View Full Attributes", style=discord.ButtonStyle.primary, emoji="📊")
    async def view_full_attrs(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = create_full_attributes_embed(self.wrestler)
        await interaction.response.send_message(embed=embed, ephemeral=True)


# Main creation flow with back/cancel buttons
class WrestlerCreationView(discord.ui.View):
    def __init__(self, db, user, settings, guild):
        super().__init__(timeout=600)
        self.db = db
        self.user = user
        self.settings = settings
        self.guild = guild
        self.step = 1
        
        # Store all answers
        self.answers = {}
        self.gender = None
        self.body_type = None
        self.appearance = None
        self.outfit = None
        self.persona = None
        self.finisher_category = None
        self.signature_category = None
        self.finisher = None
        self.signature = None
        self.name = None
        
        # Navigation history for back button
        self.history = []
        
        self.update_buttons()
    
    def save_state(self):
        """Save current state for back button"""
        self.history.append({
            'step': self.step,
            'answers': self.answers.copy(),
            'gender': self.gender,
            'body_type': self.body_type,
            'persona': self.persona,
            'finisher_category': self.finisher_category,
            'signature_category': self.signature_category,
            'finisher': self.finisher,
            'signature': self.signature
        })
    
    def go_back(self):
        """Restore previous state"""
        if self.history:
            state = self.history.pop()
            self.step = state['step']
            self.answers = state['answers']
            self.gender = state['gender']
            self.body_type = state['body_type']
            self.persona = state['persona']
            self.finisher_category = state['finisher_category']
            self.signature_category = state['signature_category']
            self.finisher = state['finisher']
            self.signature = state['signature']
            return True
        return False
    
    def update_buttons(self):
        self.clear_items()
        
        # Add back button if not on first step
        if self.step > 1 and self.history:
            self.add_item(BackButton())
        
        # Add cancel button on all steps
        self.add_item(CancelButton())
        
        if self.step == 1:  # Gender
            self.add_item(GenderButton("👨 Male", "Male"))
            self.add_item(GenderButton("👩 Female", "Female"))
        
        elif self.step == 2:  # Body Type
            for body_type in BODY_TYPES.keys():
                self.add_item(BodyTypeButton(body_type, body_type))
        
        elif self.step == 3:  # Physical Build
            options = [
                ("🗿 Towering and massive", "towering"),
                ("💪 Muscular and powerful", "muscular"),
                ("🏃 Lean and quick", "lean"),
                ("🥊 Compact and explosive", "compact"),
                ("⚡ Athletic and balanced", "athletic")
            ]
            for label, value in options:
                self.add_item(AnswerButton(label, value, "physical_build"))
        
        elif self.step == 4:  # In-Ring Approach
            options = [
                ("💥 Overpower opponents", "overpower"),
                ("🧠 Outthink and outmaneuver", "outthink"),
                ("⚡ Outpace with speed", "outpace"),
                ("🦅 High-risk aerial attacks", "high_risk"),
                ("🔄 Wear them down", "wear_down")
            ]
            for label, value in options:
                self.add_item(AnswerButton(label, value, "in_ring_approach"))
        
        elif self.step == 5:  # Opponent Behavior
            options = [
                ("🤝 Show respect", "respect"),
                ("😈 Mock and taunt", "mock"),
                ("😐 Ignore them", "ignore"),
                ("📊 Study their moves", "study")
            ]
            for label, value in options:
                self.add_item(AnswerButton(label, value, "opponent_behavior"))
        
        elif self.step == 6:  # Handling Adversity
            options = [
                ("💪 Fight harder", "fight_harder"),
                ("😈 Bend the rules", "bend_rules"),
                ("🧠 Get strategic", "strategic"),
                ("🎲 Risk it all", "risk_it_all")
            ]
            for label, value in options:
                self.add_item(AnswerButton(label, value, "handling_adversity"))
        
        elif self.step == 7:  # Crowd Reaction
            options = [
                ("😇 Inspire them", "inspire"),
                ("😈 Provoke them", "provoke"),
                ("🎉 Entertain them", "entertain"),
                ("😠 Intimidate them", "intimidate")
            ]
            for label, value in options:
                self.add_item(AnswerButton(label, value, "crowd_reaction"))
        
        elif self.step == 8:  # Victory Celebration
            options = [
                ("🙏 Stay humble", "humble"),
                ("🎉 Showboat wildly", "showboat"),
                ("🤝 Acknowledge opponent", "acknowledge"),
                ("🚶 Leave quickly", "leave_quickly")
            ]
            for label, value in options:
                self.add_item(AnswerButton(label, value, "victory_celebration"))
        
        elif self.step == 9:  # Partnership
            options = [
                ("🤝 Trust completely", "trust_completely"),
                ("👀 Watch their back", "watch_back"),
                ("⚠️ Stay cautious", "cautious"),
                ("⚔️ Strike first if needed", "strike_first")
            ]
            for label, value in options:
                self.add_item(AnswerButton(label, value, "partnership"))
        
        elif self.step == 10:  # Match Tempo
            options = [
                ("⚡ Fast-paced", "fast_paced"),
                ("🧠 Methodical", "methodical"),
                ("💥 Explosive bursts", "explosive"),
                ("🎲 Unpredictable", "unpredictable")
            ]
            for label, value in options:
                self.add_item(AnswerButton(label, value, "match_tempo"))
        
        elif self.step == 11:  # Appearance Modal Button
            self.add_item(AppearanceModalButton())
        
        elif self.step == 12:  # Outfit Modal Button
            self.add_item(OutfitModalButton())
        
        elif self.step == 13:  # Persona Selection - FILTERED
            # Personas are added in OutfitModal.on_submit
            # This is only called during back navigation
            calculated = calculate_archetype_and_alignment(self.answers)
            archetype = calculated['archetype']
            alignment = calculated['alignment']
            weight_class = calculated['weight_class']
            
            from utils.constants import get_available_personas
            available_personas = get_available_personas(archetype, weight_class, alignment)
            
            if not available_personas:
                available_personas = list(PERSONAS.keys())
            
            self.add_item(PersonaDropdown(available_personas))
        
        elif self.step == 14:  # Finisher Category
            for category, data in MOVE_CATEGORIES.items():
                self.add_item(MoveCategoryButton(f"{data['emoji']} {category}", category, "finisher"))
        
        elif self.step == 15:  # Signature Category
            for category, data in MOVE_CATEGORIES.items():
                self.add_item(MoveCategoryButton(f"{data['emoji']} {category}", category, "signature"))
    
    async def finalize_creation(self, interaction: discord.Interaction):
        """Final step: Get wrestler name and create"""
        
        class NameModal(discord.ui.Modal, title="Name Your Wrestler"):
            name_input = discord.ui.TextInput(
                label="Wrestler Name",
                placeholder="Enter your wrestler's name...",
                min_length=2,
                max_length=50,
                required=True
            )
            
            def __init__(self, parent_view):
                super().__init__()
                self.parent_view = parent_view
            
            async def on_submit(self, interaction: discord.Interaction):
                wrestler_name = self.name_input.value.strip()
                
                # Check if name already exists for this user
                existing = await self.parent_view.db.get_wrestlers_by_user(
                    interaction.guild_id,
                    interaction.user.id
                )
                if any(w['name'].lower() == wrestler_name.lower() for w in existing):
                    await interaction.response.send_message(
                        f"❌ You already have a wrestler named '{wrestler_name}'!",
                        ephemeral=True
                    )
                    return
                
                # Calculate archetype, alignment, weight class
                calculated = calculate_archetype_and_alignment(self.parent_view.answers)
                archetype = calculated['archetype']
                alignment = calculated['alignment']
                weight_class = calculated['weight_class']
                
                # Calculate personality traits
                personality = calculate_personality_traits(self.parent_view.answers)
                
                # Generate attributes (DEFAULT 50 NOW!)
                attributes = get_base_attributes(archetype, self.parent_view.persona)
                
                # Auto-generate height (gender-based)
                height_data = get_height_for_archetype(archetype, self.parent_view.gender)
                height_feet_decimal = random.uniform(height_data['feet_min'], height_data['feet_max'])
                feet = int(height_feet_decimal)
                inches = int((height_feet_decimal - feet) * 12)
                height_feet_str = f"{feet}'{inches}\""
                height_cm = height_data['cm_min'] + int((height_feet_decimal - height_data['feet_min']) / 
                                                        (height_data['feet_max'] - height_data['feet_min']) * 
                                                        (height_data['cm_max'] - height_data['cm_min']))
                
                # Create wrestler
                wrestler_id = await self.parent_view.db.create_wrestler(
                    guild_id=interaction.guild_id,
                    user_id=interaction.user.id,
                    name=wrestler_name,
                    archetype=archetype,
                    weight_class=weight_class,
                    persona=self.parent_view.persona,
                    finisher=self.parent_view.finisher,
                    signature=self.parent_view.signature,
                    attributes=attributes,
                    personality=personality,
                    gender=self.parent_view.gender,
                    alignment=alignment,
                    body_type=self.parent_view.body_type,
                    height_feet=height_feet_str,
                    height_cm=height_cm,
                    appearance=self.parent_view.appearance,
                    outfit=self.parent_view.outfit
                )
                
                # Get created wrestler
                wrestler = await self.parent_view.db.get_wrestler_by_id(wrestler_id, interaction.guild_id)
                wrestler['currency_name'] = self.parent_view.settings['currency_name']
                wrestler['currency_symbol'] = self.parent_view.settings['currency_symbol']
                
                # Success embed
                embed = create_wrestler_embed(wrestler, interaction.user)
                embed.title = f"✅ Wrestler Created: {wrestler_name}"
                embed.color = discord.Color.green()
                
                await interaction.response.edit_message(content=None, embed=embed, view=None)
                
                # Full announcement
                if self.parent_view.settings['announcement_channel_id']:
                    channel = self.parent_view.guild.get_channel(
                        self.parent_view.settings['announcement_channel_id']
                    )
                    if channel:
                        announce_embed = create_full_wrestler_embed(wrestler, interaction.user)
                        await channel.send(embed=announce_embed)
        
        modal = NameModal(self)
        await interaction.response.send_modal(modal)


# Navigation buttons
class BackButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="← Back", style=discord.ButtonStyle.secondary, row=4)
    
    async def callback(self, interaction: discord.Interaction):
        view: WrestlerCreationView = self.view
        
        if view.go_back():
            view.update_buttons()
            
            step_names = [
                "Gender", "Body Type", "Physical Build", "In-Ring Approach",
                "Opponent Behavior", "Handling Adversity", "Crowd Reaction",
                "Victory Celebration", "Partnership", "Match Tempo",
                "Appearance", "Outfit", "Persona", "Finisher", "Signature"
            ]
            
            embed = discord.Embed(
                title="🏆 Create Your Wrestler",
                description="Went back to previous question.",
                color=discord.Color.blue()
            )
            
            if view.step <= len(step_names):
                embed.add_field(
                    name=f"Question {view.step}/16",
                    value=f"**{step_names[view.step-1]}**",
                    inline=False
                )
            
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await interaction.response.send_message(
                "❌ Can't go back further!",
                ephemeral=True
            )


class CancelButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="✖ Cancel", style=discord.ButtonStyle.danger, row=4)
    
    async def callback(self, interaction: discord.Interaction):
        # Confirmation view
        class ConfirmCancelView(discord.ui.View):
            def __init__(self, original_message):
                super().__init__(timeout=30)
                self.original_message = original_message
            
            @discord.ui.button(label="Yes, Cancel Creation", style=discord.ButtonStyle.danger)
            async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
                # Delete the original creation message
                try:
                    await self.original_message.delete()
                except:
                    pass  # Message might already be deleted
                
                await interaction.response.send_message(
                    "❌ Wrestler creation cancelled.",
                    ephemeral=True
                )
                self.stop()
            
            @discord.ui.button(label="No, Continue", style=discord.ButtonStyle.success)
            async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.response.edit_message(
                    content="✅ Continuing creation...",
                    embed=None,
                    view=None
                )
                self.stop()
        
        embed = discord.Embed(
            title="⚠️ Cancel Creation?",
            description="Are you sure you want to cancel? All progress will be lost.",
            color=discord.Color.orange()
        )
        
        # Get the original message to delete it later
        original_message = interaction.message
        
        await interaction.response.send_message(embed=embed, view=ConfirmCancelView(original_message), ephemeral=True)


# Gender button
class GenderButton(discord.ui.Button):
    def __init__(self, label, gender):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.gender = gender
    
    async def callback(self, interaction: discord.Interaction):
        view: WrestlerCreationView = self.view
        view.save_state()
        view.gender = self.gender
        view.step = 2
        view.update_buttons()
        
        embed = discord.Embed(
            title="🏆 Create Your Wrestler",
            description=f"**Gender:** {self.gender}",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Question 2/16",
            value="**What's your wrestler's body type?**",
            inline=False
        )
        
        await interaction.response.edit_message(embed=embed, view=view)


# Body Type button
class BodyTypeButton(discord.ui.Button):
    def __init__(self, label, body_type):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.body_type = body_type
    
    async def callback(self, interaction: discord.Interaction):
        view: WrestlerCreationView = self.view
        view.save_state()
        view.body_type = self.body_type
        view.step = 3
        view.update_buttons()
        
        embed = discord.Embed(
            title="🏆 Create Your Wrestler",
            description=f"**Body Type:** {self.body_type}",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Question 3/16",
            value="**What's your wrestler's physical build?**",
            inline=False
        )
        
        await interaction.response.edit_message(embed=embed, view=view)


# Generic answer button for behavioral questions
class AnswerButton(discord.ui.Button):
    def __init__(self, label, value, answer_key):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.value = value
        self.answer_key = answer_key
    
    async def callback(self, interaction: discord.Interaction):
        view: WrestlerCreationView = self.view
        view.save_state()
        view.answers[self.answer_key] = self.value
        view.step += 1
        view.update_buttons()
        
        step_names = {
            3: "Physical Build", 4: "In-Ring Approach", 5: "Opponent Behavior",
            6: "Handling Adversity", 7: "Crowd Reaction", 8: "Victory Celebration",
            9: "Partnership", 10: "Match Tempo"
        }
        
        next_questions = {
            4: "How do you approach your opponents?",
            5: "How do you treat your opponents?",
            6: "How do you handle adversity?",
            7: "What's your goal with the crowd?",
            8: "How do you celebrate victory?",
            9: "How do you view partnerships?",
            10: "What's your preferred match tempo?",
            11: "Describe your appearance"
        }
        
        embed = discord.Embed(
            title="🏆 Create Your Wrestler",
            description=f"**{step_names.get(view.step-1, 'Answer')}:** Selected",
            color=discord.Color.blue()
        )
        
        if view.step in next_questions:
            embed.add_field(
                name=f"Question {view.step}/16",
                value=f"**{next_questions[view.step]}**",
                inline=False
            )
        
        await interaction.response.edit_message(embed=embed, view=view)


# Appearance Modal Button
class AppearanceModalButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="📝 Describe Appearance", style=discord.ButtonStyle.primary)
    
    async def callback(self, interaction: discord.Interaction):
        modal = AppearanceModal(self.view)
        await interaction.response.send_modal(modal)


class AppearanceModal(discord.ui.Modal, title="Describe Your Wrestler's Appearance"):
    appearance_input = discord.ui.TextInput(
        label="Appearance",
        placeholder="Hair color, facial features, build details, etc.",
        style=discord.TextStyle.paragraph,
        min_length=10,
        max_length=500,
        required=True
    )
    
    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view
    
    async def on_submit(self, interaction: discord.Interaction):
        view: WrestlerCreationView = self.parent_view
        view.save_state()
        view.appearance = self.appearance_input.value.strip()
        view.step = 12
        view.update_buttons()
        
        embed = discord.Embed(
            title="🏆 Create Your Wrestler",
            description="✅ Appearance saved!",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Question 12/16",
            value="**Describe your wrestler's ring outfit:**",
            inline=False
        )
        
        await interaction.response.edit_message(embed=embed, view=view)


# Outfit Modal Button
class OutfitModalButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="👕 Describe Outfit", style=discord.ButtonStyle.primary)
    
    async def callback(self, interaction: discord.Interaction):
        modal = OutfitModal(self.view)
        await interaction.response.send_modal(modal)


class OutfitModal(discord.ui.Modal, title="Describe Your Wrestler's Ring Outfit"):
    outfit_input = discord.ui.TextInput(
        label="Ring Outfit",
        placeholder="Colors, style, accessories, gear, etc.",
        style=discord.TextStyle.paragraph,
        min_length=10,
        max_length=500,
        required=True
    )
    
    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            view: WrestlerCreationView = self.parent_view
            view.save_state()
            view.outfit = self.outfit_input.value.strip()
            view.step = 13
            
            # Calculate archetype/alignment for persona filtering
            calculated = calculate_archetype_and_alignment(view.answers)
            archetype = calculated['archetype']
            alignment = calculated['alignment']
            weight_class = calculated['weight_class']
            
            # Get available personas
            from utils.constants import get_available_personas
            available_personas = get_available_personas(archetype, weight_class, alignment)
            
            if not available_personas:
                # Fallback - should never happen
                available_personas = list(PERSONAS.keys())
            
            # Update view with filtered personas
            view.clear_items()
            view.add_item(PersonaDropdown(available_personas))
            view.add_item(BackButton())
            view.add_item(CancelButton())
            
            embed = discord.Embed(
                title="🏆 Create Your Wrestler",
                description="✅ Outfit saved!",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="Question 13/16",
                value="**Choose your wrestling persona:**",
                inline=False
            )
            
            await interaction.response.edit_message(embed=embed, view=view)
            
        except Exception as e:
            print(f"[ERROR] OutfitModal.on_submit failed: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            
            await interaction.response.send_message(
                f"❌ **Error:** {type(e).__name__}: {str(e)}\n\nPlease report this to an admin!",
                ephemeral=True
            )


# Persona dropdown - FILTERED
class PersonaDropdown(discord.ui.Select):
    def __init__(self, available_personas):
        # Create options only for available personas
        options = [
            discord.SelectOption(
                label=persona,
                description=PERSONAS[persona]['description'][:100]
            )
            for persona in available_personas
        ]
        
        super().__init__(
            placeholder="Choose your wrestling persona...",
            min_values=1,
            max_values=1,
            options=options,
            row=0
        )
    
    async def callback(self, interaction: discord.Interaction):
        view: WrestlerCreationView = self.view
        view.save_state()
        view.persona = self.values[0]
        view.step = 14
        view.update_buttons()
        
        embed = discord.Embed(
            title="🏆 Create Your Wrestler",
            description=f"**{view.persona}** - {PERSONAS[view.persona]['description']}",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Question 14/16",
            value="**What type of finisher does your wrestler use?**",
            inline=False
        )
        
        await interaction.response.edit_message(embed=embed, view=view)


# Move category button with smart filtering and ERROR LOGGING
class MoveCategoryButton(discord.ui.Button):
    def __init__(self, label, category, move_type):
        super().__init__(label=label, style=discord.ButtonStyle.primary, row=0 if move_type=="finisher" else 1)
        self.category = category
        self.move_type = move_type
    
    async def callback(self, interaction: discord.Interaction):
        try:
            # Step 1: Defer response
            print(f"[DEBUG] Step 1: Attempting to defer response for {self.category} {self.move_type}")
            await interaction.response.defer()
            print(f"[DEBUG] Step 1: Successfully deferred!")
            
            view: WrestlerCreationView = self.view
            
            # Step 2: Calculate alignment
            print(f"[DEBUG] Step 2: Calculating alignment...")
            calculated = calculate_archetype_and_alignment(view.answers)
            alignment = calculated['alignment']
            archetype = calculated['archetype']
            print(f"[DEBUG] Step 2: Alignment={alignment}, Archetype={archetype}")
            
            # Step 3: Get all moves
            print(f"[DEBUG] Step 3: Getting moves from {self.category}...")
            all_moves = MOVE_CATEGORIES[self.category]['moves']['Finishers' if self.move_type == 'finisher' else 'Signatures']
            print(f"[DEBUG] Step 3: Found {len(all_moves)} total moves")
            
            # Step 4: Filter taken moves
            print(f"[DEBUG] Step 4: Checking which moves are available...")
            available_moves = []
            for i, move in enumerate(all_moves):
                is_taken = await view.db.check_move_exists(
                    interaction.guild_id,
                    move,
                    self.move_type
                )
                if not is_taken:
                    available_moves.append(move)
                if i % 5 == 0:  # Progress every 5 moves
                    print(f"[DEBUG] Step 4: Checked {i+1}/{len(all_moves)} moves...")
            
            print(f"[DEBUG] Step 4: {len(available_moves)} moves available")
            
            if not available_moves:
                print(f"[DEBUG] ERROR: No moves available!")
                await interaction.followup.send(
                    f"❌ All {self.category} {self.move_type}s are taken! Choose another category.",
                    ephemeral=True
                )
                return
            
            # Step 5: Smart filtering
            print(f"[DEBUG] Step 5: Filtering moves by character...")
            filtered_moves = self.filter_moves_by_character(
                available_moves,
                alignment,
                archetype,
                self.category
            )
            print(f"[DEBUG] Step 5: Filtered to {len(filtered_moves)} moves: {filtered_moves}")
            
            # Step 6: Create view
            print(f"[DEBUG] Step 6: Creating FilteredMoveSelectionView...")
            view.save_state()
            move_view = FilteredMoveSelectionView(view, self.category, self.move_type, filtered_moves)
            print(f"[DEBUG] Step 6: View created successfully")
            
            # Step 7: Create embed
            print(f"[DEBUG] Step 7: Creating embed...")
            step = "14/16" if self.move_type == "finisher" else "15/16"
            move_label = "Finisher" if self.move_type == "finisher" else "Signature"
            
            embed = discord.Embed(
                title="🏆 Create Your Wrestler",
                color=discord.Color.blue()
            )
            embed.add_field(
                name=f"Question {step}",
                value=f"**Choose your {move_label}:**\n\n{self.category}\n*Showing {len(filtered_moves)} moves suited to your character*",
                inline=False
            )
            print(f"[DEBUG] Step 7: Embed created")
            
            # Step 8: Edit message
            print(f"[DEBUG] Step 8: Editing message with followup...")
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=embed,
                view=move_view
            )
            print(f"[DEBUG] Step 8: SUCCESS! Message edited")
            
        except Exception as e:
            # Catch ANY error and show it
            print(f"[DEBUG] EXCEPTION CAUGHT: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            
            try:
                await interaction.followup.send(
                    f"❌ **ERROR:** {type(e).__name__}: {str(e)}\n\nPlease report this to an admin!",
                    ephemeral=True
                )
            except:
                # If followup fails, try response
                try:
                    await interaction.response.send_message(
                        f"❌ **ERROR:** {type(e).__name__}: {str(e)}",
                        ephemeral=True
                    )
                except:
                    print("[DEBUG] Could not send error message to user")
    
    def filter_moves_by_character(self, available_moves, alignment, archetype, category):
        """Filter moves based on alignment and archetype - return 5-6 best fits"""
        
        # Define move preferences
        heel_keywords = ['choke', 'sleeper', 'guillotine', 'rear naked', 'trap', 'heel', 'behind']
        face_keywords = ['splash', 'press', 'crossbody', 'moonsault', 'elbow drop']
        technical_keywords = ['lock', 'bar', 'crab', 'stretch', 'figure']
        power_keywords = ['slam', 'bomb', 'press', 'gorilla', 'military']
        aerial_keywords = ['diving', 'springboard', 'moonsault', 'splash', 'shooting star', 'top rope']
        
        scored_moves = []
        
        for move in available_moves:
            move_lower = move.lower()
            score = 0
            
            # Alignment scoring
            if alignment == "Heel":
                if any(kw in move_lower for kw in heel_keywords):
                    score += 3
            elif alignment == "Face":
                if any(kw in move_lower for kw in face_keywords):
                    score += 3
                if any(kw in move_lower for kw in heel_keywords):
                    score -= 2
            
            # Archetype scoring
            if archetype == "Technical":
                if any(kw in move_lower for kw in technical_keywords):
                    score += 2
            elif archetype == "Powerhouse":
                if any(kw in move_lower for kw in power_keywords):
                    score += 2
            elif archetype == "High Flyer":
                if any(kw in move_lower for kw in aerial_keywords):
                    score += 2
            
            scored_moves.append((move, score))
        
        # Sort by score and return top 5-6
        scored_moves.sort(key=lambda x: x[1], reverse=True)
        
        # Return top 6, or all if less than 6
        result = [move for move, score in scored_moves[:6]]
        
        # If we have less than 5, add more random ones
        if len(result) < 5 and len(available_moves) > len(result):
            remaining = [m for m in available_moves if m not in result]
            result.extend(remaining[:5-len(result)])
        
        return result


# Filtered move selection
class FilteredMoveSelectionView(discord.ui.View):
    def __init__(self, parent_view, category, move_type, filtered_moves):
        super().__init__(timeout=600)
        self.parent_view = parent_view
        self.category = category
        self.move_type = move_type
        
        # Add move buttons - distribute across rows (max 5 per row)
        for i, move in enumerate(filtered_moves):
            row = i // 5  # Row 0 for moves 0-4, Row 1 for moves 5-9, etc.
            button = MoveButton(move, move_type)
            button.row = row
            self.add_item(button)
        
        # Add back button on last row - goes back to category selection
        last_row = (len(filtered_moves) - 1) // 5 + 1
        back_btn = BackToCategoryButton(move_type)
        back_btn.row = last_row
        cancel_btn = CancelButton()
        cancel_btn.row = last_row
        
        self.add_item(back_btn)
        self.add_item(cancel_btn)


# Special Back button for move selection - returns to category
class BackToCategoryButton(discord.ui.Button):
    def __init__(self, move_type):
        super().__init__(label="← Back to Categories", style=discord.ButtonStyle.secondary)
        self.move_type = move_type
    
    async def callback(self, interaction: discord.Interaction):
        view: FilteredMoveSelectionView = self.view
        parent_view: WrestlerCreationView = view.parent_view
        
        # Restore parent view buttons (category selection)
        parent_view.update_buttons()
        
        step = "14/16" if self.move_type == "finisher" else "15/16"
        move_label = "Finisher" if self.move_type == "finisher" else "Signature"
        
        embed = discord.Embed(
            title="🏆 Create Your Wrestler",
            color=discord.Color.blue()
        )
        embed.add_field(
            name=f"Question {step}",
            value=f"**What type of {move_label.lower()} does your wrestler use?**\n\nChoose a category:",
            inline=False
        )
        
        await interaction.response.edit_message(embed=embed, view=parent_view)


# Move button
class MoveButton(discord.ui.Button):
    def __init__(self, move, move_type):
        super().__init__(label=move, style=discord.ButtonStyle.success)
        self.move = move
        self.move_type = move_type
    
    async def callback(self, interaction: discord.Interaction):
        parent_view: WrestlerCreationView = self.view.parent_view
        
        # Double-check availability
        is_taken = await parent_view.db.check_move_exists(
            interaction.guild_id,
            self.move,
            self.move_type
        )
        
        if is_taken:
            await interaction.response.send_message(
                f"❌ '{self.move}' was just taken! Please choose another.",
                ephemeral=True
            )
            return
        
        if self.move_type == 'finisher':
            parent_view.finisher = self.move
            parent_view.step = 15
            parent_view.update_buttons()
            
            embed = discord.Embed(
                title="🏆 Create Your Wrestler",
                description=f"**Finisher:** {self.move}",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="Question 15/16",
                value="**What type of signature move?**",
                inline=False
            )
            
            await interaction.response.edit_message(embed=embed, view=parent_view)
        else:
            parent_view.signature = self.move
            
            embed = discord.Embed(
                title="🏆 Create Your Wrestler",
                description=f"**Signature:** {self.move}",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="Question 16/16",
                value="**Name your wrestler:**",
                inline=False
            )
            
            name_view = FinalNameView(parent_view)
            await interaction.response.edit_message(embed=embed, view=name_view)

async def setup(bot):
    await bot.add_cog(Wrestler(bot))
