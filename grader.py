import gspread

# --- 1. CONNECT TO DATABASE ---
print("Connecting to database...")
gc = gspread.service_account(filename='secrets.json')
sh = gc.open("IPL_PickEm_DB")
picks_sheet = sh.worksheet("User_Picks")
leaderboard_sheet = sh.worksheet("Users_Leaderboard")
schedule_sheet = sh.worksheet("Match_Schedule_Results")

def calculate_scores():
    # Load all data
    picks = picks_sheet.get_all_records()
    schedule = schedule_sheet.get_all_records()
    users = leaderboard_sheet.get_all_records()

    # Create a map of completed match results and actual runs
    results_map = {}
    for m in schedule:
        if str(m.get('Status', '')).strip() == 'Completed':
            results_map[str(m['Match_ID'])] = {
                'winner': str(m['Winner']).strip(),
                'actual_runs': int(m.get('Actual_Total_Runs', 0))
            }
    
    if not results_map:
        print("❌ No completed matches found.")
        return

    # Initialize scores
    user_scores = {str(u['User_Name']): {'points': 0, 'pp_left': 5, 'tie_diff': 999} for u in users}

    # Calculate points and tiebreaker closeness
    for pick in picks:
        user = str(pick['User_Name'])
        match_id = str(pick['Match_ID'])
        predicted = str(pick['Predicted_Winner']).strip()
        used_pp = str(pick['Used_PowerPlay']).lower() == 'true'
        user_tie = int(pick.get('Tiebreaker_Runs', 0))

        if match_id in results_map:
            actual = results_map[match_id]
            
            # 1. Points Logic
            if predicted == actual['winner']:
                if used_pp:
                    user_scores[user]['points'] += 20
                    user_scores[user]['pp_left'] -= 1
                else:
                    user_scores[user]['points'] += 10
            else:
                if used_pp:
                    user_scores[user]['points'] -= 5
                    user_scores[user]['pp_left'] -= 1
            
            # 2. Tiebreaker Logic (Closeness to actual runs)
            diff = abs(actual['actual_runs'] - user_tie)
            # We track the smallest difference for the week
            if diff < user_scores[user]['tie_diff']:
                user_scores[user]['tie_diff'] = diff

    # Determine Weekly Winner (Example for Match 1)
    weekly_winner = min(user_scores, key=lambda x: (-user_scores[x]['points'], user_scores[x]['tie_diff']))

    # Prepare data for upload
    updated_rows = []
    for u in users:
        name = str(u['User_Name'])
        pwd = u['Password']
        pts = user_scores[name]['points']
        pp = user_scores[name]['pp_left']
        updated_rows.append([name, pwd, pts, pp])

    # --- UPLOAD ---
    print("Pushing updates...")
    leaderboard_sheet.batch_clear(["C2:D100"]) 
    leaderboard_sheet.update(range_name='A2', values=updated_rows, value_input_option='RAW')
    
    print(f"✅ Grading Complete!")
    print(f"🏆 Weekly Winner (based on tiebreaker): {weekly_winner}")

if __name__ == "__main__":
    calculate_scores()