"""
Database Setup — V2 (81 Columns)
Initializes the SQLite database with the full 81-column schema.
Includes tables for calls, re-entries, settings, and topic maps.
"""

import sqlite3

DB_NAME = "crypto_data.db"

def setup_database():
    print(f"🔧 Initializing {DB_NAME} with V2 Schema (81 columns)...")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Shared column definition for calls and re_entries
    columns_def = """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME,
        channel_id INTEGER,
        channel_name TEXT,
        symbol TEXT,
        ca TEXT,
        
        -- Token Metadata
        token_name TEXT DEFAULT '',
        created_on TEXT DEFAULT '',
        has_twitter INTEGER DEFAULT 0,
        has_website INTEGER DEFAULT 0,
        has_discord INTEGER DEFAULT 0,
        has_instagram INTEGER DEFAULT 0,
        twitter_url TEXT DEFAULT '',
        description TEXT DEFAULT '',
        creator_wallet TEXT DEFAULT '',
        token_created_time INTEGER DEFAULT 0,
        token_age_hours REAL DEFAULT 0,
        
        -- Market Data (Entry)
        entry_price REAL,
        entry_mcap REAL,
        entry_vol_5m REAL,
        entry_vol_1h REAL DEFAULT 0,
        entry_vol_6h REAL DEFAULT 0,
        entry_vol_24h REAL DEFAULT 0,
        vol_mcap_ratio REAL DEFAULT 0,
        initial_liquidity REAL DEFAULT 0,
        liquidity_sol REAL DEFAULT 0,
        primary_market TEXT DEFAULT '',
        lp_burn_pct REAL DEFAULT 0,
        freeze_authority TEXT DEFAULT '',
        mint_authority TEXT DEFAULT '',
        buys_total INTEGER DEFAULT 0,
        sells_total INTEGER DEFAULT 0,
        buy_sell_ratio REAL DEFAULT 0,
        total_txns INTEGER DEFAULT 0,
        volume_24h REAL DEFAULT 0,
        mc_vol_ratio_24h REAL DEFAULT 0,
        holders INTEGER DEFAULT 0,
        pool_count INTEGER DEFAULT 0,
        is_graduated INTEGER DEFAULT 0,
        curve_percentage REAL,
        is_cashback_coin INTEGER DEFAULT 0,
        pool_created_at INTEGER DEFAULT 0,
        pool_age_minutes REAL DEFAULT 0,
        
        -- Price Changes (at call time)
        price_change_1m REAL,
        price_change_5m REAL,
        price_change_15m REAL,
        price_change_30m REAL,
        price_change_1h REAL,
        price_change_6h REAL,
        price_change_24h REAL,
        
        -- Risk Data
        risk_score INTEGER DEFAULT 0,
        is_rugged INTEGER DEFAULT 0,
        top10_holder_pct REAL DEFAULT 0,
        dev_pct REAL DEFAULT 0,
        sniper_count INTEGER DEFAULT 0,
        sniper_pct REAL DEFAULT 0,
        sniper_active_count INTEGER DEFAULT 0,
        sniper_dump_pct REAL DEFAULT 0,
        bundler_count INTEGER DEFAULT 0,
        bundler_pct REAL DEFAULT 0,
        bundler_initial_pct REAL DEFAULT 0,
        insider_count INTEGER DEFAULT 0,
        insider_pct REAL DEFAULT 0,
        risk_flags_json TEXT DEFAULT '[]',
        
        -- Trading Fees (Bot Activity)
        fees_gmgn REAL DEFAULT 0,
        fees_padre REAL DEFAULT 0,
        fees_axiom REAL DEFAULT 0,
        fees_bullx REAL DEFAULT 0,
        fees_photon REAL DEFAULT 0,
        fees_trojan REAL DEFAULT 0,
        fees_maestro REAL DEFAULT 0,
        fees_total_trading REAL DEFAULT 0,
        fees_total_tips REAL DEFAULT 0,
        
        -- Computed & Totals
        total_liquidity_usd REAL DEFAULT 0,
        is_multi_pool INTEGER DEFAULT 0,
        
        -- Tracking State (Watcher)
        current_price REAL DEFAULT 0,
        max_price REAL DEFAULT 0,
        peak_multiplier REAL DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        is_rug INTEGER DEFAULT 0
    """

    # 1. Calls Table
    c.execute(f"CREATE TABLE IF NOT EXISTS calls ({columns_def})")
    print("✅ Table 'calls' ready.")

    # 2. Re-entries Table
    c.execute(f"CREATE TABLE IF NOT EXISTS re_entries ({columns_def})")
    print("✅ Table 're_entries' ready.")

    # 3. Settings Table
    c.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)
    print("✅ Table 'settings' ready.")

    # 4. Indexes
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_calls_ca ON calls(ca)",
        "CREATE INDEX IF NOT EXISTS idx_calls_channel_ca ON calls(channel_id, ca)",
        "CREATE INDEX IF NOT EXISTS idx_calls_active ON calls(is_active)",
        "CREATE INDEX IF NOT EXISTS idx_re_ca ON re_entries(ca)",
    ]
    for idx in indexes:
        c.execute(idx)
    print("✅ Indexes optimized.")

    # 5. Defaults
    defaults = [
        ("rug_threshold", "500"),
        ("spam_cooldown", "120"),
        ("tracking_days", "7"),
        ("is_active", "1")
    ]
    for key, val in defaults:
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, val))
    
    conn.commit()
    conn.close()
    print("\n🚀 Setup Complete. Use db_upgrade.py if you have an existing old DB.")

if __name__ == "__main__":
    setup_database()