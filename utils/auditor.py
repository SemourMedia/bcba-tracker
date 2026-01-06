import pandas as pd
import datetime as dt
from typing import Tuple, Optional, List
from utils.schema import LogEntry

class Auditor:
    """
    The 'Aggressive Auditor' module (Feature C).
    Acts as a blocking defense against risky data entries that could trigger a BACB audit.
    """
    
    audit_threshold_hours = 12.0

    @staticmethod
    def check_save_safety(new_entry: LogEntry, existing_history: pd.DataFrame) -> Tuple[bool, List[str]]:
        errors = []
        
        # 1. Human Capability Check (Fast)
        if new_entry.duration_hours > Auditor.audit_threshold_hours:
            errors.append(f"AUDIT RISK: Session duration exceeds limit.")

        # 2. Temporal Paradox Check (Vectorized)
        if not existing_history.empty:
            # Convert new entry times to comparable types once
            new_start = new_entry.start_time
            new_end = new_entry.end_time
            target_date = pd.to_datetime(new_entry.date)

            # Ensure history 'date' is datetime64 for fast comparison
            # (This should ideally be done once during loading, not here)
            if not pd.api.types.is_datetime64_any_dtype(existing_history['date']):
                history_dates = pd.to_datetime(existing_history['date'], errors='coerce')
            else:
                history_dates = existing_history['date']

            # Filter for same day (Vectorized mask)
            # Note: formatting dates to strings is slow; comparing datetime objects is fast
            same_day_mask = (history_dates.dt.date == target_date.date())
            day_entries = existing_history.loc[same_day_mask].copy()

            if not day_entries.empty:
                # Fast loop fallback (only for the specific day's rows, which is small)
                # Given the current mix of types, the biggest win is removing the 'apply(to_date_str)' 
                # from the main filter above.
                
                for _, row in day_entries.iterrows():
                    row_start = Auditor._parse_time(row['start_time'])
                    row_end = Auditor._parse_time(row['end_time'])
                    
                    if row_start and row_end:
                         if (new_start < row_end) and (new_end > row_start):
                             errors.append(f"OVERLAP DETECTED: Clashes with entry on {target_date.date()} ({row_start} - {row_end}).")
                             break 

        return (len(errors) == 0), errors

    @staticmethod
    def _parse_time(t_input) -> Optional[dt.time]:
        """Helper to coerce various time formats into datetime.time"""
        if isinstance(t_input, dt.time):
            return t_input
        if isinstance(t_input, dt.datetime):
            return t_input.time()
        if isinstance(t_input, str):
            try:
                return dt.datetime.strptime(t_input, "%H:%M:%S").time()
            except ValueError:
                try:
                    return dt.datetime.strptime(t_input, "%H:%M").time()
                except ValueError:
                    return None
        return None
