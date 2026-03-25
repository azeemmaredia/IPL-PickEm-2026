import streamlit as st
import gspread
import pandas as pd
import time
from datetime import datetime
import requests

# --- 1. SETTINGS & CLOUD DATABASE CONNECT ---
# The site uses your RapidAPI key to fetch scores
RAPIDAPI_KEY = "676f0b3707msh73bee328eb66010p111aa6jsn5a146c1321cb"

# The Translation Brain
TEAM_MAPPING = {
    "RCB": "Royal Challengers Bengaluru",
    "CSK": "Chennai Super Kings",
    "MI": "Mumbai Indians",
    "KKR": "Kolkata Knight Riders",
    "SRH": "Sunrisers Hyderabad",
    "RR": "Rajasthan Royals",
    "DC": "Delhi Capitals",
    "PBKS": "Punjab Kings",
    "GT": "Gujarat Titans",
    "LSG": "Lucknow Super Giants",
    "NZW": "New Zealand Women",
    "RSAW": "South Africa Women"
}

try:
    gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
    sh = gc.open("IPL_PickEm_DB")
    picks_sheet = sh.worksheet("User_Picks")
    leaderboard_sheet = sh.worksheet("Users_Leaderboard")
    schedule_sheet = sh.worksheet("Match_Schedule_Results")
except Exception as e:
    st.error("Database Connection Failed. Check your Streamlit Secrets!")
    st.stop()

