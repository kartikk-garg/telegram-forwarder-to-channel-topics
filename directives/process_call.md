# Process Call

When a new Telegram message containing a token CA is detected, execute this flow:

## Steps

1. **Extract CA** from message text using regex pattern
   - Pattern: `(?:dexscreener\.com\/[\w-]+\/)?([1-9A-HJ-NP-Za-km-z]{32,44}|0x[a-fA-F0-9]{40})`
   - Multiple CAs can appear in one message — process each separately

2. **Fetch DexScreener data**
   - Script: `execution/fetch_dexscreener.py`
   - Function: `search_token(address)` → returns price, mcap, volumes, liquidity, socials
   - If returns `None`, skip this CA

3. **Fetch Solana Tracker risk data**
   - Script: `execution/fetch_solana_tracker.py`
   - Function: `get_risk_data(token_address)` → returns top10, bundlers, snipers, insiders
   - Requires `SOLANA_TRACKER_API_KEY` in `.env`
   - If API key missing, returns safe defaults (all zeros)

4. **Log to database**
   - Script: `execution/db_operations.py`
   - Function: `insert_call(conn, data_dict)` with all enriched fields
   - Handles spam check (2h cooldown) and re-entry detection automatically
   - Returns call tag: `"🆕 NEW CALL"`, `"🔁 RE-ENTRY"`, or `"⚠️ SPAM"`

5. **Format message**
   - Script: `execution/format_message.py`
   - Function: `build_call_message(call_tag, ch_name, token_data, risk_data, ...)`
   - Includes: token info, volume line, risk line, CA, social links, Maestro/DexScreener links

6. **Forward to Telegram** with media (banner + logo + original media)

## Edge Cases

- **Rate limits**: DexScreener allows 300 req/min. Solana Tracker has its own limits — returns 429 on hit.
- **Missing API key**: Solana Tracker data will be all zeros. DexScreener is free (no key needed).
- **No pairs found**: Skip the token silently, don't crash.
- **Media failures**: Try album → fallback to first media + replies → fallback to text only.

## Data Stored Per Call

| Field | Source |
|---|---|
| Price, MCap, Liquidity | DexScreener |
| Volume (5m, 1h, 6h, 24h) | DexScreener |
| Vol/MCap ratio | Computed (vol_h1 / mcap) |
| Top 10 holder % | Solana Tracker |
| Bundler count + % | Solana Tracker |
| Sniper count + % | Solana Tracker |
| Insider count + % | Solana Tracker |
| Call time | System clock |
