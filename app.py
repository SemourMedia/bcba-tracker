import streamlit as st
import pandas as pd
import altair as alt
from utils.config_manager import ConfigManager
from utils.data_manager import DataManager
import uuid

# MUST be the first Streamlit command
st.set_page_config(
    page_title="BACB Fieldwork Tracker",
    page_icon="📊",
    layout="centered"
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
        </style>
    """, unsafe_allow_html=True)

# Inject CSS immediately
inject_custom_css()


# Initialize session state for page navigation if not present
if "page" not in st.session_state:
    st.session_state["page"] = "Home"

# Initialize Config Manager
config_manager = ConfigManager()

def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets["APP_PASSWORD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.text_input(
            "Please enter the access password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        st.text_input(
            "Please enter the access password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        # Password correct.
        return True

if check_password():
    # Sidebar Navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Home", "Import Data", "Settings", "Reports", "Help"])
    
    if page == "Home":
        # --- 3A: DASHBOARD VISUALS (FRENCH CLINICAL) ---
        
        # 1. Header & Context
        st.markdown("# 📂 Fieldwork Ledger")
        
        # 2. Metrics / Progress
        from utils.calculations import ComplianceEngine
        
        # Initialize Engine (Default to 2022/Standard for now)
        # Initialize Engine (Default to 2022/Standard for now)
        current_settings = config_manager.settings
        engine = ComplianceEngine(
            ruleset_version=current_settings.get("ruleset_version", "2022"), 
            mode=current_settings.get("mode", "Standard")
        )
        
        # Load Data from Google Sheets
        dm = DataManager()
        if "local_logs" not in st.session_state:
             st.session_state["local_logs"] = dm.load_logs()
        
        # Ensure dates are datetime objects for calc
        df_logs = st.session_state["local_logs"]
        if not df_logs.empty:
            # Convert date if needed
            if not pd.api.types.is_datetime64_any_dtype(df_logs['date']):
                df_logs['date'] = pd.to_datetime(df_logs['date'])
            # Fill NaNs in text fields
            df_logs = df_logs.fillna("")
            st.session_state["local_logs"] = df_logs
            
        stats = engine.calculate_monthly_stats(st.session_state["local_logs"])
        
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
            # Altair Heatmap
            energy_chart = alt.Chart(energy_df).mark_rect().encode(
                x=alt.X('date:T', axis=alt.Axis(format='%d', title='Day')),
                y=alt.Y('month(date):O', title='Month'),
                color=alt.Color('energy_rating:Q', scale=alt.Scale(domain=[1, 5], range=['white', '#ffbedb', '#800000']), legend=None),
                tooltip=['date', 'energy_rating']
            ).properties(
                height=150
            ).configure_axis(
                grid=False
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
                default_start = dt.time(9, 0)
                if "last_end_time" in st.session_state:
                    default_start = st.session_state["last_end_time"]
                    
                start_input = st.time_input("Start Time", value=default_start)
                
            with c3:
                end_input = st.time_input("End Time", value=dt.time(10, 0))
        
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
                dm.save_logs(st.session_state["local_logs"])

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

    elif page == "Help":
        st.markdown("# ❓ Setup & FAQ")
        
        st.markdown("---")
        
        # --- GOOGLE SHEETS SETUP ---
        st.markdown("## 📊 Google Sheets Setup (REQUIRED)")
        st.warning("You MUST complete this setup before the app can save your data!")
        
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
        st.markdown("""
        In the **`Logs`** tab, create headers in **Row 1**. Copy these column headers exactly:
        """)
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
        st.markdown("""
        In the **`Config`** tab, create headers in **Row 1**:
        """)
        st.code("Category | Key | Value", language=None)
        st.markdown("""
        This tab stores your supervisors and settings. The app will populate it automatically, but having the headers is required.
        """)
        
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
            *   This email was provided to you when the app was set up. It looks like:
            *   `service@bcba-fieldwork-tracker-sem.iam.gserviceaccount.com`
            *   If you don't know it, check with your administrator or look in the app's secrets configuration.
        """)
        
        st.info("📧 **Need the email?** Ask the app administrator for the Service Account email address.")
        
        st.markdown("""
        2.  **Open your Google Sheet** (the one you just created).
        3.  Click the **"Share"** button (top-right, green button).
        4.  In the "Add people and groups" field, **paste the Service Account email**.
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

