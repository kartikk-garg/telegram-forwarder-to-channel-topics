# Project Handover: Crypto Call Forwarder & Analyzer (V2)

This document serves as the complete technical handover for the 3-layer crypto call system.

## 🏗 System Architecture (The 3-Layer Logic)

The project follows a strict separation of concerns to ensure modularity and ease of maintenance:

1.  **Directives (SOPs)**: Located in `directives/`. Markdown files documenting the "Standard Operating Procedures" for each bot function. Useful for AI agents or humans to understand *how* the logic should flow.
2.  **Orchestration (The Brains)**: Top-level scripts (`forwarder.py`, `watcher.py`, `reporter.py`). These are "thin" wrappers that coordinate between the user (Telegram) and the execution logic. They do not contain API calls or complex math.
3.  **Execution (The Tools)**: Located in `execution/`. Modular Python scripts that handle specific tasks: API fetching, Database I/O, Message Formatting, AI Analysis.

---

## 🔁 Complete Process Flow

1.  **Detection**: `forwarder.py` listens to Telegram. Regex finds a Solana CA.
2.  **Enrichment (Hybrid Strategy)**:
    *   **DexScreener**: Fetches Banner, Logo, Socials, and **1h Volume**.
    *   **Solana Tracker**: Fetches "Deep Data" (~55 fields) including Risk Score, Bundlers, Snipers, Insiders, and specific Trading Bot activity.
3.  **Validation**: `db_operations.py` checks for spam (2hr cooldown) and re-entries (same CA from same channel).
4.  **Storage**: Enriched data is flattened and saved into an **81-column wide table** in SQLite.
5.  **Output**: `format_message.py` builds a clean, premium Telegram message with dividers and condensed risk/bot signals.
6.  **Persistence**: `export_to_sheets.py` periodically syncs the entire DB to a 10-tab Google Sheet for analysis.

---

## 📂 Module Breakdown

### 1. Orchestration Layer

#### `forwarder.py`
- **Input**: New Telegram message in monitored channels.
- **Output**: Formatted message sent to destination and stored in DB.
- **Key Logic**: Merges DexScreener (Media) + Solana Tracker (Risk) data into a single flat dict.

#### `watcher.py`
- **Input**: Active rows from `calls` and `re_entries` tables.
- **Output**: DB updates for `current_price`, `max_price`, and `is_rug` status.
- **Triage Mode**: Checks "young" tokens every minute, "mid" every 5, and "old" every 30 to save API resources.

#### `reporter.py`
- **Input**: Last 7 days of DB data.
- **Output**: A "Leaderboard" message summarizing channel performance (Win Rate, Rug Rate, Peak Multipliers).

### 2. Execution Layer (`execution/`)

#### `fetch_solana_tracker.py`
- **Function**: `get_full_token_data(ca)`
- **Input**: Token Mint Address (str).
- **Return**: Flat dict with ~55 fields (Token Info, Risk, Bot Fees, Graduates).
- **Unique Logic**: Selects primary pool by highest liquidity; normalizes timestamps; detects backfilled price events.

#### `fetch_dexscreener.py`
- **Function**: `search_token(ca)`
- **Input**: Token Mint Address (str).
- **Return**: Media URLs, Socials, and 1h Volume breakdown.
- **Batching**: `fetch_prices_batch(addresses)` allows the watcher to check 30 tokens in a single request.

#### `db_operations.py`
- **Function**: `insert_call(conn, data)`
- **Input**: Flat dict of ~75 fields.
- **Logic**: Handles the heavy lifting of mapping API fields to the 81 DB columns. Returns a "TAG" (`🆕 NEW CALL` or `🔁 RE-ENTRY`).

#### `format_message.py`
- **Function**: `build_call_message(...)`
- **Output**: High-fidelity Telegram Markdown.
- **Design**: Uses modular sub-functions (e.g., `build_risk_line`, `build_fees_line`) to keep the layout clean and adaptable.

#### `export_to_sheets.py`
- **Input**: All SQLite tables.
- **Output**: Google Sheets update.
- **Setup**: Requires `service.json` and `SHEET_ID` in `.env`.

---

## 📊 Database Schema (V2 - 81 Columns)

The project uses a **denormalized (flat) table** design for the `calls` table. This means *all data point available at call time* is stored in a single row.

**Core Categories stored:**
- **Token Metadata**: name, symbol, creation time, description, creator wallet.
- **Market Stats**: price, mcap, total vs primary liquidity, graduated status, holders.
- **Price Action**: 1m, 5m, 15m, 30m, 1h, 6h, 24h changes.
- **Deep Risk**: Risk Score (1-10), Rug flag, Top10 %, Dev %, Bundler count & initial %, Sniper dump status.
- **Bot Signals**: Detailed SOL spend by GMGN, Photon, Trojan, Axiom, etc.
- **Watcher Progress**: entry vs max vs current price, peak multiplier, rug detection.

