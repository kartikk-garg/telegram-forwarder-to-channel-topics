"""
Database Operations — V2
All SQLite interactions — insert, query, update, leaderboard.
Wide flat table: ~75 columns per call row.

Usage:
    python execution/db_operations.py --check
"""

import sqlite3
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DEFAULT_DB = "crypto_data.db"


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

def get_connection(db_name=DEFAULT_DB):
    """Returns a WAL-mode SQLite connection for safe concurrency."""
    conn = sqlite3.connect(db_name, check_same_thread=False, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=10000")
    return conn


# ---------------------------------------------------------------------------
# Insert Call — spam check + re-entry detection + full data insert
# ---------------------------------------------------------------------------

# All columns in insert order (excluding id, max_price, current_price, is_active, peak_multiplier, is_rug)
INSERT_COLUMNS = [
    'timestamp', 'channel_id', 'channel_name', 'symbol', 'ca',
    # Token metadata
    'token_name', 'created_on', 'has_twitter', 'has_website', 'has_discord',
    'has_instagram', 'twitter_url', 'description', 'creator_wallet',
    'token_created_time', 'token_age_hours',
    # Market data
    'entry_price', 'entry_mcap', 'entry_vol_5m', 'entry_vol_1h', 'entry_vol_6h', 'entry_vol_24h',
    'vol_mcap_ratio', 'initial_liquidity', 'liquidity_sol', 'primary_market',
    'lp_burn_pct', 'freeze_authority', 'mint_authority',
    'buys_total', 'sells_total', 'buy_sell_ratio', 'total_txns',
    'volume_24h', 'mc_vol_ratio_24h', 'holders',
    'pool_count', 'is_graduated', 'curve_percentage', 'is_cashback_coin',
    'pool_created_at', 'pool_age_minutes',
    # Price changes
    'price_change_1m', 'price_change_5m', 'price_change_15m',
    'price_change_30m', 'price_change_1h', 'price_change_6h', 'price_change_24h',
    # Risk
    'risk_score', 'is_rugged', 'top10_holder_pct', 'dev_pct',
    'sniper_count', 'sniper_pct', 'sniper_active_count', 'sniper_dump_pct',
    'bundler_count', 'bundler_pct', 'bundler_initial_pct',
    'insider_count', 'insider_pct', 'risk_flags_json',
    # Trading fees
    'fees_gmgn', 'fees_padre', 'fees_axiom', 'fees_bullx',
    'fees_photon', 'fees_trojan', 'fees_maestro',
    'fees_total_trading', 'fees_total_tips',
    # Computed
    'total_liquidity_usd', 'is_multi_pool',
    # Message metadata (V3)
    'raw_message_text', 'forwarded_from_name',
    'message_has_media', 'message_has_tweet_link',
    'message_has_external_link', 'extracted_tweet_url',
    # Tracking fields
    'max_price', 'current_price', 'is_active',
]


def insert_call(conn, data):
    """
    Inserts a call with full enriched data.

    Args:
        conn: sqlite3.Connection
        data: flat dict from get_full_token_data() + channel info

    Returns:
        str: "🆕 NEW CALL", "🔁 RE-ENTRY", "⚠️ SPAM", or None on error
    """
    try:
        ca = data.get('ca', '')
        channel_id = data.get('channel_id', 0)

        # 1. SPAM CHECK (2-Hour Cooldown)
        if conn.execute(
            "SELECT id FROM calls WHERE channel_id = ? AND ca = ? AND timestamp > datetime('now', '-2 hours')",
            (channel_id, ca)
        ).fetchone():
            return "⚠️ SPAM"

        # 2. RE-ENTRY CHECK
        is_reentry = conn.execute(
            "SELECT id FROM calls WHERE channel_id = ? AND ca = ?",
            (channel_id, ca)
        ).fetchone() is not None
        table_name = "re_entries" if is_reentry else "calls"

        # 3. Build values list matching INSERT_COLUMNS order
        price = data.get('price', 0)
        values = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            channel_id, data.get('channel_name', ''),
            data.get('symbol', ''), ca,
            # Token metadata
            data.get('token_name', ''), data.get('created_on', ''),
            data.get('has_twitter', 0), data.get('has_website', 0),
            data.get('has_discord', 0), data.get('has_instagram', 0),
            data.get('twitter_url', ''), data.get('description', ''),
            data.get('creator_wallet', ''),
            data.get('token_created_time', 0), data.get('token_age_hours', 0),
            # Market data
            price, data.get('mcap', 0),
            data.get('vol_5m', 0), data.get('vol_h1', 0),
            data.get('vol_h6', 0), data.get('vol_h24', 0),
            data.get('vol_mcap_ratio', 0), data.get('liquidity', 0),
            data.get('liquidity_sol', 0), data.get('primary_market', ''),
            data.get('lp_burn_pct', 0), data.get('freeze_authority', ''),
            data.get('mint_authority', ''),
            data.get('buys_total', 0), data.get('sells_total', 0),
            data.get('buy_sell_ratio', 0), data.get('total_txns', 0),
            data.get('volume_24h', 0), data.get('mc_vol_ratio_24h', 0),
            data.get('holders', 0),
            data.get('pool_count', 0), data.get('is_graduated', 0),
            data.get('curve_percentage', None), data.get('is_cashback_coin', 0),
            data.get('pool_created_at', 0), data.get('pool_age_minutes', 0),
            # Price changes
            data.get('price_change_1m'), data.get('price_change_5m'),
            data.get('price_change_15m'), data.get('price_change_30m'),
            data.get('price_change_1h'), data.get('price_change_6h'),
            data.get('price_change_24h'),
            # Risk
            data.get('risk_score', 0), data.get('is_rugged', 0),
            data.get('top10_holder_pct', 0), data.get('dev_pct', 0),
            data.get('sniper_count', 0), data.get('sniper_pct', 0),
            data.get('sniper_active_count', 0), data.get('sniper_dump_pct', 0),
            data.get('bundler_count', 0), data.get('bundler_pct', 0),
            data.get('bundler_initial_pct', 0),
            data.get('insider_count', 0), data.get('insider_pct', 0),
            data.get('risk_flags_json', '[]'),
            # Trading fees
            data.get('fees_gmgn', 0), data.get('fees_padre', 0),
            data.get('fees_axiom', 0), data.get('fees_bullx', 0),
            data.get('fees_photon', 0), data.get('fees_trojan', 0),
            data.get('fees_maestro', 0),
            data.get('fees_total_trading', 0), data.get('fees_total_tips', 0),
            # Computed
            data.get('total_liquidity_usd', 0), data.get('is_multi_pool', 0),
            # Message metadata (V3)
            data.get('raw_message_text', ''), data.get('forwarded_from_name', ''),
            data.get('message_has_media', 0), data.get('message_has_tweet_link', 0),
            data.get('message_has_external_link', 0), data.get('extracted_tweet_url', ''),
            # Tracking
            price, price, 1,  # max_price, current_price, is_active
        ]

        placeholders = ', '.join(['?'] * len(INSERT_COLUMNS))
        cols = ', '.join(INSERT_COLUMNS)
        query = f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})"

        conn.execute(query, values)
        conn.commit()

        tag = "🔁 RE-ENTRY" if is_reentry else "🆕 NEW CALL"
        logging.info(f"{tag}: {data.get('symbol', '?')} ({ca[:8]}...)")
        return tag

    except Exception as e:
        logging.error(f"❌ DB insert error: {e}")
        return None


