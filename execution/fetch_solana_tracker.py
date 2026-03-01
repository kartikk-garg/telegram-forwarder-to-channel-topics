"""
Solana Tracker API Client — Full Token Data Extraction
Extracts ALL useful data from /tokens/{address} endpoint in one call.
Returns a flat dict with ~55 fields ready for DB insertion.

Implements pitfall fixes:
- Primary pool selected by highest liquidity (not array index)
- Dead pools filtered (0 liquidity, null price)
- Timestamp normalization (ms→sec for pool.createdAt)
- Price event backfill detection (nulls windows > token age)
- Sniper active count computed from wallet balances
- Bundler initial vs current pct stored separately

Requires SOLANA_TRACKER_API_KEY in .env

Usage:
    python execution/fetch_solana_tracker.py <token_address>
"""

import os
import re
import json
import time
import requests
import logging
from dotenv import load_dotenv

load_dotenv()

SOLANA_TRACKER_API_KEY = os.getenv('SOLANA_TRACKER_API_KEY', '')
BASE_URL = "https://data.solanatracker.io"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# ---------------------------------------------------------------------------
# Default values — returned when API fails or key is missing
# ---------------------------------------------------------------------------

DEFAULTS = {
    # Token metadata
    'token_name': '', 'symbol': '', 'ca': '', 'created_on': '',
    'has_twitter': 0, 'has_website': 0, 'has_discord': 0, 'has_instagram': 0,
    'twitter_url': '', 'description': '', 'creator_wallet': '',
    'token_created_time': 0, 'token_age_hours': 0,
    # Market data (primary pool)
    'price': 0, 'mcap': 0, 'liquidity': 0, 'liquidity_sol': 0,
    'primary_market': '', 'lp_burn_pct': 0,
    'freeze_authority': '', 'mint_authority': '',
    'buys_total': 0, 'sells_total': 0, 'buy_sell_ratio': 0,
    'total_txns': 0, 'volume_24h': 0, 'vol_5m': 0,
    'vol_h1': 0, 'vol_h6': 0, 'vol_h24': 0,
    'vol_mcap_ratio': 0, 'mc_vol_ratio_24h': 0,
    'holders': 0, 'pool_count': 0,
    'is_graduated': 0, 'curve_percentage': 0, 'is_cashback_coin': 0,
    'pool_created_at': 0, 'pool_age_minutes': 0,
    # Price changes
    'price_change_1m': None, 'price_change_5m': None, 'price_change_15m': None,
    'price_change_30m': None, 'price_change_1h': None,
    'price_change_6h': None, 'price_change_24h': None,
    # Risk
    'risk_score': 0, 'is_rugged': 0,
    'top10_holder_pct': 0, 'dev_pct': 0,
    'sniper_count': 0, 'sniper_pct': 0, 'sniper_active_count': 0, 'sniper_dump_pct': 0,
    'bundler_count': 0, 'bundler_pct': 0, 'bundler_initial_pct': 0,
    'insider_count': 0, 'insider_pct': 0,
    'risk_flags_json': '[]',
    # Trading fees
    'fees_gmgn': 0, 'fees_padre': 0, 'fees_axiom': 0, 'fees_bullx': 0,
    'fees_photon': 0, 'fees_trojan': 0, 'fees_maestro': 0,
    'fees_total_trading': 0, 'fees_total_tips': 0,
    # Computed
    'total_liquidity_usd': 0, 'is_multi_pool': 0,
}


# ---------------------------------------------------------------------------
# Internal: Raw API call
# ---------------------------------------------------------------------------

def _fetch_token_data(token_address):
    """Raw API call to Solana Tracker. Returns full JSON or None."""
    if not SOLANA_TRACKER_API_KEY:
        logging.warning("⚠️ SOLANA_TRACKER_API_KEY not set.")
        return None
    try:
        url = f"{BASE_URL}/tokens/{token_address}"
        headers = {'x-api-key': SOLANA_TRACKER_API_KEY}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 429:
            logging.warning("⚠️ Rate limit hit! Sleeping 3s...")
            time.sleep(3)
            return None
        if response.status_code != 200:
            logging.warning(f"⚠️ Solana Tracker returned {response.status_code}")
            return None
        return response.json()
    except Exception as e:
        logging.error(f"❌ Solana Tracker API error: {e}")
        return None


# ---------------------------------------------------------------------------
# Primary pool selector — by highest USD liquidity, filter dead pools
# ---------------------------------------------------------------------------

