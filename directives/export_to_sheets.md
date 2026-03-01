# Export to Google Sheets

Exports all database tables to a Google Sheets spreadsheet, one tab per table.

## Prerequisites (one-time setup)

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create project → enable **Google Sheets API** + **Google Drive API**
3. Create a **Service Account** → Download JSON → save as `credentials.json` in project root
4. Create a blank Google Sheet → copy its ID from the URL:
   - `https://docs.google.com/spreadsheets/d/`**`THIS_PART`**`/edit`
5. **Share** the sheet with the service account email (from `credentials.json` → `client_email`)
6. Add to `.env`: `GOOGLE_SHEET_ID=your_sheet_id_here`
7. `pip install gspread google-auth`

## Steps

1. **Fetch data** from DB
   - Script: `execution/export_to_sheets.py`
   - Function: `fetch_table(table_name)` → headers + rows for each table

2. **Open spreadsheet** using service account credentials

3. **Write each table** to its own tab
   - Tab names: `📞 Calls`, `🔁 Re-Entries`
   - Clears tab first, then writes header row (bolded) + data rows

4. **Write summary tab** `📋 Summary` with export timestamp + row counts

5. **Return sheet URL** for confirmation

## Run

```bash
python execution/export_to_sheets.py
```

## Edge Cases

- **Missing credentials.json**: Script will print setup instructions and exit.
- **Missing GOOGLE_SHEET_ID**: Will exit with clear error.
- **Empty table** (e.g. re_entries): Skips that tab silently.
- **Rate limits**: gspread handles Google's 100 req/100s limit automatically.
