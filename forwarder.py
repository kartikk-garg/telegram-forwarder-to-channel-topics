import os
import json
import re
import requests
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.tl.types import MessageMediaWebPage

# 1. Load CONFIG
load_dotenv()
api_id = int(os.getenv('API_ID'))
api_hash = os.getenv('API_HASH')

with open('config.json', 'r') as f:
    config = json.load(f)

DESTINATION_CHAT_ID = config['destination_id']
TOPIC_MAP = {int(k): v for k, v in config['topics'].items()}

SESSION_NAME = 'local_test' # Change to 'crypto_session' for EC2

# --- UPDATED REGEX ---
# 1. Strict patterns for raw text (prevents false positives)
SOL_REGEX = r'[1-9A-HJ-NP-Za-km-z]{32,44}'
EVM_REGEX = r'0x[a-fA-F0-9]{40}'

# 2. permissive pattern specifically for URLs (Captures the address part)
# Matches: dexscreener.com/solana/AnyStringHere
DEX_URL_REGEX = r'dexscreener\.com\/[\w-]+\/([a-zA-Z0-9]+)'

client = TelegramClient(SESSION_NAME, api_id, api_hash)

def get_token_info(input_address):
    try:
        # Use Search API to handle both Pairs and Tokens
        url = f"https://api.dexscreener.com/latest/dex/search?q={input_address}"
        response = requests.get(url, timeout=5)
        data = response.json()
        
        if not data.get('pairs'):
            return None, None
            
        pair = data['pairs'][0]
        real_ca = pair['baseToken']['address']
        
        symbol = pair['baseToken']['symbol']
        price = float(pair.get('priceUsd', 0) or 0)
        fdv = pair.get('fdv', 0)
        liquidity = pair.get('liquidity', {}).get('usd', 0)
        vol_5m = pair.get('volume', {}).get('m5', 0)
        
        def human_format(num):
            num = float(num)
            if num >= 1_000_000:
                return f"${num/1_000_000:.1f}M"
            if num >= 1_000:
                return f"${num/1_000:.1f}K"
            return f"${num:.0f}"

        info_line = (
            f"💎 **{symbol}** (${price:.4f})\n"
            f"💰 **MC:** {human_format(fdv)}  |  "
            f"💧 **Liq:** {human_format(liquidity)}  |  "
            f"📊 **Vol(5m):** {human_format(vol_5m)}"
        )
        return info_line, real_ca

    except Exception as e:
        print(f"⚠️ API Error: {e}")
        return None, None

print(f"🚀 Bot running. URL Detection Fixed.")

@client.on(events.NewMessage(chats=list(TOPIC_MAP.keys())))
async def handler(event):
    source_id = event.chat_id
    topic_id = TOPIC_MAP.get(source_id)

    if not topic_id:
        return

    msg_text = event.raw_text or ""
    
    # --- SEARCH PRIORITY ---
    detected_address = None
    
    # 1. Check for DexScreener Link FIRST (Most accurate)
    url_match = re.search(DEX_URL_REGEX, msg_text)
    
    if url_match:
        # group(1) is the part AFTER the slash
        detected_address = url_match.group(1)
        print(f"🔗 Found URL Address: {detected_address}")
        
    else:
        # 2. If no URL, check for Raw Addresses
        sol_match = re.search(SOL_REGEX, msg_text)
        evm_match = re.search(EVM_REGEX, msg_text)
        
        if sol_match:
            detected_address = sol_match.group()
        elif evm_match:
            detected_address = evm_match.group()

    # BRANCH A: Address Detected
    if detected_address:
        try:
            print(f"🔍 Processing: {detected_address}...")
            
            market_data, real_ca = get_token_info(detected_address)
            
            # Fallback if API fails
            final_ca = real_ca if real_ca else detected_address
            header = market_data if market_data else f"**CA:** `{final_ca}`"

            maestro_link = f"https://t.me/MaestroSniperBot?start={final_ca}"
            dex_link = f"https://dexscreener.com/search?q={final_ca}"
            
            new_text = (
                f"{msg_text}\n\n"
                f"{header}\n"
                f"`{final_ca}`\n\n"
                f"🚀 [Buy on Maestro]({maestro_link})  |  📊 [DexScreener]({dex_link})"
            )

            # Media Filter (Block Link Previews)
            media_to_send = event.media
            if isinstance(media_to_send, MessageMediaWebPage):
                media_to_send = None

            await client.send_message(
                DESTINATION_CHAT_ID,
                new_text,
                file=media_to_send,
                reply_to=topic_id,
                link_preview=False 
            )
            return
            
        except Exception as e:
            print(f"⚠️ Error in custom flow: {e}")

    # BRANCH B: Standard Forward
    try:
        await client.forward_messages(DESTINATION_CHAT_ID, event.message, reply_to=topic_id)
    except:
        await client.send_message(DESTINATION_CHAT_ID, event.message, reply_to=topic_id)

with client:
    client.run_until_disconnected()