def _get_primary_pool(pools):
    """
    Returns the pool with highest liquidity.
    Filters out dead pools (0 liquidity or null price).
    """
    if not pools:
        return None
    active = [
        p for p in pools
        if p.get('liquidity', {}).get('usd', 0) and p.get('liquidity', {}).get('usd', 0) > 0
        and p.get('price', {}).get('usd') is not None
    ]
    if not active:
        return None
    return max(active, key=lambda p: p.get('liquidity', {}).get('usd', 0))


# ---------------------------------------------------------------------------
# Price event cleaner — nulls out backfilled windows
# ---------------------------------------------------------------------------

def _clean_price_events(events, token_age_hours):
    """
    Returns price change values, but nulls out windows older than the token.
    Prevents backfilled duplicate values from misleading the AI.
    """
    windows = {
        '1m': 1/60, '5m': 5/60, '15m': 0.25, '30m': 0.5,
        '1h': 1, '2h': 2, '3h': 3, '4h': 4,
        '5h': 5, '6h': 6, '12h': 12, '24h': 24
    }
    result = {}
    for key, hours in windows.items():
        event = events.get(key, {})
        value = event.get('priceChangePercentage')
        if value is not None and hours <= token_age_hours:
            result[key] = round(value, 4)
        else:
            result[key] = None
    return result


# ---------------------------------------------------------------------------
# Description link extractor
# ---------------------------------------------------------------------------

def _extract_links_from_description(description):
    """Extracts URLs from token description text."""
    if not description:
        return []
    url_pattern = r'https?://[^\s,\'"<>]+'
    return re.findall(url_pattern, description)


# ---------------------------------------------------------------------------
# MAIN: get_full_token_data — returns ~55 fields in one flat dict
# ---------------------------------------------------------------------------