---

## 🛠 Operation & Maintenance

- **Adding a Channel**: Update `config.json` with the channel ID and its corresponding Topic ID.
- **Database Upgrades**: Use `db_upgrade.py` if you ever add new columns.
- **Spam Control**: Controlled via `settings` table (default 2-hour cooldown per token per channel).
- **Environment**: Keep `.env` and `service.json` secure.

---

## 🌐 VPC / EC2 Deployment Guide (Ubuntu)

Follow these steps to deploy the project on a remote Linux server (e.g., AWS EC2, DigitalOcean).

### 1. Server Preparation
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-venv screen git -y
```

### 2. Project Setup
```bash
# Clone and enter directory
git clone <your-repo-url>
cd cryptocalls

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
Upload your `.env`, `config.json`, and `service.json` to the server root.
Ensure `SESSION_NAME` in `forwarder.py` and `reporter.py` is consistent or use a persistent `.session` file.

### 4. Running the Bot (Persistence)

You have two options for keeping the bot running:

#### Option A: Using Screen (Quick & Manual)
```bash
# Create a session for the forwarder
screen -S forwarder
source venv/bin/activate
python forwarder.py
# Press Ctrl+A, then D to detach
```

#### Option B: Systemd (Professional & Auto-Restart)
Create a service file: `sudo nano /etc/systemd/system/crypto-forwarder.service`
```ini
[Unit]
Description=Crypto Call Forwarder
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/cryptocalls
ExecStart=/home/ubuntu/cryptocalls/venv/bin/python forwarder.py
Restart=always

[Install]
WantedBy=multi-user.target
```
Then enable and start:
```bash
sudo systemctl enable crypto-forwarder
sudo systemctl start crypto-forwarder
```

---

## ☁️ Oracle Cloud Infrastructure (OCI) Deployment Guide

Deploying on Oracle Cloud (OCI) is similar to AWS but follows a different naming convention.

### 1. Networking (VCN Setup)
1.  Go to **Networking > Virtual Cloud Networks**.
2.  Use **Start VCN Wizard** > **Create VCN with Internet Connectivity**.
3.  This creates a Public Subnet, an Internet Gateway, and a Default Security List.

### 2. Create Compute Instance
1.  Go to **Compute > Instances > Create Instance**.
2.  **Image**: Choose **Ubuntu 22.04** (Recommended) or Oracle Linux.
3.  **Shape**: `VM.Standard.E4.Flex` (Always Free eligible) or `VM.Standard.A1.Flex` (ARM).
4.  **Networking**: Select the VCN and Public Subnet created above.
5.  **SSH Keys**: Generate or upload your public key (`.pub`). **Save the private key!**

### 3. Server Access & Firewall
1.  **SSH**:
    *   If Ubuntu: `ssh -i <private_key> ubuntu@<public_ip>`
    *   If Oracle Linux: `ssh -i <private_key> opc@<public_ip>`
2.  **Oracle Linux (OPC) Server Preparation**:
    ```bash
    sudo dnf update -y
    sudo dnf install python3 python3-pip git screen -y
    ```
3.  **OCI Secured Firewall (REQUIRED)**:
    Do **NOT** leave your firewall wide open. Use these commands to allow only what's necessary:
    ```bash
    # 1. Install iptables-services
    sudo dnf install iptables-services -y
    
    # 2. Reset to a safe baseline
    sudo iptables -F
    sudo iptables -P INPUT DROP
    sudo iptables -P FORWARD DROP
    sudo iptables -P OUTPUT ACCEPT # Allow the bot to talk to APIs
    
    # 3. Allow established connections (Critical for return traffic)
    sudo iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
    
    # 4. Allow Loopback (Internal communication)
    sudo iptables -A INPUT -i lo -j ACCEPT
    
    # 5. Allow SSH (Port 22) - Change this to your specific IP if possible
    sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT
    
    # 6. Save and Enable
    sudo service iptables save
    sudo systemctl enable iptables
    sudo systemctl restart iptables
    ```
    *Note: If you run OpenClaw or other services, only open the specific ports they require (e.g., 8000 for a web UI).*

### 4. Bot Setup & Persistence
Follow the **Project Setup** and **Running the Bot** steps from the EC2 guide above. Note: use `dnf` instead of `apt` for any package installs.

---

## 🛠 OpenClaw Integration & GitHub Workflow

To allow **OpenClaw** (or any agentic framework) to leverage your project as a "Skill Engine," follow this recommended setup.

### 1. Recommended Directory Structure
On your OCI/OPC server, keep things organized:
```text
/home/ubuntu/
├── openclaw/             # Your agent framework
└── scripts/
    └── cryptocalls/      # This project (The Skill Engine)
```

### 2. GitHub Sync Workflow
Since you push from your local machine to GitHub and pull on OPC:

