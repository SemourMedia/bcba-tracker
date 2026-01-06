
import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from typing import Optional

class GSheetManager:
    """
    Handles interactions with specific Google Sheets (Storage Layer).
    Replaces DataManager to support multi-user architecture where each user has their own sheet.
    """
    
    def __init__(self, sheet_url: str):
        """
        Initialize with a specific sheet URL.
        
        Args:
            sheet_url: The full URL of the Google Sheet to connect to.
        """
        self.sheet_url = sheet_url
        try:
            self.conn = st.connection("gsheets", type=GSheetsConnection)
        except Exception as e:
            st.error(f"Failed to initialize GSheets connection: {e}")
            self.conn = None

    def validate_user_ownership(self, user_email: str) -> bool:
        """
        Validates that the sheet is accessible (shared with Service Account).
        NOTE: This does not strictly prove the user owns it, but that the app can access it
        as the user intended. Registry handles the email<->url mapping trust.
        
        Args:
            user_email: (Unused in V1 check, mainly for logging/future validation)
            
        Returns:
            True if accessible, False otherwise.
        """
        if self.conn is None or not self.sheet_url:
            return False
            
        try:
            # Try to read the 'Config' tab as a lightweight check
            # We explicitly pass the spreadsheet URL
            self.conn.read(spreadsheet=self.sheet_url, worksheet="Config", usecols=[0])
            return True
        except Exception:
            return False

    def add_user_context(self, df: pd.DataFrame, user_id: str) -> pd.DataFrame:
        """
        Ensures the 'user_id' column is populated for all rows.
        This is a critical defense-in-depth step for data isolation.
        
        Args:
            df: The dataframe to enrich.
            user_id: The UUID of the current user.
            
        Returns:
            The dataframe with 'user_id' set.
        """
        if df is None:
            return df
            
        # Ensure user_id column exists
        if "user_id" not in df.columns:
            df["user_id"] = None
            
        # Fill missing values and overwrite to ensure consistency
        # We enforce that all rows in this sheet belong to this user
        df["user_id"] = user_id
        return df

    @st.cache_data(ttl=300) 
    def load_logs(_self) -> pd.DataFrame:
        """
        Loads the 'Logs' worksheet from the configured URL.
        Cached for 5 minutes.
        """
        if _self.conn is None:
            return pd.DataFrame()
            
        try:
            # Explicitly pass spreadsheet=self.sheet_url
            df = _self.conn.read(spreadsheet=_self.sheet_url, worksheet="Logs")
            
            # Ensure proper types immediately after load
            required_cols = ["uid", "user_id", "date", "start_time", "end_time", "duration_hours", 
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
            return pd.DataFrame(columns=["uid", "user_id", "date", "start_time", "end_time", "duration_hours", 
                                         "activity_type", "supervision_type", "supervisor", "notes", "energy_rating"])

    def save_logs(self, df: pd.DataFrame, user_id: str):
        """
        Saves the logs dataframe to the 'Logs' worksheet.
        Injects user_id context before saving.
        """
        if self.conn:
            # Defense in depth: Check context
            df = self.add_user_context(df, user_id)
            
            self.conn.update(spreadsheet=self.sheet_url, worksheet="Logs", data=df)
            
            # OPTIMIZATION: Removed st.cache_data.clear() to prevent full app reload.
            # We rely on st.session_state["local_logs"] for immediate UI updates.

    @st.cache_data(ttl=300)
    def load_config_raw(_self) -> pd.DataFrame:
        """Loads the 'Config' worksheet as raw Key-Value dataframe."""
        if _self.conn is None:
            return pd.DataFrame()
            
        try:
            df = _self.conn.read(spreadsheet=_self.sheet_url, worksheet="Config")
            if df.empty:
                return pd.DataFrame(columns=["Category", "Key", "Value"])
            return df
        except:
             return pd.DataFrame(columns=["Category", "Key", "Value"])

    def save_config_raw(self, df: pd.DataFrame):
        """Saves the raw config dataframe."""
        if self.conn:
            self.conn.update(spreadsheet=self.sheet_url, worksheet="Config", data=df)
            st.cache_data.clear()
