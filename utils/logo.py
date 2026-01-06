import streamlit as st
import base64

def get_logo_svg(height_px=200):
    """
    Returns the raw SVG string for the 'Metric Prism' logo.
    Adjusted to ensure the Oxblood square is distinct and separate.
    """
    return f"""
    <svg width="{height_px}" height="{height_px}" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
      <rect width="200" height="200" fill="#FFFFFF" />

      <rect x="5" y="5" width="190" height="190" fill="none" stroke="#000000" stroke-width="4" />

      <rect x="35" y="110" width="30" height="50" fill="#000000" />

      <rect x="85" y="70" width="30" height="90" fill="#000000" />

      <rect x="135" y="25" width="30" height="30" fill="#800000" />
      
      <rect x="135" y="65" width="30" height="95" fill="#000000" />
    </svg>
    """

def render_sidebar_logo():
    """
    Renders the logo specifically for the Sidebar with correct padding.
    """
    svg = get_logo_svg(height_px=150)
    b64 = base64.b64encode(svg.encode('utf-8')).decode("utf-8")
    
    # Injected HTML with specific margin to align with Streamlit's sidebar padding
    st.sidebar.markdown(
        f"""
        <div style="display: flex; justify-content: center; margin-bottom: 20px;">
            <img src="data:image/svg+xml;base64,{b64}" alt="BCBA Tracker Logo">
        </div>
        """,
        unsafe_allow_html=True
    )
