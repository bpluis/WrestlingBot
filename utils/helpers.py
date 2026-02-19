import discord
from datetime import datetime
from typing import Dict, List, Any
import random

def create_wrestler_embed(wrestler_data: Dict[str, Any], user: discord.User) -> discord.Embed:
    """Create a rich embed to display wrestler information"""
    
    # Determine alignment emoji
    alignment = wrestler_data.get('alignment', 'Neutral')
    alignment_emoji = "😇" if alignment == "Face" else "😈" if alignment == "Heel" else "⚖️"
    
    embed = discord.Embed(
        title=f"🏆 {wrestler_data['name']}",
        description=f"{alignment_emoji} **{alignment}** | **{wrestler_data['gender']}** | **{wrestler_data['archetype']}**",
        color=discord.Color.gold()
    )
    
    embed.set_author(name=f"Owned by {user.name}", icon_url=user.display_avatar.url)
    
    # Physical Stats
    height_display = f"{wrestler_data.get('height_feet', '?')}'  ({wrestler_data.get('height_cm', '?')} cm)"
    embed.add_field(
        name="📏 Physical",
        value=f"**Height:** {height_display}\n**Weight Class:** {wrestler_data['weight_class']}\n**Build:** {wrestler_data.get('body_type', 'Athletic')}",
        inline=True
    )
    
    # Performance Stats
    embed.add_field(
        name="📊 Record",
        value=f"**Level:** {wrestler_data.get('level', 1)}\n**Wins:** {wrestler_data.get('wins', 0)}\n**Losses:** {wrestler_data.get('losses', 0)}",
        inline=True
    )
    
    # Currency
    currency_symbol = wrestler_data.get('currency_symbol', '$')
    embed.add_field(
        name=f"💰 {wrestler_data.get('currency_name', 'Dollars')}",
        value=f"{currency_symbol}{wrestler_data.get('currency', 0)}",
        inline=True
    )
    
    # Style & Persona
    embed.add_field(
        name="🎭 Style",
        value=f"**Persona:** {wrestler_data['persona']}",
        inline=False
    )
    
    # Moves
    embed.add_field(
        name="🎯 Finisher",
        value=f"{wrestler_data.get('finisher', 'None')}",
        inline=True
    )
    
    embed.add_field(
        name="⚡ Signature",
        value=f"{wrestler_data.get('signature', 'None')}",
        inline=True
    )
    
    embed.add_field(name="\u200b", value="\u200b", inline=True)  # Spacer
    
    # Top Attributes (show top 6)
    attributes = wrestler_data.get('attributes', {})
    if attributes:
        sorted_attrs = sorted(attributes.items(), key=lambda x: x[1], reverse=True)[:6]
        attr_text = "\n".join([f"**{attr}:** {value}" for attr, value in sorted_attrs])
        embed.add_field(
            name="📈 Top Attributes",
            value=attr_text,
            inline=False
        )
    
    # Appearance (if provided)
    if wrestler_data.get('appearance'):
        embed.add_field(
            name="👤 Appearance",
            value=wrestler_data['appearance'][:100],  # Truncate if too long
            inline=False
        )
    
    embed.set_footer(text=f"Wrestler ID: {wrestler_data['id']} | Created {wrestler_data.get('created_at', 'Unknown')[:10]}")
    embed.timestamp = datetime.utcnow()
    
    return embed


