"""
Watcher — V3 with Crash Recovery + Peak Timing
Monitors active calls, fetches live prices, updates DB.
Triage: young (<1h) every loop, mid (1-24h) every 5th, old (>24h) every 30th.

Crash Recovery:
 - Tracks last_checked_at per row so restarts resume efficiently
 - Increments check_failures on API errors
Peak Timing:
 - Records peak_hit_at when a new high is set
 - Computes time_to_peak_hours and time_to_2x_hours
"""

import time
from datetime import datetime

# --- Execution Layer Imports ---
from execution.fetch_dexscreener import fetch_prices_batch
from execution.db_operations import get_connection, get_active_calls, update_prices

# --- CONFIG ---
RUG_THRESHOLD = 500       # Liquidity < $500 = Rug
TRACKING_DAYS = 7         # Stop tracking after 7 days


def run_watcher():
    print("👀 Watcher V3 Started (Crash Recovery + Peak Timing)...")
    loop_count = 0

    while True:
        loop_count += 1
        start_time = time.time()

        try:
            conn = get_connection()

            # --- TRIAGE LOGIC ---
            check_mid = (loop_count % 5 == 0)
            check_old = (loop_count % 30 == 0)

            # Collect targets from both tables
            targets = []
            for table in ['calls', 're_entries']:
                # Always check young
                rows = get_active_calls(conn, table, "young")
                targets.extend([(table, row) for row in rows])

                if check_mid:
                    rows = get_active_calls(conn, table, "mid")
                    targets.extend([(table, row) for row in rows])

                if check_old:
                    rows = get_active_calls(conn, table, "old")
                    targets.extend([(table, row) for row in rows])

            if not targets:
                conn.close()
                time.sleep(60)
                continue

            # Extract unique CAs
            unique_cas = list(set(t[1][1] for t in targets))
            print(f"🔍 Cycle {loop_count}: Checking {len(unique_cas)} tokens...")

            # Batch fetch live prices
            live_data = fetch_prices_batch(unique_cas)
            now_ts = int(time.time())

            # Process updates per table
            for table in ['calls', 're_entries']:
                table_rows = [t[1] for t in targets if t[0] == table]
                updates = []

                for row in table_rows:
                    row_id, ca, entry, current_max, timestamp = row

                    if ca not in live_data:
                        # Increment check failures for missing tokens
                        try:
                            conn.execute(
                                f"UPDATE {table} SET check_failures = check_failures + 1, last_checked_at = ? WHERE id = ?",
                                (now_ts, row_id)
                            )
                        except:
                            pass
                        continue

                    market = live_data[ca]
                    curr_price = market['price']
                    curr_liq = market['liq']

                    new_max = max(current_max, curr_price)
                    peak_mult = new_max / entry if entry > 0 else 0
                    is_rug = 1 if curr_liq < RUG_THRESHOLD else 0

                    # --- Peak Timing ---
                    peak_hit_at = 0
                    time_to_peak_hours = None
                    time_to_2x_hours = None

                    if new_max > current_max:
                        # New peak! Record timestamp
                        peak_hit_at = now_ts

                    # Compute time_to_peak_hours from entry timestamp
                    try:
                        entry_date = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                        entry_ts = int(entry_date.timestamp())
                        days_old = (datetime.now() - entry_date).days

                        if peak_hit_at > 0:
                            time_to_peak_hours = round((peak_hit_at - entry_ts) / 3600, 2)

                        # Check for 2x milestone
                        if peak_mult >= 2.0:
                            # Approximate: if we just crossed 2x this cycle, record it
                            current_mult = current_max / entry if entry > 0 else 0
                            if current_mult < 2.0:
                                # Just crossed 2x this cycle!
                                time_to_2x_hours = round((now_ts - entry_ts) / 3600, 2)
                    except:
                        days_old = 0

                    is_active = 0 if (is_rug or days_old >= TRACKING_DAYS) else 1

                    if is_rug:
                        print(f"💀 RUG DETECTED in {table}: {ca}")

                    # Tuple: (curr_price, max_price, peak_mult, is_rug, is_active,
                    #          last_checked_at, peak_hit_at, time_to_peak_hours, time_to_2x_hours, row_id)
                    updates.append((
                        curr_price, new_max, peak_mult, is_rug, is_active,
                        now_ts, peak_hit_at if peak_hit_at > 0 else None,
                        time_to_peak_hours, time_to_2x_hours,
                        row_id
                    ))

                update_prices(conn, table, updates)

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"❌ Watcher Loop Error: {e}")

        # Sleep until the next minute mark
        elapsed = time.time() - start_time
        sleep_time = max(1, 60 - elapsed)
        time.sleep(sleep_time)


if __name__ == "__main__":
    run_watcher()