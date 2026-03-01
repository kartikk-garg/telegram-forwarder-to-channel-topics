"""
Forwarder — Thin Orchestrator (V2)
Listens for Telegram messages, detects token CAs, enriches with full
Solana Tracker + DexScreener data, logs to DB, forwards formatted messages.

All business logic lives in execution/.
"""

import os
import json
import re
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.tl.types import MessageMediaWebPage

# --- Execution Layer ---
from execution.fetch_dexscreener import search_token
from execution.fetch_solana_tracker import get_full_token_data
from execution.db_operations import get_connection, insert_call
from execution.format_message import build_call_message

# --- CONFIG ---
load_dotenv()
api_id = int(os.getenv('API_ID'))
api_hash = os.getenv('API_HASH')

with open('config.json', 'r') as f:
    config = json.load(f)

DESTINATION_CHAT_ID = config['destination_id']
TOPIC_MAP = {int(k): v for k, v in config['topics'].items()}
SESSION_NAME = 'local_test'

# --- REGEX ---
ALL_PATTERNS = r'(?:dexscreener\.com\/[\w-]+\/)?([1-9A-HJ-NP-Za-km-z]{32,44}|0x[a-fA-F0-9]{40})'

# --- INIT ---
conn = get_connection()
client = TelegramClient(SESSION_NAME, api_id, api_hash)

print("🚀 Smart Forwarder V2 Running...")

@client.on(events.NewMessage(chats=list(TOPIC_MAP.keys())))
async def handler(event):
    source_id = event.chat_id
    topic_id = TOPIC_MAP.get(source_id)
    msg_text = event.raw_text or ""

    # --- Reply context ---
    reply_context = ""
    if event.is_reply:
        try:
            reply_msg = await event.get_reply_message()
            if reply_msg and reply_msg.text:
                reply_context = f"\n\n↩️ **Replied to:**\n_{reply_msg.text[:400]}_"
        except:
            pass

    # --- Find tokens ---
    found_tokens = set(re.findall(ALL_PATTERNS, msg_text))

    if not found_tokens:
        try:
            await client.send_message(DESTINATION_CHAT_ID, event.message, reply_to=topic_id)
            print(f"📨 Copied non-token msg from {source_id}")
        except Exception as e:
            print(f"⚠️ Copy Error: {e}")
        return

    # --- Get channel name ---
    try:
        entity = await client.get_entity(source_id)
        ch_name = entity.title
    except:
        ch_name = f"ID_{source_id}"

    # --- Process each token ---
    for ca in found_tokens:
        try:
            # 1. DEXSCREENER: Get banner, logo, socials (lightweight)
            dex_data = search_token(ca)
            if not dex_data:
                continue

            final_ca = dex_data['real_ca']

            # 2. SOLANA TRACKER: Get FULL token data (~55 fields)
            st_data = get_full_token_data(final_ca)

            # 3. MERGE: Solana Tracker is primary, DexScreener adds media/socials/1h volume
            call_data = {
                **st_data,           # All 55 fields from Solana Tracker
                'ca': final_ca,      # Ensure correct CA
                'real_ca': final_ca,
                'channel_id': source_id,
                'channel_name': ch_name,
                # DexScreener-only fields (media + socials)
                'banner': dex_data.get('banner'),
                'logo': dex_data.get('logo'),
                'websites': dex_data.get('websites', []),
                'socials': dex_data.get('socials', []),
                # DexScreener provides the 1h volume breakdown
                'vol_h1': dex_data.get('vol_h1', 0),
                'vol_mcap_ratio': dex_data.get('vol_mcap_ratio', 0), # This is 1h ratio from DexScreener
            }

            # Use DexScreener price/mcap as fallback if Solana Tracker returned 0
            if call_data['price'] == 0 and dex_data['price'] > 0:
                call_data['price'] = dex_data['price']
                call_data['mcap'] = dex_data['mcap']
                call_data['liquidity'] = dex_data['liquidity']

            # 4. DB: Insert with all enriched data
            call_tag = insert_call(conn, call_data)
            if not call_tag:
                continue

            # 5. FORMAT: Build message
            final_msg = build_call_message(
                call_tag, ch_name, call_data,
                original_text=msg_text, reply_context=reply_context
            )

            # 6. SEND: Forward with media
            media_files = []
            if event.media and not isinstance(event.media, MessageMediaWebPage):
                media_files.append(event.media)
            if call_data.get('banner'):
                media_files.append(call_data['banner'])
            if call_data.get('logo'):
                media_files.append(call_data['logo'])

            if media_files:
                try:
                    await client.send_message(
                        DESTINATION_CHAT_ID, final_msg,
                        file=media_files if len(media_files) > 1 else media_files[0],
                        reply_to=topic_id, link_preview=False
                    )
                    print(f"✅ {call_data['symbol']} from {ch_name} | "
                          f"Risk:{call_data['risk_score']} Bundlers:{call_data['bundler_count']} "
                          f"Holders:{call_data['holders']} ({len(media_files)} media)")
                except Exception as e:
                    print(f"⚠️ Album failed: {e}, fallback")
                    try:
                        sent_msg = await client.send_message(
                            DESTINATION_CHAT_ID, final_msg,
                            file=media_files[0], reply_to=topic_id, link_preview=False
                        )
                        for media in media_files[1:]:
                            try:
                                await client.send_message(
                                    DESTINATION_CHAT_ID, file=media,
                                    reply_to=sent_msg.id, link_preview=False
                                )
                            except:
                                pass
                    except:
                        await client.send_message(
                            DESTINATION_CHAT_ID, final_msg,
                            reply_to=topic_id, link_preview=False
                        )
            else:
                await client.send_message(
                    DESTINATION_CHAT_ID, final_msg,
                    reply_to=topic_id, link_preview=False
                )
                print(f"✅ {call_data['symbol']} from {ch_name} (text only)")

        except Exception as e:
            print(f"⚠️ Handler Error: {e}")

with client:
    client.run_until_disconnected()