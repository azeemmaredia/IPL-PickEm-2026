import gspread

gc = gspread.service_account(filename='secrets.json')
sh = gc.open("IPL_PickEm_DB")
schedule_sheet = sh.worksheet("Match_Schedule_Results")

print("--- DEBUGGING START ---")
all_rows = schedule_sheet.get_all_records()

for i, row in enumerate(all_rows):
    status = row.get('Status', 'NOT FOUND')
    winner = row.get('Winner', 'NOT FOUND')
    print(f"Row {i+2}: Match {row.get('Match_ID')} | Status: '{status}' | Winner: '{winner}'")

print("--- DEBUGGING END ---")