# utils/sheet_provisioner.py
"""Google Sheet auto-provisioning for BCBA Fieldwork Tracker V2.

This module handles automatic creation and configuration of user sheets:
- Creating new Google Sheets via the Sheets API
- Initializing with Logs/Config tabs and headers
- Sharing with user email
- Applying formatting and data validation
"""

from datetime import datetime
from typing import Optional
import streamlit as st

try:
    from googleapiclient.discovery import build
    from google.oauth2.service_account import Credentials
except ImportError:
    raise ImportError(
        "Google API libraries not installed. Run: pip install google-api-python-client"
    )


class SheetProvisioner:
    """Handles automatic Google Sheet creation for new users.
    
    Uses the Google Sheets and Drive APIs to create, configure, and share
    new spreadsheets for users when they first sign in.
    
    Attributes:
        credentials: Google Service Account credentials
        sheets_service: Google Sheets API service
        drive_service: Google Drive API service
        
    Example:
        >>> provisioner = SheetProvisioner(st.secrets["gcp_service_account"])
        >>> sheet_info = provisioner.create_user_sheet(
        ...     user_email="user@gmail.com",
        ...     display_name="Jane Doe"
        ... )
        >>> print(sheet_info["sheet_url"])
    """
    
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    # Schema for the Logs tab
    LOGS_HEADERS = [
        "uid",
        "user_id",
        "date",
        "start_time",
        "end_time",
        "duration_hours",
        "activity_type",
        "supervision_type",
        "supervisor",
        "notes",
        "energy_rating"
    ]
    
    # Default config for new users
    DEFAULT_CONFIG = {
        "supervisors": "",
        "ruleset_version": "2022",
        "mode": "Standard",
        "work_days": "Mon,Tue,Wed,Thu,Fri",
        "work_hours_start": "08:00",
        "work_hours_end": "17:00",
        "primary_supervisor": "",
        "candidate_name": "",
        "candidate_id": "",
        "program_name": "",
        "university": ""
    }
    
    def __init__(self, service_account_info: dict):
        """Initialize the SheetProvisioner.
        
        Args:
            service_account_info: Service account JSON as a dict
                                 (from st.secrets["gcp_service_account"])
        """
        self.credentials = Credentials.from_service_account_info(
            service_account_info,
            scopes=self.SCOPES
        )
        
        self._sheets_service = None
        self._drive_service = None
    
    @property
    def sheets_service(self):
        """Lazy-load the Sheets API service."""
        if self._sheets_service is None:
            self._sheets_service = build(
                "sheets", "v4",
                credentials=self.credentials
            )
        return self._sheets_service
    
    @property
    def drive_service(self):
        """Lazy-load the Drive API service."""
        if self._drive_service is None:
            self._drive_service = build(
                "drive", "v3",
                credentials=self.credentials
            )
        return self._drive_service
    
    def create_user_sheet(
        self,
        user_email: str,
        display_name: str,
        user_id: Optional[str] = None
    ) -> dict:
        """Create a new Google Sheet for a user.
        
        Creates a fresh spreadsheet with initialized Logs and Config tabs,
        applies formatting, and shares it with the user.
        
        Args:
            user_email: User's email address
            display_name: User's display name
            user_id: Optional user UUID (for user_id column in Logs)
            
        Returns:
            Dictionary containing:
                - sheet_id: Google Sheet ID
                - sheet_url: Full URL to the sheet
                - title: Sheet title
        """
        # Generate sheet title
        today = datetime.now().strftime("%Y-%m-%d")
        title = f"BCBA Tracker - {display_name} ({today})"
        
        # Create the spreadsheet
        spreadsheet_body = {
            "properties": {
                "title": title
            },
            "sheets": [
                {
                    "properties": {
                        "title": "Logs",
                        "sheetId": 0,
                        "gridProperties": {
                            "rowCount": 1000,
                            "columnCount": len(self.LOGS_HEADERS)
                        }
                    }
                },
                {
                    "properties": {
                        "title": "Config",
                        "sheetId": 1,
                        "gridProperties": {
                            "rowCount": 50,
                            "columnCount": 2
                        }
                    }
                }
            ]
        }
        
        try:
            result = self.sheets_service.spreadsheets().create(
                body=spreadsheet_body
            ).execute()
            
            sheet_id = result["spreadsheetId"]
            sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
            
            # Initialize sheet structure
            self._initialize_logs_tab(sheet_id, user_id)
            self._initialize_config_tab(sheet_id)
            
            # Apply formatting
            self._apply_formatting(sheet_id)
            
            # Share with user
            self._share_with_user(sheet_id, user_email)
            
            return {
                "sheet_id": sheet_id,
                "sheet_url": sheet_url,
                "title": title
            }
            
        except Exception as e:
            st.error(f"Failed to create user sheet: {e}")
            raise
    
    def _initialize_logs_tab(
        self,
        sheet_id: str,
        user_id: Optional[str] = None
    ) -> None:
        """Set up the Logs tab with headers.
        
        Args:
            sheet_id: Google Sheet ID
            user_id: Optional user UUID for pre-populating
        """
        # Write headers to first row
        values = [self.LOGS_HEADERS]
        
        body = {"values": values}
        
        self.sheets_service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range="Logs!A1",
            valueInputOption="RAW",
            body=body
        ).execute()
    
    def _initialize_config_tab(self, sheet_id: str) -> None:
        """Set up the Config tab with default settings.
        
        Args:
            sheet_id: Google Sheet ID
        """
        # Config is stored as key-value pairs
        config_rows = [["key", "value"]]  # Header row
        
        for key, value in self.DEFAULT_CONFIG.items():
            config_rows.append([key, value])
        
        body = {"values": config_rows}
        
        self.sheets_service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range="Config!A1",
            valueInputOption="RAW",
            body=body
        ).execute()
    
    def _apply_formatting(self, sheet_id: str) -> None:
        """Apply visual formatting to the sheet.
        
        Applies:
        - Header row styling (bold, background color)
        - Column widths
        
        Args:
            sheet_id: Google Sheet ID
        """
        requests = [
            # Bold header row for Logs
            {
                "repeatCell": {
                    "range": {
                        "sheetId": 0,
                        "startRowIndex": 0,
                        "endRowIndex": 1
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {
                                "red": 0.9,
                                "green": 0.9,
                                "blue": 0.9
                            },
                            "textFormat": {
                                "bold": True
                            }
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor,textFormat)"
                }
            },
            # Bold header row for Config
            {
                "repeatCell": {
                    "range": {
                        "sheetId": 1,
                        "startRowIndex": 0,
                        "endRowIndex": 1
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {
                                "red": 0.9,
                                "green": 0.9,
                                "blue": 0.9
                            },
                            "textFormat": {
                                "bold": True
                            }
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor,textFormat)"
                }
            },
            # Freeze header row in Logs
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": 0,
                        "gridProperties": {
                            "frozenRowCount": 1
                        }
                    },
                    "fields": "gridProperties.frozenRowCount"
                }
            },
            # Freeze header row in Config
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": 1,
                        "gridProperties": {
                            "frozenRowCount": 1
                        }
                    },
                    "fields": "gridProperties.frozenRowCount"
                }
            }
        ]
        
        self.sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=sheet_id,
            body={"requests": requests}
        ).execute()
    
    def _share_with_user(
        self,
        sheet_id: str,
        user_email: str,
        role: str = "reader"
    ) -> None:
        """Share the sheet with the user.
        
        Args:
            sheet_id: Google Sheet ID
            user_email: User's email address
            role: Permission role ('reader', 'writer', 'owner')
        """
        permission = {
            "type": "user",
            "role": role,
            "emailAddress": user_email
        }
        
        try:
            self.drive_service.permissions().create(
                fileId=sheet_id,
                body=permission,
                sendNotificationEmail=True,
                emailMessage=(
                    "Your BCBA Fieldwork Tracker has been created! "
                    "You can view your data in this sheet."
                )
            ).execute()
        except Exception as e:
            # Log but don't fail if sharing fails
            st.warning(f"Could not share sheet with user: {e}")
    
    def delete_user_sheet(self, sheet_id: str) -> None:
        """Permanently delete a user's sheet (admin function).
        
        Args:
            sheet_id: Google Sheet ID to delete
        """
        try:
            self.drive_service.files().delete(fileId=sheet_id).execute()
        except Exception as e:
            st.error(f"Failed to delete sheet: {e}")
            raise
    
    def get_sheet_size(self, sheet_id: str) -> int:
        """Get approximate size of a sheet in bytes.
        
        Args:
            sheet_id: Google Sheet ID
            
        Returns:
            Approximate size in bytes
        """
        try:
            file_info = self.drive_service.files().get(
                fileId=sheet_id,
                fields="size"
            ).execute()
            return int(file_info.get("size", 0))
        except Exception:
            return 0
    
    def sheet_exists(self, sheet_id: str) -> bool:
        """Check if a sheet exists and is accessible.
        
        Args:
            sheet_id: Google Sheet ID
            
        Returns:
            True if sheet exists and is accessible
        """
        try:
            self.drive_service.files().get(fileId=sheet_id).execute()
            return True
        except Exception:
            return False
