"""
Google Sheets Exporter
Exports all DB tables to Google Sheets — one tab per table.
Handles auth via service account (credentials.json in project root).

Setup:
    1. Go to console.cloud.google.com
    2. Create project → enable Google Sheets API + Google Drive API
    3. Create Service Account → download JSON as 'credentials.json'
    4. Share your target Google Sheet with the service account email
    5. Add GOOGLE_SHEET_ID to .env
    pip install gspread google-auth

Usage:
    python execution/export_to_sheets.py
"""

import os
import sqlite3
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DB_NAME = "crypto_data.db"
SHEET_ID = os.getenv("GOOGLE_SHEET_ID") or os.getenv("SHEET_ID", "")
CREDENTIALS_FILE = "service.json"

# Tables to export and their display names
TABLES = [
    ("calls",       "📞 Calls"),
    ("re_entries",  "🔁 Re-Entries"),
]


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def get_sheets_client():
    """
    Authenticates with Google Sheets via service account.
    Returns an authenticated gspread client.
    """
    try:
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
        return gspread.authorize(creds)
    except ImportError:
        raise RuntimeError("Missing packages. Run: pip install gspread google-auth")
    except FileNotFoundError:
        raise RuntimeError(f"credentials.json not found. See setup instructions in this file.")


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def fetch_table(table_name):
    """
    Fetches all rows + column headers from a DB table.

    Returns:
        (headers: list[str], rows: list[list]) or ([], []) on error
    """
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {table_name} ORDER BY id DESC")
        rows = cursor.fetchall()
        headers = [d[0] for d in cursor.description]
        conn.close()
        return headers, [list(r) for r in rows]
    except Exception as e:
        logging.error(f"❌ Failed to fetch {table_name}: {e}")
        return [], []


# ---------------------------------------------------------------------------
# Sheet helpers
# ---------------------------------------------------------------------------

def ensure_tab(spreadsheet, tab_name):
    """
    Gets or creates a worksheet tab by name.
    Returns the worksheet.
    """
    try:
        return spreadsheet.worksheet(tab_name)
    except Exception:
        logging.info(f"📝 Creating new tab: {tab_name}")
        return spreadsheet.add_worksheet(title=tab_name, rows=2000, cols=30)


def write_tab(ws, headers, rows):
    """
    Clears and rewrites a worksheet with headers + data.
    """
    ws.clear()

    # Build all data: header row first then data rows
    all_data = [headers] + rows

    # Format None values and datetimes
    cleaned = []
    for row in all_data:
        cleaned_row = []
        for cell in row:
            if cell is None:
                cleaned_row.append("")
            else:
                cleaned_row.append(str(cell))
        cleaned.append(cleaned_row)

    if cleaned:
        ws.update("A1", cleaned)
        # Bold the header row
        ws.format("1:1", {"textFormat": {"bold": True}})

    logging.info(f"✅ Wrote {len(rows)} rows to tab '{ws.title}'")


# ---------------------------------------------------------------------------
# Main export function
# ---------------------------------------------------------------------------

def export_all_tables():
    """
    Exports all tables from the DB to Google Sheets.
    Each table → its own tab. Also writes a summary tab.
    """
    if not SHEET_ID:
        raise ValueError("GOOGLE_SHEET_ID not set in .env")

    logging.info("🔑 Authenticating with Google Sheets...")
    gc = get_sheets_client()

    logging.info(f"📊 Opening spreadsheet {SHEET_ID[:10]}...")
    spreadsheet = gc.open_by_key(SHEET_ID)

    # Export each table
    total_rows = 0
    for table_name, tab_name in TABLES:
        logging.info(f"📦 Exporting {table_name}...")
        headers, rows = fetch_table(table_name)

        if not headers:
            logging.warning(f"⚠️ Skipping {table_name} (empty or error)")
            continue

        ws = ensure_tab(spreadsheet, tab_name)
        write_tab(ws, headers, rows)
        total_rows += len(rows)

    # Write a summary/meta tab
    _write_summary_tab(spreadsheet, total_rows)

    sheet_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"
    logging.info(f"🚀 Export complete! View at: {sheet_url}")
    return sheet_url


def _write_summary_tab(spreadsheet, total_rows):
    """Writes a summary tab with export metadata."""
    ws = ensure_tab(spreadsheet, "📋 Summary")
    ws.clear()

    summary = [
        ["Crypto Calls DB Export"],
        [],
        ["Exported at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        ["Total rows", str(total_rows)],
        [],
        ["Table", "Description"],
        ["📞 Calls", "New token calls — tracked from call time"],
        ["🔁 Re-Entries", "Re-calls for tokens already called from same channel"],
    ]
    ws.update("A1", summary)
    ws.format("A1", {"textFormat": {"bold": True, "fontSize": 14}})
    ws.format("A6:B6", {"textFormat": {"bold": True}})


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if not os.path.exists(CREDENTIALS_FILE):
        print("❌ credentials.json not found!")
        print()
        print("Setup steps:")
        print("  1. Go to https://console.cloud.google.com")
        print("  2. Create a project → enable Sheets API + Drive API")
        print("  3. Create Service Account → Download JSON as 'credentials.json'")
        print("  4. Share your Google Sheet with the service account email")
        print("  5. Add GOOGLE_SHEET_ID=<your_sheet_id> to .env")
        print("  6. pip install gspread google-auth")
        sys.exit(1)

    if not SHEET_ID:
        print("❌ GOOGLE_SHEET_ID not set in .env")
        sys.exit(1)

    try:
        url = export_all_tables()
        print(f"\n✅ Done! View at: {url}")
    except Exception as e:
        print(f"\n❌ Export failed: {e}")
        sys.exit(1)
