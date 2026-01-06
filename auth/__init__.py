# auth/__init__.py
"""Authentication module for BCBA Fieldwork Tracker V2."""

from .google_oauth import GoogleAuthenticator

__all__ = ["GoogleAuthenticator"]
