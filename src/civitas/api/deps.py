"""Shared FastAPI dependencies."""

from __future__ import annotations

from collections.abc import Generator

from fastapi import Request
from sqlalchemy.orm import Session


def get_db(request: Request) -> Generator[Session, None, None]:
    """Get database session with proper cleanup.

    This dependency yields a session and ensures it is closed after the request,
    preventing connection pool exhaustion.
    """
    session = Session(request.app.state.engine)
    try:
        yield session
    finally:
        session.close()
