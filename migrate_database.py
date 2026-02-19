"""
DATABASE MIGRATION SCRIPT
Adds Phase 3 features to existing database WITHOUT deleting wrestler data
Run this ONCE to upgrade your database!
"""

import aiosqlite
import asyncio
from datetime import datetime

DB_PATH = "wrestling_bot.db"  # Change this if your DB has a different name

async def migrate_database():
    """Add Phase 3 tables and update existing tables"""
    
    print("🔄 Starting database migration...")
    
    async with aiosqlite.connect(DB_PATH) as db:
        
        # ========== ADD NEW PHASE 3 TABLES ==========
        
        print("📋 Creating event_templates table...")
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
        
        print("📋 Creating event_instances table...")
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
        
        print("📋 Creating event_instance_matches table...")
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
        
        print("📋 Creating event_instance_applications table...")
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
        
        # ========== UPDATE WRESTLERS TABLE (PHASE 3: LEVEL SYSTEM) ==========
        
        print("📊 Adding level and XP system to wrestlers...")
        
        async with db.execute("PRAGMA table_info(wrestlers)") as cursor:
            columns = await cursor.fetchall()
            column_names = [col[1] for col in columns]
        
        if 'level' not in column_names:
            print("➕ Adding level column...")
            await db.execute("ALTER TABLE wrestlers ADD COLUMN level INTEGER DEFAULT 1")
        
        if 'xp' not in column_names:
            print("➕ Adding xp column...")
            await db.execute("ALTER TABLE wrestlers ADD COLUMN xp INTEGER DEFAULT 0")
        
        if 'last_daily_claim' not in column_names:
            print("➕ Adding last_daily_claim column...")
            await db.execute("ALTER TABLE wrestlers ADD COLUMN last_daily_claim TEXT")
        
        if 'daily_streak' not in column_names:
            print("➕ Adding daily_streak column...")
            await db.execute("ALTER TABLE wrestlers ADD COLUMN daily_streak INTEGER DEFAULT 0")
        
        if 'longest_streak' not in column_names:
            print("➕ Adding longest_streak column...")
            await db.execute("ALTER TABLE wrestlers ADD COLUMN longest_streak INTEGER DEFAULT 0")
        
        # ========== USER WRESTLER LIMITS TABLE ==========
        
        print("📋 Creating user_wrestler_limits table...")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_wrestler_limits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                wrestler_limit INTEGER NOT NULL,
                UNIQUE(guild_id, user_id)
            )
        """)
        
        # Fix: If old table has max_wrestlers column, rename it
        print("🔧 Checking for old column name...")
        async with db.execute("PRAGMA table_info(user_wrestler_limits)") as cursor:
            limit_columns = await cursor.fetchall()
            limit_column_names = [col[1] for col in limit_columns]
        
        if 'max_wrestlers' in limit_column_names and 'wrestler_limit' not in limit_column_names:
            print("➕ Renaming max_wrestlers to wrestler_limit...")
            # Drop new table if it exists
            await db.execute("DROP TABLE IF EXISTS user_wrestler_limits_new")
            
            # Create new table
            await db.execute("""
                CREATE TABLE user_wrestler_limits_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    wrestler_limit INTEGER NOT NULL,
                    UNIQUE(guild_id, user_id)
                )
            """)
            
            # Copy data (without id, let it auto-increment)
            await db.execute("""
                INSERT INTO user_wrestler_limits_new (guild_id, user_id, wrestler_limit)
                SELECT guild_id, user_id, max_wrestlers FROM user_wrestler_limits
            """)
            
            # Drop old and rename new
            await db.execute("DROP TABLE user_wrestler_limits")
            await db.execute("ALTER TABLE user_wrestler_limits_new RENAME TO user_wrestler_limits")
            print("✅ Column renamed!")
        elif 'max_wrestlers' in limit_column_names and 'wrestler_limit' in limit_column_names:
            print("⚠️ Both columns exist! Keeping wrestler_limit, dropping max_wrestlers...")
            # This shouldn't happen but handle it anyway
            await db.execute("DROP TABLE IF EXISTS user_wrestler_limits_new")
            await db.execute("""
                CREATE TABLE user_wrestler_limits_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    wrestler_limit INTEGER NOT NULL,
                    UNIQUE(guild_id, user_id)
                )
            """)
            await db.execute("""
                INSERT INTO user_wrestler_limits_new (guild_id, user_id, wrestler_limit)
                SELECT guild_id, user_id, wrestler_limit FROM user_wrestler_limits
            """)
            await db.execute("DROP TABLE user_wrestler_limits")
            await db.execute("ALTER TABLE user_wrestler_limits_new RENAME TO user_wrestler_limits")
            print("✅ Cleaned up columns!")
        
        # ========== UPDATE SERVER SETTINGS ==========
        
        print("⚙️  Checking server_settings table for default_wrestler_limit...")
        async with db.execute("PRAGMA table_info(server_settings)") as cursor:
            settings_columns = await cursor.fetchall()
            settings_column_names = [col[1] for col in settings_columns]
        
        if 'default_wrestler_limit' not in settings_column_names:
            print("➕ Adding default_wrestler_limit column...")
            await db.execute("ALTER TABLE server_settings ADD COLUMN default_wrestler_limit INTEGER DEFAULT 1")
        
        # ========== UPDATE CHAMPIONSHIPS TABLE ==========
        
        print("🏆 Checking championships table for updates...")
        
        # Check if current_champion_ids column exists (for tag teams)
        async with db.execute("PRAGMA table_info(championships)") as cursor:
            columns = await cursor.fetchall()
            column_names = [col[1] for col in columns]
        
        if 'current_champion_ids' not in column_names:
            print("➕ Adding current_champion_ids to championships (for tag teams)...")
            await db.execute("ALTER TABLE championships ADD COLUMN current_champion_ids TEXT")  # JSON array
            
            # Migrate existing single champions to array format
            print("🔄 Migrating existing champions to new format...")
            async with db.execute("SELECT id, current_champion_id FROM championships WHERE current_champion_id IS NOT NULL") as cursor:
                champs = await cursor.fetchall()
            
            for champ in champs:
                import json
                # Convert single ID to JSON array
                await db.execute(
                    "UPDATE championships SET current_champion_ids = ? WHERE id = ?",
                    (json.dumps([champ[1]]), champ[0])
                )
        
        # Add event_id column to matches if not exists
        print("📊 Checking matches table...")
        async with db.execute("PRAGMA table_info(matches)") as cursor:
            match_columns = await cursor.fetchall()
            match_column_names = [col[1] for col in match_columns]
        
        if 'event_instance_id' not in match_column_names:
            print("➕ Adding event_instance_id to matches table...")
            await db.execute("ALTER TABLE matches ADD COLUMN event_instance_id INTEGER")
        
        # ========== PHASE 4: INACTIVITY SYSTEM ==========
        
        print("📊 Adding inactivity columns to wrestlers table...")
        async with db.execute("PRAGMA table_info(wrestlers)") as cursor:
            wrestler_cols = await cursor.fetchall()
            wrestler_col_names = [col[1] for col in wrestler_cols]
        
        if 'last_active' not in wrestler_col_names:
            print("➕ Adding last_active column...")
            await db.execute("ALTER TABLE wrestlers ADD COLUMN last_active TEXT")
            await db.execute(
                "UPDATE wrestlers SET last_active = ? WHERE last_active IS NULL",
                (datetime.utcnow().isoformat(),)
            )
        
        if 'is_inactive' not in wrestler_col_names:
            print("➕ Adding is_inactive column...")
            await db.execute("ALTER TABLE wrestlers ADD COLUMN is_inactive INTEGER DEFAULT 0")
        
        print("📊 Adding inactivity settings to server_settings...")
        async with db.execute("PRAGMA table_info(server_settings)") as cursor:
            settings_cols = await cursor.fetchall()
            settings_col_names = [col[1] for col in settings_cols]
        
        if 'inactivity_days' not in settings_col_names:
            print("➕ Adding inactivity_days column...")
            await db.execute("ALTER TABLE server_settings ADD COLUMN inactivity_days INTEGER DEFAULT 30")
        
        if 'warning_days' not in settings_col_names:
            print("➕ Adding warning_days column...")
            await db.execute("ALTER TABLE server_settings ADD COLUMN warning_days INTEGER DEFAULT 25")
        
        if 'inactivity_log_channel_id' not in settings_col_names:
            print("➕ Adding inactivity_log_channel_id column...")
            await db.execute("ALTER TABLE server_settings ADD COLUMN inactivity_log_channel_id INTEGER")
        
        await db.commit()
        
        print("✅ Migration complete!")
        print("\n📊 Summary:")
        print("  ✓ Phase 3 tables created")
        print("  ✓ Phase 4 inactivity columns added")
        print("  ✓ All existing data preserved!")
        print("\n🎉 Your database is ready for Phase 4!")

if __name__ == "__main__":
    print("=" * 60)
    print("🔧 WRESTLING BOT DATABASE MIGRATION")
    print("=" * 60)
    print(f"\nTarget Database: {DB_PATH}")
    print("\n⚠️  IMPORTANT:")
    print("  • This will ADD new tables")
    print("  • This will NOT delete any wrestlers or matches")
    print("  • Make a backup just in case!")
    print("\nPress ENTER to continue or Ctrl+C to cancel...")
    input()
    
    asyncio.run(migrate_database())
    
    print("\n" + "=" * 60)
    print("✅ MIGRATION COMPLETE - Restart your bot!")
    print("=" * 60)