# --- 2. ZERO-TOUCH AUTO UPDATER ---
# ttl=300 means this function is only allowed to run ONCE every 5 minutes.
@st.cache_data(ttl=300, show_spinner=False)
def fetch_live_scores_from_cloud():
    url = "https://cricbuzz-cricket.p.rapidapi.com/matches/v1/live"
    try:
        headers = {
            "X-RapidAPI-Key": RAPIDAPI_KEY,
            "X-RapidAPI-Host": "cricbuzz-cricket.p.rapidapi.com"
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200: return False
        
        data = response.json()
        matches_found = []
        
        for match_type in data.get('typeMatches', []):
            for series in match_type.get('seriesMatches', []):
                wrapper = series.get('seriesAdWrapper', series)
                if isinstance(wrapper, dict) and 'matches' in wrapper:
                    for match_obj in wrapper['matches']:
                        match_info = match_obj.get('matchInfo', {})
                        m_id = str(match_info.get('matchId', ''))
                        t1 = match_info.get('team1', {}).get('teamSName', '')
                        t2 = match_info.get('team2', {}).get('teamSName', '')
                        status = match_info.get('status', 'In Progress')
                        
                        if m_id:
                            full_t1 = TEAM_MAPPING.get(t1, t1)
                            full_t2 = TEAM_MAPPING.get(t2, t2)
                            matches_found.append({'id': m_id, 'team1': full_t1, 'team2': full_t2, 'status': status})
        
        all_rows = schedule_sheet.get_all_records()
        updates = []
        for i, row in enumerate(all_rows):
            sheet_row = i + 2
            sheet_home = str(row.get('Home_Team', '')).strip()
            sheet_away = str(row.get('Away_Team', '')).strip()
            current_api_id = str(row.get('API_Match_ID', '')).strip()
            
            for m in matches_found:
                teams_match = (m['team1'] in [sheet_home, sheet_away]) and (m['team2'] in [sheet_home, sheet_away])
                if teams_match or (current_api_id == m['id']):
                    updates.append({'range': f'G{sheet_row}', 'values': [[m['status']]]})
                    if not current_api_id:
                        updates.append({'range': f'J{sheet_row}', 'values': [[m['id']]]})
                    break # Move to next sheet row
                    
        if updates: 
            schedule_sheet.batch_update(updates)
        return True
    except Exception as e:
        return False

# 🚨 TRIGGER THE AUTO-UPDATER EVERY TIME SOMEONE LOADS THE PAGE
fetch_live_scores_from_cloud()


# --- 3. PAGE SETUP & UI ---
st.set_page_config(page_title="IPL Pick'Em 2026", page_icon="🏏", layout="wide")

st.markdown("""
    <style>
    .stMetric { background-color: #f8f9fa; padding: 20px; border-radius: 15px; border: 1px solid #e9ecef; }
    div.stButton > button:first-child { border-radius: 10px; height: 3em; transition: all 0.3s ease; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. APP MEMORY (SESSION STATE) ---
if 'username' not in st.session_state:
    st.session_state.username = None
if 'auth_view' not in st.session_state:
    st.session_state.auth_view = "Login"

# --- 5. LANDING PAGE (LOGIN / REGISTER) ---
if st.session_state.username is None:
    st.title("🏏 IPL 2026 Advanced Pick'Em")
    st.write("### Sign in to manage your league picks")
    
    col1, col2, _ = st.columns([1, 1, 2])
    
    with col1:
        login_type = "primary" if st.session_state.auth_view == "Login" else "secondary"
        if st.button("🔒 GO TO LOGIN", type=login_type, use_container_width=True):
            st.session_state.auth_view = "Login"
            st.rerun()
            
    with col2:
        reg_type = "primary" if st.session_state.auth_view == "Register" else "secondary"
        if st.button("📝 NEW ACCOUNT", type=reg_type, use_container_width=True):
            st.session_state.auth_view = "Register"
            st.rerun()
    
    st.divider()

    if st.session_state.auth_view == "Login":
        st.subheader("Account Login")
        with st.form("login_form"):
            login_user = st.text_input("Username:")
            login_pass = st.text_input("Password:", type="password")
            submit_login = st.form_submit_button("ENTER ARENA ➔", use_container_width=True)
            
            if submit_login:
                with st.spinner("Authenticating..."):
                    users_data = leaderboard_sheet.get_all_records()
                    user_rec = next((item for item in users_data if str(item.get("User_Name", "")) == login_user), None)
                    if user_rec and str(user_rec.get("Password", "")) == login_pass:
                        st.session_state.username = login_user
                        st.success("Access Granted!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Invalid Username or Password.")

    elif st.session_state.auth_view == "Register":
        st.subheader("Create New Profile")
        with st.form("register_form"):
            new_user = st.text_input("Choose Username:")
            new_pass = st.text_input("Choose Password:", type="password")
            confirm_pass = st.text_input("Confirm Password:", type="password")
            submit_register = st.form_submit_button("CREATE & JOIN LEAGUE ➔", use_container_width=True)
            
            if submit_register:
                if new_pass != confirm_pass:
                    st.error("Passwords do not match!")
                elif not new_user or not new_pass:
                    st.warning("All fields are required.")
                else:
                    with st.spinner("Creating profile..."):
                        existing = leaderboard_sheet.col_values(1)
                        if new_user in existing:
                            st.error("Username already taken!")
                        else:
                            leaderboard_sheet.append_row([new_user, new_pass, 0, 5])
                            st.success(f"Account Created for {new_user}!")
                            time.sleep(1)
                            st.session_state.username = new_user
                            st.rerun()

# --- 6. MAIN APP (LOGGED IN VIEW) ---
else:
    st.sidebar.title(f"👤 {st.session_state.username}")
    if st.sidebar.button("Logout"):
        st.session_state.username = None
        st.session_state.auth_view = "Login"
        st.rerun()
        
    page = st.sidebar.radio("Navigation", ["📊 Dashboard", "🎯 Make Picks", "🏆 Leaderboard", "📜 Rules & Schedule"])
    
    if page == "📊 Dashboard":
        st.title("Player Dashboard")
        lb_data = leaderboard_sheet.get_all_records()
        stats = next((item for item in lb_data if str(item.get("User_Name", "")) == st.session_state.username), None)
        all_picks = picks_sheet.get_all_records()
        sch_data = schedule_sheet.get_all_records()
        user_picks = [p for p in all_picks if str(p.get('User_Name', '')) == st.session_state.username]
        
        projected_pts = 0
        live_matches = [m for m in sch_data if str(m.get("Status", "")).strip() in ["Live", "In Progress"]]
        for m in live_matches:
            match_pick = next((p for p in user_picks if p['Match_ID'] == m['Match_ID']), None)
            if match_pick and str(match_pick['Predicted_Winner']) == str(m['Winner']):
                val = 20 if str(match_pick['Used_PowerPlay']).lower() == 'true' else 10
                projected_pts += val

        if stats:
            m1, m2, m3 = st.columns(3)
            m1.metric("🏆 Season Points", stats.get("Total_Points", 0))
            m2.metric("⚡ Power Plays Left", stats.get("Power_Plays_Remaining", 0))
            m3.metric("📈 Live Projection", f"+{projected_pts}")
        
        st.divider()
        st.subheader("🔴 Match Center")
        if live_matches:
            for m in live_matches:
                with st.container(border=True):
                    st.markdown(f"#### 🏏 {m['Home_Team']} vs {m['Away_Team']} - <span style='color:red'>LIVE</span>", unsafe_allow_html=True)
                    st.info(f"**Live Update:** {m.get('Win_Method', 'Match in progress...')}")
        else:
            st.info("No matches live right now.")
        
        st.divider()
        st.subheader("📝 Your Pick History")
        if user_picks:
            for p in reversed(user_picks):
                with st.container(border=True):
                    pp = "✅ Yes" if str(p.get('Used_PowerPlay', '')).lower() == 'true' else "❌ No"
                    t_runs = p.get('Tiebreaker_Runs') if p.get('Tiebreaker_Runs') else p.get('Tiebreaker', 0)
                    st.markdown(f"**Match:** `{p.get('Match_ID', 'N/A')}`")
                    c1, c2, c3 = st.columns(3)
                    c1.write(f"🏆 **Winner:** {p.get('Predicted_Winner')}")
                    c2.write(f"⚡ **Power Play:** {pp}")
                    c3.write(f"🔢 **Tiebreaker:** {t_runs} runs")

    elif page == "🎯 Make Picks":
        st.title("Tournament Predictions")
        picks = picks_sheet.get_all_records()
        user_match_ids = [p['Match_ID'] for p in picks if str(p.get('User_Name', '')) == st.session_state.username]
        sch = schedule_sheet.get_all_records()
        upcoming = [m for m in sch if str(m.get("Status", "")) == "Upcoming"]
        
        if not upcoming:
            st.success("No upcoming matches!")
        else:
            for m in upcoming:
                mid = m['Match_ID']
                with st.container(border=True):
                    st.subheader(f"🏏 {m['Home_Team']} vs {m['Away_Team']} ({m['Date']})")
                    if mid in user_match_ids:
                        st.success("✅ Pick recorded.")
                    with st.form(f"form_{mid}"):
                        winner = st.radio("Who wins?", [m['Home_Team'], m['Away_Team']], key=f"r_{mid}")
                        pp = st.checkbox("Use Power Play?", key=f"p_{mid}")
                        tie = st.number_input("Tiebreaker: Total Runs", min_value=0, max_value=600, value=300, key=f"t_{mid}")
                        if st.form_submit_button("Lock Pick"):
                            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            row_idx = None
                            for i, p in enumerate(picks):
                                if str(p.get('User_Name', '')) == st.session_state.username and str(p.get('Match_ID', '')) == mid:
                                    row_idx = i + 2
                                    break
                            if row_idx:
                                picks_sheet.update(values=[[ts, st.session_state.username, mid, winner, str(pp), tie]], range_name=f'A{row_idx}:F{row_idx}')
                            else:
                                picks_sheet.append_row([ts, st.session_state.username, mid, winner, str(pp), tie])
                            st.rerun()

    elif page == "🏆 Leaderboard":
        st.title("Rankings")
        t_season, t_weekly = st.tabs(["Season Standings", "Weekly Winners"])
        with t_season:
            lb = leaderboard_sheet.get_all_records()
            if lb:
                df = pd.DataFrame(lb).drop(columns=['Password'], errors='ignore')
                df = df.sort_values(by="Total_Points", ascending=False)
                st.dataframe(df, use_container_width=True, hide_index=True)
        with t_weekly:
            st.info("Weekly King results appear here after grading!")

    elif page == "📜 Rules & Schedule":
        st.title("League Information")
        with st.expander("📖 View Official Rules"):
            st.write("- Winner: +10 pts | PP Win: +20 pts | PP Loss: -5 pts")
        sch_all = schedule_sheet.get_all_records()
        if sch_all:
            st.dataframe(pd.DataFrame(sch_all), use_container_width=True, hide_index=True)