def create_full_wrestler_embed(wrestler_data: Dict[str, Any], user: discord.User) -> discord.Embed:
    """Create a COMPLETE embed with ALL wrestler information for announcements"""
    
    alignment = wrestler_data.get('alignment', 'Neutral')
    alignment_emoji = "😇" if alignment == "Face" else "😈" if alignment == "Heel" else "⚖️"
    
    embed = discord.Embed(
        title=f"🆕 {wrestler_data['name']} Joins the League!",
        description=f"{alignment_emoji} **{alignment}** | **{wrestler_data['gender']}** | **{wrestler_data['archetype']}**",
        color=discord.Color.green()
    )
    
    embed.set_author(name=f"Owner: {user.name}", icon_url=user.display_avatar.url)
    
    # Physical & Style
    height_display = f"{wrestler_data.get('height_feet', '?')}'  ({wrestler_data.get('height_cm', '?')} cm)"
    embed.add_field(
        name="📏 Physical Stats",
        value=f"**Height:** {height_display}\n**Weight Class:** {wrestler_data['weight_class']}\n**Build:** {wrestler_data.get('body_type', 'Athletic')}",
        inline=True
    )
    
    embed.add_field(
        name="🎭 Wrestling Style",
        value=f"**Archetype:** {wrestler_data['archetype']}\n**Persona:** {wrestler_data['persona']}",
        inline=True
    )
    
    embed.add_field(name="\u200b", value="\u200b", inline=True)  # Spacer
    
    # Moves
    embed.add_field(
        name="💥 Signature Moves",
        value=f"**Finisher:** {wrestler_data.get('finisher', 'None')}\n**Signature:** {wrestler_data.get('signature', 'None')}",
        inline=False
    )
    
    # Appearance
    if wrestler_data.get('appearance'):
        embed.add_field(
            name="👤 Appearance",
            value=wrestler_data['appearance'][:200],
            inline=False
        )
    
    if wrestler_data.get('outfit'):
        embed.add_field(
            name="👕 Outfit",
            value=wrestler_data['outfit'][:200],
            inline=False
        )
    
    # All Attributes
    attributes = wrestler_data.get('attributes', {})
    if attributes:
        # Group by category
        offense = ["Arm Power", "Leg Power", "Grapple Offense", "Running Offense", "Aerial Offense", "Aerial Range"]
        submissions = ["Power Submission", "Technical Submission", "Power Submission Defense", "Technical Submission Defense"]
        reversals = ["Strike Reversal", "Grapple Reversal", "Aerial Reversal", "Pin Escape"]
        durability = ["Head Durability", "Arm Durability", "Leg Durability"]
        physical = ["Strength", "Stamina", "Agility", "Movement Speed", "Recovery"]
        special = ["Special", "Finisher"]
        
        def format_attrs(attr_list):
            return " • ".join([f"{attr}: {attributes.get(attr, 30)}" for attr in attr_list])
        
        embed.add_field(name="⚔️ Offense", value=format_attrs(offense), inline=False)
        embed.add_field(name="🔒 Submissions", value=format_attrs(submissions), inline=False)
        embed.add_field(name="🛡️ Reversals", value=format_attrs(reversals), inline=False)
        embed.add_field(name="💪 Durability", value=format_attrs(durability), inline=False)
        embed.add_field(name="🏃 Physical", value=format_attrs(physical), inline=False)
        embed.add_field(name="✨ Special", value=format_attrs(special), inline=False)
    
    # Personality Traits
    personality = wrestler_data.get('personality', {})
    if personality:
        trait_text = "\n".join([
            f"**{trait.replace('_', ' ')}:** {value:+d}"
            for trait, value in personality.items()
        ])
        embed.add_field(
            name="🎭 Personality Traits",
            value=trait_text,
            inline=False
        )
    
    embed.set_footer(text=f"Good luck in the ring, {wrestler_data['name']}!")
    embed.timestamp = datetime.utcnow()
    
    return embed


