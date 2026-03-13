"""
Database Migration — V3
Adds 11 new columns for architectural improvements:
- Message metadata (raw text, tweet links, media flags)
- Watcher crash recovery (last_checked_at, check_failures)
- Peak timing analytics (peak_hit_at, time_to_peak_hours, time_to_2x_hours)

Safe to re-run: silently skips columns that already exist.
"""

import sqlite3

DB_NAME = "crypto_data.db"

V3_COLUMNS = [
    # Message metadata
    ("raw_message_text",        "TEXT DEFAULT ''"),
    ("forwarded_from_name",     "TEXT DEFAULT ''"),
    ("message_has_media",       "INTEGER DEFAULT 0"),
    ("message_has_tweet_link",  "INTEGER DEFAULT 0"),
    ("message_has_external_link","INTEGER DEFAULT 0"),
    ("extracted_tweet_url",     "TEXT DEFAULT ''"),
    # Watcher crash recovery
    ("last_checked_at",         "INTEGER DEFAULT 0"),
    ("check_failures",          "INTEGER DEFAULT 0"),
    # Peak timing
    ("peak_hit_at",             "INTEGER DEFAULT 0"),
    ("time_to_peak_hours",      "REAL"),
    ("time_to_2x_hours",        "REAL"),
]

# V2 columns from previous migration (for backwards compat)
V2_COLUMNS = [
    ("token_name",          "TEXT DEFAULT ''"),
    ("created_on",          "TEXT DEFAULT ''"),
    ("has_twitter",         "INTEGER DEFAULT 0"),
    ("has_website",         "INTEGER DEFAULT 0"),
    ("has_discord",         "INTEGER DEFAULT 0"),
    ("has_instagram",       "INTEGER DEFAULT 0"),
    ("twitter_url",         "TEXT DEFAULT ''"),
    ("description",         "TEXT DEFAULT ''"),
    ("creator_wallet",      "TEXT DEFAULT ''"),
    ("token_created_time",  "INTEGER DEFAULT 0"),
    ("token_age_hours",     "REAL DEFAULT 0"),
    ("liquidity_sol",       "REAL DEFAULT 0"),
    ("primary_market",      "TEXT DEFAULT ''"),
    ("lp_burn_pct",         "REAL DEFAULT 0"),
    ("freeze_authority",    "TEXT DEFAULT ''"),
    ("mint_authority",      "TEXT DEFAULT ''"),
    ("buys_total",          "INTEGER DEFAULT 0"),
    ("sells_total",         "INTEGER DEFAULT 0"),
    ("buy_sell_ratio",      "REAL DEFAULT 0"),
    ("total_txns",          "INTEGER DEFAULT 0"),
    ("volume_24h",          "REAL DEFAULT 0"),
    ("mc_vol_ratio_24h",    "REAL DEFAULT 0"),
    ("holders",             "INTEGER DEFAULT 0"),
    ("pool_count",          "INTEGER DEFAULT 0"),
    ("is_graduated",        "INTEGER DEFAULT 0"),
    ("curve_percentage",    "REAL"),
    ("is_cashback_coin",    "INTEGER DEFAULT 0"),
    ("pool_created_at",     "INTEGER DEFAULT 0"),
    ("pool_age_minutes",    "REAL DEFAULT 0"),
    ("price_change_1m",     "REAL"),
    ("price_change_5m",     "REAL"),
    ("price_change_15m",    "REAL"),
    ("price_change_30m",    "REAL"),
    ("price_change_1h",     "REAL"),
    ("price_change_6h",     "REAL"),
    ("price_change_24h",    "REAL"),
    ("risk_score",          "INTEGER DEFAULT 0"),
    ("is_rugged",           "INTEGER DEFAULT 0"),
    ("dev_pct",             "REAL DEFAULT 0"),
    ("sniper_active_count", "INTEGER DEFAULT 0"),
    ("sniper_dump_pct",     "REAL DEFAULT 0"),
    ("bundler_initial_pct", "REAL DEFAULT 0"),
    ("risk_flags_json",     "TEXT DEFAULT '[]'"),
    ("fees_gmgn",           "REAL DEFAULT 0"),
    ("fees_padre",          "REAL DEFAULT 0"),
    ("fees_axiom",          "REAL DEFAULT 0"),
    ("fees_bullx",          "REAL DEFAULT 0"),
    ("fees_photon",         "REAL DEFAULT 0"),
    ("fees_trojan",         "REAL DEFAULT 0"),
    ("fees_maestro",        "REAL DEFAULT 0"),
    ("fees_total_trading",  "REAL DEFAULT 0"),
    ("fees_total_tips",     "REAL DEFAULT 0"),
    ("total_liquidity_usd", "REAL DEFAULT 0"),
    ("is_multi_pool",       "INTEGER DEFAULT 0"),
]


def run_migration():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    all_columns = V2_COLUMNS + V3_COLUMNS

    for table in ["calls", "re_entries"]:
        existing = {row[1] for row in c.execute(f"PRAGMA table_info({table})").fetchall()}
        added = 0
        for col_name, col_type in all_columns:
            if col_name not in existing:
                try:
                    c.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
                    added += 1
                except Exception as e:
                    print(f"  ⚠️ Skipping {col_name}: {e}")
        print(f"✅ {table}: {added} new columns added ({len(existing) + added} total)")

    # Enable WAL mode
    c.execute("PRAGMA journal_mode=WAL")
    print("✅ WAL mode enabled")

    # Add default setting for sheets sync cursor
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('last_sheet_sync_row_id', '0')")

    conn.commit()
    conn.close()
    print("\n🚀 Migration V3 complete!")


if __name__ == "__main__":
    run_migration()