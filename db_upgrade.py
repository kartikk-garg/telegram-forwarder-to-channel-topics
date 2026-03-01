"""
Database Upgrade Script — V2
Adds ALL new columns for comprehensive token data collection.
Run this ONCE on existing databases to migrate them.
"""

import sqlite3

DB_NAME = "crypto_data.db"

# All new columns to add (name, type + default)
NEW_COLUMNS = [
    # Token metadata
    ("token_name", "TEXT DEFAULT ''"),
    ("created_on", "TEXT DEFAULT ''"),
    ("has_twitter", "INTEGER DEFAULT 0"),
    ("has_website", "INTEGER DEFAULT 0"),
    ("has_discord", "INTEGER DEFAULT 0"),
    ("has_instagram", "INTEGER DEFAULT 0"),
    ("twitter_url", "TEXT DEFAULT ''"),
    ("description", "TEXT DEFAULT ''"),
    ("creator_wallet", "TEXT DEFAULT ''"),
    ("token_created_time", "INTEGER DEFAULT 0"),
    ("token_age_hours", "REAL DEFAULT 0"),
    # Market data (primary pool)
    ("liquidity_sol", "REAL DEFAULT 0"),
    ("primary_market", "TEXT DEFAULT ''"),
    ("lp_burn_pct", "REAL DEFAULT 0"),
    ("freeze_authority", "TEXT DEFAULT ''"),
    ("mint_authority", "TEXT DEFAULT ''"),
    ("buys_total", "INTEGER DEFAULT 0"),
    ("sells_total", "INTEGER DEFAULT 0"),
    ("buy_sell_ratio", "REAL DEFAULT 0"),
    ("total_txns", "INTEGER DEFAULT 0"),
    ("volume_24h", "REAL DEFAULT 0"),
    ("mc_vol_ratio_24h", "REAL DEFAULT 0"),
    ("holders", "INTEGER DEFAULT 0"),
    ("pool_count", "INTEGER DEFAULT 0"),
    ("is_graduated", "INTEGER DEFAULT 0"),
    ("curve_percentage", "REAL"),
    ("is_cashback_coin", "INTEGER DEFAULT 0"),
    ("pool_created_at", "INTEGER DEFAULT 0"),
    ("pool_age_minutes", "REAL DEFAULT 0"),
    # Price changes
    ("price_change_1m", "REAL"),
    ("price_change_5m", "REAL"),
    ("price_change_15m", "REAL"),
    ("price_change_30m", "REAL"),
    ("price_change_1h", "REAL"),
    ("price_change_6h", "REAL"),
    ("price_change_24h", "REAL"),
    # Expanded risk
    ("risk_score", "INTEGER DEFAULT 0"),
    ("is_rugged", "INTEGER DEFAULT 0"),
    ("dev_pct", "REAL DEFAULT 0"),
    ("sniper_active_count", "INTEGER DEFAULT 0"),
    ("bundler_initial_pct", "REAL DEFAULT 0"),
    ("sniper_dump_pct", "REAL DEFAULT 0"),
    ("risk_flags_json", "TEXT DEFAULT '[]'"),
    # Trading fees
    ("fees_gmgn", "REAL DEFAULT 0"),
    ("fees_padre", "REAL DEFAULT 0"),
    ("fees_axiom", "REAL DEFAULT 0"),
    ("fees_bullx", "REAL DEFAULT 0"),
    ("fees_photon", "REAL DEFAULT 0"),
    ("fees_trojan", "REAL DEFAULT 0"),
    ("fees_maestro", "REAL DEFAULT 0"),
    ("fees_total_trading", "REAL DEFAULT 0"),
    ("fees_total_tips", "REAL DEFAULT 0"),
    # Computed
    ("total_liquidity_usd", "REAL DEFAULT 0"),
    ("is_multi_pool", "INTEGER DEFAULT 0"),
]

print("🔧 Upgrading Database Schema (V2 — Full Data)...")
conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

for table in ["calls", "re_entries"]:
    print(f"\n📦 Upgrading table: {table}")
    added = 0
    for col_name, col_type in NEW_COLUMNS:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
            print(f"  ✅ Added: {col_name}")
            added += 1
        except sqlite3.OperationalError:
            pass  # Already exists, skip silently
    print(f"  📊 {added} new columns added")

conn.commit()
conn.close()
print("\n🚀 Database upgrade complete!")