def get_full_token_data(token_address):
    """
    Fetches the COMPLETE token profile from Solana Tracker.
    Returns a flat dict with ~55 fields ready for DB insertion.

    Args:
        token_address: Solana token mint address

    Returns:
        dict with all fields (see DEFAULTS for structure)
    """
    data = _fetch_token_data(token_address)
    if not data:
        return dict(DEFAULTS)

    now = int(time.time())
    result = dict(DEFAULTS)  # Start with safe defaults

    try:
        # ========== TOKEN METADATA ==========
        token = data.get('token', {})
        result['token_name'] = token.get('name', '')
        result['symbol'] = token.get('symbol', '')
        result['ca'] = token.get('mint', token_address)
        result['created_on'] = token.get('createdOn', '')
        result['description'] = (token.get('description', '') or '')[:500]
        result['creator_wallet'] = token.get('creation', {}).get('creator', '')

        # Token age
        created_time = token.get('creation', {}).get('created_time', 0)
        result['token_created_time'] = created_time
        result['token_age_hours'] = round((now - created_time) / 3600, 2) if created_time > 0 else 0

        # Socials flags
        socials = token.get('strictSocials', {})
        result['has_twitter'] = 1 if (token.get('twitter') or socials.get('twitter')) else 0
        result['has_website'] = 1 if token.get('website') else 0
        result['has_discord'] = 1 if socials.get('discord') else 0
        result['has_instagram'] = 1 if socials.get('instagram') else 0
        result['twitter_url'] = token.get('twitter', '') or socials.get('twitter', '') or ''

        # ========== POOLS — PRIMARY POOL SELECTION ==========
        pools = data.get('pools', [])
        result['pool_count'] = len([p for p in pools if p.get('liquidity', {}).get('usd', 0) > 0])
        result['is_multi_pool'] = 1 if result['pool_count'] > 1 else 0

        # Total liquidity across all active pools
        result['total_liquidity_usd'] = round(
            sum(p.get('liquidity', {}).get('usd', 0) for p in pools if p.get('liquidity', {}).get('usd', 0) > 0), 2
        )

        primary = _get_primary_pool(pools)
        if primary:
            result['price'] = float(primary.get('price', {}).get('usd', 0) or 0)
            result['mcap'] = float(primary.get('marketCap', {}).get('usd', 0) or 0)
            result['liquidity'] = float(primary.get('liquidity', {}).get('usd', 0) or 0)
            result['liquidity_sol'] = float(primary.get('liquidity', {}).get('quote', 0) or 0)
            result['primary_market'] = primary.get('market', '')
            result['lp_burn_pct'] = float(primary.get('lpBurn', 0) or 0)

            # Security
            security = primary.get('security', {})
            result['freeze_authority'] = security.get('freezeAuthority') or ''
            result['mint_authority'] = security.get('mintAuthority') or ''

            # Pool timing — createdAt is in MILLISECONDS
            pool_created_ms = primary.get('createdAt', 0)
            result['pool_created_at'] = int(pool_created_ms / 1000) if pool_created_ms else 0
            result['pool_age_minutes'] = round((now - result['pool_created_at']) / 60, 2) if result['pool_created_at'] > 0 else 0

            # Graduation detection
            result['is_graduated'] = 0 if primary.get('market') == 'pumpfun' else 1

            # PumpFun-specific
            pf_data = primary.get('pumpfun-amm', primary.get('pumpfun', {}))
            result['is_cashback_coin'] = 1 if pf_data.get('isCashbackCoin') else 0

            # Curve percentage (from bonding curve pool if exists)
            for p in pools:
                if p.get('curvePercentage') is not None:
                    result['curve_percentage'] = float(p.get('curvePercentage', 0) or 0)
                    break

            # Volume from primary pool txns
            txns = primary.get('txns', {})
            result['volume_24h'] = float(txns.get('volume24h', 0) or 0)

        # ========== ROOT-LEVEL AGGREGATES ==========
        result['buys_total'] = int(data.get('buys', 0) or 0)
        result['sells_total'] = int(data.get('sells', 0) or 0)
        result['total_txns'] = int(data.get('txns', 0) or 0)
        result['holders'] = int(data.get('holders', 0) or 0)

        # Computed: buy/sell ratio
        result['buy_sell_ratio'] = round(
            result['buys_total'] / result['sells_total'], 4
        ) if result['sells_total'] > 0 else 0

        # Computed: MC/volume ratios
        if result['mcap'] > 0:
            result['mc_vol_ratio_24h'] = round(result['volume_24h'] / result['mcap'] * 100, 4)
            # vol_mcap_ratio uses vol_h1 if available, fallback to volume_24h
            result['vol_mcap_ratio'] = result['mc_vol_ratio_24h']

        # ========== PRICE CHANGE EVENTS ==========
        events = data.get('events', {})
        cleaned = _clean_price_events(events, result['token_age_hours'])
        result['price_change_1m'] = cleaned.get('1m')
        result['price_change_5m'] = cleaned.get('5m')
        result['price_change_15m'] = cleaned.get('15m')
        result['price_change_30m'] = cleaned.get('30m')
        result['price_change_1h'] = cleaned.get('1h')
        result['price_change_6h'] = cleaned.get('6h')
        result['price_change_24h'] = cleaned.get('24h')

        # ========== RISK DATA ==========
        risk = data.get('risk', {})
        result['risk_score'] = int(risk.get('score', 0) or 0)
        result['is_rugged'] = 1 if risk.get('rugged') else 0
        result['top10_holder_pct'] = round(float(risk.get('top10', 0) or 0), 2)
        result['dev_pct'] = round(float(risk.get('dev', {}).get('percentage', 0) or 0), 4)

        # Snipers
        snipers = risk.get('snipers', {})
        sniper_wallets = snipers.get('wallets', [])
        result['sniper_count'] = int(snipers.get('count', 0) or 0)
        result['sniper_pct'] = round(float(snipers.get('totalPercentage', 0) or 0), 4)
        result['sniper_active_count'] = len([w for w in sniper_wallets if w.get('balance', 0) > 0])

        # Sniper dump percentage
        sniper_initial_pct = float(snipers.get('totalPercentage', 0) or 0)
        result['sniper_dump_pct'] = round(
            1 - (result['sniper_pct'] / max(sniper_initial_pct, 0.0001)), 4
        ) if sniper_initial_pct > 0 else 0

        # Bundlers
        bundlers = risk.get('bundlers', {})
        result['bundler_count'] = int(bundlers.get('count', 0) or 0)
        result['bundler_pct'] = round(float(bundlers.get('totalPercentage', 0) or 0), 4)
        result['bundler_initial_pct'] = round(float(bundlers.get('totalInitialPercentage', 0) or 0), 4)

        # Insiders
        insiders = risk.get('insiders', {})
        result['insider_count'] = int(insiders.get('count', 0) or 0)
        result['insider_pct'] = round(float(insiders.get('totalPercentage', 0) or 0), 4)

        # Risk flags as JSON
        result['risk_flags_json'] = json.dumps(risk.get('risks', []))

        # ========== TRADING FEES ==========
        fees = risk.get('fees', {})
        result['fees_gmgn'] = round(float(fees.get('gmgn', 0) or 0), 4)
        result['fees_padre'] = round(float(fees.get('padre', 0) or 0), 4)
        result['fees_axiom'] = round(float(fees.get('axiom', 0) or 0), 4)
        result['fees_bullx'] = round(float(fees.get('bullx', 0) or 0), 4)
        result['fees_photon'] = round(float(fees.get('photon', 0) or 0), 4)
        result['fees_trojan'] = round(float(fees.get('trojan', 0) or 0), 4)
        result['fees_maestro'] = round(float(fees.get('maestro', 0) or 0), 4)
        result['fees_total_trading'] = round(float(fees.get('totalTrading', 0) or 0), 4)
        result['fees_total_tips'] = round(float(fees.get('totalTips', 0) or 0), 4)

        logging.info(
            f"✅ Full data: {result['symbol']} | ${result['mcap']:.0f} MCap | "
            f"Risk={result['risk_score']} | Bundlers={result['bundler_count']} | "
            f"Snipers={result['sniper_count']} ({result['sniper_active_count']} active) | "
            f"Top10={result['top10_holder_pct']}%"
        )

    except Exception as e:
        logging.error(f"❌ Data extraction error: {e}")

    return result


