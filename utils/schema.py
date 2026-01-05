from datetime import date, time
from enum import Enum
from typing import Optional, List
from dataclasses import dataclass

class ActivityType(Enum):
    RESTRICTED = "Restricted"
    UNRESTRICTED = "Unrestricted"

class SupervisionType(Enum):
    NONE = "None"
    INDIVIDUAL = "Individual"
    GROUP = "Group"

@dataclass
class LogEntry:
    uid: str
    date: date
    start_time: time
    end_time: time
    duration_hours: float
    activity_type: ActivityType
    supervision_type: SupervisionType
    supervisor: str
    energy_rating: Optional[int] = None
    notes: Optional[str] = ""

    def validate(self):
        """
        Validates the LogEntry instance.
        Raises ValueError if any constraints are violated.
        """
        # 1. Validate Duration
        if self.duration_hours <= 0:
            raise ValueError(f"Duration must be positive. Calculated: {self.duration_hours}")
        
        # 2. Validate End Time after Start Time (if on same day - logic usually handled before creation, but good to check)
        # Note: Since we only store time objects, we assume single-day entries for now. 
        # If spanning midnight, duration calculation needs to handle it, but here we just check raw values for sanity if duration expects > 0.
        # However, duration_hours is the source of truth for the math.
        
        # 3. Validate Supervisor if Supervision is logged
        if self.supervision_type != SupervisionType.NONE and not self.supervisor:
            raise ValueError("Supervisor name is required for supervised sessions.")
        
        # 4. Validate Group Supervision Logic (Constraint: Max 50% - this is a monthly aggregate rule, not a single entry rule.
        # But we can enforce that Group requires SupervisionType.GROUP)
        
        return True
