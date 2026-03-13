"""
Reporter — Thin Orchestrator (V3)
Generates and sends enhanced weekly leaderboard to Telegram.
Includes: call frequency, speed score, best call of the week.
"""

import os
import json
import asyncio
from dotenv import load_dotenv
from telethon import TelegramClient

# --- Execution Layer Imports ---
from execution.db_operations import get_connection, get_leaderboard, get_best_call
from execution.format_message import build_report_message

# --- CONFIG ---
load_dotenv()
api_id = int(os.getenv('API_ID'))
api_hash = os.getenv('API_HASH')

with open('config.json', 'r') as f:
    config = json.load(f)

DESTINATION_ID = config['destination_id']
GENERAL_TOPIC_ID = config.get('general_topic_id', 1)
SESSION_NAME = 'crypto_session'


async def send_report():
    client = TelegramClient(SESSION_NAME, api_id, api_hash)
    await client.start()

    # 1. QUERY: Get leaderboard + best call
    conn = get_connection()
    rows = get_leaderboard(conn, days=7, limit=15)
    best = get_best_call(conn, days=7)
    conn.close()

    # 2. FORMAT: Build enhanced message
    msg = build_report_message(rows, best_call=best)

    # 3. SEND: To Telegram
    try:
        await client.send_message(DESTINATION_ID, msg, reply_to=GENERAL_TOPIC_ID)
        print("✅ Enhanced Report sent to Telegram!")
    except Exception as e:
        print(f"❌ Failed to send: {e}")

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(send_report())
