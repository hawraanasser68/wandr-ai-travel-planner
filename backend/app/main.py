"""
FastAPI Application Entry Point
--------------------------------
- Lifespan: runs RAG ingestion on startup (skips if already populated)
- CORS: allows requests from the React dev server and production frontend
- Routers: /auth and /agent
- Health check: GET /health (used by Docker and load balancers)
"""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import agent as agent_router
from app.api import auth as auth_router
from app.config import get_settings
from app.rag.ingestion import ingest_documents

log = structlog.get_logger()


@asynccontextmanager #lets you define async startup and shutdown logic in one function using yield.
async def lifespan(app: FastAPI):
    """
    Code before `yield` runs on startup; code after runs on shutdown.
    We use this to ingest RAG documents once when the server first starts.
    """
    log.info("app.startup")
    settings = get_settings()

    await ingest_documents()

    log.info("app.ready", env=settings.app_env)

    yield  # ← server is running and handling requests

    log.info("app.shutdown")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="AI Travel Planner",
        version="1.0.0",
        docs_url="/docs" if settings.app_env == "development" else None,
        redoc_url=None, #ReDoc is a tool that automatically generates API documentation from your FastAPI endpoints.
        lifespan=lifespan,
    )

    # ── CORS ───────────────────────────────────────────────────────────────────
    # Allow the React dev server (port 5173) and production origin.
    # Adjust ALLOWED_ORIGINS in production to your actual domain.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",   # Vite dev server
            "http://localhost:3000",   # alternative dev port
        ],
        allow_credentials=True,        # needed for Authorization header
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ────────────────────────────────────────────────────────────────
    app.include_router(auth_router.router)
    app.include_router(agent_router.router)

    # ── Health check ───────────────────────────────────────────────────────────
    @app.get("/health", tags=["health"])
    async def health():
        return {"status": "ok", "env": settings.app_env}

    return app


# Uvicorn target: uvicorn app.main:app --reload
app = create_app()
