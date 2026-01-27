"""FastAPI application for Civitas.

Exposes legislative data from the Python backend to the Next.js frontend.
"""

from .main import app, create_app

__all__ = ["app", "create_app"]
