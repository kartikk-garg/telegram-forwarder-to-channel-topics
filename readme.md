# 🚀 Solana Crypto Call Forwarder & Analyzer (V2)

A professional-grade Telegram automation engine designed to detect, analyze, and track Solana crypto calls across multiple alpha channels.

---

## ✨ Key Features

*   **⚡ Hybrid Data Enrichment**: Combines **Solana Tracker** (Deep Risk/Bundler Analysis) and **DexScreener** (Real-time Prices/Media) for the most accurate call data.
*   **📊 81-Column Deep Storage**: Every call captures ~81 data points including Risk Scores, Sniper activity, Insider holdings, and Trading Bot fees (GMGN, Trojan, etc.).
*   **🎯 Smart Forwarding**: Automatically routes calls from source channels to specific "Topic IDs" in your destination group.
*   **👀 24/7 Price Watcher**: Monitors every call for 7 days. Tracks peak multipliers, handles rug detection, and updates PnL in real-time.
*   **📈 Alpha Leaderboards**: Automatically generates weekly reports on channel performance (Win Rate, Avg Peak, Rug Rate).
*   **📗 Google Sheets Sync**: One-click export of your entire call history to a multi-tabbed Google Spreadsheet.

---

## 🏗 System Architecture (3-Layer Design)

This project follows a modular 3-layer architecture for maximum stability and easy "Skill Integration" with agents like **OpenClaw**:

1.  **Directives**: SOPs for bot operations.
2.  **Orchestration**: Lightweight scripts (`forwarder.py`, `watcher.py`, `reporter.py`) that handle the logic flow.
3.  **Execution**: A heavy-duty "Skill Engine" in `execution/` that handles APIs, Database, and UI Formatting.

---

## 🚀 Quick Setup

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
2.  **Configure Environment**:
    Fill in your `.env` (API Keys) and `config.json` (Channels/Topics).
3.  **Initialize Database**:
    ```bash
    python setup_db.py
    ```
4.  **Run the Engine**:
    ```bash
    # Start the forwarder
    python forwarder.py
    # Start the price watcher (separate process)
    python watcher.py
    ```

> [!NOTE]
> For a deep dive into the technical architecture, deployment on **AWS/Oracle Cloud**, and **OpenClaw** integration, see the **[HANDOVER.md](HANDOVER.md)**.

---

## 💎 Message UI (Premium Layout)
The bot generates high-fidelity, clean Telegram messages with:
- **Condensed Risk Scores** (Score, Top10, Bundlers, Snipers).
- **Price Change Timeframes** (1m to 24h).
- **Bot Activity Signals** (SOL volume spent by GMGN, Padre, BullX, etc.).
- **Quick Links** to Maestro and DexScreener.

---

## 🛠 Maintenance & Deployment
The project is optimized for **Ubuntu** and **Oracle Linux (RHEL)**. It includes pre-configured `systemd` service templates for 24/7 persistent operation. 

> [!IMPORTANT]
> **Security First**: The `HANDOVER.md` now includes a **Secured Firewall Policy** specifically for Oracle Cloud. Do NOT leave your ports wide open!

---
*Created by Antigravity AI for Kartikk's Crypto Arsenal.*
