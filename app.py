import streamlit as st
import pandas as pd
import altair as alt
from utils.config_manager import ConfigManager
from utils.gsheet import GSheetManager
from utils.config_manager import ConfigManager
from utils.gsheet import GSheetManager
from utils.logo import render_sidebar_logo
from utils.calculations import ComplianceEngine
import uuid

# MUST be the first Streamlit command
st.set_page_config(
    page_title="BCBA Fieldwork Tracker",
    page_icon="assets/favicon.svg",
    layout="wide",
    initial_sidebar_state="expanded"
)

def inject_custom_css():
    st.markdown("""
        <style>
            /* Import Fonts */
            @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Inter:wght@400;600&family=JetBrains+Mono&display=swap');

            /* Headers */
            h1, h2, h3 {
                font-family: 'Playfair Display', serif !important;
                font-weight: 700;
                color: #000000 !important;
                letter-spacing: 1px !important;
            }

            /* Global Text */
            p, div, label, span {
                font-family: 'Inter', sans-serif;
                color: #000000;
            }

            /* Metric/Number styling */
            [data-testid="stMetricValue"] {
                font-family: 'JetBrains Mono', monospace;
                color: #800000; /* Oxblood for numbers */
            }

            /* Progress Bar Color Override */
            .stProgress > div > div > div > div {
                background-color: #800000;
            }

            /* Button Styling - Sharp Corners */
            button {
                border-radius: 0px !important;
                border: 1px solid #000000 !important;
                box-shadow: none !important;
            }
            
            /* Hide Streamlit Branding if possible (optional) */
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            
            /* Remove Streamlit's default top padding to make logo distinct */
            .css-1d391kg { padding-top: 1rem; }
        </style>
    """, unsafe_allow_html=True)

# Inject CSS immediately
inject_custom_css()


# Initialize session state for page navigation if not present
if "page" not in st.session_state:
    st.session_state["page"] = "Home"

# =============================================================================
# AUTHENTICATION (V2: Google OAuth)
# =============================================================================

def check_auth():
    """Authenticate user via Google OAuth or fallback to password.
    
    Returns:
        True if authenticated, False otherwise
    """
    # Check if V2 OAuth is configured
    use_oauth = (
        "google_oauth" in st.secrets 
        and st.secrets["google_oauth"].get("client_id")
        and st.secrets["google_oauth"]["client_id"] != "YOUR_CLIENT_ID.apps.googleusercontent.com"
    )
    
    if use_oauth:
        return _check_oauth()
    else:
        st.error("Google OAuth not configured. Please add [google_oauth] secrets.")
        st.stop()


def _check_oauth():
    """V2: Google OAuth authentication flow."""
    try:
        from auth import GoogleAuthenticator
        from auth.google_oauth import render_user_profile
        
        auth = GoogleAuthenticator(
            client_id=st.secrets["google_oauth"]["client_id"],
            client_secret=st.secrets["google_oauth"]["client_secret"],
            redirect_uri=st.secrets["google_oauth"]["redirect_uri"]
        )
        
        user = auth.require_auth()
        
        if user:
            # User is authenticated - handle user registry
            _handle_user_registry(user)
            return True
        else:
            # Not authenticated - login page is shown by require_auth()
            return False
            
        st.error(f"OAuth module not available: {e}")
        st.stop()
    except Exception as e:
        st.error(f"OAuth error: {e}")
        return False


def _handle_user_registry(user: dict):
    """Handle user registry lookup and provisioning for V2."""
    # Check if registry is configured
    if "registry" not in st.secrets or not st.secrets["registry"].get("sheet_url"):
        # No registry configured - just store user in session
        st.session_state["current_user"] = user
        return
    
    try:
        @st.cache_resource
        def get_registry_connection_v2():
            from utils.user_registry import UserRegistry
            return UserRegistry(st.secrets["registry"]["sheet_url"])
            
        registry = get_registry_connection_v2()
        
        # 1. Lookup User
        user_record = registry.get_user_by_email(user["email"])
        
        if not user_record:
            # 2. New User -> Show Onboarding UI
            _render_onboarding(user, registry)
            
            # Stop execution here (don't load the dashboard yet)
            st.stop()
            
        else:
            # 3. Existing User -> Update Login & Load Context
            if "login_updated" not in st.session_state:
                try:
                    registry.update_last_login(user_record["user_id"])
                    st.session_state["login_updated"] = True
                except Exception:
                    pass # Don't block
            
            st.session_state["current_user"] = user_record
        
    except Exception as e:
        # Non-critical - continue without registry features if partial failure
        # But if we STOPPED in onboarding, we won't get here.
        st.error(f"Registry Error: {e}")
        st.session_state["current_user"] = user

