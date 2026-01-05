import io
import os
import datetime
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject
from typing import Dict, Any

class PDFGenerator:
    """
    Handles population of the BACB Monthly Verification Form.
    """
    
    FORM_FILENAME = "BACB_Monthly_Verification_Form.pdf"
    
    def __init__(self):
        # Locate the PDF template
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.template_path = os.path.join(base_path, self.FORM_FILENAME)
        
    def generate_verification_form(self, 
                                 stats: Any, 
                                 config: Dict[str, Any], 
                                 month_year_str: str,
                                 supervisor_name: str) -> bytes:
        """
        Fills the PDF form with data.
        
        Args:
            stats: MonthlyStats object from calculations.py
            config: Configuration dictionary (settings)
            month_year_str: String e.g "October 2023"
            supervisor_name: Name of supervisor for this form
            
        Returns:
            bytes: The PDF file content
        """
        
        if not os.path.exists(self.template_path):
            raise FileNotFoundError(f"PDF Template not found at {self.template_path}")
            
        # Initialize Writer by cloning the template (preserves keys/structure)
        try:
            writer = PdfWriter(clone_from=self.template_path)
        except TypeError:
            # Fallback for older pypdf versions if necessary
            reader = PdfReader(self.template_path)
            writer = PdfWriter()
            writer.append(reader)
            # Copy root dict to ensure AcroForm presence if append didn't do it
            if "/AcroForm" in reader.trailer["/Root"]:
                 writer._root_object.update({
                    NameObject("/AcroForm"): reader.trailer["/Root"]["/AcroForm"]
                })
            
        # Prepare Field Map
        # Field Names found via inspection:
        # TRAINEE_NAME, TRAINEE_BACB_ID, TRAINEE_CERTIFICATE_MONTH/YEAR
        # CHECK_SUPERVISED_FIELDWORK (Btn), TRAINEE_FIELDWORK_STATE, TRAINEE_FIELDWORK_COUNTRY
        # RESPONSIBLE_SUPERVISOR_NAME, RESPONSIBLE_SUPERVISOR_BACB_ID
        # INDEPENDENT_HOURS, SUPERVISED_HOURS, TOTAL_FIELDWORK, PERCENT_HOURS_SUPERVISED
        
        field_data = {
            "TRAINEE_NAME": config.get("trainee_name", ""),
            "TRAINEE_BACB_ID": config.get("trainee_id", ""),
            "TRAINEE_CERTIFICATE_MONTH/YEAR": month_year_str,
            "TRAINEE_FIELDWORK_STATE": config.get("fieldwork_state", ""),
            "TRAINEE_FIELDWORK_COUNTRY": config.get("fieldwork_country", "USA"),
            
            "RESPONSIBLE_SUPERVISOR_NAME": supervisor_name,
            # We don't have supervisor ID in config yet, leave blank
            "RESPONSIBLE_SUPERVISOR_BACB_ID": "",
            
            "INDEPENDENT_HOURS": f"{stats.independent_hours:.2f}",
            "SUPERVISED_HOURS": f"{stats.supervised_hours:.2f}",
            "TOTAL_FIELDWORK": f"{stats.total_hours:.2f}",
            "PERCENT_HOURS_SUPERVISED": f"{stats.supervision_percent * 100:.1f}%",
            
            # Dates
            "TRAINEE_SIGNATURE_DATE": datetime.date.today().strftime("%Y-%m-%d"),
            "SUPERVISOR_SIGNATURE_DATE": "" # Left for supervisor
        }
        
        # Handle Checkboxes
        # CHECK_SUPERVISED_FIELDWORK
        # This fieldwork included prorated hours for a partial month
        
        # NOTE: pypdf form filling for checkboxes can be tricky. 
        # Usually need to set the value to the 'On' state name.
        # For now we will try setting '/V' to '/Yes' or checking attributes.
        # Update: update_page_form_field_values is the high level API.
        
        # Let's map check boxes if needed.
        # "CHECK_SUPERVISED_FIELDWORK" -> seems to be single selection?
        
        writer.update_page_form_field_values(
            writer.pages[0], 
            field_data,
            auto_regenerate=False # Optimization
        )
        
        # Flatten form to prevent editing matches "Secure" requirement usually
        # But for this user might need to sign it electronically?
        # Typically "Flatten" means fields become content.
        # Let's flatten so values are permanent.
        # writer.flatten() # Optional, maybe let user decide? Sticking to non-flattened for signatures.
        
        output_stream = io.BytesIO()
        writer.write(output_stream)
        output_stream.seek(0)
        
        return output_stream.getvalue()
