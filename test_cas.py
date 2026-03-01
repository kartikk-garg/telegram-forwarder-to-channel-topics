
import asyncio
from execution.fetch_solana_tracker import get_full_token_data
from execution.db_operations import get_connection, insert_call
from execution.fetch_dexscreener import search_token
from execution.format_message import build_call_message
from execution.export_to_sheets import export_all_tables

CAS = [
    "FjRVgPYUjvwkfEnjL6QBBWfcVVLeZDKBnxsxWBTrpump",
    "48f42bcMWE2AHmHQYNQU9cHq94hBC4WWMhvekX3tpump",
    "2x5jFDMsgj1cyKHMofnAD4jfS6exTXEAftRb8ozgpump",
    "DPwhfb4GoVsC3hqSNipi9bkGhT5VLDKh7TZQHmonpump"
]

def test_cas():
    conn = get_connection()
    for ca in CAS:
        print(f"\n🚀 Testing CA: {ca}")
        
        # 1. Enrich
        dex_data = search_token(ca)
        st_data = get_full_token_data(ca)
        
        # 2. Merge
        call_data = {
            **st_data,
            'ca': ca,
            'channel_id': 99999,
            'channel_name': 'Manual Test',
            'websites': dex_data.get('websites', []) if dex_data else [],
            'socials': dex_data.get('socials', []) if dex_data else [],
            'banner': dex_data.get('banner') if dex_data else None,
            'logo': dex_data.get('logo') if dex_data else None,
        }
        
        # 3. Insert
        tag = insert_call(conn, call_data)
        print(f"Result: {tag}")
        
        # 4. Preview
        msg = build_call_message(tag, "Manual Test", call_data)
        print("-" * 30)
        print(msg)
        print("-" * 30)

    print("\n📊 Updating Google Sheets...")
    export_all_tables()
    print("✅ All done!")

if __name__ == "__main__":
    test_cas()
