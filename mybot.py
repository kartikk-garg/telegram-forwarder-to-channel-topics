import os
import json
import subprocess
import asyncio
from dotenv import load_dotenv
from telethon import TelegramClient, events

# --- CONFIG ---
load_dotenv()
api_id = int(os.getenv('API_ID'))
api_hash = os.getenv('API_HASH')
bot_token = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))

if not bot_token or not ADMIN_ID:
    print("❌ Error: Missing BOT_TOKEN or ADMIN_ID in .env")
    exit(1)

bot = TelegramClient('admin_session', api_id, api_hash).start(bot_token=bot_token)
CONFIG_FILE = 'config.json'

def load_config():
    with open(CONFIG_FILE, 'r') as f: return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, 'w') as f: json.dump(data, f, indent=4)

async def is_admin(event):
    if event.sender_id != ADMIN_ID:
        await event.respond("⛔ Access Denied.")
        return False
    return True

# --- COMMANDS ---

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    if not await is_admin(event): return
    await event.respond(
        "**🤖 CryptoBot Commander**\n\n"
        "1️⃣ `/restart` - Restart Service\n"
        "2️⃣ `/add <channel_id> <topic_id>` - Add Channel\n"
        "3️⃣ `/report` - Run Report (Safe Mode)\n"
        "4️⃣ `/settings` - View Config"
    )

@bot.on(events.NewMessage(pattern='/restart'))
async def restart_service(event):
    if not await is_admin(event): return
    msg = await event.respond("🔄 Restarting...")
    try:
        subprocess.run(["sudo", "systemctl", "restart", "cryptobot"], check=True)
        await msg.edit("✅ **Service Restarted!**")
    except Exception as e:
        await msg.edit(f"❌ Error: `{e}`")

@bot.on(events.NewMessage(pattern='/report'))
async def generate_report(event):
    if not await is_admin(event): return
    msg = await event.respond("⏳ **Generating Report...**\n_(Pausing Forwarder to release lock)_")
    
    try:
        # 1. Stop Forwarder (Release DB Lock)
        subprocess.run(["sudo", "systemctl", "stop", "cryptobot"], check=True)
        
        # 2. Run Reporter
        result = subprocess.run(
            ["/home/ubuntu/telegram_forwarder/venv/bin/python3", "reporter.py"], 
            capture_output=True, text=True
        )
        
        # 3. Restart Forwarder
        subprocess.run(["sudo", "systemctl", "start", "cryptobot"], check=True)
        
        if result.returncode == 0:
            await msg.edit("✅ **Report Sent!**\nService resumed.")
        else:
            await msg.edit(f"❌ **Reporter Failed:**\n`{result.stderr[-500:]}`")
            
    except Exception as e:
        subprocess.run(["sudo", "systemctl", "start", "cryptobot"]) # Safety restart
        await msg.edit(f"❌ Error: `{e}`")

@bot.on(events.NewMessage(pattern=r'/add (-?\d+) (-?\d+)'))
async def add_channel(event):
    if not await is_admin(event): return
    try:
        cid = int(event.pattern_match.group(1))
        tid = int(event.pattern_match.group(2))
        data = load_config()
        data['topics'][str(cid)] = tid
        save_config(data)
        subprocess.run(["sudo", "systemctl", "restart", "cryptobot"], check=True)
        await event.respond(f"✅ Added `{cid}` -> Topic `{tid}`\nBot Restarted.")
    except Exception as e:
        await event.respond(f"❌ Error: `{e}`")

@bot.on(events.NewMessage(pattern='/settings'))
async def show_settings(event):
    if not await is_admin(event): return
    data = load_config()
    t_list = "\n".join([f"• `{k}` ➔ `{v}`" for k, v in data['topics'].items()])
    await event.respond(f"**Settings**\n\n**Dest:** `{data['destination_id']}`\n{t_list}")

print("🤖 Admin Bot Listening...")
bot.run_until_disconnected()