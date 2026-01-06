# auth/google_oauth.py
"""Google OAuth 2.0 authentication for Streamlit applications.

This module handles the complete OAuth flow including:
- Login URL generation
- Callback/token exchange handling
- Session management
- Authentication guards
"""

import uuid
import streamlit as st
from typing import Optional
from urllib.parse import urlencode

try:
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests
    from google_auth_oauthlib.flow import Flow
except ImportError:
    raise ImportError(
        "Google auth libraries not installed. Run: pip install google-auth google-auth-oauthlib"
    )


class GoogleAuthenticator:
    """Manages Google OAuth 2.0 flow for Streamlit applications.
    
    This class provides a complete authentication solution using Google's
    OAuth 2.0 protocol. It handles user login, token validation, and session
    management within Streamlit's session state.
    
    Attributes:
        client_id: Google OAuth client ID
        client_secret: Google OAuth client secret
        redirect_uri: Callback URL for OAuth flow
        scopes: OAuth scopes to request (default: openid, email, profile)
    
    Example:
        >>> auth = GoogleAuthenticator(
        ...     client_id=st.secrets["google_oauth"]["client_id"],
        ...     client_secret=st.secrets["google_oauth"]["client_secret"],
        ...     redirect_uri=st.secrets["google_oauth"]["redirect_uri"]
        ... )
        >>> user = auth.require_auth()
        >>> if user:
        ...     st.write(f"Welcome, {user['name']}!")
    """
    
    SCOPES = [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile"
    ]
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str
    ):
        """Initialize the GoogleAuthenticator.
        
        Args:
            client_id: OAuth 2.0 client ID from Google Cloud Console
            client_secret: OAuth 2.0 client secret from Google Cloud Console
            redirect_uri: Authorized redirect URI (must match GCP configuration)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        
        # OAuth client configuration
        self._client_config = {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri],
            }
        }
    
    def get_login_url(self, state: Optional[str] = None) -> str:
        """Generate the Google OAuth authorization URL.
        
        Creates a URL that redirects users to Google's login page.
        After authentication, users are redirected back to the app's
        callback URL with an authorization code.
        
        Args:
            state: Optional state parameter for CSRF protection
            
        Returns:
            Authorization URL string
        """
        if state is None:
            state = str(uuid.uuid4())
        
        # Store state in session for verification
        st.session_state["oauth_state"] = state
        
        flow = Flow.from_client_config(
            self._client_config,
            scopes=self.SCOPES,
            redirect_uri=self.redirect_uri
        )
        
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            state=state,
            prompt="select_account"  # Always show account selector
        )
        
        return auth_url
    
    def handle_callback(self, auth_code: str, state: Optional[str] = None) -> dict:
        """Exchange authorization code for tokens and retrieve user info.
        
        Called after Google redirects back to the app with an auth code.
        Exchanges the code for access tokens and fetches the user's
        profile information.
        
        Args:
            auth_code: Authorization code from Google callback
            state: State parameter for CSRF validation
            
        Returns:
            User information dictionary containing:
                - email: User's email address
                - name: User's display name
                - picture: URL to user's profile picture
                - user_id: Generated UUID for this user
                - google_id: Google's user ID (sub claim)
                
        Raises:
            ValueError: If state doesn't match or token validation fails
        """
        # Validate state if provided
        stored_state = st.session_state.get("oauth_state")
        if state and stored_state and state != stored_state:
            raise ValueError("Invalid state parameter - possible CSRF attack")
        
        # Exchange code for tokens
        flow = Flow.from_client_config(
            self._client_config,
            scopes=self.SCOPES,
            redirect_uri=self.redirect_uri
        )
        
        flow.fetch_token(code=auth_code)
        credentials = flow.credentials
        
        # Verify the ID token
        request = google_requests.Request()
        id_info = id_token.verify_oauth2_token(
            credentials.id_token,
            request,
            self.client_id
        )
        
        # Build user info
        user_info = {
            "email": id_info.get("email"),
            "name": id_info.get("name", id_info.get("email", "User")),
            "picture": id_info.get("picture", ""),
            "google_id": id_info.get("sub"),
            "user_id": str(uuid.uuid4()),  # Generate app-specific user ID
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
        }
        
        # Store in session
        st.session_state["user"] = user_info
        st.session_state["authenticated"] = True
        
        # Clear OAuth state
        if "oauth_state" in st.session_state:
            del st.session_state["oauth_state"]
        
        return user_info
    
    def get_current_user(self) -> Optional[dict]:
        """Get the currently authenticated user from session state.
        
        Returns:
            User info dict if authenticated, None otherwise
        """
        if st.session_state.get("authenticated", False):
            return st.session_state.get("user")
        return None
    
    def is_authenticated(self) -> bool:
        """Check if a user is currently authenticated.
        
        Returns:
            True if user is authenticated, False otherwise
        """
        return st.session_state.get("authenticated", False)
    
    def logout(self) -> None:
        """Log out the current user and clear session state.
        
        Removes all authentication-related data from session state.
        Note: This does not revoke the OAuth tokens on Google's end.
        """
        keys_to_remove = ["user", "authenticated", "oauth_state"]
        for key in keys_to_remove:
            if key in st.session_state:
                del st.session_state[key]
    
    def require_auth(self) -> Optional[dict]:
        """Authentication guard that handles the complete OAuth flow.
        
        This is the main entry point for authentication. It:
        1. Checks if user is already authenticated
        2. Handles OAuth callbacks (code in query params)
        3. Displays login button if not authenticated
        
        Returns:
            User info dict if authenticated, None if showing login
            
        Example:
            >>> auth = GoogleAuthenticator(...)
            >>> user = auth.require_auth()
            >>> if not user:
            ...     st.stop()  # Stop execution if not authenticated
            >>> # User is authenticated, continue with app
        """
        # Check for existing authentication
        if self.is_authenticated():
            return self.get_current_user()
        
        # Check for OAuth callback (code in URL)
        query_params = st.query_params
        if "code" in query_params:
            try:
                auth_code = query_params.get("code")
                state = query_params.get("state")
                
                user = self.handle_callback(auth_code, state)
                
                # Clear query params and rerun
                st.query_params.clear()
                st.rerun()
                
            except Exception as e:
                st.error(f"Authentication failed: {str(e)}")
                st.query_params.clear()
                return None
        
        # Not authenticated - show login button
        self._render_login_page()
        return None
    
    def _render_login_page(self) -> None:
        """Render the login page with Google sign-in button.
        
        Displays a styled login interface following the French Clinical
        design system using native Streamlit components.
        """
        import base64
        from utils.logo import get_logo_svg
        
        # Get Logo as base64
        logo_svg = get_logo_svg(height_px=150)
        logo_b64 = base64.b64encode(logo_svg.encode('utf-8')).decode("utf-8")
        
        # Inject CSS for French Clinical styling
        st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Inter:wght@400;500;600&display=swap');
            
            /* Style the link button to have sharp corners */
            div[data-testid="stLinkButton"] > a {
                border-radius: 0px !important;
                border: 1px solid #000000 !important;
                background-color: #FFFFFF !important;
                color: #000000 !important;
                font-weight: 600 !important;
                text-transform: uppercase !important;
            }
            
            div[data-testid="stLinkButton"] > a:hover {
                background-color: #000000 !important;
                color: #800000 !important; /* Oxblood red on hover */
            }
        </style>
        """, unsafe_allow_html=True)
        
        # Spacer
        st.write("")
        st.write("")
        
        # Center content using columns
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            # Logo
            st.image(f"data:image/svg+xml;base64,{logo_b64}", width=150)
            
            st.write("")
            
            # Title
            st.markdown("## FIELDWORK LEDGER")
            st.caption("SECURE CLINICAL TRACKING ENVIRONMENT")
            
            st.write("")
            st.write("")
            
            # Login Button using native st.link_button with Google logo
            login_url = self.get_login_url()
            st.link_button("🇬 CONTINUE WITH GOOGLE", login_url, use_container_width=True)
            
            # Divider
            st.markdown("""
            <div style="width: 60px; height: 2px; background-color: #800000; margin: 2rem auto;"></div>
            """, unsafe_allow_html=True)
            
            # Terms text
            st.caption(
                "Your data is exclusively yours. This application is a stateless logic engine "
                "that connects directly to your private Google Sheet."
            )


def render_user_profile(user: dict) -> None:
    """Render the user profile component in the sidebar.
    
    Displays the authenticated user's information and sign-out option.
    Should be called in the sidebar after successful authentication.
    
    Args:
        user: User info dictionary from authentication
    """
    with st.sidebar:
        st.markdown("---")
        
        # User info
        col1, col2 = st.columns([1, 3])
        with col1:
            if user.get("picture"):
                st.image(user["picture"], width=40)
            else:
                st.markdown("👤")
        with col2:
            st.markdown(f"**{user.get('name', 'User')}**")
            st.caption(user.get("email", ""))
        
        # Sign out button
        if st.button("🚪 Sign Out"):
            from auth import GoogleAuthenticator
            # Clear session - actual logout
            for key in list(st.session_state.keys()):
                if key in ["user", "authenticated", "oauth_state"]:
                    del st.session_state[key]
            st.rerun()
