import aiosqlite
import json
from datetime import datetime
from typing import Optional, Dict, List, Any
from utils.constants import ATTRIBUTES, DEFAULT_ATTRIBUTE_VALUE

class Database:
    def __init__(self, db_path: str = "wrestling_bot.db"):
        self.db_path = db_path
    
    async def initialize(self):
        """Initialize database tables"""
        async with aiosqlite.connect(self.db_path) as db:
            # Server settings table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS server_settings (
                    guild_id INTEGER PRIMARY KEY,
                    currency_name TEXT DEFAULT 'Dollars',
                    currency_symbol TEXT DEFAULT '$',
                    currency_min INTEGER DEFAULT 5,
                    currency_max INTEGER DEFAULT 15,
                    currency_cooldown INTEGER DEFAULT 60,
                    announcement_channel_id INTEGER,
                    shop_channel_id INTEGER,
                    currency_channels TEXT,
                    max_wrestlers_per_user INTEGER DEFAULT 3,
                    booker_role_id INTEGER,
                    setup_completed INTEGER DEFAULT 0
                )
            """)
            
            # Wrestlers table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS wrestlers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    archetype TEXT NOT NULL,
                    weight_class TEXT NOT NULL,
                    persona TEXT NOT NULL,
                    finisher TEXT NOT NULL,
                    signature TEXT NOT NULL,
                    attributes TEXT NOT NULL,
                    personality TEXT,
                    gender TEXT,
                    alignment TEXT,
                    body_type TEXT,
                    height_feet TEXT,
                    height_cm INTEGER,
                    appearance TEXT,
                    outfit TEXT,
                    currency INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 1,
                    xp INTEGER DEFAULT 0,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    is_retired INTEGER DEFAULT 0,
                    UNIQUE(guild_id, user_id, name)
                )
            """)
            
            # Currency tracking for cooldowns
            await db.execute("""
                CREATE TABLE IF NOT EXISTS currency_cooldowns (
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    last_earned TEXT NOT NULL,
                    PRIMARY KEY (guild_id, user_id)
                )
            """)
            
            # Upgrade queue for admins
            await db.execute("""
                CREATE TABLE IF NOT EXISTS upgrade_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    wrestler_id INTEGER NOT NULL,
                    wrestler_name TEXT NOT NULL,
                    attribute TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    old_value INTEGER,
                    new_value INTEGER,
                    timestamp TEXT NOT NULL,
                    processed INTEGER DEFAULT 0
                )
            """)
            
            # User wrestler limits (overrides)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_wrestler_limits (
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    max_wrestlers INTEGER NOT NULL,
                    PRIMARY KEY (guild_id, user_id)
                )
            """)
            
            # ========== PHASE 2 TABLES ==========
            
            # Matches table - stores all match results
            await db.execute("""
                CREATE TABLE IF NOT EXISTS matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    event_id INTEGER,
                    winner_ids TEXT NOT NULL,
                    winner_names TEXT NOT NULL,
                    loser_ids TEXT NOT NULL,
                    loser_names TEXT NOT NULL,
                    match_type TEXT NOT NULL,
                    finish_type TEXT NOT NULL,
                    rating REAL,
                    championship_id INTEGER,
                    match_date TEXT NOT NULL,
                    notes TEXT,
                    FOREIGN KEY (championship_id) REFERENCES championships(id),
                    FOREIGN KEY (event_id) REFERENCES events(id)
                )
            """)
            
            # Championships table - defines all titles
            await db.execute("""
                CREATE TABLE IF NOT EXISTS championships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    gender_requirement TEXT,
                    weight_class_requirement TEXT,
                    is_tag_team INTEGER DEFAULT 0,
                    current_champion_id INTEGER,
                    created_at TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    UNIQUE(guild_id, name)
                )
            """)
            
            # Title reigns table - tracks championship history
            await db.execute("""
                CREATE TABLE IF NOT EXISTS title_reigns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    championship_id INTEGER NOT NULL,
                    wrestler_id INTEGER NOT NULL,
                    wrestler_name TEXT NOT NULL,
                    reign_number INTEGER NOT NULL,
                    won_date TEXT NOT NULL,
                    lost_date TEXT,
                    days_held INTEGER DEFAULT 0,
                    successful_defenses INTEGER DEFAULT 0,
                    is_current INTEGER DEFAULT 1,
                    FOREIGN KEY (championship_id) REFERENCES championships(id),
                    FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id)
                )
            """)
            
            # Title divisions - assigns wrestlers to title divisions
            await db.execute("""
                CREATE TABLE IF NOT EXISTS title_divisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    championship_id INTEGER NOT NULL,
                    wrestler_id INTEGER NOT NULL,
                    wrestler_name TEXT NOT NULL,
                    assigned_date TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    FOREIGN KEY (championship_id) REFERENCES championships(id),
                    FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id),
                    UNIQUE(championship_id, wrestler_id)
                )
            """)
            
            # Division rankings - point-based contender system
            await db.execute("""
                CREATE TABLE IF NOT EXISTS division_rankings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    championship_id INTEGER NOT NULL,
                    wrestler_id INTEGER NOT NULL,
                    wrestler_name TEXT NOT NULL,
                    points INTEGER DEFAULT 0,
                    wins INTEGER DEFAULT 0,
                    losses INTEGER DEFAULT 0,
                    last_updated TEXT NOT NULL,
                    FOREIGN KEY (championship_id) REFERENCES championships(id),
                    FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id),
                    UNIQUE(championship_id, wrestler_id)
                )
            """)
            
            # Events table - stores shows/PPVs
            await db.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    event_date TEXT NOT NULL,
                    description TEXT,
                    announcement_message_id INTEGER,
                    is_completed INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    UNIQUE(guild_id, name, event_date)
                )
            """)
            
            # Event matches - planned match card
            await db.execute("""
                CREATE TABLE IF NOT EXISTS event_matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER NOT NULL,
                    match_order INTEGER,
                    wrestler1_id INTEGER,
                    wrestler1_name TEXT,
                    wrestler2_id INTEGER,
                    wrestler2_name TEXT,
                    match_type TEXT NOT NULL,
                    championship_id INTEGER,
                    stipulation TEXT,
                    is_open_spot INTEGER DEFAULT 0,
                    open_spots_count INTEGER DEFAULT 0,
                    open_spot_description TEXT,
                    match_result_id INTEGER,
                    FOREIGN KEY (event_id) REFERENCES events(id),
                    FOREIGN KEY (wrestler1_id) REFERENCES wrestlers(id),
                    FOREIGN KEY (wrestler2_id) REFERENCES wrestlers(id),
                    FOREIGN KEY (championship_id) REFERENCES championships(id),
                    FOREIGN KEY (match_result_id) REFERENCES matches(id)
                )
            """)
            
            # Event applications - users apply for open spots
            await db.execute("""
                CREATE TABLE IF NOT EXISTS event_applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_match_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    wrestler_id INTEGER NOT NULL,
                    wrestler_name TEXT NOT NULL,
                    application_date TEXT NOT NULL,
                    is_accepted INTEGER DEFAULT 0,
                    FOREIGN KEY (event_match_id) REFERENCES event_matches(id),
                    FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id),
                    UNIQUE(event_match_id, wrestler_id)
                )
            """)
            
            # ==================== PHASE 3 TABLES ====================
            
            # Event Templates - reusable show/event templates
            await db.execute("""
                CREATE TABLE IF NOT EXISTS event_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    default_time TEXT,
                    announcement_channel_id INTEGER,
                    banner_url TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE(guild_id, name)
                )
            """)
            
            # Event Instances - specific occurrences with auto-numbering  
            await db.execute("""
                CREATE TABLE IF NOT EXISTS event_instances (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    template_id INTEGER,
                    base_name TEXT NOT NULL,
                    full_name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    instance_number INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    time TEXT,
                    description TEXT,
                    banner_url TEXT,
                    status TEXT DEFAULT 'planned',
                    announcement_message_id INTEGER,
                    announcement_channel_id INTEGER,
                    created_at TEXT NOT NULL,
                    completed_at TEXT,
                    FOREIGN KEY (template_id) REFERENCES event_templates(id)
                )
            """)
            
            # Event Instance Matches - match card
            await db.execute("""
                CREATE TABLE IF NOT EXISTS event_instance_matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_instance_id INTEGER NOT NULL,
                    match_order INTEGER NOT NULL,
                    match_type TEXT NOT NULL,
                    championship_id INTEGER,
                    participants TEXT NOT NULL,
                    is_open_spot INTEGER DEFAULT 0,
                    spots_available INTEGER,
                    spots_filled INTEGER DEFAULT 0,
                    open_spot_description TEXT,
                    is_main_event INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'pending',
                    match_id INTEGER,
                    FOREIGN KEY (event_instance_id) REFERENCES event_instances(id),
                    FOREIGN KEY (championship_id) REFERENCES championships(id),
                    FOREIGN KEY (match_id) REFERENCES matches(id)
                )
            """)
            
            # Event Instance Applications - user applications
            await db.execute("""
                CREATE TABLE IF NOT EXISTS event_instance_applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_instance_match_id INTEGER NOT NULL,
                    wrestler_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    applied_at TEXT NOT NULL,
                    status TEXT DEFAULT 'accepted',
                    FOREIGN KEY (event_instance_match_id) REFERENCES event_instance_matches(id),
                    FOREIGN KEY (wrestler_id) REFERENCES wrestlers(id),
                    UNIQUE(event_instance_match_id, wrestler_id)
                )
            """)
            
            await db.commit()
    
    # ==================== SERVER SETTINGS ====================
    
    async def get_server_settings(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """Get server settings"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM server_settings WHERE guild_id = ?",
                (guild_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    settings = dict(row)
                    # Parse currency channels JSON
                    if settings['currency_channels']:
                        settings['currency_channels'] = json.loads(settings['currency_channels'])
                    return settings
                return None
    
    async def setup_server(
        self,
        guild_id: int,
        currency_name: str,
        currency_symbol: str,
        currency_min: int,
        currency_max: int,
        announcement_channel_id: int,
        currency_channels: List[int],
        max_wrestlers_per_user: int
    ):
        """Initial server setup"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO server_settings 
                (guild_id, currency_name, currency_symbol, currency_min, currency_max, 
                 announcement_channel_id, currency_channels, max_wrestlers_per_user, setup_completed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                guild_id, currency_name, currency_symbol, currency_min, currency_max,
                announcement_channel_id, json.dumps(currency_channels), max_wrestlers_per_user
            ))
            await db.commit()
    
    async def update_server_setting(self, guild_id: int, setting: str, value: Any):
        """Update a specific server setting"""
        async with aiosqlite.connect(self.db_path) as db:
            if setting == 'currency_channels' and isinstance(value, list):
                value = json.dumps(value)
            
            await db.execute(
                f"UPDATE server_settings SET {setting} = ? WHERE guild_id = ?",
                (value, guild_id)
            )
            await db.commit()
    
    # ==================== WRESTLERS ====================
    
    async def create_wrestler(
        self,
        guild_id: int,
        user_id: int,
        name: str,
        archetype: str,
        weight_class: str,
        persona: str,
        finisher: str,
        signature: str,
        attributes: Dict[str, int],
        personality: Dict[str, int] = None,
        gender: str = None,
        alignment: str = None,
        body_type: str = None,
        height_feet: str = None,
        height_cm: int = None,
        appearance: str = None,
        outfit: str = None
    ) -> int:
        """Create a new wrestler and return its ID"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO wrestlers 
                (guild_id, user_id, name, archetype, weight_class, persona, finisher, signature, 
                 attributes, personality, gender, alignment, body_type, height_feet, height_cm,
                 appearance, outfit, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                guild_id, user_id, name, archetype, weight_class, persona,
                finisher, signature, json.dumps(attributes), 
                json.dumps(personality) if personality else None,
                gender, alignment, body_type, height_feet, height_cm,
                appearance, outfit, datetime.utcnow().isoformat()
            ))
            await db.commit()
            return cursor.lastrowid
    
    async def get_wrestler_by_id(self, wrestler_id: int, guild_id: int) -> Optional[Dict[str, Any]]:
        """Get wrestler by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM wrestlers WHERE id = ? AND guild_id = ? AND is_retired = 0",
                (wrestler_id, guild_id)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    wrestler = dict(row)
                    wrestler['attributes'] = json.loads(wrestler['attributes'])
                    if wrestler.get('personality'):
                        wrestler['personality'] = json.loads(wrestler['personality'])
                    return wrestler
                return None
    
    async def get_wrestlers_by_user(self, guild_id: int, user_id: int) -> List[Dict[str, Any]]:
        """Get all active wrestlers owned by a user"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM wrestlers WHERE guild_id = ? AND user_id = ? AND is_retired = 0",
                (guild_id, user_id)
            ) as cursor:
                rows = await cursor.fetchall()
                wrestlers = []
                for row in rows:
                    wrestler = dict(row)
                    wrestler['attributes'] = json.loads(wrestler['attributes'])
                    if wrestler.get('personality'):
                        wrestler['personality'] = json.loads(wrestler['personality'])
                    wrestlers.append(wrestler)
                return wrestlers
    
    async def get_all_wrestlers(self, guild_id: int) -> List[Dict[str, Any]]:
        """Get all active wrestlers in a server"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM wrestlers WHERE guild_id = ? AND is_retired = 0",
                (guild_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                wrestlers = []
                for row in rows:
                    wrestler = dict(row)
                    wrestler['attributes'] = json.loads(wrestler['attributes'])
                    if wrestler.get('personality'):
                        wrestler['personality'] = json.loads(wrestler['personality'])
                    wrestlers.append(wrestler)
                return wrestlers
    
    async def update_wrestler_currency(self, wrestler_id: int, amount: int):
        """Update wrestler's currency"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE wrestlers SET currency = currency + ? WHERE id = ?",
                (amount, wrestler_id)
            )
            await db.commit()
    
    async def update_wrestler_attribute(self, wrestler_id: int, attribute: str, amount: int):
        """Update a wrestler's attribute"""
        async with aiosqlite.connect(self.db_path) as db:
            # Get current attributes
            async with db.execute(
                "SELECT attributes FROM wrestlers WHERE id = ?",
                (wrestler_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    attributes = json.loads(row[0])
                    # Update attribute (cap at 100)
                    current = attributes.get(attribute, DEFAULT_ATTRIBUTE_VALUE)
                    attributes[attribute] = min(100, current + amount)
                    
                    # Save back
                    await db.execute(
                        "UPDATE wrestlers SET attributes = ? WHERE id = ?",
                        (json.dumps(attributes), wrestler_id)
                    )
                    await db.commit()
                    return attributes[attribute]
        return None
    
    async def retire_wrestler(self, wrestler_id: int):
        """Mark wrestler as retired"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE wrestlers SET is_retired = 1 WHERE id = ?",
                (wrestler_id,)
            )
            await db.commit()
    
    async def check_move_exists(self, guild_id: int, move: str, move_type: str) -> bool:
        """Check if a unique move is already taken in the server"""
        async with aiosqlite.connect(self.db_path) as db:
            column = "finisher" if move_type == "finisher" else "signature"
            async with db.execute(
                f"SELECT COUNT(*) FROM wrestlers WHERE guild_id = ? AND {column} = ? AND is_retired = 0",
                (guild_id, move)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] > 0
    
    # ==================== CURRENCY COOLDOWNS ====================
    
    async def get_last_currency_earned(self, guild_id: int, user_id: int) -> Optional[str]:
        """Get when user last earned currency"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT last_earned FROM currency_cooldowns WHERE guild_id = ? AND user_id = ?",
                (guild_id, user_id)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None
    
    async def update_currency_cooldown(self, guild_id: int, user_id: int):
        """Update when user last earned currency"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO currency_cooldowns (guild_id, user_id, last_earned)
                VALUES (?, ?, ?)
            """, (guild_id, user_id, datetime.utcnow().isoformat()))
            await db.commit()
    
    # ==================== UPGRADE QUEUE ====================
    
    async def add_upgrade_to_queue(
        self,
        guild_id: int,
        wrestler_id: int,
        wrestler_name: str,
        attribute: str,
        amount: int,
        old_value: int,
        new_value: int
    ):
        """Add an upgrade to the admin queue"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO upgrade_queue 
                (guild_id, wrestler_id, wrestler_name, attribute, amount, old_value, new_value, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (guild_id, wrestler_id, wrestler_name, attribute, amount, old_value, new_value, datetime.utcnow().isoformat()))
            await db.commit()
    
    async def get_pending_upgrades(self, guild_id: int) -> List[Dict[str, Any]]:
        """Get all pending upgrades for a server"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM upgrade_queue WHERE guild_id = ? AND processed = 0 ORDER BY timestamp",
                (guild_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def get_wrestler_upgrade_history(self, wrestler_id: int) -> List[Dict[str, Any]]:
        """Get complete upgrade history for a specific wrestler (including processed)"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM upgrade_queue WHERE wrestler_id = ? ORDER BY timestamp DESC",
                (wrestler_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def clear_processed_upgrades(self, guild_id: int):
        """Mark all upgrades as processed"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE upgrade_queue SET processed = 1 WHERE guild_id = ?",
                (guild_id,)
            )
            await db.commit()
    
    # ==================== USER LIMITS ====================
    
    async def get_user_wrestler_limit(self, guild_id: int, user_id: int) -> Optional[int]:
        """Get custom wrestler limit for a user (None if using server default)"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT max_wrestlers FROM user_wrestler_limits WHERE guild_id = ? AND user_id = ?",
                (guild_id, user_id)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None
    
    
    # ==================== MATCHES (PHASE 2) ====================
    
    async def record_match(
        self,
        guild_id: int,
        winner_ids: List[int],
        winner_names: List[str],
        loser_ids: List[int],
        loser_names: List[str],
        match_type: str,
        finish_type: str,
        rating: Optional[float] = None,
        championship_id: Optional[int] = None,
        event_instance_id: Optional[int] = None,
        notes: Optional[str] = None
    ) -> int:
        """Record a match result with multiple participants"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO matches 
                (guild_id, event_instance_id, winner_ids, winner_names, loser_ids, loser_names, 
                 match_type, finish_type, rating, championship_id, match_date, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                guild_id, event_instance_id, 
                json.dumps(winner_ids), json.dumps(winner_names),
                json.dumps(loser_ids), json.dumps(loser_names),
                match_type, finish_type, rating, championship_id, 
                datetime.utcnow().isoformat(), notes
            ))
            await db.commit()
            return cursor.lastrowid
    
    async def update_wrestler_record(self, wrestler_id: int, won: bool):
        """Update wrestler's win/loss record"""
        async with aiosqlite.connect(self.db_path) as db:
            if won:
                await db.execute(
                    "UPDATE wrestlers SET wins = wins + 1 WHERE id = ?",
                    (wrestler_id,)
                )
            else:
                await db.execute(
                    "UPDATE wrestlers SET losses = losses + 1 WHERE id = ?",
                    (wrestler_id,)
                )
            await db.commit()
    
    async def get_wrestler_matches(self, wrestler_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get match history for a wrestler"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            # Get all recent matches
            async with db.execute("""
                SELECT * FROM matches 
                ORDER BY match_date DESC
                LIMIT ?
            """, (limit * 10,)) as cursor:  # Get more than needed, filter in Python
                rows = await cursor.fetchall()
                matches = []
                for row in rows:
                    match = dict(row)
                    # Parse JSON arrays
                    winner_ids = json.loads(match['winner_ids'])
                    loser_ids = json.loads(match['loser_ids'])
                    
                    # Check if wrestler_id is actually in the arrays
                    if wrestler_id in winner_ids or wrestler_id in loser_ids:
                        match['winner_ids'] = winner_ids
                        match['winner_names'] = json.loads(match['winner_names'])
                        match['loser_ids'] = loser_ids
                        match['loser_names'] = json.loads(match['loser_names'])
                        matches.append(match)
                        
                        # Stop once we have enough
                        if len(matches) >= limit:
                            break
                
                return matches
    
    async def set_booker_role(self, guild_id: int, role_id: int):
        """Set the booker role for match/event management"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE server_settings SET booker_role_id = ? WHERE guild_id = ?",
                (role_id, guild_id)
            )
            await db.commit()
    
    async def remove_booker_role(self, guild_id: int):
        """Remove booker role (only admins can manage)"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE server_settings SET booker_role_id = NULL WHERE guild_id = ?",
                (guild_id,)
            )
            await db.commit()
    
    # ==================== CHAMPIONSHIPS (PHASE 2B) ====================
    
    async def create_championship(
        self,
        guild_id: int,
        name: str,
        description: Optional[str],
        gender_requirement: str,
        weight_class_requirement: str,
        is_tag_team: bool
    ) -> int:
        """Create a new championship"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO championships 
                (guild_id, name, description, gender_requirement, weight_class_requirement, 
                 is_tag_team, created_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                guild_id, name, description, gender_requirement, weight_class_requirement,
                1 if is_tag_team else 0, datetime.utcnow().isoformat()
            ))
            await db.commit()
            return cursor.lastrowid
    
    async def get_championship_by_name(self, guild_id: int, name: str) -> Optional[Dict[str, Any]]:
        """Get championship by name"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM championships WHERE guild_id = ? AND name = ? AND is_active = 1",
                (guild_id, name)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
    
    async def get_all_championships(self, guild_id: int) -> List[Dict[str, Any]]:
        """Get all active championships"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM championships WHERE guild_id = ? AND is_active = 1 ORDER BY name",
                (guild_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def update_current_champion(self, championship_id: int, wrestler_id: Optional[int]):
        """Update current champion (None = vacant)"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE championships SET current_champion_id = ? WHERE id = ?",
                (wrestler_id, championship_id)
            )
            await db.commit()
    
    async def start_title_reign(
        self,
        championship_id: int,
        wrestler_id: int,
        wrestler_name: str
    ) -> int:
        """Start a new title reign"""
        async with aiosqlite.connect(self.db_path) as db:
            # Get reign number (previous reigns + 1)
            async with db.execute(
                "SELECT COUNT(*) FROM title_reigns WHERE championship_id = ? AND wrestler_id = ?",
                (championship_id, wrestler_id)
            ) as cursor:
                row = await cursor.fetchone()
                reign_number = row[0] + 1
            
            # Create new reign
            cursor = await db.execute("""
                INSERT INTO title_reigns
                (championship_id, wrestler_id, wrestler_name, reign_number, 
                 won_date, days_held, successful_defenses, is_current)
                VALUES (?, ?, ?, ?, ?, 0, 0, 1)
            """, (
                championship_id, wrestler_id, wrestler_name, reign_number,
                datetime.utcnow().isoformat()
            ))
            await db.commit()
            return cursor.lastrowid
    
    async def end_title_reign(self, championship_id: int):
        """End current title reign"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            # Get current reign
            async with db.execute(
                "SELECT * FROM title_reigns WHERE championship_id = ? AND is_current = 1",
                (championship_id,)
            ) as cursor:
                reign = await cursor.fetchone()
            
            if reign:
                reign_dict = dict(reign)
                won_date = datetime.fromisoformat(reign_dict['won_date'])
                days_held = (datetime.utcnow() - won_date).days
                
                # Update reign
                await db.execute("""
                    UPDATE title_reigns 
                    SET lost_date = ?, days_held = ?, is_current = 0
                    WHERE id = ?
                """, (datetime.utcnow().isoformat(), days_held, reign_dict['id']))
                
                await db.commit()
    
    async def increment_title_defense(self, championship_id: int):
        """Increment successful defenses for current champion"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE title_reigns 
                SET successful_defenses = successful_defenses + 1
                WHERE championship_id = ? AND is_current = 1
            """, (championship_id,))
            await db.commit()
    
    async def get_current_reign(self, championship_id: int) -> Optional[Dict[str, Any]]:
        """Get current title reign"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM title_reigns WHERE championship_id = ? AND is_current = 1",
                (championship_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
    
    async def get_championship_reigns(self, championship_id: int) -> List[Dict[str, Any]]:
        """Get all reigns for a championship"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT tr.*, c.name as championship_name
                FROM title_reigns tr
                JOIN championships c ON tr.championship_id = c.id
                WHERE tr.championship_id = ?
                ORDER BY tr.won_date DESC
            """, (championship_id,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def get_wrestler_title_reigns(self, wrestler_id: int) -> List[Dict[str, Any]]:
        """Get all title reigns for a wrestler"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT tr.*, c.name as championship_name
                FROM title_reigns tr
                JOIN championships c ON tr.championship_id = c.id
                WHERE tr.wrestler_id = ?
                ORDER BY tr.won_date DESC
            """, (wrestler_id,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def check_championship_eligibility(
        self,
        championship_id: int,
        wrestler_gender: str,
        wrestler_weight: str,
        is_tag_team: bool
    ) -> Optional[str]:
        """Check if wrestler is eligible for championship. Returns error message or None"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM championships WHERE id = ?",
                (championship_id,)
            ) as cursor:
                champ = await cursor.fetchone()
            
            if not champ:
                return "Championship not found"
            
            # Check tag team requirement
            if champ['is_tag_team'] and not is_tag_team:
                return "This is a tag team championship"
            
            # Check gender requirement
            if champ['gender_requirement'] != "Mixed" and champ['gender_requirement'] != wrestler_gender:
                return f"This championship is for {champ['gender_requirement']} wrestlers only"
            
            # Check weight class requirement
            if champ['weight_class_requirement'] != "All" and champ['weight_class_requirement'] != wrestler_weight:
                return f"This championship is for {champ['weight_class_requirement']} weight class only"
            
            return None
    
    # ==================== EVENTS (PHASE 3) ====================
    
    async def create_event(
        self,
        guild_id: int,
        name: str,
        event_date: str,
        description: Optional[str]
    ) -> int:
        """Create a new event/show"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO events 
                (guild_id, name, event_date, description, created_at, is_completed)
                VALUES (?, ?, ?, ?, ?, 0)
            """, (guild_id, name, event_date, description, datetime.utcnow().isoformat()))
            await db.commit()
            return cursor.lastrowid
    
    async def get_event_by_name(self, guild_id: int, name: str) -> Optional[Dict[str, Any]]:
        """Get event by name"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM events WHERE guild_id = ? AND name = ?",
                (guild_id, name)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
    
    async def get_all_events(self, guild_id: int) -> List[Dict[str, Any]]:
        """Get all events for a server"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM events WHERE guild_id = ? ORDER BY event_date DESC",
                (guild_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def add_event_match(
        self,
        event_id: int,
        match_type: str,
        wrestler_ids: List[int],
        wrestler_names: List[str],
        championship_id: Optional[int],
        stipulation: Optional[str],
        match_order: Optional[int]
    ) -> int:
        """Add a planned match to an event"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO event_matches
                (event_id, match_type, wrestler_ids, wrestler_names, championship_id,
                 stipulation, match_order, is_open_spot, is_completed)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0)
            """, (
                event_id, match_type,
                json.dumps(wrestler_ids), json.dumps(wrestler_names),
                championship_id, stipulation, match_order
            ))
            await db.commit()
            return cursor.lastrowid
    
    async def add_open_event_match(
        self,
        event_id: int,
        match_type: str,
        spots: int,
        description: str,
        championship_id: Optional[int],
        stipulation: Optional[str],
        match_order: Optional[int]
    ) -> int:
        """Add an open spot match to an event"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO event_matches
                (event_id, match_type, championship_id, stipulation, match_order,
                 is_open_spot, open_spots_count, open_spot_description, is_completed)
                VALUES (?, ?, ?, ?, ?, 1, ?, ?, 0)
            """, (
                event_id, match_type, championship_id, stipulation, match_order,
                spots, description
            ))
            await db.commit()
            return cursor.lastrowid
    
    async def get_event_matches(self, event_id: int) -> List[Dict[str, Any]]:
        """Get all matches for an event"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT em.*, c.name as championship_name
                FROM event_matches em
                LEFT JOIN championships c ON em.championship_id = c.id
                WHERE em.event_id = ?
                ORDER BY em.match_order ASC, em.id ASC
            """, (event_id,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def update_event_announcement(self, event_id: int, message_id: int):
        """Save announcement message ID"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE events SET announcement_message_id = ? WHERE id = ?",
                (message_id, event_id)
            )
            await db.commit()
    
    async def get_event_by_id(self, event_id: int) -> Optional[Dict[str, Any]]:
        """Get event by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM events WHERE id = ?",
                (event_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    # ==================== EVENTS/SHOWS SYSTEM (PHASE 3) ====================
    
    async def create_event_template(
        self, guild_id: int, template_type: str, name: str,
        description: Optional[str], default_time: Optional[str],
        announcement_channel_id: Optional[int], banner_url: Optional[str]
    ) -> int:
        """Create reusable template"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO event_templates 
                (guild_id, type, name, description, default_time, 
                 announcement_channel_id, banner_url, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (guild_id, template_type, name, description, default_time,
                  announcement_channel_id, banner_url, datetime.utcnow().isoformat()))
            await db.commit()
            return cursor.lastrowid
    
    async def get_event_templates(self, guild_id: int, template_type: Optional[str] = None):
        """Get all templates"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if template_type:
                async with db.execute(
                    "SELECT * FROM event_templates WHERE guild_id = ? AND type = ?",
                    (guild_id, template_type)
                ) as cursor:
                    rows = await cursor.fetchall()
            else:
                async with db.execute(
                    "SELECT * FROM event_templates WHERE guild_id = ?",
                    (guild_id,)
                ) as cursor:
                    rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    def number_to_roman(self, num: int) -> str:
        """Convert to Roman numerals"""
        val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
        syms = ['M', 'CM', 'D', 'CD', 'C', 'XC', 'L', 'XL', 'X', 'IX', 'V', 'IV', 'I']
        result = ''
        i = 0
        while num > 0:
            for _ in range(num // val[i]):
                result += syms[i]
                num -= val[i]
            i += 1
        return result
    
    async def create_event_instance(
        self, guild_id: int, template_id: int, base_name: str,
        event_type: str, date: str, time: Optional[str],
        description: Optional[str], banner_url: Optional[str],
        announcement_channel_id: Optional[int]
    ):
        """Create instance with auto-numbering"""
        async with aiosqlite.connect(self.db_path) as db:
            # Get next number
            async with db.execute(
                "SELECT MAX(instance_number) FROM event_instances WHERE guild_id = ? AND template_id = ?",
                (guild_id, template_id)
            ) as cursor:
                row = await cursor.fetchone()
                next_num = (row[0] or 0) + 1
            
            # Format name
            if event_type == "Event":
                full_name = f"{base_name} {self.number_to_roman(next_num)}"
            else:
                full_name = f"{base_name} #{next_num}"
            
            cursor = await db.execute("""
                INSERT INTO event_instances
                (guild_id, template_id, base_name, full_name, type, instance_number,
                 date, time, description, banner_url, announcement_channel_id, created_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'planned')
            """, (guild_id, template_id, base_name, full_name, event_type, next_num,
                  date, time, description, banner_url, announcement_channel_id,
                  datetime.utcnow().isoformat()))
            await db.commit()
            return cursor.lastrowid, full_name
    
    async def get_event_instances(self, guild_id: int, status: Optional[str] = None):
        """Get all instances"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if status:
                async with db.execute(
                    "SELECT * FROM event_instances WHERE guild_id = ? AND status = ? ORDER BY date DESC",
                    (guild_id, status)
                ) as cursor:
                    rows = await cursor.fetchall()
            else:
                async with db.execute(
                    "SELECT * FROM event_instances WHERE guild_id = ? ORDER BY date DESC",
                    (guild_id,)
                ) as cursor:
                    rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def get_event_instance_by_name(self, guild_id: int, name: str):
        """Get instance by name"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM event_instances WHERE guild_id = ? AND full_name = ?",
                (guild_id, name)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
    
    async def get_event_instance_by_id(self, event_id: int):
        """Get instance by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM event_instances WHERE id = ?",
                (event_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
    
    async def add_event_match(
        self, event_id: int, order: int, match_type: str,
        participants: List[int], championship_id: Optional[int], is_main: bool
    ) -> int:
        """Add match to card"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO event_instance_matches
                (event_instance_id, match_order, match_type, participants,
                 championship_id, is_main_event, is_open_spot, status)
                VALUES (?, ?, ?, ?, ?, ?, 0, 'pending')
            """, (event_id, order, match_type, json.dumps(participants),
                  championship_id, 1 if is_main else 0))
            await db.commit()
            return cursor.lastrowid
    
    async def add_open_match(
        self, event_id: int, order: int, match_type: str,
        spots: int, description: Optional[str], is_main: bool
    ) -> int:
        """Add open spot match"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO event_instance_matches
                (event_instance_id, match_order, match_type, participants,
                 is_open_spot, spots_available, spots_filled, open_spot_description,
                 is_main_event, status)
                VALUES (?, ?, ?, '[]', 1, ?, 0, ?, ?, 'pending')
            """, (event_id, order, match_type, spots, description, 1 if is_main else 0))
            await db.commit()
            return cursor.lastrowid
    
    async def get_event_matches(self, event_id: int):
        """Get all matches for event"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM event_instance_matches WHERE event_instance_id = ? ORDER BY match_order",
                (event_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                matches = []
                for row in rows:
                    m = dict(row)
                    m['participants'] = json.loads(m['participants'])
                    matches.append(m)
                return matches
    
    async def apply_for_match(self, match_id: int, wrestler_id: int, user_id: int) -> int:
        """Apply for open spot (auto-accept first come first serve)"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM event_instance_matches WHERE id = ?", (match_id,)
            ) as cursor:
                match = await cursor.fetchone()
            
            if not match:
                raise ValueError("Match not found")
            
            m = dict(match)
            if m['spots_filled'] >= m['spots_available']:
                raise ValueError("No spots available")
            
            cursor = await db.execute("""
                INSERT INTO event_instance_applications
                (event_instance_match_id, wrestler_id, user_id, applied_at, status)
                VALUES (?, ?, ?, ?, 'accepted')
            """, (match_id, wrestler_id, user_id, datetime.utcnow().isoformat()))
            
            participants = json.loads(m['participants'])
            participants.append(wrestler_id)
            
            await db.execute("""
                UPDATE event_instance_matches
                SET participants = ?, spots_filled = spots_filled + 1
                WHERE id = ?
            """, (json.dumps(participants), match_id))
            
            await db.commit()
            return cursor.lastrowid
    
    async def update_event_status(self, event_id: int, status: str):
        """Update event status (planned/ongoing/closed)"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE event_instances SET status = ? WHERE id = ?",
                (status, event_id)
            )
            if status == 'closed':
                await db.execute(
                    "UPDATE event_instances SET completed_at = ? WHERE id = ?",
                    (datetime.utcnow().isoformat(), event_id)
                )
            await db.commit()
    
    async def update_current_champions(self, championship_id: int, wrestler_ids: List[int]):
        """Update current champion(s) - supports singles and tag teams"""
        async with aiosqlite.connect(self.db_path) as db:
            import json
            await db.execute(
                "UPDATE championships SET current_champion_ids = ?, current_champion_id = ? WHERE id = ?",
                (json.dumps(wrestler_ids), wrestler_ids[0] if wrestler_ids else None, championship_id)
            )
            await db.commit()
    
    async def get_championship_by_id(self, championship_id: int) -> Optional[Dict[str, Any]]:
        """Get championship by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM championships WHERE id = ?",
                (championship_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
    
    async def get_match_by_id(self, match_id: int) -> Optional[Dict[str, Any]]:
        """Get match by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM matches WHERE id = ?",
                (match_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
    
    async def link_match_to_event_match(self, event_instance_id: int, match_id: int, match_type: str, participants: List[int]):
        """Link a recorded match to an event match card"""
        async with aiosqlite.connect(self.db_path) as db:
            import json
            # Find matching event match
            async with db.execute("""
                SELECT id FROM event_instance_matches 
                WHERE event_instance_id = ? 
                AND match_type = ? 
                AND status = 'pending'
                ORDER BY match_order
                LIMIT 1
            """, (event_instance_id, match_type)) as cursor:
                event_match = await cursor.fetchone()
            
            if event_match:
                # Link and mark as completed
                await db.execute("""
                    UPDATE event_instance_matches 
                    SET match_id = ?, status = 'completed'
                    WHERE id = ?
                """, (match_id, event_match[0]))
                await db.commit()
                return event_match[0]
            
            return None
    
    async def update_event_instance_announcement(self, event_instance_id: int, message_id: int):
        """Save announcement message ID for event instance"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE event_instances SET announcement_message_id = ? WHERE id = ?",
                (message_id, event_instance_id)
            )
            await db.commit()
    
    async def delete_event_match(self, event_match_id: int):
        """Delete an event match"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM event_instance_matches WHERE id = ?", (event_match_id,))
            await db.commit()
    
    async def delete_event_instance(self, event_instance_id: int):
        """Delete an event instance"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM event_instances WHERE id = ?", (event_instance_id,))
            await db.commit()
    
    # ========== LEVEL SYSTEM ==========
    
    
    async def get_attribute_cap(self, level: int) -> int:
        """Get the attribute cap for a given level"""
        caps = {
            1: 70,
            2: 75,
            3: 80,
            4: 85,
            5: 90,
            6: 92,
            7: 95,
            8: 97,
            9: 99,
            10: 100
        }
        return caps.get(level, 70)
    
    async def get_upgrade_cost(self, current_value: int) -> int:
        """Calculate cost to upgrade attribute (progressive tax)"""
        # Base cost increases with attribute value
        if current_value < 50:
            return 100
        elif current_value < 70:
            return 200
        elif current_value < 85:
            return 500
        elif current_value < 95:
            return 1000
        else:
            return 2000  # 95-100 is very expensive
    
    async def add_xp(self, wrestler_id: int, xp: int):
        """Add XP to wrestler and check for level up"""
        async with aiosqlite.connect(self.db_path) as db:
            # Get current stats
            async with db.execute(
                "SELECT level, xp FROM wrestlers WHERE id = ?",
                (wrestler_id,)
            ) as cursor:
                result = await cursor.fetchone()
                if not result:
                    return None
                
                current_level, current_xp = result
                new_xp = current_xp + xp
                
                # Level thresholds
                thresholds = [0, 250, 850, 1950, 3750, 6450, 10250, 15450, 22450, 31950]
                
                # Check for level up
                new_level = current_level
                if current_level < 10:
                    for level in range(current_level, 10):
                        if new_xp >= thresholds[level]:
                            new_level = level + 1
                        else:
                            break
                
                # Update wrestler
                await db.execute(
                    "UPDATE wrestlers SET xp = ?, level = ? WHERE id = ?",
                    (new_xp, new_level, wrestler_id)
                )
                
                # Award currency bonus on level up
                if new_level > current_level:
                    bonus_currency = 0
                    if new_level == 2:
                        bonus_currency = 500
                    elif new_level == 6:
                        bonus_currency = 1000
                    
                    if bonus_currency > 0:
                        await db.execute(
                            "UPDATE wrestlers SET currency = currency + ? WHERE id = ?",
                            (bonus_currency, wrestler_id)
                        )
                
                await db.commit()
                
                # Return level up info if leveled
                if new_level > current_level:
                    return {
                        'old_level': current_level, 
                        'new_level': new_level, 
                        'xp': new_xp,
                        'bonus_currency': bonus_currency if new_level > current_level else 0
                    }
                return None
    
    async def get_attribute_cap(self, level: int) -> int:
        """Get maximum attribute value for a given level"""
        caps = {
            1: 70, 2: 75, 3: 80, 4: 85, 5: 90,
            6: 92, 7: 95, 8: 97, 9: 99, 10: 100
        }
        return caps.get(level, 70)
    
    async def get_level_unlock(self, level: int) -> str:
        """Get unlock description for a level"""
        unlocks = {
            1: "🎭 Rookie Status",
            2: "💰 +$500 Bonus",
            3: "🎯 Signature Slot Unlocked (check shop)",
            4: "🎨 Sideplates Unlocked (check shop)",
            5: "🔥 Finisher Slot Unlocked (check shop)",
            6: "💰 +$1,000 Bonus",
            7: "⚡ Superfinisher Unlocked (check shop)",
            8: "🎬 Custom Entrance Unlocked (check shop)",
            9: "🏛️ Hall of Fame Eligibility",
            10: "⭐ Legend Status + 🤝 Stable Creation Unlocked"
        }
        return unlocks.get(level, "")
    
    async def claim_daily_reward(self, wrestler_id: int):
        """Claim daily reward and update streak"""
        from datetime import datetime, timedelta
        
        async with aiosqlite.connect(self.db_path) as db:
            # Get current data
            async with db.execute(
                "SELECT last_daily_claim, daily_streak, longest_streak, currency FROM wrestlers WHERE id = ?",
                (wrestler_id,)
            ) as cursor:
                result = await cursor.fetchone()
                if not result:
                    return None
                
                last_claim_str, current_streak, longest_streak, currency = result
                now = datetime.now()
                
                # Parse last claim
                if last_claim_str:
                    last_claim = datetime.fromisoformat(last_claim_str)
                    
                    # Check if already claimed today
                    if last_claim.date() == now.date():
                        time_until_next = datetime.combine(now.date() + timedelta(days=1), datetime.min.time()) - now
                        hours = int(time_until_next.total_seconds() // 3600)
                        minutes = int((time_until_next.total_seconds() % 3600) // 60)
                        return {
                            'success': False,
                            'reason': 'already_claimed',
                            'next_claim_hours': hours,
                            'next_claim_minutes': minutes,
                            'current_streak': current_streak
                        }
                    
                    # Check if claimed yesterday (streak continues)
                    yesterday = now.date() - timedelta(days=1)
                    if last_claim.date() == yesterday:
                        new_streak = current_streak + 1
                        streak_broken = False
                    else:
                        # Streak broken
                        new_streak = 1
                        streak_broken = True
                else:
                    # First claim ever
                    new_streak = 1
                    streak_broken = False
                
                # Calculate reward based on streak
                reward = self.calculate_daily_reward(new_streak)
                
                # Update longest streak
                new_longest = max(longest_streak or 0, new_streak)
                
                # Update database
                await db.execute(
                    """UPDATE wrestlers 
                       SET last_daily_claim = ?, 
                           daily_streak = ?, 
                           longest_streak = ?,
                           currency = currency + ?
                       WHERE id = ?""",
                    (now.isoformat(), new_streak, new_longest, reward, wrestler_id)
                )
                await db.commit()
                
                return {
                    'success': True,
                    'reward': reward,
                    'streak': new_streak,
                    'streak_broken': streak_broken,
                    'new_balance': currency + reward,
                    'is_milestone': new_streak in [3, 7, 14, 30]
                }
    
    def calculate_daily_reward(self, streak: int) -> int:
        """Calculate reward based on streak"""
        base = 100
        
        # Every 7th day = big bonus
        if streak % 7 == 0:
            return 200  # Weekly bonus
        
        # Days 3-6 = small bonus
        if streak >= 3:
            return 125  # 25% bonus
        
        # Days 1-2 = base
        return base
    
    async def set_default_wrestler_limit(self, guild_id: int, limit: int):
        """Set default wrestler limit for all users"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE server_settings SET default_wrestler_limit = ? WHERE guild_id = ?",
                (limit, guild_id)
            )
            await db.commit()
    
    async def set_user_wrestler_limit(self, guild_id: int, user_id: int, limit: int):
        """Set wrestler limit for specific user"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Check if user limit exists
                async with db.execute(
                    "SELECT * FROM user_wrestler_limits WHERE guild_id = ? AND user_id = ?",
                    (guild_id, user_id)
                ) as cursor:
                    existing = await cursor.fetchone()
                
                if existing:
                    await db.execute(
                        "UPDATE user_wrestler_limits SET wrestler_limit = ? WHERE guild_id = ? AND user_id = ?",
                        (limit, guild_id, user_id)
                    )
                    print(f"✅ Updated user {user_id} limit to {limit}")
                else:
                    await db.execute(
                        "INSERT INTO user_wrestler_limits (guild_id, user_id, wrestler_limit) VALUES (?, ?, ?)",
                        (guild_id, user_id, limit)
                    )
                    print(f"✅ Created user {user_id} limit: {limit}")
                await db.commit()
        except Exception as e:
            print(f"❌ ERROR in set_user_wrestler_limit: {e}")
            raise
    
    async def update_currency_settings(self, guild_id: int, currency_name: str, currency_symbol: str):
        """Update currency settings"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE server_settings SET currency_name = ?, currency_symbol = ? WHERE guild_id = ?",
                (currency_name, currency_symbol, guild_id)
            )
            await db.commit()
    
    async def set_shop_channel(self, guild_id: int, channel_id: int):
        """Set shop channel restriction"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE server_settings SET shop_channel_id = ? WHERE guild_id = ?",
                (channel_id, guild_id)
            )
            await db.commit()
    
    async def create_server_settings(
        self,
        guild_id: int,
        currency_name: str,
        currency_symbol: str,
        announcement_channel_id: Optional[int] = None,
        booker_role_id: Optional[int] = None
    ):
        """Create initial server settings"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO server_settings 
                (guild_id, currency_name, currency_symbol, announcement_channel_id, booker_role_id, setup_completed)
                VALUES (?, ?, ?, ?, ?, 1)
            """, (guild_id, currency_name, currency_symbol, announcement_channel_id, booker_role_id))
            await db.commit()
    
    async def get_wrestler_limit(self, guild_id: int, user_id: int) -> int:
        """Get wrestler limit for a user (checks user-specific first, then default)"""
        async with aiosqlite.connect(self.db_path) as db:
            # Check user-specific limit
            async with db.execute(
                "SELECT wrestler_limit FROM user_wrestler_limits WHERE guild_id = ? AND user_id = ?",
                (guild_id, user_id)
            ) as cursor:
                user_limit = await cursor.fetchone()
                if user_limit:
                    return user_limit[0]
            
            # Fall back to server default
            async with db.execute(
                "SELECT default_wrestler_limit FROM server_settings WHERE guild_id = ?",
                (guild_id,)
            ) as cursor:
                default = await cursor.fetchone()
                return default[0] if default and default[0] else 1
            
    # ==================== PHASE 4: INACTIVITY SYSTEM ====================
    
    async def update_last_active(self, user_id: int, guild_id: int):
        """Update last_active for all wrestlers of a user + reactivate if inactive"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE wrestlers 
                SET last_active = ?, is_inactive = 0
                WHERE user_id = ? AND guild_id = ?
            """, (datetime.utcnow().isoformat(), user_id, guild_id))
            await db.commit()
    
    async def get_inactive_wrestlers(self, guild_id: int, days: int):
        """Get all wrestlers inactive for more than X days"""
        from datetime import timedelta
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM wrestlers
                WHERE guild_id = ?
                AND is_retired = 0
                AND is_inactive = 0
                AND (last_active IS NULL OR last_active < ?)
            """, (guild_id, cutoff)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def get_warning_wrestlers(self, guild_id: int, warning_days: int, inactivity_days: int):
        """Get wrestlers approaching inactivity (between warning_days and inactivity_days)"""
        from datetime import timedelta
        warning_cutoff = (datetime.utcnow() - timedelta(days=warning_days)).isoformat()
        inactive_cutoff = (datetime.utcnow() - timedelta(days=inactivity_days)).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM wrestlers
                WHERE guild_id = ?
                AND is_retired = 0
                AND is_inactive = 0
                AND last_active < ?
                AND last_active >= ?
            """, (guild_id, warning_cutoff, inactive_cutoff)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def set_wrestler_inactive(self, wrestler_id: int):
        """Set a wrestler as inactive"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE wrestlers SET is_inactive = 1 WHERE id = ?",
                (wrestler_id,)
            )
            await db.commit()
    
    async def set_wrestler_active(self, wrestler_id: int):
        """Set a wrestler as active"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE wrestlers SET is_inactive = 0, last_active = ? WHERE id = ?",
                (datetime.utcnow().isoformat(), wrestler_id)
            )
            await db.commit()
    
    async def get_wrestler_champions(self, guild_id: int):
        """Get all wrestlers who are currently champions"""
        import json
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM championships WHERE guild_id = ? AND is_active = 1",
                (guild_id,)
            ) as cursor:
                championships = [dict(row) for row in await cursor.fetchall()]
            
            champion_wrestlers = []
            for champ in championships:
                if champ.get('current_champion_ids'):
                    ids = json.loads(champ['current_champion_ids']) if isinstance(champ['current_champion_ids'], str) else champ['current_champion_ids']
                    for w_id in ids:
                        champion_wrestlers.append({
                            'wrestler_id': w_id,
                            'championship_name': champ['name']
                        })
            return champion_wrestlers
    
    async def update_inactivity_settings(self, guild_id: int, inactivity_days: int, warning_days: int, log_channel_id: int = None):
        """Update inactivity settings for server"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE server_settings 
                SET inactivity_days = ?, warning_days = ?, inactivity_log_channel_id = ?
                WHERE guild_id = ?
            """, (inactivity_days, warning_days, log_channel_id, guild_id))
            await db.commit()
    # ==================== PHASE 4: RIVALRIES ====================
    
    async def create_rivalry(self, guild_id: int, wrestler1_id: int, wrestler2_id: int):
        """Create a new rivalry between two wrestlers"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO rivalries 
                (guild_id, wrestler1_id, wrestler2_id, created_date)
                VALUES (?, ?, ?, ?)
            """, (guild_id, wrestler1_id, wrestler2_id, datetime.utcnow().isoformat()))
            await db.commit()
    
    async def get_active_rivalry_for_wrestler(self, wrestler_id: int):
        """Get active rivalry for a wrestler (if any)"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM rivalries
                WHERE (wrestler1_id = ? OR wrestler2_id = ?)
                AND is_active = 1
            """, (wrestler_id, wrestler_id)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None
    
    async def get_all_active_rivalries(self, guild_id: int):
        """Get all active rivalries in a guild"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT r.*, 
                       w1.name as wrestler1_name,
                       w2.name as wrestler2_name
                FROM rivalries r
                JOIN wrestlers w1 ON r.wrestler1_id = w1.id
                JOIN wrestlers w2 ON r.wrestler2_id = w2.id
                WHERE r.guild_id = ? AND r.is_active = 1
                ORDER BY r.created_date DESC
            """, (guild_id,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def end_rivalry(self, rivalry_id: int):
        """End a rivalry"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE rivalries SET is_active = 0 WHERE id = ?",
                (rivalry_id,)
            )
            await db.commit()
    
    async def check_rivalry_between_wrestlers(self, wrestler_ids: list):
        """Check if any two wrestlers in the list are rivals"""
        if len(wrestler_ids) < 2:
            return None
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # Check all combinations
            for i, w1 in enumerate(wrestler_ids):
                for w2 in wrestler_ids[i+1:]:
                    async with db.execute("""
                        SELECT * FROM rivalries
                        WHERE ((wrestler1_id = ? AND wrestler2_id = ?)
                           OR (wrestler1_id = ? AND wrestler2_id = ?))
                        AND is_active = 1
                    """, (w1, w2, w2, w1)) as cursor:
                        row = await cursor.fetchone()
                        if row:
                            return dict(row)
            
            return None
    
    async def update_rivalry_after_match(self, rivalry_id: int, winner_ids: list, loser_ids: list):
        """Update rivalry stats after a match"""
        async with aiosqlite.connect(self.db_path) as db:
            # Get rivalry
            async with db.execute(
                "SELECT wrestler1_id, wrestler2_id FROM rivalries WHERE id = ?",
                (rivalry_id,)
            ) as cursor:
                rivalry = await cursor.fetchone()
                if not rivalry:
                    return
            
            wrestler1_id, wrestler2_id = rivalry
            
            # Determine who won
            wrestler1_won = wrestler1_id in winner_ids
            wrestler2_won = wrestler2_id in winner_ids
            
            # Update stats
            if wrestler1_won:
                await db.execute("""
                    UPDATE rivalries 
                    SET matches_fought = matches_fought + 1,
                        wrestler1_wins = wrestler1_wins + 1,
                        last_match_date = ?
                    WHERE id = ?
                """, (datetime.utcnow().isoformat(), rivalry_id))
            elif wrestler2_won:
                await db.execute("""
                    UPDATE rivalries 
                    SET matches_fought = matches_fought + 1,
                        wrestler2_wins = wrestler2_wins + 1,
                        last_match_date = ?
                    WHERE id = ?
                """, (datetime.utcnow().isoformat(), rivalry_id))
            
            await db.commit()

    # ==================== PHASE 4: WRESTLER CHANGES ====================
    
    async def record_turn(self, wrestler_id: int, old_alignment: str, new_alignment: str, 
                          old_persona: str, new_persona: str):
        """Record a turn in history"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO turn_history 
                (wrestler_id, old_alignment, new_alignment, old_persona, new_persona, turn_date)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (wrestler_id, old_alignment, new_alignment, old_persona, new_persona, 
                  datetime.utcnow().isoformat()))
            
            await db.execute(
                "UPDATE wrestlers SET last_turn_date = ? WHERE id = ?",
                (datetime.utcnow().isoformat(), wrestler_id)
            )
            await db.commit()
    
    async def get_turn_history(self, wrestler_id: int):
        """Get turn history for a wrestler"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM turn_history 
                WHERE wrestler_id = ? 
                ORDER BY turn_date DESC
            """, (wrestler_id,)) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def update_wrestler_alignment_and_persona(self, wrestler_id: int, alignment: str, 
                                                     persona: str, personality_traits: dict):
        """Update wrestler alignment, persona, and personality traits"""
        import json
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE wrestlers 
                SET alignment = ?, persona = ?, personality_traits = ?
                WHERE id = ?
            """, (alignment, persona, json.dumps(personality_traits), wrestler_id))
            await db.commit()
    
    async def update_wrestler_signature(self, wrestler_id: int, signature: str):
        """Update wrestler's signature move"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE wrestlers SET signature = ? WHERE id = ?",
                (signature, wrestler_id)
            )
            await db.commit()
    
    async def update_wrestler_finisher(self, wrestler_id: int, finisher: str):
        """Update wrestler's finisher"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE wrestlers SET finisher = ? WHERE id = ?",
                (finisher, wrestler_id)
            )
            await db.commit()
    
    async def rename_wrestler(self, wrestler_id: int, new_name: str, old_name: str):
        """Rename a wrestler and store old name in history"""
        import json
        async with aiosqlite.connect(self.db_path) as db:
            # Get current former_names
            async with db.execute(
                "SELECT former_names FROM wrestlers WHERE id = ?",
                (wrestler_id,)
            ) as cursor:
                row = await cursor.fetchone()
                former_names = json.loads(row[0]) if row and row[0] else []
            
            # Add old name to history
            former_names.append({
                'name': old_name,
                'date': datetime.utcnow().isoformat()
            })
            
            # Update wrestler
            await db.execute("""
                UPDATE wrestlers 
                SET name = ?, former_names = ?, last_rename_date = ?
                WHERE id = ?
            """, (new_name, json.dumps(former_names), datetime.utcnow().isoformat(), wrestler_id))
            await db.commit()
    
    async def check_turn_cooldown(self, wrestler_id: int, cooldown_days: int) -> dict:
        """Check if wrestler can turn (cooldown check)"""
        from datetime import timedelta
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT last_turn_date FROM wrestlers WHERE id = ?",
                (wrestler_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if not row or not row[0]:
                    return {'can_turn': True, 'days_remaining': 0}
                
                last_turn = datetime.fromisoformat(row[0])
                days_since = (datetime.utcnow() - last_turn).days
                days_remaining = max(0, cooldown_days - days_since)
                
                return {
                    'can_turn': days_remaining == 0,
                    'days_remaining': days_remaining,
                    'last_turn_date': row[0]
                }
    
    async def check_rename_cooldown(self, wrestler_id: int, cooldown_days: int) -> dict:
        """Check if wrestler can be renamed (cooldown check)"""
        from datetime import timedelta
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT last_rename_date FROM wrestlers WHERE id = ?",
                (wrestler_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if not row or not row[0]:
                    return {'can_rename': True, 'days_remaining': 0}
                
                last_rename = datetime.fromisoformat(row[0])
                days_since = (datetime.utcnow() - last_rename).days
                days_remaining = max(0, cooldown_days - days_since)
                
                return {
                    'can_rename': days_remaining == 0,
                    'days_remaining': days_remaining,
                    'last_rename_date': row[0]
                }