# ---------------------------------------------------------------------------
# Get Active Calls — for watcher triage
# ---------------------------------------------------------------------------

def get_active_calls(conn, table_name, age_filter="all"):
    """Fetches active calls for price watching."""
    conditions = ["is_active=1"]
    if age_filter == "young":
        conditions.append("timestamp >= datetime('now', '-1 hour')")
    elif age_filter == "mid":
        conditions.append("timestamp BETWEEN datetime('now', '-24 hours') AND datetime('now', '-1 hour')")
    elif age_filter == "old":
        conditions.append("timestamp < datetime('now', '-24 hours')")
    where = " AND ".join(conditions)
    query = f"SELECT id, ca, entry_price, max_price, timestamp FROM {table_name} WHERE {where}"
    return conn.execute(query).fetchall()


# ---------------------------------------------------------------------------
# Update Prices — batch update for watcher
# ---------------------------------------------------------------------------

def update_prices(conn, table_name, updates):
    """
    Batch updates price data for tracked calls.
    Each update tuple: (current_price, max_price, peak_multiplier, is_rug, is_active,
                        last_checked_at, peak_hit_at, time_to_peak_hours, time_to_2x_hours, id)
    """
    if not updates:
        return 0
    conn.executemany(f"""
        UPDATE {table_name}
        SET current_price=?, max_price=?, peak_multiplier=?, is_rug=?, is_active=?,
            last_checked_at=?, peak_hit_at=?, time_to_peak_hours=?, time_to_2x_hours=?
        WHERE id=?
    """, updates)
    logging.info(f"✅ Updated {len(updates)} rows in '{table_name}'")
    return len(updates)


# ---------------------------------------------------------------------------
# Leaderboard Query — for reporter
# ---------------------------------------------------------------------------

def get_leaderboard(conn, days=7, limit=15):
    """Returns enhanced leaderboard data for the weekly report."""
    query = f"""
    SELECT channel_name,
           COUNT(*) as total,
           SUM(is_rug) as rugs,
           AVG(peak_multiplier) as avg_x,
           MAX(peak_multiplier) as best_x,
           SUM(CASE WHEN peak_multiplier > 2 THEN 1 ELSE 0 END) as wins,
           AVG(time_to_2x_hours) as avg_speed_to_2x,
           COUNT(*) * 1.0 / {days} as calls_per_day
    FROM calls WHERE timestamp >= datetime('now', '-{days} days')
    GROUP BY channel_name HAVING total > 0
    ORDER BY wins DESC, avg_x DESC LIMIT {limit}
    """
    cursor = conn.execute(query)
    columns = [d[0] for d in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_best_call(conn, days=7):
    """Returns the single best call of the week."""
    query = f"""
    SELECT symbol, ca, channel_name, peak_multiplier, time_to_peak_hours,
           entry_mcap, risk_score
    FROM calls WHERE timestamp >= datetime('now', '-{days} days')
    ORDER BY peak_multiplier DESC LIMIT 1
    """
    cursor = conn.execute(query)
    columns = [d[0] for d in cursor.description]
    row = cursor.fetchone()
    return dict(zip(columns, row)) if row else None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    if "--check" in sys.argv:
        conn = get_connection()
        for table in ["calls", "re_entries"]:
            try:
                cols = [d[1] for d in conn.execute(f"PRAGMA table_info({table})").fetchall()]
                count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                print(f"📦 {table}: {len(cols)} columns, {count} rows")
                print(f"   Columns: {', '.join(cols)}")
            except Exception as e:
                print(f"❌ {table}: {e}")
        conn.close()
    else:
        print("Usage: python execution/db_operations.py --check")
