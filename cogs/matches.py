import discord
from discord import app_commands
from discord.ext import commands
from database import Database
from datetime import datetime
from typing import Optional, List
import json


# Autocomplete for wrestlers
async def wrestler_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    db = Database()
    wrestlers = await db.get_all_wrestlers(interaction.guild_id)
    if not wrestlers:
        return [app_commands.Choice(name="(No wrestlers found)", value="none")]
    filtered = [w for w in wrestlers if current.lower() in w['name'].lower()][:25]
    return [app_commands.Choice(name=w['name'], value=w['name']) for w in filtered]


class Matches(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
    
    @app_commands.command(name="leaderboard", description="View server leaderboards")
    @app_commands.choices(
        stat=[
            app_commands.Choice(name="🏆 Most Wins", value="wins"),
            app_commands.Choice(name="📊 Best Win Rate", value="winrate"),
            app_commands.Choice(name="💰 Most Currency", value="currency")
        ],
        streak=[
            app_commands.Choice(name="🔥 Longest Streak (Any)", value="overall"),
            app_commands.Choice(name="🔥 Hottest (Win Streaks)", value="hot"),
            app_commands.Choice(name="❄️ Coldest (Loss Streaks)", value="cold")
        ]
    )
    async def leaderboard(
        self,
        interaction: discord.Interaction,
        stat: Optional[app_commands.Choice[str]] = None,
        streak: Optional[app_commands.Choice[str]] = None
    ):
        """View leaderboards"""
        
        if not stat and not streak:
            await interaction.response.send_message("❌ Please select either a stat or streak type!", ephemeral=True)
            return
        
        all_wrestlers = await self.db.get_all_wrestlers(interaction.guild_id)
        
        if not all_wrestlers:
            await interaction.response.send_message("❌ No wrestlers found in this server!", ephemeral=True)
            return
        
        embed = discord.Embed(title="🏆 Leaderboard", color=discord.Color.gold())
        
        if stat:
            stat_value = stat.value
            
            if stat_value == "wins":
                wrestlers_with_matches = [w for w in all_wrestlers if w['wins'] + w['losses'] > 0]
                
                if not wrestlers_with_matches:
                    await interaction.response.send_message("❌ No matches recorded yet!", ephemeral=True)
                    return
                
                sorted_wrestlers = sorted(wrestlers_with_matches, key=lambda x: x['wins'], reverse=True)[:10]
                embed.description = "**Most Wins**"
                
                for i, wrestler in enumerate(sorted_wrestlers, 1):
                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"**{i}.**"
                    embed.add_field(
                        name=f"{medal} {wrestler['name']}",
                        value=f"**{wrestler['wins']}** wins | Record: {wrestler['wins']}-{wrestler['losses']}",
                        inline=False
                    )
            
            elif stat_value == "winrate":
                wrestlers_with_matches = [w for w in all_wrestlers if w['wins'] + w['losses'] > 0]
                
                if not wrestlers_with_matches:
                    await interaction.response.send_message("❌ No matches recorded yet!", ephemeral=True)
                    return
                
                for wrestler in wrestlers_with_matches:
                    total = wrestler['wins'] + wrestler['losses']
                    wrestler['winrate'] = (wrestler['wins'] / total * 100) if total > 0 else 0
                
                qualified = [w for w in wrestlers_with_matches if w['wins'] + w['losses'] >= 3]
                
                if not qualified:
                    await interaction.response.send_message("❌ No wrestlers with at least 3 matches!", ephemeral=True)
                    return
                
                sorted_wrestlers = sorted(qualified, key=lambda x: x['winrate'], reverse=True)[:10]
                embed.description = "**Best Win Rate** (min. 3 matches)"
                
                for i, wrestler in enumerate(sorted_wrestlers, 1):
                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"**{i}.**"
                    embed.add_field(
                        name=f"{medal} {wrestler['name']}",
                        value=f"**{wrestler['winrate']:.1f}%** | Record: {wrestler['wins']}-{wrestler['losses']}",
                        inline=False
                    )
            
            elif stat_value == "currency":
                sorted_wrestlers = sorted(all_wrestlers, key=lambda x: x['currency'], reverse=True)[:10]
                
                settings = await self.db.get_server_settings(interaction.guild_id)
                symbol = settings['currency_symbol']
                name = settings['currency_name']
                
                embed.description = f"**Most {name}**"
                
                for i, wrestler in enumerate(sorted_wrestlers, 1):
                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"**{i}.**"
                    embed.add_field(
                        name=f"{medal} {wrestler['name']}",
                        value=f"**{symbol}{wrestler['currency']:,}** {name}",
                        inline=False
                    )
        
        elif streak:
            streak_type = streak.value
            wrestlers_with_streaks = []
            
            for wrestler in all_wrestlers:
                matches = await self.db.get_wrestler_matches(wrestler['id'], limit=50)
                
                if not matches:
                    continue
                
                current_streak = 0
                current_type = None
                
                for match in matches:
                    is_win = wrestler['id'] in match['winner_ids']
                    
                    if current_streak == 0:
                        current_streak = 1
                        current_type = "W" if is_win else "L"
                    elif (is_win and current_type == "W") or (not is_win and current_type == "L"):
                        current_streak += 1
                    else:
                        break
                
                wrestler['current_streak'] = current_streak
                wrestler['streak_type'] = current_type
                
                if current_streak > 0:
                    wrestlers_with_streaks.append(wrestler)
            
            if not wrestlers_with_streaks:
                await interaction.response.send_message("❌ No active streaks!", ephemeral=True)
                return
            
            if streak_type == "overall":
                sorted_wrestlers = sorted(wrestlers_with_streaks, key=lambda x: x['current_streak'], reverse=True)[:10]
                embed.description = "**Longest Current Streaks**"
            elif streak_type == "hot":
                hot_streaks = [w for w in wrestlers_with_streaks if w['streak_type'] == "W"]
                if not hot_streaks:
                    await interaction.response.send_message("❌ No win streaks!", ephemeral=True)
                    return
                sorted_wrestlers = sorted(hot_streaks, key=lambda x: x['current_streak'], reverse=True)[:10]
                embed.description = "🔥 **Hottest Win Streaks**"
            else:  # cold
                cold_streaks = [w for w in wrestlers_with_streaks if w['streak_type'] == "L"]
                if not cold_streaks:
                    await interaction.response.send_message("❌ No loss streaks!", ephemeral=True)
                    return
                sorted_wrestlers = sorted(cold_streaks, key=lambda x: x['current_streak'], reverse=True)[:10]
                embed.description = "❄️ **Coldest Loss Streaks**"
            
            for i, wrestler in enumerate(sorted_wrestlers, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"**{i}.**"
                streak_icon = "🔥" if wrestler['streak_type'] == "W" else "❄️"
                streak_text = "Win" if wrestler['streak_type'] == "W" else "Loss"
                
                embed.add_field(
                    name=f"{medal} {wrestler['name']}",
                    value=f"{streak_icon} **{wrestler['current_streak']}** {streak_text} Streak | Record: {wrestler['wins']}-{wrestler['losses']}",
                    inline=False
                )
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="match_history", description="View a wrestler's match history")
    @app_commands.autocomplete(wrestler_name=wrestler_autocomplete)
    async def match_history(self, interaction: discord.Interaction, wrestler_name: str, limit: Optional[int] = 10):
        """View match history for a wrestler"""
        
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
        

async def setup(bot):
    await bot.add_cog(Matches(bot))