# ---------------------------------------------------------------------------
# Backward compat wrapper — returns only risk fields (old format)
# ---------------------------------------------------------------------------

def get_risk_data(token_address):
    """Thin wrapper for backward compatibility. Returns only risk fields."""
    full = get_full_token_data(token_address)
    return {
        'top10_holder_pct': full['top10_holder_pct'],
        'bundler_count': full['bundler_count'],
        'bundler_pct': full['bundler_pct'],
        'sniper_count': full['sniper_count'],
        'sniper_pct': full['sniper_pct'],
        'insider_count': full['insider_count'],
        'insider_pct': full['insider_pct']
    }


# ---------------------------------------------------------------------------
# Granular getters — for skills that only need one piece
# ---------------------------------------------------------------------------

def get_bundlers(token_address):
    """Returns bundler details with wallet list."""
    data = _fetch_token_data(token_address)
    if not data:
        return {'count': 0, 'pct': 0, 'initial_pct': 0, 'wallets': []}
    bundlers = data.get('risk', {}).get('bundlers', {})
    return {
        'count': int(bundlers.get('count', 0) or 0),
        'pct': round(float(bundlers.get('totalPercentage', 0) or 0), 4),
        'initial_pct': round(float(bundlers.get('totalInitialPercentage', 0) or 0), 4),
        'wallets': bundlers.get('wallets', [])[:30]  # Top 30 only
    }


def get_snipers(token_address):
    """Returns sniper details with wallet list."""
    data = _fetch_token_data(token_address)
    if not data:
        return {'count': 0, 'pct': 0, 'active_count': 0, 'wallets': []}
    snipers = data.get('risk', {}).get('snipers', {})
    wallets = snipers.get('wallets', [])
    return {
        'count': int(snipers.get('count', 0) or 0),
        'pct': round(float(snipers.get('totalPercentage', 0) or 0), 4),
        'active_count': len([w for w in wallets if w.get('balance', 0) > 0]),
        'wallets': wallets
    }


def get_insiders(token_address):
    """Returns insider details with wallet list."""
    data = _fetch_token_data(token_address)
    if not data:
        return {'count': 0, 'pct': 0, 'wallets': []}
    insiders = data.get('risk', {}).get('insiders', {})
    return {
        'count': int(insiders.get('count', 0) or 0),
        'pct': round(float(insiders.get('totalPercentage', 0) or 0), 4),
        'wallets': insiders.get('wallets', [])
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python execution/fetch_solana_tracker.py <token_address>")
        sys.exit(1)

    address = sys.argv[1]
    print(f"🔍 Fetching full token data for {address[:12]}...")

    result = get_full_token_data(address)

    # Pretty print organized by category
    categories = {
        '📋 Token': ['token_name', 'symbol', 'ca', 'created_on', 'creator_wallet',
                     'token_age_hours', 'has_twitter', 'has_website', 'has_discord'],
        '💰 Market': ['price', 'mcap', 'liquidity', 'liquidity_sol', 'primary_market',
                     'lp_burn_pct', 'is_graduated', 'pool_count', 'holders',
                     'buys_total', 'sells_total', 'buy_sell_ratio', 'volume_24h',
                     'mc_vol_ratio_24h'],
        '📈 Price Changes': ['price_change_1m', 'price_change_5m', 'price_change_15m',
                             'price_change_30m', 'price_change_1h', 'price_change_6h',
                             'price_change_24h'],
        '🔍 Risk': ['risk_score', 'is_rugged', 'top10_holder_pct', 'dev_pct',
                    'sniper_count', 'sniper_active_count', 'sniper_pct', 'sniper_dump_pct',
                    'bundler_count', 'bundler_pct', 'bundler_initial_pct',
                    'insider_count', 'insider_pct'],
        '🤖 Bot Fees': ['fees_gmgn', 'fees_padre', 'fees_axiom', 'fees_photon',
                        'fees_trojan', 'fees_maestro', 'fees_total_trading', 'fees_total_tips']
    }

    for cat_name, fields in categories.items():
        print(f"\n{cat_name}:")
        for f in fields:
            val = result.get(f)
            print(f"  {f}: {val}")
