# Generate Report

Generates and sends the weekly alpha leaderboard to Telegram.

## Steps

1. **Query leaderboard data**
   - Script: `execution/db_operations.py`
   - Function: `get_leaderboard(conn, days=7, limit=15)`
   - Returns: list of dicts with channel_name, total, rugs, avg_x, best_x, wins

2. **Format report message**
   - Script: `execution/format_message.py`
   - Function: `build_report_message(leaderboard_rows)`
   - Includes status flags: ✅ (>40% win), ⛔ (>30% rug), ➖ (neutral)

3. **Send to Telegram** General Topic

## Edge Cases

- **No data**: Returns `"⚠️ Weekly Report: Not enough data collected yet."`
- **Session**: Uses `crypto_session` (separate from forwarder's `local_test`)
