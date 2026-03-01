"""
DexScreener API Client
Handles all interactions with the DexScreener API.
Provides token search, volume extraction, and batch price fetching.

Usage:
    python execution/fetch_dexscreener.py <token_address>
"""

import requests
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ---------------------------------------------------------------------------
# Token Search — returns full token info for a given address
# ---------------------------------------------------------------------------

def search_token(address):
    """
    Searches DexScreener for a token by address.
    Returns the most liquid pair's data as a flat dict.
    
    Args:
        address: Token contract address or DexScreener pair address
    
    Returns:
        dict with keys: symbol, price, mcap, vol_5m, vol_h1, vol_h6, vol_h24,
                        vol_mcap_ratio, liquidity, real_ca, banner, logo,
                        websites, socials
        None on failure.
    """
    try:
        url = f"https://api.dexscreener.com/latest/dex/search?q={address}"
        response = requests.get(url, timeout=5)
        data = response.json()

        if not data.get('pairs'):
            return None

        # Most liquid pair is first
        pair = data['pairs'][0]
        real_ca = pair['baseToken']['address']
        info = pair.get('info', {})

        # Extract volumes
        volumes = extract_volumes(pair)

        return {
            'symbol': pair['baseToken']['symbol'],
            'price': float(pair.get('priceUsd', 0) or 0),
            'mcap': float(pair.get('fdv', 0) or 0),
            'liquidity': float(pair.get('liquidity', {}).get('usd', 0) or 0),
            'real_ca': real_ca,
            # Volume fields
            'vol_5m': volumes['vol_5m'],
            'vol_h1': volumes['vol_h1'],
            'vol_h6': volumes['vol_h6'],
            'vol_h24': volumes['vol_h24'],
            'vol_mcap_ratio': volumes['vol_mcap_ratio'],
            # Media
            'banner': info.get('header', None),
            'logo': info.get('imageUrl', None),
            # Links
            'websites': info.get('websites', []),
            'socials': info.get('socials', [])
        }

    except Exception as e:
        logging.error(f"❌ DexScreener search error: {e}")
        return None


# ---------------------------------------------------------------------------
# Volume Extraction — pulls m5/h1/h6/h24 + computes vol/mcap ratio
# ---------------------------------------------------------------------------

def extract_volumes(pair_data):
    """
    Extracts volume fields from a raw DexScreener pair dict.
    Computes vol/mcap ratio using 1h volume.

    Args:
        pair_data: Raw DexScreener pair object

    Returns:
        dict with vol_5m, vol_h1, vol_h6, vol_h24, vol_mcap_ratio
    """
    try:
        volume = pair_data.get('volume', {})
        mcap = float(pair_data.get('fdv', 0) or 0)

        vol_5m = float(volume.get('m5', 0) or 0)
        vol_h1 = float(volume.get('h1', 0) or 0)
        vol_h6 = float(volume.get('h6', 0) or 0)
        vol_h24 = float(volume.get('h24', 0) or 0)

        # Vol/mcap ratio as percentage (1h vol / mcap * 100)
        vol_mcap_ratio = round((vol_h1 / mcap * 100), 4) if mcap > 0 else 0

        return {
            'vol_5m': vol_5m,
            'vol_h1': vol_h1,
            'vol_h6': vol_h6,
            'vol_h24': vol_h24,
            'vol_mcap_ratio': vol_mcap_ratio
        }
    except Exception as e:
        logging.error(f"❌ Volume extraction error: {e}")
        return {'vol_5m': 0, 'vol_h1': 0, 'vol_h6': 0, 'vol_h24': 0, 'vol_mcap_ratio': 0}


# ---------------------------------------------------------------------------
# Batch Price Fetch — chunks of 30 addresses, respects rate limits
# ---------------------------------------------------------------------------

def fetch_prices_batch(addresses):
    """
    Fetches live prices in chunks of 30 to respect DexScreener limits.

    Args:
        addresses: list of token contract addresses

    Returns:
        dict: { 'ca_address': {'price': float, 'liq': float}, ... }
    """
    if not addresses:
        return {}

    unique_addrs = list(set(addresses))
    results = {}
    chunk_size = 30

    chunks = [unique_addrs[i:i + chunk_size] for i in range(0, len(unique_addrs), chunk_size)]

    for chunk in chunks:
        try:
            url = f"https://api.dexscreener.com/latest/dex/tokens/{','.join(chunk)}"
            response = requests.get(url, timeout=10)

            if response.status_code == 429:
                logging.warning("⚠️ Rate Limit Hit! Sleeping 5s...")
                time.sleep(5)
                continue

            data = response.json()
            if not data.get('pairs'):
                continue

            for pair in data['pairs']:
                ca = pair['baseToken']['address']
                price = float(pair.get('priceUsd', 0) or 0)
                liq = float(pair.get('liquidity', {}).get('usd', 0) or 0)

                # Keep pair with best liquidity
                if ca not in results or liq > results[ca]['liq']:
                    results[ca] = {'price': price, 'liq': liq}

            # Rate limit safety pause
            time.sleep(1.1)

        except Exception as e:
            logging.error(f"⚠️ Batch error: {e}")

    return results


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python execution/fetch_dexscreener.py <token_address>")
        sys.exit(1)

    address = sys.argv[1]
    print(f"🔍 Searching DexScreener for {address[:12]}...")

    result = search_token(address)
    if result:
        print(json.dumps(result, indent=2, default=str))
    else:
        print("❌ No data found.")
