import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

class DataManager:
    """
    Handles all interactions with Google Sheets (Storage Layer).
    Implements caching to minimize API calls.
    """
    
    def __init__(self):
        try:
            self.conn = st.connection("gsheets", type=GSheetsConnection)
        except Exception as e:
            st.error(f"Failed to connect to Google Sheets: {e}")
            self.conn = None

    @st.cache_data(ttl=300) 
    def load_logs(_self) -> pd.DataFrame:
        """
        Loads the 'Logs' worksheet.
        Cached for 5 minutes or until manually cleared.
        """
        if _self.conn is None:
            return pd.DataFrame()
            
        try:
            # Explicitly define columns to ensure empty sheet handles correctly
            df = _self.conn.read(worksheet="Logs")
            
            # Ensure proper types immediately after load
            required_cols = ["uid", "date", "start_time", "end_time", "duration_hours", 
                             "activity_type", "supervision_type", "supervisor", "notes", "energy_rating"]
            
            if df.empty:
                return pd.DataFrame(columns=required_cols)
            
            # Ensure all columns exist
            for col in required_cols:
                if col not in df.columns:
                    df[col] = None
                    
            return df
            
        except Exception:
            # If sheet doesn't exist or error
            return pd.DataFrame(columns=["uid", "date", "start_time", "end_time", "duration_hours", 
                                         "activity_type", "supervision_type", "supervisor", "notes", "energy_rating"])

    def save_logs(self, df: pd.DataFrame):
        """Saves the logs dataframe to the 'Logs' worksheet."""
        if self.conn:
            self.conn.update(worksheet="Logs", data=df)
            st.cache_data.clear()

    @st.cache_data(ttl=300)
    def load_config_raw(_self) -> pd.DataFrame:
        """Loads the 'Config' worksheet as raw Key-Value dataframe."""
        if _self.conn is None:
            return pd.DataFrame()
            
        try:
            df = _self.conn.read(worksheet="Config")
            if df.empty:
                return pd.DataFrame(columns=["Category", "Key", "Value"])
            return df
        except:
             return pd.DataFrame(columns=["Category", "Key", "Value"])

    def save_config_raw(self, df: pd.DataFrame):
        """Saves the raw config dataframe."""
        if self.conn:
            self.conn.update(worksheet="Config", data=df)
            st.cache_data.clear()
