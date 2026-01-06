import pandas as pd
import json
import os
from dataclasses import dataclass
from typing import Dict, Any, Tuple

from utils.schema import SupervisionType, ActivityType

@dataclass
class MonthlyStats:
    total_hours: float
    supervised_hours: float
    independent_hours: float
    supervision_percent: float
    
    # Compliance Flags
    is_compliant_supervision: bool
    is_compliant_min_hours: bool
    is_compliant_max_hours: bool
    
    # Guidance
    hours_needed_for_5_percent: float
    
class ComplianceEngine:
    """
    Business Logic for BACB Fieldwork Requirements.
    """
    
    def __init__(self, ruleset_version: str = "2022", mode: str = "Standard"):
        self.ruleset_version = ruleset_version
        self.mode = mode
        self.rules = self._load_rules(ruleset_version)
        
    def _load_rules(self, version: str) -> Dict[str, Any]:
        """Loads specific ruleset from json file."""
        # Assume data is at ../data/bacb_requirements.json relative to this file
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_path = os.path.join(base_path, 'data', 'bacb_requirements.json')
        
        try:
            with open(data_path, 'r') as f:
                all_rules = json.load(f)
                
            if version not in all_rules:
                # Fallback to 2022 if version not found
                return all_rules.get("2022", {})
                
            return all_rules[version]
            
        except FileNotFoundError:
            # Fallback hardcoded defaults if file missing (Safety net)
            return {
                "monthly_min_hours": 20,
                "monthly_max_hours": 130,
                "supervision_ratios": {"Standard": 0.05, "Concentrated": 0.10},
                "group_supervision_max_percent": 0.50
            }

    def calculate_monthly_stats(self, df: pd.DataFrame) -> MonthlyStats:
        """
        Calculates compliance statistics for a given DataFrame of log entries.
        Expects DataFrame to have: 'duration_hours', 'supervision_type'.
        """
        if df.empty:
            return MonthlyStats(
                total_hours=0.0,
                supervised_hours=0.0,
                independent_hours=0.0,
                supervision_percent=0.0,
                is_compliant_supervision=False,
                is_compliant_min_hours=False,
                is_compliant_max_hours=True, # 0 < 130
                hours_needed_for_5_percent=0.0
            )

        # 1. Total Hours
        total_hours = df['duration_hours'].sum()
        
        # 2. Supervised Hours
        # Filter where supervision_type is NOT None
        # Note: We compare against the string value of the Enum usually stored in DB/DF
        # Vectorized Check
        invalid_types = [SupervisionType.NONE.value, "None", None, "", SupervisionType.NONE]
        sup_mask = ~df['supervision_type'].isin(invalid_types)
            
        supervised_hours = df.loc[sup_mask, 'duration_hours'].sum()
        independent_hours = total_hours - supervised_hours
        
        # 3. Supervision Percentage
        if total_hours > 0:
            supervision_percent = (supervised_hours / total_hours)
        else:
            supervision_percent = 0.0
            
        # 4. Requirements
        req_ratio = self.rules['supervision_ratios'].get(self.mode, 0.05)
        min_h = self.rules['monthly_min_hours']
        max_h = self.rules['monthly_max_hours']
        
        # 5. Compliance Checks
        is_compliant_supervision = (supervision_percent >= req_ratio)
        is_compliant_min_hours = (total_hours >= min_h)
        is_compliant_max_hours = (total_hours <= max_h)
        
        # 6. Delta Calculation
        # Target: (Total * Ratio) <= Supervised
        # Actually, formula is: Supervised / Total >= Ratio
        # Implies: Supervised >= Total * Ratio
        # Wait, if we add supervision, Total increases too.
        # Let x be needed supervision hours.
        # (Current_Sup + x) / (Current_Total + x) = Ratio
        # This is complex "how much more". 
        # Simpler view: "At current total, how much supervision *should* I have?"
        target_supervised_at_current = total_hours * req_ratio
        hours_missing = max(0.0, target_supervised_at_current - supervised_hours)

        return MonthlyStats(
            total_hours=total_hours,
            supervised_hours=supervised_hours,
            independent_hours=independent_hours,
            supervision_percent=supervision_percent,
            is_compliant_supervision=is_compliant_supervision,
            is_compliant_min_hours=is_compliant_min_hours,
            is_compliant_max_hours=is_compliant_max_hours,
            hours_needed_for_5_percent=hours_missing
        )