def create_full_attributes_embed(wrestler_data: Dict[str, Any]) -> discord.Embed:
    """Create a detailed embed showing all wrestler attributes"""
    
    embed = discord.Embed(
        title=f"📊 Full Attributes - {wrestler_data['name']}",
        color=discord.Color.blue()
    )
    
    attributes = wrestler_data.get('attributes', {})
    
    # Group attributes by category
    offense = ["Arm Power", "Leg Power", "Grapple Offense", "Running Offense", "Aerial Offense", "Aerial Range"]
    submissions = ["Power Submission", "Technical Submission", "Power Submission Defense", "Technical Submission Defense"]
    reversals = ["Strike Reversal", "Grapple Reversal", "Aerial Reversal", "Pin Escape"]
    durability = ["Head Durability", "Arm Durability", "Leg Durability"]
    physical = ["Strength", "Stamina", "Agility", "Movement Speed", "Recovery"]
    special = ["Special", "Finisher"]
    
    def format_attrs(attr_list):
        return "\n".join([f"**{attr}:** {attributes.get(attr, 30)}" for attr in attr_list])
    
    embed.add_field(name="⚔️ Offense", value=format_attrs(offense), inline=True)
    embed.add_field(name="🔒 Submissions", value=format_attrs(submissions), inline=True)
    embed.add_field(name="🛡️ Reversals", value=format_attrs(reversals), inline=True)
    embed.add_field(name="💪 Durability", value=format_attrs(durability), inline=True)
    embed.add_field(name="🏃 Physical", value=format_attrs(physical), inline=True)
    embed.add_field(name="✨ Special", value=format_attrs(special), inline=True)
    
    return embed


