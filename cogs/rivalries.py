import discord
from discord import app_commands
from discord.ext import commands
from database import Database
from datetime import datetime
from typing import Optional, List


# Autocomplete
async def wrestler_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    db = Database()
    wrestlers = await db.get_all_wrestlers(interaction.guild_id)
    if not wrestlers:
        return [app_commands.Choice(name="(No wrestlers found)", value="none")]
    filtered = [w for w in wrestlers if current.lower() in w['name'].lower()][:25]
    return [app_commands.Choice(name=w['name'], value=w['name']) for w in filtered]


async def is_admin_or_booker(interaction: discord.Interaction, db: Database) -> bool:
    """Check if user is admin or booker"""
    if interaction.user.guild_permissions.administrator:
        return True
    
    settings = await db.get_server_settings(interaction.guild_id)
    booker_role_id = settings.get('booker_role_id')
    if booker_role_id:
        booker_role = interaction.guild.get_role(booker_role_id)
        if booker_role and booker_role in interaction.user.roles:
            return True
    
    return False


class Rivalries(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
    
    rivalry_group = app_commands.Group(
        name="rivalry",
        description="Manage wrestler rivalries"
    )
    
    # ==================== CREATE RIVALRY ====================
    
    @rivalry_group.command(name="create", description="Create a rivalry between two wrestlers")
    @app_commands.autocomplete(wrestler1=wrestler_autocomplete, wrestler2=wrestler_autocomplete)
    async def create(
        self,
        interaction: discord.Interaction,
        wrestler1: str,
        wrestler2: str
    ):
        """Create a new rivalry"""
        
        if not await is_admin_or_booker(interaction, self.db):
            await interaction.response.send_message("❌ Admin/Booker only!", ephemeral=True)
            return
        
        # Get wrestlers
        all_wrestlers = await self.db.get_all_wrestlers(interaction.guild_id)
        w1 = next((w for w in all_wrestlers if w['name'].lower() == wrestler1.lower()), None)
        w2 = next((w for w in all_wrestlers if w['name'].lower() == wrestler2.lower()), None)
        
        if not w1:
            await interaction.response.send_message(f"❌ Wrestler '{wrestler1}' not found!", ephemeral=True)
            return
        if not w2:
            await interaction.response.send_message(f"❌ Wrestler '{wrestler2}' not found!", ephemeral=True)
            return
        
        if w1['id'] == w2['id']:
            await interaction.response.send_message("❌ A wrestler can't have a rivalry with themselves!", ephemeral=True)
            return
        
        # Check if either wrestler already has an active rivalry
        rivalry1 = await self.db.get_active_rivalry_for_wrestler(w1['id'])
        if rivalry1:
            # Get opponent name
            opponent_id = rivalry1['wrestler2_id'] if rivalry1['wrestler1_id'] == w1['id'] else rivalry1['wrestler1_id']
            opponent = next((w for w in all_wrestlers if w['id'] == opponent_id), None)
            await interaction.response.send_message(
                f"❌ **{w1['name']}** already has a rivalry with **{opponent['name'] if opponent else 'Unknown'}**!\n"
                f"End it first with `/rivalry end`",
                ephemeral=True
            )
            return
        
        rivalry2 = await self.db.get_active_rivalry_for_wrestler(w2['id'])
        if rivalry2:
            opponent_id = rivalry2['wrestler2_id'] if rivalry2['wrestler1_id'] == w2['id'] else rivalry2['wrestler1_id']
            opponent = next((w for w in all_wrestlers if w['id'] == opponent_id), None)
            await interaction.response.send_message(
                f"❌ **{w2['name']}** already has a rivalry with **{opponent['name'] if opponent else 'Unknown'}**!\n"
                f"End it first with `/rivalry end`",
                ephemeral=True
            )
            return
        
        # Create rivalry
        await self.db.create_rivalry(interaction.guild_id, w1['id'], w2['id'])
        
        embed = discord.Embed(
            title="⚔️ Rivalry Created!",
            description=f"**{w1['name']}** vs **{w2['name']}**",
            color=discord.Color.red()
        )
        embed.add_field(
            name="Bonus",
            value="Both wrestlers get **+10% XP** when they face each other!",
            inline=False
        )
        embed.set_footer(text="The feud begins...")
        
        await interaction.response.send_message(embed=embed)
    
    # ==================== END RIVALRY ====================
    
    @rivalry_group.command(name="end", description="End a wrestler's rivalry")
    @app_commands.autocomplete(wrestler=wrestler_autocomplete)
    async def end(
        self,
        interaction: discord.Interaction,
        wrestler: str
    ):
        """End a rivalry"""
        
        if not await is_admin_or_booker(interaction, self.db):
            await interaction.response.send_message("❌ Admin/Booker only!", ephemeral=True)
            return
        
        # Get wrestler
        all_wrestlers = await self.db.get_all_wrestlers(interaction.guild_id)
        w = next((wr for wr in all_wrestlers if wr['name'].lower() == wrestler.lower()), None)
        
        if not w:
            await interaction.response.send_message(f"❌ Wrestler '{wrestler}' not found!", ephemeral=True)
            return
        
        # Get active rivalry
        rivalry = await self.db.get_active_rivalry_for_wrestler(w['id'])
        if not rivalry:
            await interaction.response.send_message(
                f"❌ **{w['name']}** doesn't have an active rivalry!",
                ephemeral=True
            )
            return
        
        # Get opponent name
        opponent_id = rivalry['wrestler2_id'] if rivalry['wrestler1_id'] == w['id'] else rivalry['wrestler1_id']
        opponent = next((wr for wr in all_wrestlers if wr['id'] == opponent_id), None)
        
        # End rivalry
        await self.db.end_rivalry(rivalry['id'])
        
        # Calculate record
        if rivalry['wrestler1_id'] == w['id']:
            my_wins = rivalry['wrestler1_wins']
            their_wins = rivalry['wrestler2_wins']
        else:
            my_wins = rivalry['wrestler2_wins']
            their_wins = rivalry['wrestler1_wins']
        
        embed = discord.Embed(
            title="🏁 Rivalry Ended",
            description=f"**{w['name']}** vs **{opponent['name'] if opponent else 'Unknown'}**",
            color=discord.Color.dark_gray()
        )
        embed.add_field(name="Total Matches", value=f"{rivalry['matches_fought']}", inline=True)
        embed.add_field(name="Final Record", value=f"{my_wins}-{their_wins}", inline=True)
        embed.set_footer(text="The feud is over... for now.")
        
        await interaction.response.send_message(embed=embed)
    
    # ==================== LIST RIVALRIES ====================
    
    @rivalry_group.command(name="list", description="View all active rivalries")
    async def list_rivalries(self, interaction: discord.Interaction):
        """List all active rivalries in the server"""
        
        rivalries = await self.db.get_all_active_rivalries(interaction.guild_id)
        
        if not rivalries:
            await interaction.response.send_message(
                "📭 No active rivalries!\nCreate one with `/rivalry create`",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="⚔️ Active Rivalries",
            description=f"Total: **{len(rivalries)}**",
            color=discord.Color.red()
        )
        
        for rivalry in rivalries:
            w1_wins = rivalry['wrestler1_wins']
            w2_wins = rivalry['wrestler2_wins']
            total_matches = rivalry['matches_fought']
            
            # Determine leader
            if w1_wins > w2_wins:
                leader_text = f"{rivalry['wrestler1_name']} leads"
            elif w2_wins > w1_wins:
                leader_text = f"{rivalry['wrestler2_name']} leads"
            else:
                leader_text = "Tied"
            
            value = (
                f"**Matches:** {total_matches}\n"
                f"**Record:** {w1_wins}-{w2_wins} ({leader_text})\n"
            )
            
            if rivalry.get('last_match_date'):
                last_match = datetime.fromisoformat(rivalry['last_match_date'])
                days_ago = (datetime.utcnow() - last_match).days
                value += f"*Last match: {days_ago} day{'s' if days_ago != 1 else ''} ago*"
            else:
                value += f"*No matches yet*"
            
            embed.add_field(
                name=f"{rivalry['wrestler1_name']} vs {rivalry['wrestler2_name']}",
                value=value,
                inline=False
            )
        
        embed.set_footer(text="Rivalry matches grant +10% XP bonus!")
        
        await interaction.response.send_message(embed=embed)
    
    # ==================== VIEW RIVALRY ====================
    
    @rivalry_group.command(name="view", description="View detailed rivalry stats for a wrestler")
    @app_commands.autocomplete(wrestler=wrestler_autocomplete)
    async def view(
        self,
        interaction: discord.Interaction,
        wrestler: str
    ):
        """View rivalry details for a specific wrestler"""
        
        # Get wrestler
        all_wrestlers = await self.db.get_all_wrestlers(interaction.guild_id)
        w = next((wr for wr in all_wrestlers if wr['name'].lower() == wrestler.lower()), None)
        
        if not w:
            await interaction.response.send_message(f"❌ Wrestler '{wrestler}' not found!", ephemeral=True)
            return
        
        # Get active rivalry
        rivalry = await self.db.get_active_rivalry_for_wrestler(w['id'])
        if not rivalry:
            await interaction.response.send_message(
                f"📭 **{w['name']}** doesn't have an active rivalry!",
                ephemeral=True
            )
            return
        
        # Get opponent
        opponent_id = rivalry['wrestler2_id'] if rivalry['wrestler1_id'] == w['id'] else rivalry['wrestler1_id']
        opponent = next((wr for wr in all_wrestlers if wr['id'] == opponent_id), None)
        
        # Calculate stats
        if rivalry['wrestler1_id'] == w['id']:
            my_wins = rivalry['wrestler1_wins']
            their_wins = rivalry['wrestler2_wins']
        else:
            my_wins = rivalry['wrestler2_wins']
            their_wins = rivalry['wrestler1_wins']
        
        total_matches = rivalry['matches_fought']
        win_percentage = (my_wins / total_matches * 100) if total_matches > 0 else 0
        
        embed = discord.Embed(
            title=f"⚔️ {w['name']} vs {opponent['name'] if opponent else 'Unknown'}",
            color=discord.Color.red()
        )
        
        embed.add_field(name="Total Matches", value=f"**{total_matches}**", inline=True)
        embed.add_field(name="Record", value=f"**{my_wins}-{their_wins}**", inline=True)
        embed.add_field(name="Win %", value=f"**{win_percentage:.1f}%**", inline=True)
        
        # Created date
        created = datetime.fromisoformat(rivalry['created_date'])
        days_active = (datetime.utcnow() - created).days
        embed.add_field(
            name="Rivalry Started",
            value=f"{created.strftime('%Y-%m-%d')}\n*{days_active} day{'s' if days_active != 1 else ''} ago*",
            inline=True
        )
        
        # Last match
        if rivalry.get('last_match_date'):
            last_match = datetime.fromisoformat(rivalry['last_match_date'])
            days_ago = (datetime.utcnow() - last_match).days
            embed.add_field(
                name="Last Match",
                value=f"{last_match.strftime('%Y-%m-%d')}\n*{days_ago} day{'s' if days_ago != 1 else ''} ago*",
                inline=True
            )
        else:
            embed.add_field(
                name="Last Match",
                value="*No matches yet*",
                inline=True
            )
        
        embed.add_field(
            name="Bonus",
            value="**+10% XP** when facing each other!",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Rivalries(bot))
