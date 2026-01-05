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
        """
        Master validation function.
        Returns: (is_safe_to_save, [list_of_error_messages])
        """
        errors = []
        
        # 1. Human Capability Check (The "Superman" Rule)
        if new_entry.duration_hours > Auditor.audit_threshold_hours:
            errors.append(f"AUDIT RISK: Session duration ({new_entry.duration_hours:.2f}h) exceeds daily safety limit ({Auditor.audit_threshold_hours}h).")

        # 2. Temporal Paradox Check (The "Time Traveler" Rule)
        # We need to check for overlaps with existing entries on the SAME day.
        
        if not existing_history.empty:
            # Ensure dates are comparable. Convert strings to date objects if needed.
            # We assume existing_history has 'date', 'start_time', 'end_time' columns.
            
            # Filter for the same date
            # Note: We cast to string for comparison to avoid Date vs datetime.date issues common in Pandas
            input_date_str = new_entry.date.strftime("%Y-%m-%d")
            
            # Create a mask for same day entries
            # We assume the dataframe 'date' column matches the format or object type
            # Handling generic pandas object types safely:
            
            # Helper to normalize date to string
            def to_date_str(x):
                if isinstance(x, (dt.date, dt.datetime)):
                    return x.strftime("%Y-%m-%d")
                return str(x)

            day_entries = existing_history[existing_history['date'].apply(to_date_str) == input_date_str]

            if not day_entries.empty:
                # Check for overlap
                # Logic: (StartA < EndB) and (EndA > StartB)
                
                new_start = new_entry.start_time
                new_end = new_entry.end_time
                
                for _, row in day_entries.iterrows():
                    # Parse times if they are strings (common in loaded CSVs/Sheets)
                    row_start = Auditor._parse_time(row['start_time'])
                    row_end = Auditor._parse_time(row['end_time'])
                    
                    if row_start and row_end:
                         if (new_start < row_end) and (new_end > row_start):
                             errors.append(f"OVERLAP DETECTED: Clashes with entry on {input_date_str} ({row_start} - {row_end}).")
                             break # One overlap is enough to block

        is_safe = (len(errors) == 0)
        return is_safe, errors

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
