import streamlit as st
import pandas as pd
from typing import List, Dict, Any
from utils.gsheet import GSheetManager

class ConfigManager:
    """
    Manages application configuration including Supervisors and Rulesets.
    Persists to Google Sheets via Config tab.
    """
    
    DEFAULTS = {
        "supervisors": ["Supervisor A", "Supervisor B"],
        "settings": {
            "ruleset_version": "2022",
            "mode": "Standard", # Standard vs Concentrated
            "work_days": ["Mon", "Tue", "Wed", "Thu", "Fri"],
            "work_hours_start": "09:00",
            "work_hours_end": "17:00",
            "primary_supervisor": "Supervisor A",
            # User Profile for PDF
            "trainee_name": "",
            "trainee_id": "",
            "fieldwork_state": "",
            "fieldwork_country": "USA",
            "time_precision": 15 # Minutes (1, 5, 15, 30)
        }
    }

    def __init__(self, gsheet_manager):
        self.gm = gsheet_manager
        self._initialize_state()

    def _initialize_state(self):
        """Ensures config exists in session_state, loaded from DB if possible."""
        if "config" not in st.session_state:
            # Load from Sheet
            df = self.gm.load_config_raw()
            
            # Start with defaults
            config = {
                "supervisors": [],
                "settings": dict(self.DEFAULTS["settings"])
            }
            
            if not df.empty and "Category" in df.columns:
                # Parse DF
                for _, row in df.iterrows():
                    cat = row.get("Category")
                    key = row.get("Key")
                    val = row.get("Value")
                    
                    if cat == "Supervisor":
                        if val not in config["supervisors"]:
                            config["supervisors"].append(val)
                    elif cat == "Setting":
                        # Handle List types (like work_days) which might be stored as string
                        if key == "work_days" and isinstance(val, str) and "[" in val:
                            try:
                                # Safe eval for list
                                import ast
                                val = ast.literal_eval(val)
                            except:
                                pass
                        config["settings"][key] = val
            
            # If no supervisors found in DB, use default
            if not config["supervisors"]:
                config["supervisors"] = list(self.DEFAULTS["supervisors"])

            st.session_state["config"] = config

    def _save_to_db(self):
        """Persists current state to Google Sheets."""
        rows = []
        for sup in self.supervisors:
            rows.append({"Category": "Supervisor", "Key": "Name", "Value": sup})
        
        for k, v in self.settings.items():
            # Convert list to string representation if needed
            val = v
            if isinstance(v, list):
                val = str(v)
            rows.append({"Category": "Setting", "Key": k, "Value": val})
        
        df = pd.DataFrame(rows)
        self.gm.save_config_raw(df)

    @property
    def supervisors(self) -> List[str]:
        return st.session_state["config"]["supervisors"]

    @property
    def settings(self) -> Dict[str, Any]:
        return st.session_state["config"]["settings"]

    def add_supervisor(self, name: str):
        """Adds a new supervisor if not exists."""
        if name and name not in self.supervisors:
            st.session_state["config"]["supervisors"].append(name)
            self._save_to_db()
            
    def remove_supervisor(self, name: str):
        """Removes a supervisor."""
        if name in self.supervisors:
            st.session_state["config"]["supervisors"].remove(name)
            
            # Reset primary if needed
            if self.settings.get("primary_supervisor") == name:
                 # Default to first available or None
                if self.supervisors:
                    self.update_setting("primary_supervisor", self.supervisors[0])
                else:
                    self.update_setting("primary_supervisor", "")
            else:
                self._save_to_db()

    def update_setting(self, key: str, value: Any):
        """Updates a specific setting key."""
        st.session_state["config"]["settings"][key] = value
        self._save_to_db()

    def get_all_config(self):
        """Returns the full config dict."""
        return st.session_state["config"]