def create_shop_embed(currency_name: str, currency_symbol: str, user_balance: int) -> discord.Embed:
    """Create an embed for the shop"""
    
    embed = discord.Embed(
        title="🛒 Wrestler Shop",
        description="Upgrade your wrestler with attributes and moves!",
        color=discord.Color.green()
    )
    
    embed.add_field(
        name=f"💰 Your Balance",
        value=f"{currency_symbol}{user_balance} {currency_name}",
        inline=False
    )
    
    embed.add_field(
        name="📈 Attribute Upgrades",
        value=(
            f"**+1 Attribute** - {currency_symbol}150\n"
            f"**+5 Attribute Bundle** - {currency_symbol}700 *(5% discount)*\n"
            f"**+10 Attribute Bundle** - {currency_symbol}1,300 *(13% discount)*"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🎯 Premium Moves",
        value="*Coming in Phase 2!*",
        inline=False
    )
    
    embed.add_field(
        name="📦 Loot Packs",
        value="*Coming in Phase 2!*",
        inline=False
    )
    
    embed.set_footer(text="Use the buttons below to make a purchase!")
    
    return embed


def create_pending_upgrades_embed(upgrades: List[Dict[str, Any]]) -> discord.Embed:
    """Create an embed showing pending wrestler upgrades for admin with old→new values"""
    
    if not upgrades:
        embed = discord.Embed(
            title="✅ No Pending Upgrades",
            description="All upgrades have been processed!",
            color=discord.Color.green()
        )
        return embed
    
    embed = discord.Embed(
        title="📋 Pending Wrestler Upgrades",
        description=f"Total pending upgrades: {len(upgrades)}",
        color=discord.Color.orange()
    )
    
    # Group by wrestler
    wrestler_upgrades = {}
    for upgrade in upgrades:
        wrestler_name = upgrade['wrestler_name']
        if wrestler_name not in wrestler_upgrades:
            wrestler_upgrades[wrestler_name] = []
        wrestler_upgrades[wrestler_name].append(upgrade)
    
    for wrestler_name, wrestler_ups in wrestler_upgrades.items():
        upgrade_text = "\n".join([
            f"• **{up['attribute']}:** {up.get('old_value', '?')} → **{up.get('new_value', '?')}** (+{up['amount']})"
            for up in wrestler_ups
        ])
        
        embed.add_field(
            name=f"🏆 {wrestler_name}",
            value=upgrade_text,
            inline=False
        )
    
    embed.set_footer(text="Use /clear_upgrades when you've applied these in-game")
    
    return embed


def format_currency(amount: int, symbol: str) -> str:
    """Format currency with symbol"""
    return f"{symbol}{amount:,}"


def calculate_archetype_and_alignment(answers: Dict[str, str]) -> Dict[str, str]:
    """
    Calculate archetype and face/heel alignment from creation answers
    Returns: {"archetype": str, "alignment": str, "weight_class": str}
    """
    
    # Archetype scoring
    archetype_score = {
        "Giant": 0,
        "Powerhouse": 0,
        "Technical": 0,
        "High Flyer": 0,
        "Striker": 0
    }
    
    # Alignment scoring
    alignment_score = 0  # Positive = Face, Negative = Heel
    
    # Question 1: Physical Build
    build = answers.get('physical_build')
    if build == "towering":
        archetype_score["Giant"] += 4
        archetype_score["Powerhouse"] += 1
    elif build == "muscular":
        archetype_score["Powerhouse"] += 3
        archetype_score["Striker"] += 1
    elif build == "lean":
        archetype_score["Technical"] += 2
        archetype_score["High Flyer"] += 2
    elif build == "compact":
        archetype_score["High Flyer"] += 3
        archetype_score["Striker"] += 1
    elif build == "athletic":
        archetype_score["Technical"] += 2
        archetype_score["Powerhouse"] += 1
        archetype_score["Striker"] += 1
    
    # Question 2: In-Ring Approach
    approach = answers.get('in_ring_approach')
    if approach == "overpower":
        archetype_score["Powerhouse"] += 3
        archetype_score["Giant"] += 2
    elif approach == "outthink":
        archetype_score["Technical"] += 4
        alignment_score += 2  # Technical wrestlers tend to be faces
    elif approach == "outpace":
        archetype_score["Striker"] += 2
        archetype_score["High Flyer"] += 2
    elif approach == "high_risk":
        archetype_score["High Flyer"] += 4
        alignment_score += 1
    elif approach == "wear_down":
        archetype_score["Technical"] += 2
        archetype_score["Powerhouse"] += 2
    
    # Question 3: Match Tempo
    tempo = answers.get('match_tempo')
    if tempo == "fast_paced":
        archetype_score["High Flyer"] += 2
        archetype_score["Striker"] += 2
    elif tempo == "methodical":
        archetype_score["Technical"] += 3
        alignment_score += 1
    elif tempo == "explosive":
        archetype_score["Powerhouse"] += 2
        archetype_score["Striker"] += 1
    elif tempo == "unpredictable":
        archetype_score["High Flyer"] += 1
        archetype_score["Technical"] += 1
        alignment_score -= 1  # Unpredictable leans heel
    
    # Question 4: Opponent Behavior
    opponent = answers.get('opponent_behavior')
    if opponent == "respect":
        alignment_score += 3  # Face
    elif opponent == "mock":
        alignment_score -= 3  # Heel
    elif opponent == "ignore":
        alignment_score -= 1  # Slight heel
    elif opponent == "study":
        archetype_score["Technical"] += 2
        alignment_score += 1
    
    # Question 5: Handling Adversity
    adversity = answers.get('handling_adversity')
    if adversity == "fight_harder":
        alignment_score += 2  # Face
    elif adversity == "bend_rules":
        alignment_score -= 3  # Heel
    elif adversity == "strategic":
        archetype_score["Technical"] += 1
    elif adversity == "risk_it_all":
        archetype_score["High Flyer"] += 2
    
    # Question 6: Crowd Reaction
    crowd = answers.get('crowd_reaction')
    if crowd == "inspire":
        alignment_score += 3  # Face
    elif crowd == "provoke":
        alignment_score -= 3  # Heel
    elif crowd == "entertain":
        alignment_score += 1  # Slight face
        archetype_score["High Flyer"] += 1
    elif crowd == "intimidate":
        alignment_score -= 2  # Heel
        archetype_score["Giant"] += 1
        archetype_score["Powerhouse"] += 1
    
    # Determine archetype
    archetype = max(archetype_score.items(), key=lambda x: x[1])[0]
    
    # Determine alignment
    if alignment_score > 2:
        alignment = "Face"
    elif alignment_score < -2:
        alignment = "Heel"
    else:
        alignment = "Tweener"
    
    # Determine weight class from archetype and build
    weight_class_map = {
        "Giant": "Ultraheavy",
        "Powerhouse": "Superheavy" if build == "muscular" else "Heavy",
        "Technical": "Heavy" if build in ["muscular", "athletic"] else "Light",
        "High Flyer": "Cruiser" if build == "compact" else "Light",
        "Striker": "Light" if build in ["lean", "athletic"] else "Heavy"
    }
    weight_class = weight_class_map.get(archetype, "Heavy")
    
    return {
        "archetype": archetype,
        "alignment": alignment,
        "weight_class": weight_class
    }


def calculate_personality_traits(answers: Dict[str, str]) -> Dict[str, int]:
    """
    Calculate personality trait values (-100 to +100) from creation answers
    """
    
    traits = {
        "Prideful_Egotistical": 0,
        "Respectful_Disrespectful": 0,
        "Perseverant_Desperate": 0,
        "Loyal_Treacherous": 0,
        "Bold_Cowardly": 0,
        "Disciplined_Aggressive": 0
    }
    
    # Opponent Behavior influences Respectful/Disrespectful
    opponent = answers.get('opponent_behavior')
    if opponent == "respect":
        traits["Respectful_Disrespectful"] += 40
    elif opponent == "mock":
        traits["Respectful_Disrespectful"] -= 40
    elif opponent == "ignore":
        traits["Respectful_Disrespectful"] -= 20
    elif opponent == "study":
        traits["Respectful_Disrespectful"] += 20
    
    # Handling Adversity influences Perseverant/Desperate
    adversity = answers.get('handling_adversity')
    if adversity == "fight_harder":
        traits["Perseverant_Desperate"] += 35
        traits["Bold_Cowardly"] += 30
    elif adversity == "bend_rules":
        traits["Perseverant_Desperate"] -= 40
        traits["Disciplined_Aggressive"] -= 30
    elif adversity == "strategic":
        traits["Perseverant_Desperate"] += 25
        traits["Disciplined_Aggressive"] += 20
    elif adversity == "risk_it_all":
        traits["Bold_Cowardly"] += 40
        traits["Disciplined_Aggressive"] -= 20
    
    # Crowd Reaction influences Prideful/Egotistical
    crowd = answers.get('crowd_reaction')
    if crowd == "inspire":
        traits["Prideful_Egotistical"] += 30
    elif crowd == "provoke":
        traits["Prideful_Egotistical"] -= 40
    elif crowd == "entertain":
        traits["Prideful_Egotistical"] += 20
    elif crowd == "intimidate":
        traits["Prideful_Egotistical"] -= 30
        traits["Disciplined_Aggressive"] -= 25
    
    # Victory Celebration influences multiple traits
    celebration = answers.get('victory_celebration')
    if celebration == "humble":
        traits["Prideful_Egotistical"] += 35
        traits["Respectful_Disrespectful"] += 30
    elif celebration == "showboat":
        traits["Prideful_Egotistical"] -= 35
        traits["Respectful_Disrespectful"] -= 20
    elif celebration == "acknowledge":
        traits["Respectful_Disrespectful"] += 40
        traits["Prideful_Egotistical"] += 20
    elif celebration == "leave_quickly":
        traits["Prideful_Egotistical"] += 10
        traits["Disciplined_Aggressive"] += 15
    
    # Partnership Question influences Loyal/Treacherous
    partnership = answers.get('partnership')
    if partnership == "trust_completely":
        traits["Loyal_Treacherous"] += 50
    elif partnership == "watch_back":
        traits["Loyal_Treacherous"] += 30
    elif partnership == "cautious":
        traits["Loyal_Treacherous"] += 10
    elif partnership == "strike_first":
        traits["Loyal_Treacherous"] -= 50
    
    # Match Tempo influences Disciplined/Aggressive
    tempo = answers.get('match_tempo')
    if tempo == "methodical":
        traits["Disciplined_Aggressive"] += 30
    elif tempo == "explosive":
        traits["Disciplined_Aggressive"] -= 20
    elif tempo == "unpredictable":
        traits["Disciplined_Aggressive"] -= 15
    
    # Add some randomness to make each wrestler unique (-10 to +10 per trait)
    for trait in traits:
        random_factor = random.randint(-10, 10)
        traits[trait] += random_factor
    
    # Ensure all values are within -100 to +100
    for trait in traits:
        traits[trait] = max(-100, min(100, traits[trait]))
    
    return traits
