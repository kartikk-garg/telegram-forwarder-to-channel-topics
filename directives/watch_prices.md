# Watch Prices

Continuously monitors active tracked tokens, fetches live prices, detects rugs, and updates the database.

## Steps

1. **Triage** — determine which tokens to check this cycle
   - Young (< 1 hour): every loop (~1 min)
   - Mid (1h - 24h): every 5th loop (~5 min)
   - Old (> 24 hours): every 30th loop (~30 min)
   - Script: `execution/db_operations.py`
   - Function: `get_active_calls(conn, table, age_filter)`

2. **Batch fetch prices** from DexScreener
   - Script: `execution/fetch_dexscreener.py`
   - Function: `fetch_prices_batch(addresses)` — chunks of 30, respects rate limits
   - Returns `{ca: {price, liq}}` dict

3. **Compute updates** for each token
   - New max price = `max(current_max, live_price)`
   - Peak multiplier = `max_price / entry_price`
   - Rug detection: liquidity < $500
   - Expiry: deactivate after 7 days

4. **Batch update database**
   - Script: `execution/db_operations.py`
   - Function: `update_prices(conn, table, updates)`

5. **Sleep** until next minute mark

## Edge Cases

- **Rate limits**: 1.1s pause between DexScreener batches. On 429, sleep 5s and skip batch.
- **Rug detection**: Prints `💀 RUG DETECTED` and sets `is_rug=1`, `is_active=0`.
- **Expiry**: Tokens older than `TRACKING_DAYS` (default 7) auto-deactivate.
- **Both tables**: Process `calls` and `re_entries` in same loop to save API calls.
