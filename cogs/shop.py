import discord
from discord import app_commands
from discord.ext import commands
from database import Database
from utils.constants import ATTRIBUTES, SHOP_PRICES, MAX_ATTRIBUTE_VALUE
from utils.helpers import create_shop_embed
from typing import Optional, List

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

class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
    
    @app_commands.command(name="shop", description="Browse the wrestler upgrade shop")
    @app_commands.autocomplete(wrestler_name=own_wrestler_autocomplete)
    async def shop(self, interaction: discord.Interaction, wrestler_name: Optional[str] = None):
        """Display the shop"""
        
        # Get settings first
        settings = await self.db.get_server_settings(interaction.guild_id)
        
        # Check if shop is restricted to a specific channel
        if settings.get('shop_channel_id'):
            if interaction.channel_id != settings['shop_channel_id']:
                shop_channel = interaction.guild.get_channel(settings['shop_channel_id'])
                await interaction.response.send_message(
                    f"❌ The shop can only be used in {shop_channel.mention}!",
                    ephemeral=True
                )
                return
        
        # Get user's wrestlers
        wrestlers = await self.db.get_wrestlers_by_user(interaction.guild_id, interaction.user.id)
        
        if not wrestlers:
            await interaction.response.send_message(
                "❌ You don't have any wrestlers! Create one with `/create_wrestler`.",
                ephemeral=True
            )
            return
        
        # Select wrestler
        if wrestler_name:
            wrestler = next((w for w in wrestlers if w['name'].lower() == wrestler_name.lower()), None)
            if not wrestler:
                await interaction.response.send_message(
                    f"❌ You don't have a wrestler named '{wrestler_name}'!",
                    ephemeral=True
                )
                return
        else:
            wrestler = wrestlers[0]  # Default to first wrestler
        
        embed = create_shop_embed(
            settings['currency_name'],
            settings['currency_symbol'],
            wrestler['currency']
        )
        embed.set_author(
            name=f"Shopping for: {wrestler['name']}",
            icon_url=interaction.user.display_avatar.url
        )
        
        # Create purchase view
        view = ShopView(self.db, wrestler, settings, interaction.user)
        
        await self.db.update_last_active(interaction.user.id, interaction.guild_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class ShopView(discord.ui.View):
    def __init__(self, db, wrestler, settings, user):
        super().__init__(timeout=300)
        self.db = db
        self.wrestler = wrestler
        self.settings = settings
        self.user = user
    
    @discord.ui.button(label="+1 Attribute ($150)", style=discord.ButtonStyle.primary, emoji="📈")
    async def buy_attribute_1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_attribute_selector(interaction, 1, SHOP_PRICES['attribute_1'])
    
    @discord.ui.button(label="+5 Attribute ($700)", style=discord.ButtonStyle.primary, emoji="📊")
    async def buy_attribute_5(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_attribute_selector(interaction, 5, SHOP_PRICES['attribute_5'])
    
    @discord.ui.button(label="+10 Attribute ($1,300)", style=discord.ButtonStyle.primary, emoji="⚡")
    async def buy_attribute_10(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.show_attribute_selector(interaction, 10, SHOP_PRICES['attribute_10'])
    
    async def show_attribute_selector(self, interaction: discord.Interaction, amount: int, cost: int):
        """Show attribute selection menu"""
        
        # Check if user can afford it
        if self.wrestler['currency'] < cost:
            await interaction.response.send_message(
                f"❌ Not enough {self.settings['currency_name']}! You need {self.settings['currency_symbol']}{cost} but only have {self.settings['currency_symbol']}{self.wrestler['currency']}.",
                ephemeral=True
            )
            return
        
        # Create attribute selector
        view = AttributeSelectorView(
            self.db,
            self.wrestler,
            self.settings,
            amount,
            cost,
            self.user
        )
        
        embed = discord.Embed(
            title=f"Select Attribute to Upgrade (+{amount})",
            description=f"**Cost:** {self.settings['currency_symbol']}{cost}",
            color=discord.Color.green()
        )
        embed.add_field(
            name="Current Balance",
            value=f"{self.settings['currency_symbol']}{self.wrestler['currency']}",
            inline=False
        )
        embed.set_footer(text="Select an attribute below to upgrade")
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class AttributeSelectorView(discord.ui.View):
    def __init__(self, db, wrestler, settings, amount, cost, user):
        super().__init__(timeout=180)
        self.db = db
        self.wrestler = wrestler
        self.settings = settings
        self.amount = amount
        self.cost = cost
        self.user = user
        
        # Create dropdown with all attributes
        self.add_item(AttributeDropdown(db, wrestler, settings, amount, cost, user))

class AttributeDropdown(discord.ui.Select):
    def __init__(self, db, wrestler, settings, amount, cost, user):
        self.db = db
        self.wrestler = wrestler
        self.settings = settings
        self.amount = amount
        self.cost = cost
        self.user = user
        
        # Get level cap
        wrestler_level = wrestler.get('level', 1)
        level_caps = {1: 70, 2: 75, 3: 80, 4: 85, 5: 90, 6: 92, 7: 95, 8: 97, 9: 99, 10: 100}
        attribute_cap = level_caps.get(wrestler_level, 70)
        
        # Group attributes for easier selection
        options = []
        
        # Add all attributes
        for attr in ATTRIBUTES:
            current_value = wrestler['attributes'].get(attr, 50)
            
            # Calculate new value respecting both caps
            new_value = min(attribute_cap, MAX_ATTRIBUTE_VALUE, current_value + amount)
            actual_increase = new_value - current_value
            
            # Check if at level cap
            if current_value >= attribute_cap:
                label = f"{attr} (Level {wrestler_level} Cap)"
                options.append(discord.SelectOption(
                    label=label[:100],
                    value=attr,
                    description=f"At cap ({current_value}/{attribute_cap}) - Level up!",
                    emoji="🔒"
                ))
            # Check if at max
            elif current_value >= MAX_ATTRIBUTE_VALUE:
                label = f"{attr} (MAX)"
                options.append(discord.SelectOption(
                    label=label,
                    value=attr,
                    description=f"Already at maximum (100)",
                    emoji="🔒"
                ))
            else:
                label = f"{attr} ({current_value} → {new_value})"
                desc = f"Increase by +{actual_increase}"
                if new_value >= attribute_cap:
                    desc += f" (reaches Lvl {wrestler_level} cap)"
                
                options.append(discord.SelectOption(
                    label=label[:100],
                    value=attr,
                    description=desc[:100],
                    emoji="📈"
                ))
        
        super().__init__(
            placeholder="Choose an attribute to upgrade...",
            min_values=1,
            max_values=1,
            options=options[:25]  # Discord limit
        )
    
    async def callback(self, interaction: discord.Interaction):
        selected_attr = self.values[0]
        
        # Get wrestler's current level and cap
        wrestler_level = self.wrestler.get('level', 1)
        level_caps = {1: 70, 2: 75, 3: 80, 4: 85, 5: 90, 6: 92, 7: 95, 8: 97, 9: 99, 10: 100}
        attribute_cap = level_caps.get(wrestler_level, 70)
        
        # Check current value
        current = self.wrestler['attributes'].get(selected_attr, 50)
        
        # Check if already at level cap
        if current >= attribute_cap:
            await interaction.response.send_message(
                f"❌ **{selected_attr}** is at your level cap!\n\n"
                f"**Current:** {current}\n"
                f"**Level {wrestler_level} Cap:** {attribute_cap}\n\n"
                f"Level up to increase your attribute cap!",
                ephemeral=True
            )
            return
        
        # Check if already at max
        if current >= MAX_ATTRIBUTE_VALUE:
            await interaction.response.send_message(
                f"❌ **{selected_attr}** is already at maximum (100)!",
                ephemeral=True
            )
            return
        
        # Calculate new value (respect BOTH level cap AND max cap)
        new_value = min(attribute_cap, MAX_ATTRIBUTE_VALUE, current + self.amount)
        actual_increase = new_value - current
        
        # If no increase possible due to cap
        if actual_increase <= 0:
            await interaction.response.send_message(
                f"❌ Cannot upgrade **{selected_attr}**!\n\n"
                f"**Current:** {current}\n"
                f"**Level {wrestler_level} Cap:** {attribute_cap}\n\n"
                f"You need to level up first!",
                ephemeral=True
            )
            return
        
        # Deduct currency
        await self.db.update_wrestler_currency(self.wrestler['id'], -self.cost)
        
        # Update attribute
        final_value = await self.db.update_wrestler_attribute(
            self.wrestler['id'],
            selected_attr,
            actual_increase
        )
        
        # Add to upgrade queue WITH old and new values
        await self.db.add_upgrade_to_queue(
            interaction.guild_id,
            self.wrestler['id'],
            self.wrestler['name'],
            selected_attr,
            actual_increase,
            current,  # old_value
            new_value  # new_value
        )
        
        # Calculate new balance
        new_balance = self.wrestler['currency'] - self.cost
        
        # Success message
        embed = discord.Embed(
            title="✅ Upgrade Purchased!",
            description=f"**{selected_attr}** upgraded for **{self.wrestler['name']}**",
            color=discord.Color.green()
        )
        embed.add_field(
            name="Attribute Change",
            value=f"{current} → **{new_value}** (+{actual_increase})",
            inline=True
        )
        embed.add_field(
            name="New Balance",
            value=f"{self.settings['currency_symbol']}{new_balance}",
            inline=True
        )
        embed.set_footer(text="This upgrade has been added to the admin queue for in-game application")
        
        await interaction.response.edit_message(embed=embed, view=None)
        
        # Update wrestler data for future purchases
        self.wrestler['currency'] = new_balance
        self.wrestler['attributes'][selected_attr] = new_value

async def setup(bot):
    await bot.add_cog(Shop(bot))