1.  **Local**: `git add .`, `git commit`, `git push origin main`
2.  **Server**: 
    ```bash
    cd /home/ubuntu/scripts/cryptocalls
    git pull origin main
    sudo systemctl restart crypto-forwarder
    ```

### 3. OpenClaw "Skill" Integration
OpenClaw can use your `execution/` layer as modular skills. 

**Option A: The Symlink (Recommended)**
Link your execution folder directly into OpenClaw's workspace so it "sees" your functions:
```bash
ln -s /home/ubuntu/scripts/cryptocalls/execution /home/ubuntu/openclaw/skills/crypto_skills
```

**Option B: Python Path**
Tell OpenClaw where your code is by adding it to the environment:
```bash
export PYTHONPATH=$PYTHONPATH:/home/ubuntu/scripts/cryptocalls
```

### 4. Why this works for OpenClaw:
- **Modular Entrypoints**: OpenClaw doesn't need to run the whole bot. It can just import `get_full_token_data` from your `execution` layer to perform a "Search" or "Analyze" task.
- **Clean Handover**: By keeping the logic in `execution/`, you've created a "Library" that OpenClaw can use without needing to understand Telegram or WebSockets.

---

## 🗄 Database Migration (AWS to OCI)

Since the project uses **SQLite**, migrating the database is as simple as copying a single file.

### Step 1: Stop the Bot on AWS
Ensure no new data is being written:
```bash
sudo systemctl stop crypto-forwarder
```

### Step 2: Transfer the Database
You can use `scp` (Secure Copy) to move the file directly between servers OR use your local machine as a middleman.

**Method A: Local Machine as Middleman (Easiest)**
1.  **From Local Terminal**: Download from AWS
    ```bash
    scp -i "aws_key.pem" ubuntu@<aws_ip>:/home/ubuntu/scripts/cryptocalls/crypto_data.db ./crypto_data.db
    ```
2.  **From Local Terminal**: Upload to OCI
    ```bash
    scp -i "oci_key.pem" ./crypto_data.db ubuntu@<oci_ip>:/home/ubuntu/scripts/cryptocalls/crypto_data.db
    ```

**Method B: Direct Server-to-Server (Fastest)**
From the AWS server:
```bash
scp -i "oci_key.pem" crypto_data.db ubuntu@<oci_ip>:/home/ubuntu/scripts/cryptocalls/
```

### Step 3: Verify & Start on OCI
Once the file is on OCI, check the row count:
```bash
sqlite3 crypto_data.db "SELECT count(*) FROM calls;"
```
Then start the bot:
```bash
sudo systemctl start crypto-forwarder
```

---

## 🔧 Production Hardening (V3)

### 1. SQLite WAL Mode (Concurrency Fix)
Running `forwarder.py` and `watcher.py` concurrently causes `database is locked` errors under load. WAL mode fixes this:
```python
# Automatically enabled in get_connection()
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA synchronous=NORMAL")
conn.execute("PRAGMA cache_size=10000")
```
**After deploying**, run the V3 migration to enable WAL permanently:
```bash
python db_upgrade.py
```

### 2. Watcher Crash Recovery
The watcher now records `last_checked_at` per row. On restart, it resumes efficiently instead of re-checking everything:
- **`last_checked_at`**: Unix timestamp of last successful price check.
- **`check_failures`**: Incremented on API errors for that token.
- On restart, only tokens not checked in the last 60 seconds are re-queried.

### 3. Peak Timing Analytics
The watcher now tracks **when** peaks happen (not just the value):
- **`peak_hit_at`**: Unix timestamp when the highest price was recorded.
- **`time_to_peak_hours`**: Hours from call entry to peak.
- **`time_to_2x_hours`**: Hours to first reach 2x (null if never). This is your most valuable AI training feature.

### 4. Idempotent Google Sheets Sync
`export_to_sheets.py` now uses a cursor (`last_sheet_sync_row_id` in the `settings` table).
- **Default**: Incremental sync (only new rows since last export).
- **Full re-sync**: `python execution/export_to_sheets.py --full`

### 5. Message Metadata Capture
The forwarder now stores the raw Telegram message and extracts structured metadata for AI training:
| Column | Purpose |
|---|---|
| `raw_message_text` | Full original message for retroactive AI scoring |
| `message_has_tweet_link` | Boolean: contains twitter.com or x.com |
| `extracted_tweet_url` | First detected tweet URL |
| `message_has_media` | Boolean: has attached images/video |

---

## ⚠️ Known Issues & Tips

1.  **Telethon Media**: Sending many images at once can sometimes trigger a `MediaInvalid` or Flood error. The `forwarder.py` has a fallback logic to switch to text-only if the album fails.
2.  **API Rate Limits**: Solana Tracker is sensitive. The client includes 3-second sleep buffers on 429 errors.
3.  **DexScreener Lag**: Prices can be 30-60s behind on-chain events. Use Solana Tracker for high-frequency pricing if needed.

