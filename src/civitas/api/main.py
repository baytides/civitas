"""FastAPI application entry point."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from civitas.db.models import get_database_url, get_engine


def create_app(
    db_url: str | None = None,
    debug: bool = False,
) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        db_url: Database URL. Defaults to DATABASE_URL env var or sqlite.
        debug: Enable debug mode.

    Returns:
        Configured FastAPI application.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        """Application lifespan handler."""
        # Startup - use flexible database URL getter
        url = get_database_url(db_url)
        app.state.engine = get_engine(url)
        yield
        # Shutdown
        app.state.engine.dispose()

    app = FastAPI(
        title="Civitas API",
        description="API for accessing legislative data and P2025 tracking",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
        debug=debug,
    )

    # CORS configuration
    origins = [
        "http://localhost:3000",  # Next.js dev
        "https://projectcivitas.com",
        "https://www.projectcivitas.com",
        "https://civitas-bft.pages.dev",  # Cloudflare Pages
        "http://civitas-bft.pages.dev",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    from civitas.api.routers import (
        cases,
        executive_orders,
        legislation,
        objectives,
        resistance,
        search,
        states,
    )

    app.include_router(objectives.router, prefix="/api/v1", tags=["objectives"])
    app.include_router(executive_orders.router, prefix="/api/v1", tags=["executive-orders"])
    app.include_router(legislation.router, prefix="/api/v1", tags=["legislation"])
    app.include_router(cases.router, prefix="/api/v1", tags=["cases"])
    app.include_router(states.router, prefix="/api/v1", tags=["states"])
    app.include_router(resistance.router, prefix="/api/v1", tags=["resistance"])
    app.include_router(search.router, prefix="/api/v1", tags=["search"])

    @app.get("/api/health")
    async def health_check() -> dict:
        """Health check endpoint."""
        return {"status": "healthy", "version": "1.0.0"}

    return app


# Default application instance
app = create_app()
