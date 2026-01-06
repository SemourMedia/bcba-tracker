# utils/user_registry.py
"""User Registry management for BCBA Fieldwork Tracker V2.

This module manages user records in the master Registry Sheet, including:
- User lookup by email or ID
- User registration for new accounts
- Login tracking and audit logging
"""

import uuid
from datetime import datetime
from typing import Optional, List
import streamlit as st
import pandas as pd

try:
    from streamlit_gsheets import GSheetsConnection
except ImportError:
    GSheetsConnection = None


class UserRegistry:
    """Manages user records in the master Registry Sheet.
    
    The registry is a Google Sheet with two tabs:
    - Users: Contains user account information
    - Audit_Log: Contains security and activity events
    
    Attributes:
        registry_url: URL of the Registry Google Sheet
        conn: GSheetsConnection instance
        
    Example:
        >>> registry = UserRegistry(st.secrets["registry"]["sheet_url"])
        >>> user = registry.get_user_by_email("user@gmail.com")
        >>> if not user:
        ...     user = registry.register_user(
        ...         email="user@gmail.com",
        ...         display_name="Jane Doe",
        ...         sheet_url="https://..."
        ...     )
    """
    
    # Column names for Users tab
    USER_COLUMNS = [
        "user_id",
        "email",
        "display_name",
        "sheet_id",
        "sheet_url",
        "created_at",
        "last_login",
        "status",
        "storage_bytes"
    ]
    
    # Column names for Audit_Log tab
    AUDIT_COLUMNS = [
        "timestamp",
        "user_id",
        "action",
        "ip_address",
        "details"
    ]
    
    def __init__(self, registry_url: str):
        """Initialize the UserRegistry.
        
        Args:
            registry_url: Full URL of the Registry Google Sheet
        """
        self.registry_url = registry_url
        self._spreadsheet = None
        self._users_cache = None
        self._cache_time = None
    
    @property
    def spreadsheet(self):
        """Get or create the gspread spreadsheet connection."""
        if self._spreadsheet is None:
            try:
                import gspread
                from google.oauth2.service_account import Credentials
                
                # Get service account from secrets
                sa_info = dict(st.secrets["connections"]["gsheets"])
                # Remove non-credential keys
                sa_info.pop("spreadsheet", None)
                sa_info.pop("worksheet", None)
                
                credentials = Credentials.from_service_account_info(
                    sa_info,
                    scopes=[
                        "https://www.googleapis.com/auth/spreadsheets",
                        "https://www.googleapis.com/auth/drive"
                    ]
                )
                
                gc = gspread.authorize(credentials)
                self._spreadsheet = gc.open_by_url(self.registry_url)
            except Exception as e:
                st.error(f"Failed to connect to Registry: {e}")
                raise
        return self._spreadsheet

    @property
    def client(self):
        """Get the underlying gspread client."""
        return self.spreadsheet.client
    
    def _get_users_df(self, force_refresh: bool = False) -> pd.DataFrame:
        """Get the Users dataframe, with caching.
        
        Args:
            force_refresh: Force a fresh read from Google Sheets
            
        Returns:
            DataFrame of all user records
        """
        # Simple time-based cache (5 minutes)
        cache_ttl = 300  # seconds
        now = datetime.now()
        
        if (
            not force_refresh
            and self._users_cache is not None
            and self._cache_time is not None
            and (now - self._cache_time).seconds < cache_ttl
        ):
            return self._users_cache
        
        try:
            worksheet = self.spreadsheet.worksheet("Users")
            records = worksheet.get_all_records()
            if not records:
                df = pd.DataFrame(columns=self.USER_COLUMNS)
            else:
                df = pd.DataFrame(records)
            self._users_cache = df
            self._cache_time = now
            return df
        except Exception as e:
            st.error(f"Failed to read User Registry: {e}")
            return pd.DataFrame(columns=self.USER_COLUMNS)
    
    def _invalidate_cache(self) -> None:
        """Invalidate the users cache."""
        self._users_cache = None
        self._cache_time = None
    
    def get_user_by_email(self, email: str) -> Optional[dict]:
        """Look up a user by their email address.
        
        Args:
            email: Email address to search for
            
        Returns:
            User record dict if found, None otherwise
        """
        df = self._get_users_df()
        matches = df[df["email"].str.lower() == email.lower()]
        
        if matches.empty:
            return None
        
        return matches.iloc[0].to_dict()
    
    def get_user_by_id(self, user_id: str) -> Optional[dict]:
        """Look up a user by their UUID.
        
        Args:
            user_id: User UUID to search for
            
        Returns:
            User record dict if found, None otherwise
        """
        df = self._get_users_df()
        matches = df[df["user_id"] == user_id]
        
        if matches.empty:
            return None
        
        return matches.iloc[0].to_dict()
    
    def register_user(
        self,
        email: str,
        display_name: str,
        sheet_url: str,
        sheet_id: Optional[str] = None
    ) -> dict:
        """Create a new user record in the registry.
        
        Args:
            email: User's email address
            display_name: User's display name
            sheet_url: URL of the user's personal sheet
            sheet_id: Optional Google Sheet ID
            
        Returns:
            The created user record as a dict
        """
        # Check if user already exists
        existing = self.get_user_by_email(email)
        if existing:
            return existing
        
        # Generate user ID
        user_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        # Extract sheet_id from URL if not provided
        if sheet_id is None and "spreadsheets/d/" in sheet_url:
            parts = sheet_url.split("spreadsheets/d/")
            if len(parts) > 1:
                sheet_id = parts[1].split("/")[0]
        
        user_record = {
            "user_id": user_id,
            "email": email,
            "display_name": display_name,
            "sheet_id": sheet_id or "",
            "sheet_url": sheet_url,
            "created_at": now,
            "last_login": now,
            "status": "active",
            "storage_bytes": 0
        }
        
        # Append to Users sheet
        try:
            df = self._get_users_df()
            new_row = pd.DataFrame([user_record])
            updated_df = pd.concat([df, new_row], ignore_index=True)
            
            # Append row to Users sheet
            worksheet = self.spreadsheet.worksheet("Users")
            row_values = [user_record[col] for col in self.USER_COLUMNS]
            worksheet.append_row(row_values)
            
            # Log the event
            self.log_audit_event(
                user_id=user_id,
                action="user_created",
                details={"email": email}
            )
            
            self._invalidate_cache()
            return user_record
            
        except Exception as e:
            st.error(f"Failed to register user: {e}")
            raise
    
    def update_last_login(self, user_id: str) -> None:
        """Update the last login timestamp for a user.
        
        Args:
            user_id: User's UUID
        """
        try:
            df = self._get_users_df(force_refresh=True)
            mask = df["user_id"] == user_id
            
            if mask.any():
                df.loc[mask, "last_login"] = datetime.now().isoformat()
                # Update the specific cell
                worksheet = self.spreadsheet.worksheet("Users")
                row_idx = mask.idxmax() + 2  # +2 for header and 0-indexing
                col_idx = self.USER_COLUMNS.index("last_login") + 1
                worksheet.update_cell(row_idx, col_idx, datetime.now().isoformat())
                self._invalidate_cache()
                
                # Log the event
                self.log_audit_event(
                    user_id=user_id,
                    action="login",
                    details={}
                )
        except Exception as e:
            # Non-critical - don't block on login tracking failures
            pass
    
    def update_user_status(self, user_id: str, status: str) -> None:
        """Change a user's account status.
        
        Args:
            user_id: User's UUID
            status: New status ('active', 'suspended', 'deleted')
        """
        valid_statuses = ["active", "suspended", "deleted"]
        if status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
        
        try:
            df = self._get_users_df(force_refresh=True)
            mask = df["user_id"] == user_id
            
            if mask.any():
                old_status = df.loc[mask, "status"].iloc[0]
                df.loc[mask, "status"] = status
                # Update the specific cell
                worksheet = self.spreadsheet.worksheet("Users")
                row_idx = mask.idxmax() + 2  # +2 for header and 0-indexing
                col_idx = self.USER_COLUMNS.index("status") + 1
                worksheet.update_cell(row_idx, col_idx, status)
                self._invalidate_cache()
                
                self.log_audit_event(
                    user_id=user_id,
                    action="status_changed",
                    details={"old": old_status, "new": status}
                )
        except Exception as e:
            st.error(f"Failed to update user status: {e}")
            raise
    
    def log_audit_event(
        self,
        user_id: str,
        action: str,
        details: dict,
        ip_address: str = ""
    ) -> None:
        """Record an event in the Audit_Log tab.
        
        Args:
            user_id: User's UUID
            action: Action type (e.g., 'login', 'user_created')
            details: Additional context as a dict
            ip_address: Optional client IP address
        """
        try:
            import json
            
            audit_record = {
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id,
                "action": action,
                "ip_address": ip_address,
                "details": json.dumps(details)
            }
            
            # Append row to Audit_Log sheet
            try:
                worksheet = self.spreadsheet.worksheet("Audit_Log")
                row_values = [audit_record[col] for col in self.AUDIT_COLUMNS]
                worksheet.append_row(row_values)
            except Exception:
                pass  # Non-critical
            
        except Exception:
            # Non-critical - don't block on audit logging failures
            pass
    
    def get_all_users(self) -> List[dict]:
        """Get all registered users (admin function).
        
        Returns:
            List of all user records
        """
        df = self._get_users_df(force_refresh=True)
        return df.to_dict("records")
    
    def get_user_count(self) -> int:
        """Get the total number of registered users.
        
        Returns:
            Count of users in the registry
        """
        df = self._get_users_df()
        return len(df)
    
    def is_user_active(self, user_id: str) -> bool:
        """Check if a user account is active.
        
        Args:
            user_id: User's UUID
            
        Returns:
            True if user exists and has 'active' status
        """
        user = self.get_user_by_id(user_id)
        if user is None:
            return False
        return user.get("status") == "active"