def _render_onboarding(user: dict, registry: object):
    """Render the self-service onboarding flow for new users."""
    
    st.markdown("""
    <style>
    .onboarding-header {
        font-family: 'Playfair Display', serif;
        color: #000000;
        font-size: 2.5rem;
        margin-bottom: 1rem;
    }
    .step-card {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 0px;
        border-left: 5px solid #800000;
        margin-bottom: 1.5rem;
    }
    .step-number {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.9rem;
        color: #800000;
        font-weight: bold;
        text-transform: uppercase;
        margin-bottom: 0.5rem;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="onboarding-header">Welcome to your Tracker</div>', unsafe_allow_html=True)
    
    st.info(f"👋 Hi {user['name']}! Let's get your personal fieldwork tracker set up.")
    
    st.markdown("### Step 1: Create your Sheet")
    st.write("Since this is a privacy-first app, **you own your data**. Create your own tracking sheet from our official template.")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.link_button("📄 Open Template", "https://docs.google.com/spreadsheets/d/1N55aCT-yfz8jMoohVUQ3VWpvecrFCSRcZpj7GVSlbVY/copy", type="primary")
    with col2:
        st.caption("Click 'Make a copy' when prompted.")

    st.divider()

    st.markdown("### Step 2: Share with the App")
    st.write("The app needs permission to read and write to your new sheet.")
    
    sa_email = st.secrets["connections"]["gsheets"].get("client_email", "service@...")
    st.code(sa_email, language="text")
    st.caption("Copy this email, click **Share** in your new Google Sheet, and paste it as an **Editor**.")

    st.divider()

    st.markdown("### Step 3: Link it here")
    st.write("Paste the full URL of your new sheet below so the app can find it.")

    sheet_url = st.text_input("📋 Paste Google Sheet URL", placeholder="https://docs.google.com/spreadsheets/d/...")

    if st.button("🚀 Link My Tracker", type="primary"):
        if not sheet_url:
            st.error("Please paste your Sheet URL first.")
            return

        with st.status("Verifying connection...") as status:
            try:
                # 1. Validate Access
                # We can use the registry's existing gspread client to test access
                gc = registry.client
                try:
                    target_sheet = gc.open_by_url(sheet_url)
                    status.write("✅ Access Verified: Found sheet!")
                except Exception:
                    status.update(label="Access Denied", state="error")
                    st.error("❌ Could not access sheet. Did you share it with the email above?")
                    return

                # 2. Check Tabs (Simple check)
                try:
                    target_sheet.worksheet("Logs")
                    status.write("✅ Format Verified: 'Logs' tab found.")
                except Exception:
                    status.update(label="Invalid Format", state="error")
                    st.error("❌ Invalid Sheet. Please use the official template (missing 'Logs' tab).")
                    return

                # 3. Register User
                status.write("📝 Registering your account...")
                user_record = registry.register_user(
                    email=user["email"],
                    display_name=user["name"],
                    sheet_url=sheet_url,
                    sheet_id=target_sheet.id
                )
                
                status.update(label="Success!", state="complete")
                st.balloons()
                st.success("You are all set! Reloading...")
                import time
                time.sleep(1.5)
                st.rerun()

            except Exception as e:
                status.update(label="Error", state="error")
                st.error(f"Something went wrong: {str(e)}")



# Config Manager initialized later


if check_auth():
    # --- INITIALIZE DATA LAYER (Post-Auth) ---
    user = st.session_state.get("current_user", {})
    sheet_url = user.get("sheet_url")
    
    # Fallback for V1 (Legacy Secrets)
    if not sheet_url:
        # Check secrets for default sheet
        try:
             sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        except:
             pass
             
    if not sheet_url:
        st.error("No Google Sheet connected. Please sign in or check configuration.")
        st.stop()
        
    # Initialize Managers ONLY if not present
    if "config_manager" not in st.session_state:
        gm = GSheetManager(sheet_url)
        st.session_state["gm"] = gm
        st.session_state["config_manager"] = ConfigManager(gm)

    # Retrieve from state
    gm = st.session_state["gm"]
    config_manager = st.session_state["config_manager"]

    # Sidebar Navigation
    render_sidebar_logo()
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Home", "Import Data", "Settings", "Reports", "Privacy", "Help"])
    
    if page == "Home":
        # --- 3A: DASHBOARD VISUALS (FRENCH CLINICAL) ---
        
        # 1. Header & Context
        st.markdown("# 📂 Fieldwork Ledger")
        
        # 2. Metrics / Progress
        
        # OPTIMIZATION: Cache the stats calculation
        @st.cache_data(show_spinner=False)
        def get_cached_stats(df, version, mode):
            engine = ComplianceEngine(ruleset_version=version, mode=mode)
            return engine.calculate_monthly_stats(df)
        
        # Initialize Engine (Default to 2022/Standard for now)
        current_settings = config_manager.settings
        engine = ComplianceEngine(
            ruleset_version=current_settings.get("ruleset_version", "2022"), 
            mode=current_settings.get("mode", "Standard")
        )
        
        # Load Data from Google Sheets
        if "local_logs" not in st.session_state:
             st.session_state["local_logs"] = gm.load_logs()
        
        # Ensure dates are datetime objects for calc
        df_logs = st.session_state["local_logs"]
        if not df_logs.empty:
            # Convert date if needed (handle mixed formats)
            if 'date' in df_logs.columns and not pd.api.types.is_datetime64_any_dtype(df_logs['date']):
                df_logs['date'] = pd.to_datetime(df_logs['date'], format='mixed', errors='coerce')
            
            # Fix energy_rating type (can be int, float, string, or empty)
            if 'energy_rating' in df_logs.columns:
                df_logs['energy_rating'] = pd.to_numeric(df_logs['energy_rating'], errors='coerce')
            
            # Fix duration type
            if 'duration_hours' in df_logs.columns:
                df_logs['duration_hours'] = pd.to_numeric(df_logs['duration_hours'], errors='coerce').fillna(0)
            
            # Fill NaNs in string fields only
            string_cols = ['uid', 'activity_type', 'supervision_type', 'supervisor', 'notes']
            for col in string_cols:
                if col in df_logs.columns:
                    df_logs[col] = df_logs[col].fillna("").astype(str)
            
            st.session_state["local_logs"] = df_logs
            
        stats = get_cached_stats(
            st.session_state["local_logs"],
            current_settings.get("ruleset_version", "2022"),
            current_settings.get("mode", "Standard")
        )
        
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Month Hours", f"{stats.total_hours:.1f}h", delta=f"{stats.hours_needed_for_5_percent:.1f}h to 5%")
        
        # Supervision Calculation (Color Logic)
        sup_delta_color = "normal"
        if stats.is_compliant_supervision:
            sup_delta_color = "inverse" # Green usually
            
        col_m2.metric("Supervision", f"{stats.supervision_percent:.1%}", delta="5% Target", delta_color=sup_delta_color)
        col_m3.metric("Total Fieldwork", f"{stats.total_hours:.1f}h", delta="2000h Goal")
        
        # Linear Progress Bars (Oxblood)
        st.caption("Month Goal Progress")
        
        # Cap progress at 1.0 to avoid error
        prog_val = min(1.0, stats.total_hours / 130.0)
        st.progress(prog_val)
        
        # 3A: VISUALS - Alerts & Heatmap
        
        # Alert System
        if stats.total_hours > 0:
            if not stats.is_compliant_supervision:
                st.warning(f"⚠️ Supervision Ratio Low ({stats.supervision_percent:.1%}). Target: {engine.rules['supervision_ratios'].get(current_settings.get('mode', 'Standard'), 0.05):.0%}")
            
            if not stats.is_compliant_min_hours:
                st.info(f"ℹ️ Minimum Hours Not Met. ({stats.total_hours:.1f} / {engine.rules['monthly_min_hours']})")
                
            if not stats.is_compliant_max_hours:
                st.error(f"🛑 Monthly Maximum Exceeded! ({stats.total_hours:.1f} / {engine.rules['monthly_max_hours']})")
        
        # Calendar Heatmap (Energy Rating)
        st.markdown("### 📅 Energy Pattern")
        
        # Filter for valid energy ratings
        energy_df = st.session_state["local_logs"].dropna(subset=["energy_rating"])
        if not energy_df.empty:
            # Aggregate by date to get one value per day (mean if multiple entries per day)
            daily_energy = energy_df.groupby('date', as_index=False).agg({
                'energy_rating': 'mean'
            })
            
            # Altair Heatmap - Calendar Grid
            energy_chart = alt.Chart(daily_energy).mark_rect(
                stroke='#000000',
                strokeWidth=0.5
            ).encode(
                x=alt.X('date(date):O', axis=alt.Axis(title='Day', labelAngle=0)),
                y=alt.Y('month(date):O', axis=alt.Axis(title='Month', format='%b')),
                color=alt.Color('energy_rating:Q', 
                    scale=alt.Scale(domain=[1, 5], range=['#FFFFFF', '#ffbedb', '#800000']), 
                    legend=alt.Legend(title='Energy')
                ),
                tooltip=[
                    alt.Tooltip('date:T', title='Date', format='%Y-%m-%d'),
                    alt.Tooltip('energy_rating:Q', title='Energy', format='.1f')
                ]
            ).properties(
                height=200
            ).configure_axis(
                grid=False,
                labelFontSize=10,
                titleFontSize=12
            ).configure_view(
                strokeWidth=0
            )
            
            st.altair_chart(energy_chart, width="stretch")
        else:
            st.caption("No energy data yet. Log sessions with 'Energy Level' to see your patterns.")
        
        st.markdown("---")
        
        # --- 3B: DATA ENTRY FORM (TOP-FORM) ---
        st.markdown("### 📝 New Session Entry")
        
        # Container for the form to ensure sharp borders via CSS
        with st.container():
            c1, c2, c3 = st.columns(3)
            
            with c1:
                import datetime as dt
                today = dt.date.today()
                date_input = st.date_input("Date", value=today)
                
            with c2:
                # Smart Defaults for time could go here
                # Feature D: Session Chaining
                # Feature D: Session Chaining & Smart Time Defaults
                if "last_end_time" in st.session_state:
                    default_start = st.session_state["last_end_time"]
                else:
                    # Default to current time, rounded up to next 15 min interval
                    now_dt = dt.datetime.now()
                    # Calculate minutes to add to reach next 15m mark
                    # If minutes % 15 is 0, we can stay or add 15? "Rounding up" usually implies future.
                    # Let's say if we are exactly on :00, :15, :30, :45 stay there? 
                    # User said "closest time, rounding up". 
                    # If 10:01 -> 10:15. If 10:14 -> 10:15. If 10:15 -> 10:15.
                    
                    minutes = now_dt.minute
                    remainder = minutes % 15
                    if remainder == 0:
                         add_minutes = 0
                    else:
                         add_minutes = 15 - remainder
                    
                    rounded = now_dt + dt.timedelta(minutes=add_minutes)
                    # Handle hour overflow (if result is tomorrow, just clamp to 23:45 or wrap? time object handles wrap by just showing time)
                    # But if we go to next day, date input is separate. 
                    # It's fine, we just want the time component.
                    default_start = rounded.time().replace(second=0, microsecond=0)

                # Start Time Input
                # Get Configured Precision
                precision_min = config_manager.settings.get("time_precision", 15)
                try:
                    precision_min = int(precision_min)
                except:
                    precision_min = 15
                
                step_seconds = precision_min * 60

                start_input = st.time_input("Start Time", value=default_start, step=step_seconds)
                
            with c3:
                # Calculate default end time = start + 30 mins
                # Use a dummy date to handle time arithmetic
                dummy_dt = dt.datetime.combine(dt.date.today(), default_start)
                default_end_dt = dummy_dt + dt.timedelta(minutes=30)
                default_end = default_end_dt.time().replace(second=0, microsecond=0)
                
                end_input = st.time_input("End Time", value=default_end, step=step_seconds)
        
            c4, c5, c6 = st.columns(3)
            
            with c4:
                # Enum Maps
                from utils.schema import ActivityType, SupervisionType, LogEntry
                activity_input = st.selectbox("Activity Type", [e.value for e in ActivityType])
                
            with c5:
                supervision_input = st.selectbox("Supervision Type", [e.value for e in SupervisionType])
                
            with c6:
                supervisor_list = config_manager.supervisors
                
                # --- FEATURE D: Smart Defaults Logic ---
                # 1. Determine Default
                default_sup_index = 0
                
                # Get Config
                work_days = config_manager.settings.get("work_days", [])
                start_str = config_manager.settings.get("work_hours_start", "09:00")
                end_str = config_manager.settings.get("work_hours_end", "17:00")
                primary = config_manager.settings.get("primary_supervisor")
                
                # Current Time check
                now = dt.datetime.now()
                current_day_str = now.strftime("%a") # Mon, Tue...
                
                is_work_day = current_day_str in work_days
                
                # Parse times
                try:
                    s_h, s_m = map(int, start_str.split(":"))
                    e_h, e_m = map(int, end_str.split(":"))
                    t_start = dt.time(s_h, s_m)
                    t_end = dt.time(e_h, e_m)
                    current_time = now.time()
                    is_work_hours = t_start <= current_time <= t_end
                except:
                    is_work_hours = False # Fallback
                
                # Logic: If Work Day AND Work Hours -> Primary
                if is_work_day and is_work_hours and primary in supervisor_list:
                    default_sup_index = supervisor_list.index(primary)
                else:
                    # Requirement says: ELSE use most recently used. 
                    # Use Session State to track 'last_used_supervisor'
                    if "last_used_supervisor" in st.session_state and st.session_state["last_used_supervisor"] in supervisor_list:
                         default_sup_index = supervisor_list.index(st.session_state["last_used_supervisor"])
                    elif primary in supervisor_list:
                        # Fallback to primary if no last used
                        default_sup_index = supervisor_list.index(primary)
                        
                supervisor_input = st.selectbox("Supervisor", supervisor_list, index=default_sup_index)

            notes_input = st.text_area("Session Notes", height=68, placeholder="Brief description of activity...")
            
            # --- FEATURE F: LIFE METRICS ---
            energy_input = st.slider("Energy Level (Optional Burnout Tracker)", 1, 5, 3)

            # --- DYNAMIC VALIDATION (AUDIT DEFENSE) ---
            from utils.auditor import Auditor
            
            # Calculate Duration
            # Handle time diffs carefully
            dummy_date = dt.date(2000, 1, 1)
            dt_start = dt.datetime.combine(dummy_date, start_input)
            dt_end = dt.datetime.combine(dummy_date, end_input)
            
            if dt_end < dt_start:
                # Handle overnight ?? For now, just assume error or add day
                duration_seconds = (dt_end + dt.timedelta(days=1) - dt_start).total_seconds()
            else:
                duration_seconds = (dt_end - dt_start).total_seconds()
                
            duration_hours = duration_seconds / 3600
            
            # Real-time Feedback
            st.caption(f"Calculated Duration: **{duration_hours:.2f} hours**")
            
            # Prepare potential entry for auditing
            # Note: We don't have UUID yet, generating temp for check
            pot_entry = LogEntry(
                uid="temp",
                date=date_input,
                start_time=start_input,
                end_time=end_input,
                duration_hours=duration_hours,
                activity_type=ActivityType(activity_input),
                supervision_type=SupervisionType(supervision_input),
                supervisor=supervisor_input,
                energy_rating=energy_input,
                notes=notes_input
            )
            
            # History for Check
            history_df = st.session_state["local_logs"]
            
            # 2B: Run Aggressive Auditor
            is_safe, audit_errors = Auditor.check_save_safety(pot_entry, history_df)
            
            submit_disabled = False
            if not is_safe:
                submit_disabled = True
                for err in audit_errors:
                    st.error(f"🛑 {err}")
            
            # Save Action
            if st.button("LOG SESSION", disabled=submit_disabled, width="stretch"):
                st.success("Session Logged to Google Sheets!")
                
                # Update Smart Defaults
                st.session_state["last_end_time"] = end_input
                st.session_state["last_used_supervisor"] = supervisor_input
                
                # Create Row
                # Convert time objects to strings for storage
                new_entry = {
                    "uid": str(uuid.uuid4()),
                    "date": date_input,
                    "start_time": start_input.strftime("%H:%M:%S"),
                    "end_time": end_input.strftime("%H:%M:%S"),
                    "duration_hours": float(duration_hours),
                    "activity_type": activity_input,
                    "supervision_type": supervision_input, 
                    "supervisor": supervisor_input,
                    "notes": notes_input,
                    "energy_rating": energy_input
                }
                
                new_row = pd.DataFrame([new_entry])
                
                # Append to local
                if st.session_state["local_logs"].empty:
                     st.session_state["local_logs"] = new_row
                else:
                    st.session_state["local_logs"] = pd.concat([st.session_state["local_logs"], new_row], ignore_index=True)
                
                # Save Remote
                gm.save_logs(st.session_state["local_logs"], user_id=user.get("user_id"))

                # Re-calculate stats to check for Celebration
                new_stats = engine.calculate_monthly_stats(st.session_state["local_logs"])
                if new_stats.is_compliant_supervision:
                    st.balloons()
                
                st.rerun()

        st.markdown("---")
        
        # --- RECENT LOGS VIEW ---
        st.markdown("### 📜 Recent Logs")
        st.dataframe(pd.DataFrame(columns=["Date", "Duration", "Type", "Supervisor", "Notes"]), width="stretch")
        
    elif page == "Import Data":
        st.markdown("# 📥 Import Legacy Data")
        st.markdown("Upload your export files from other systems (e.g., Ripley).")
        
        uploaded_file = st.file_uploader("Choose a CSV or Excel file", type=['csv', 'xlsx'])
        
        if uploaded_file is not None:
            try:
                from utils.importer import process_ripley_file
                
                with st.spinner('Processing file...'):
                    df = process_ripley_file(uploaded_file)
                    
                st.success(f"Processing Complete! Found {len(df)} valid entries.")
                
                # Show Preview
                with st.expander("Preview Data", expanded=True):
                    st.dataframe(df.head(10))
                    
                if st.button("Confirm Import (Simulation)"):
                    st.balloons()
                    st.toast("Data would be saved to Google Sheets here!", icon="💾")
                    
            except Exception as e:
                st.error(f"Error processing file: {e}")
                
    elif page == "Settings":
        st.markdown("# ⚙️ Settings")
        
        # --- USER PROFILE ---
        st.markdown("### 👤 User Profile (For PDF)")
        
        with st.container():
            c_p1, c_p2 = st.columns(2)
            with c_p1:
                t_name = st.text_input("Trainee Name", value=config_manager.settings.get("trainee_name", ""))
                if t_name != config_manager.settings.get("trainee_name"):
                    config_manager.update_setting("trainee_name", t_name)
                    
                t_state = st.text_input("State / Province", value=config_manager.settings.get("fieldwork_state", ""))
                if t_state != config_manager.settings.get("fieldwork_state"):
                    config_manager.update_setting("fieldwork_state", t_state)
            
            with c_p2:
                t_id = st.text_input("BACB ID", value=config_manager.settings.get("trainee_id", ""))
                if t_id != config_manager.settings.get("trainee_id"):
                    config_manager.update_setting("trainee_id", t_id)
                    
                t_country = st.text_input("Country", value=config_manager.settings.get("fieldwork_country", "USA"))
                if t_country != config_manager.settings.get("fieldwork_country"):
                    config_manager.update_setting("fieldwork_country", t_country)
        
        st.markdown("---")

        # --- COMPLIANCE SETTINGS ---
        st.markdown("### 📋 Compliance Rules")
        
        with st.container():
            c_s1, c_s2 = st.columns(2)
            with c_s1:
                # Load available versions from JSON file (or hardcode for now if file read fails, but Engine handles it)
                # Ideally we'd read keys from bacb_requirements.json
                # For now, we know them: 2022, 2027
                import json
                
                # Try to load keys dynamocially
                # (We could move this load to ConfigManager to be cleaner, but okay here for now)
                
                current_ver = config_manager.settings.get("ruleset_version", "2022")
                new_ver = st.selectbox(
                    "Ruleset Version", 
                    ["2022", "2027"], 
                    index=["2022", "2027"].index(current_ver) if current_ver in ["2022", "2027"] else 0
                )
                
                if new_ver != current_ver:
                    config_manager.update_setting("ruleset_version", new_ver)
                    st.rerun()

            with c_s2:
                current_mode = config_manager.settings.get("mode", "Standard")
                new_mode = st.selectbox(
                    "Fieldwork Type", 
                    ["Standard", "Concentrated"], 
                    index=0 if current_mode == "Standard" else 1
                )
                
                if new_mode != current_mode:
                    config_manager.update_setting("mode", new_mode)
                    st.rerun()
                    
        st.markdown("---")

        # --- SUPERVISOR MANAGEMENT ---
        st.markdown("### 🧑‍🏫 Supervisors")
        
        # Add New
        c_add1, c_add2 = st.columns([3, 1])
        with c_add1:
            new_sup_name = st.text_input("Add Supervisor Name", label_visibility="collapsed", placeholder="Enter Name...")
        with c_add2:
            if st.button("Add Supervisor", width="stretch"):
                if new_sup_name:
                    config_manager.add_supervisor(new_sup_name)
                    st.rerun()
        
        # List Existing
        st.write("Current Supervisors:")
        for sup in config_manager.supervisors:
            c_row1, c_row2 = st.columns([4, 1])
            with c_row1:
                st.info(sup, icon="👤")
            with c_row2:
                if st.button("Remove", key=f"del_{sup}", width="stretch"):
                    config_manager.remove_supervisor(sup)
                    st.rerun()
        
        
        # --- TIME PRECISION ---
        st.markdown("### ⏱️ Time Precision")
        c_time1, c_time2 = st.columns(2)
        with c_time1:
            current_precision = config_manager.settings.get("time_precision", 15)
            # Ensure it's an int
            try:
                current_precision = int(current_precision)
            except:
                current_precision = 15
                
            new_precision = st.selectbox(
                "Time Input Step (Minutes)", 
                [1, 5, 15, 30],
                index=[1, 5, 15, 30].index(current_precision) if current_precision in [1, 5, 15, 30] else 2,
                help="Controls the granularity of the time dropdowns."
            )
            
            if new_precision != current_precision:
                config_manager.update_setting("time_precision", new_precision)
                st.rerun()

        st.markdown("---")
        
        # --- PRIMARY SUPERVISOR & SMART DEFAULTS ---
        st.markdown("### 🌟 Smart Defaults")
        
        c_smart1, c_smart2 = st.columns(2)
        
        with c_smart1:
            current_primary = config_manager.settings.get("primary_supervisor", "")
            valid_supers = config_manager.supervisors
            
            idx = 0
            if current_primary in valid_supers:
                idx = valid_supers.index(current_primary)
                
            new_primary = st.selectbox("Primary Supervisor", valid_supers, index=idx)
            if new_primary != current_primary:
                config_manager.update_setting("primary_supervisor", new_primary)

            # Work Days
            current_days = config_manager.settings.get("work_days", [])
            all_days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            new_days = st.multiselect("Work Days", all_days, default=current_days)
            if new_days != current_days:
                config_manager.update_setting("work_days", new_days)
                st.rerun()

        with c_smart2:
            # Time Range
            s_str = config_manager.settings.get("work_hours_start", "09:00")
            e_str = config_manager.settings.get("work_hours_end", "17:00")
            
            # Convert to time objects for input
            import datetime as dt
            try:
                t_s = dt.time(*map(int, s_str.split(":")))
                t_e = dt.time(*map(int, e_str.split(":")))
            except:
                t_s = dt.time(9, 0)
                t_e = dt.time(17, 0)
            
            new_start = st.time_input("Work Hours Start", value=t_s)
            new_end = st.time_input("Work Hours End", value=t_e)
            
            # Save back as strings
            ns_str = new_start.strftime("%H:%M")
            ne_str = new_end.strftime("%H:%M")
            
            if ns_str != s_str:
                config_manager.update_setting("work_hours_start", ns_str)
                st.rerun()
            if ne_str != e_str:
                config_manager.update_setting("work_hours_end", ne_str)
                st.rerun()

    elif page == "Reports":
        st.markdown("# 📄 Reports & Verification")
        st.markdown("Generate official BACB Monthly Verification Forms.")
        
        # --- PDF GENERATION UI ---
        
        with st.container():
            c_r1, c_r2, c_r3 = st.columns(3)
            
            with c_r1:
                import datetime as dt
                today = dt.date.today()
                # Month Selection
                months = ["January", "February", "March", "April", "May", "June", 
                          "July", "August", "September", "October", "November", "December"]
                selected_month = st.selectbox("Month", months, index=today.month - 1)
                
            with c_r2:
                # Year Selection
                years = [today.year - 1, today.year, today.year + 1]
                selected_year = st.selectbox("Year", years, index=1)
                
            with c_r3:
                # Supervisor Selection
                # Must accept 'All' or specific? Form requires ONE supervisor.
                # So we list supervisors.
                supers = config_manager.supervisors
                selected_super = st.selectbox("Responsible Supervisor", supers)
        
        # Filter Data for this Month/Year/Supervisor
        # Mock Data load (replace with real GS load later)
        if "local_logs" not in st.session_state:
            st.session_state["local_logs"] = pd.DataFrame(columns=["date", "duration_hours", "supervision_type", "supervisor", "energy_rating"])
            
        df = st.session_state["local_logs"]
        
        if not df.empty:
            # Ensure date is datetime
            if not pd.api.types.is_datetime64_any_dtype(df['date']):
                df['date'] = pd.to_datetime(df['date'])
            
            # Filter
            month_idx = months.index(selected_month) + 1
            mask = (df['date'].dt.month == month_idx) & \
                   (df['date'].dt.year == selected_year) & \
                   (df['supervisor'] == selected_super)
                   
            filtered_df = df.loc[mask]
        else:
            filtered_df = df # empty
            
        # Preview Stats
        st.info(f"Found {len(filtered_df)} entries for {selected_month} {selected_year} under {selected_super}.")
        
        if not filtered_df.empty:
            # Calculate Stats
            from utils.calculations import ComplianceEngine
            current_settings = config_manager.settings
            engine = ComplianceEngine(
                ruleset_version=current_settings.get("ruleset_version", "2022"), 
                mode=current_settings.get("mode", "Standard")
            )
            
            stats = engine.calculate_monthly_stats(filtered_df)
            
            # Show Mini Summary
            c_sum1, c_sum2, c_sum3 = st.columns(3)
            c_sum1.metric("Total Hours", f"{stats.total_hours:.2f}")
            c_sum2.metric("Supervised", f"{stats.supervised_hours:.2f}")
            c_sum3.metric("Indep.", f"{stats.independent_hours:.2f}")
            
            # Generate Button
            if st.button("Generate PDF Verification Form", width="stretch"):
                from utils.pdf_maker import PDFGenerator
                
                gen = PDFGenerator()
                try:
                    pdf_bytes = gen.generate_verification_form(
                        stats=stats,
                        config=current_settings,
                        month_year_str=f"{selected_month} {selected_year}",
                        supervisor_name=selected_super
                    )
                    
                    st.success("PDF Generated Successfully!")
                    st.download_button(
                        label="⬇️ Download PDF",
                        data=pdf_bytes,
                        file_name=f"Verification_{selected_month}_{selected_year}.pdf",
                        mime="application/pdf"
                    )
                    
                except Exception as e:
                    st.error(f"Error generating PDF: {e}")
        else:
            st.warning("No data found for this selection. Cannot generate report.")

    elif page == "Privacy":
        st.markdown("# 🔒 Privacy Ledger")
        st.markdown("### Transparency Report")
        
        st.write("""
        This application operates on a **"Bring Your Own Data"** model. 
        Unlike traditional SaaS products, we do not host a central database of your fieldwork logs.
        """)
        
        st.markdown("#### 1. Data Ownership")
        st.success("""
        **You own your data.** All fieldwork logs are stored in a private Google Sheet that *you* create and control. 
        The application is simply a logic layer that calculates your hours.
        """)
        
        st.markdown("#### 2. Data Isolation")
        st.write("""
        - **Your Sheet:** Contains your specialized 5th Edition Fieldwork Logs.
        - **Our Access:** The application uses a Service Account to read/write to your sheet *only while you are using the app*.
        - **Revocation:** You can revoke access at any time by removing the Service Account email from your Google Sheet's "Share" settings.
        """)
        
        st.markdown("#### 3. Security & Audit Trail")
        st.write("""
        To ensure security and prevent abuse, we maintain a minimal **Master Registry** containing:
        - **User Identity:** Email and internal UUID.
        - **Linkage:** The URL of your personal tracking sheet.
        - **Audit Logs:** Timestamps of logins and account creation events.
        """)
        
        st.warning("We DO NOT store or log any client names, PHI (Protected Health Information), or specific session notes in our central registry.")

    elif page == "Help":
        st.markdown("# ❓ Setup & FAQ")
        
        st.markdown("---")
        
        # --- GOOGLE SHEETS SETUP ---
        st.markdown("## 📊 Google Sheets Setup (REQUIRED)")
        st.warning("You MUST complete this setup before the app can save your data!")
        
        # Two paths: tabs for Automatic vs Manual
        setup_method = st.radio(
            "Choose your setup method:",
            ["🚀 Automatic (Recommended)", "🔧 Manual"],
            horizontal=True
        )
        
        if setup_method == "🚀 Automatic (Recommended)":
            st.markdown("### Step 1: Download the Template Files")
            st.markdown("Click the buttons below to download pre-configured CSV templates:")
            
            col_dl1, col_dl2 = st.columns(2)
            
            # Load and offer Logs template
            with col_dl1:
                try:
                    with open("docs/template_logs.csv", "r") as f:
                        logs_csv = f.read()
                    st.download_button(
                        label="⬇️ Download Logs Template",
                        data=logs_csv,
                        file_name="template_logs.csv",
                        mime="text/csv"
                    )
                except:
                    st.error("Logs template not found")
            
            # Load and offer Config template
            with col_dl2:
                try:
                    with open("docs/template_config.csv", "r") as f:
                        config_csv = f.read()
                    st.download_button(
                        label="⬇️ Download Config Template",
                        data=config_csv,
                        file_name="template_config.csv",
                        mime="text/csv"
                    )
                except:
                    st.error("Config template not found")
            
            st.markdown("### Step 2: Create Your Google Sheet")
            st.markdown("""
            1.  Go to [Google Sheets](https://sheets.google.com) and sign in.
            2.  Click **"+ Blank"** to create a new spreadsheet.
            3.  **Name it** `BACB Fieldwork Tracker` (top-left corner).
            """)
            
            st.markdown("### Step 3: Import the Templates")
            st.markdown("""
            **For the Logs tab:**
            1.  Rename the default "Sheet1" tab to exactly: `Logs`
            2.  Go to **File → Import**
            3.  Click **Upload** and select `template_logs.csv`
            4.  Choose **"Replace current sheet"** and click **Import data**
            
            **For the Config tab:**
            1.  Click the **+** button to create a new tab, name it exactly: `Config`
            2.  Go to **File → Import**
            3.  Click **Upload** and select `template_config.csv`
            4.  Choose **"Replace current sheet"** and click **Import data**
            """)
            
            st.success("✅ Your sheet is now properly formatted with all required columns and default settings!")
            
        else:  # Manual
            st.markdown("### Step 1: Create Your Google Sheet")
            st.markdown("""
            1.  Go to [Google Sheets](https://sheets.google.com) and sign in with your Google Account.
            2.  Click **"+ Blank"** to create a new spreadsheet.
            3.  **Name it** something like `BACB Fieldwork Tracker` (top-left corner).
            4.  **Create TWO tabs** (worksheets) at the bottom of the sheet:
                *   **Tab 1:** Rename the default "Sheet1" to exactly: `Logs`
                *   **Tab 2:** Click the `+` button to add a new tab. Name it exactly: `Config`
            """)
            
            st.info("💡 **Tip:** The tab names are case-sensitive. Make sure they are exactly `Logs` and `Config`.")
            
            st.markdown("### Step 2: Set Up the `Logs` Tab Schema")
            st.markdown("In the **`Logs`** tab, create headers in **Row 1**. Copy these column headers exactly:")
            st.code("uid | date | start_time | end_time | duration_hours | activity_type | supervision_type | supervisor | notes | energy_rating", language=None)
            st.markdown("""
            *   **uid:** A unique ID for each entry (auto-generated by the app).
            *   **date:** The date of the session (YYYY-MM-DD).
            *   **start_time / end_time:** Session times (HH:MM:SS).
            *   **duration_hours:** Calculated hours (e.g., 1.5).
            *   **activity_type:** "Restricted" or "Unrestricted".
            *   **supervision_type:** "None", "Individual", or "Group".
            *   **supervisor:** Name of your supervisor.
            *   **notes:** Optional session notes.
            *   **energy_rating:** Optional burnout tracker (1-5).
            """)
            
            st.markdown("### Step 3: Set Up the `Config` Tab Schema")
            st.markdown("In the **`Config`** tab, create headers in **Row 1**:")
            st.code("Category | Key | Value", language=None)
            st.markdown("This tab stores your supervisors and settings. The app will populate it automatically, but having the headers is required.")
        
        st.markdown("---")
        
        # --- SERVICE ACCOUNT SHARING ---
        st.markdown("## 🔐 Share Your Sheet with the App (CRITICAL)")
        st.error("If you skip this step, the app CANNOT access your sheet!")
        
        st.markdown("### What is a Service Account?")
        st.markdown("""
        A **Service Account** is like a robot email address that the app uses to read and write to your sheet.
        It does NOT have access to your entire Google Drive—only the specific sheets you share with it.
        """)
        
        st.markdown("### How to Share:")
        st.markdown("""
        1.  **Find the Service Account Email:**
            *   `service@bcba-fieldwork-tracker-sem.iam.gserviceaccount.com`
        """)
        
        # Copyable email
        st.code("service@bcba-fieldwork-tracker-sem.iam.gserviceaccount.com", language=None)
        
        st.markdown("""
        2.  **Open your Google Sheet** (the one you just created).
        3.  Click the **"Share"** button (top-right, green button).
        4.  **Paste the Service Account email** above into the "Add people and groups" field.
        5.  Set the permission to **"Editor"** (not Viewer!).
        6.  **Uncheck** "Notify people" (service accounts can't receive emails).
        7.  Click **"Share"**.
        """)
        
        st.success("✅ Once shared, the app will automatically load and save data to YOUR personal sheet!")
        
        st.markdown("### Troubleshooting Sharing Issues")
        with st.expander("Error: 'Could not connect to Sheet'"):
            st.markdown("""
            *   **Check the email:** Make sure you copied the full Service Account email (it's long!).
            *   **Check permissions:** The Service Account needs **Editor** access, not Viewer.
            *   **Check the Sheet URL:** In the app's configuration, the spreadsheet URL must match YOUR sheet.
            *   **Refresh:** After sharing, wait a few seconds and refresh the app.
            """)
        
        with st.expander("Error: 'Worksheet not found: Logs'"):
            st.markdown("""
            *   Your sheet is missing the `Logs` tab.
            *   Create a tab named **exactly** `Logs` (case-sensitive).
            *   Do the same for `Config`.
            """)
        
        st.markdown("---")
        
        # --- COPY SHEET URL ---
        st.markdown("## 📋 Get Your Sheet URL")
        st.markdown("""
        The app needs to know which sheet is yours. Here's how to get the URL:
        
        1.  Open your Google Sheet.
        2.  Look at the browser address bar. The URL looks like:
        """)
        st.code("https://docs.google.com/spreadsheets/d/1aBcDeFgHiJkLmNoPqRsTuVwXyZ/edit", language=None)
        st.markdown("""
        3.  Copy the **entire URL**.
        4.  Provide this URL to the app administrator to configure the connection.
        """)
        
        st.markdown("---")
        
        # --- QUICK START ---
        st.markdown("## 🚀 Quick Start (After Setup)")
        st.markdown("""
        Once your sheet is connected:
        
        1.  **Go to Settings** → Add your Supervisor(s).
        2.  **Set your Work Hours** → This enables Smart Defaults.
        3.  **Fill in your User Profile** → Required for PDF generation (name, BACB ID, location).
        4.  **Log your first session** on the Home page!
        5.  **Check your Google Sheet** → You should see the data appear in the `Logs` tab!
        """)
        
        st.markdown("---")
        
        # --- FAQ ---
        st.markdown("### 📖 Frequently Asked Questions")
        
        with st.expander("How does my data stay private?"):
            st.markdown("""
            Your data lives in **your own personal Google Sheet**. 
            This app connects to it using a secure Service Account, but the data never leaves your Google Drive. 
            No patient information (PHI) should ever be entered—only activity types, supervisors, and hours.
            """)
        
        with st.expander("What is the 5% Supervision Rule?"):
            st.markdown("""
            The BACB requires that at least **5% of your total fieldwork hours** must be supervised (individual or group).
            The dashboard tracks this automatically and will celebrate 🎈 when you meet the goal for the month!
            """)
        
        with st.expander("What's the difference between Restricted and Unrestricted?"):
            st.markdown("""
            * **Restricted:** Direct therapeutic delivery with clients.
            * **Unrestricted:** Analytical work like assessments, training, or report writing (the "gold" hours).
            
            You need a mix of both, and the Concentrated pathway has different ratio requirements.
            """)
        
        with st.expander("Why can't I save my session? (Red Error)"):
            st.markdown("""
            The **Audit Detector** blocks saves that could trigger a BACB audit flag:
            * Sessions over **12 hours** are flagged as "Superhuman."
            * Sessions that **overlap** with existing entries are flagged as "Time Traveler."
            
            Edit your entry to fix the issue, and the Save button will re-enable.
            """)
        
        with st.expander("How do I generate my Monthly Verification Form?"):
            st.markdown("""
            1.  Go to the **Reports** page.
            2.  Select the Month, Year, and Supervisor.
            3.  Click **"Generate PDF Verification Form"**.
            4.  Download the PDF and submit it to your supervisor for signature.
            
            **Note:** The "Energy Level" (burnout tracker) data is **never** included in exports.
            """)
        
        with st.expander("What are Smart Defaults?"):
            st.markdown("""
            Smart Defaults reduce data entry friction:
            * **Supervisor:** If it's a work day during work hours, it defaults to your Primary Supervisor.
            * **Start Time:** Defaults to the end time of your last logged session (session chaining).
            * **Date:** Defaults to today.
            
            Configure these in **Settings → Smart Defaults**.
            """)
        
        st.markdown("---")
        
        # --- GLOSSARY ---
        st.markdown("### 📚 Glossary")
        st.dataframe({
            "Term": ["BACB", "BCBA", "Fieldwork", "Supervision Ratio", "Concentrated Pathway", "Monthly Verification Form"],
            "Definition": [
                "Behavior Analyst Certification Board (the organization).",
                "Board Certified Behavior Analyst (the certification).",
                "Supervised experience hours required for certification.",
                "The percentage of fieldwork hours that must be supervised.",
                "An accelerated training pathway with higher supervision requirements.",
                "The official BACB document summarizing your monthly hours for supervisor sign-off."
            ]
        }, hide_index=True, width="stretch")
        
        st.markdown("---")
        
        # --- LINKS ---
        st.markdown("### 🔗 Useful Links")
        st.markdown("""
        * [BACB Official Website](https://www.bacb.com/)
        * [BACB Experience Standards](https://www.bacb.com/bcba/bcba-requirements/)
        * [Streamlit Documentation](https://docs.streamlit.io/)
        """)

