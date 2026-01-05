import pandas as pd
from datetime import datetime, date, time
from typing import Optional, Dict

from .schema import ActivityType, SupervisionType, LogEntry

def parse_duration_string(duration_str: str) -> float:
    """
    Parses a duration string like "1h 30m" or "45m" into float hours.
    Returns 0.0 if invalid.
    """
    if not isinstance(duration_str, str):
        return 0.0
    
    duration_str = duration_str.lower().strip()
    hours = 0.0
    minutes = 0.0
    
    if 'h' in duration_str:
        parts = duration_str.split('h')
        try:
            hours = float(parts[0].strip())
        except ValueError:
            pass
            
        if len(parts) > 1 and 'm' in parts[1]:
            try:
                minutes = float(parts[1].replace('m', '').strip())
            except ValueError:
                pass
    elif 'm' in duration_str:
        try:
            minutes = float(duration_str.replace('m', '').strip())
        except ValueError:
            pass
    else:
        # Try direct float conversion
        try:
            return float(duration_str)
        except ValueError:
            return 0.0

    return hours + (minutes / 60.0)

def map_ripley_column_to_schema(df: pd.DataFrame) -> pd.DataFrame:
    """
    Renames columns from Ripley export format to our internal schema.
    """
    # Define mapping dictionary: { Ripley_Col: Schema_Col }
    # Note: These keys are hypothetical based on "Ripley" descriptions, 
    # we will adjust as we see real data.
    mapping = {
        "Date": "date",
        "Start Time": "start_time",
        "End Time": "end_time",
        "Duration": "duration_str", # Temporary column for parsing
        "Activity": "activity_type",
        "Supervisor": "supervisor",
        "Fieldwork Type": "supervision_type", # Guessing header name
        "Description": "notes"
    }
    
    # Filter only columns we can map
    existing_cols = {k: v for k, v in mapping.items() if k in df.columns}
    df = df.rename(columns=existing_cols)
    return df

def process_ripley_file(file) -> pd.DataFrame:
    """
    Main entry point for processing an uploaded Ripley CSV/Excel file.
    Returns a DataFrame conforming to the LogEntry schema (as much as possible).
    """
    try:
        if file.name.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
    except Exception as e:
        raise ValueError(f"Could not read file: {e}")

    # 1. Rename Columns
    df = map_ripley_column_to_schema(df)
    
    # 2. Transform Data
    clean_rows = []
    
    for _, row in df.iterrows():
        # Date
        # Assume Date is string, need to parse
        # If already datetime, good.
        try:
            d_val = pd.to_datetime(row.get('date')).date()
        except:
            d_val = date.today() # Fallback or skip?
            
        # Time Parsing
        start_t = None
        end_t = None
        
        # 1. Try to parse explicit Start/End times if columns exist
        raw_start = row.get('start_time')
        raw_end = row.get('end_time')
        
        if pd.notnull(raw_start):
            try:
                # Handle various formats (AM/PM, 24h)
                # Pandas often parses to datetime/time/str
                if isinstance(raw_start, str):
                    clean_start = raw_start.strip().lower()
                    # Try common formats
                    for fmt in ["%H:%M", "%H:%M:%S", "%I:%M %p", "%I:%M%p"]:
                        try:
                            start_t = datetime.strptime(clean_start, fmt).time()
                            break
                        except ValueError:
                            continue
                elif isinstance(raw_start, (datetime, time)):
                     start_t = raw_start.time() if isinstance(raw_start, datetime) else raw_start
            except:
                pass

        if pd.notnull(raw_end):
            try:
                if isinstance(raw_end, str):
                    clean_end = raw_end.strip().lower()
                    for fmt in ["%H:%M", "%H:%M:%S", "%I:%M %p", "%I:%M%p"]:
                        try:
                            end_t = datetime.strptime(clean_end, fmt).time()
                            break
                        except ValueError:
                            continue
                elif isinstance(raw_end, (datetime, time)):
                     end_t = raw_end.time() if isinstance(raw_end, datetime) else raw_end
            except:
                pass

        # 2. Synthesize if missing but Duration exists
        # If we have duration but no times, we default to starting at 9:00 AM
        # This is a fallback to allow the data to exist, even if times are fake.
        if start_t is None and dur_val > 0:
            start_t = time(9, 0)
            
        if end_t is None and start_t is not None and dur_val > 0:
            # Calculate End from Start + Duration
            # Convert to datetime to doing math
            dummy_date = date(2000, 1, 1)
            dt_start = datetime.combine(dummy_date, start_t)
            dt_end = dt_start + pd.Timedelta(hours=dur_val)
            end_t = dt_end.time()
            
            # If explicit start was provided but not end, we use that. 
            # If both missing, we synthesized 9am start.
            
        # Final Safety Net
        if start_t is None: start_t = time(9, 0)
        if end_t is None: end_t = time(10, 0)
            
        entry = {
            "date": d_val,
            "start_time": start_t,
            "end_time": end_t,
            "duration_hours": dur_val,
            "activity_type": act_enum.value,
            "supervision_type": sup_enum.value,
            "supervisor": str(row.get('supervisor', '')),
            "energy_rating": None, # Setup for future mapping if needed
            "notes": str(row.get('notes', ''))
        }
        
        # Filter out invalid entries (e.g. 0 duration)
        if dur_val > 0:
            clean_rows.append(entry)
            
    return pd.DataFrame(clean_rows)
