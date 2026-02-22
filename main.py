"""FieldOps AI — FastAPI Application Entry Point."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import init_db
from routes.voice import router as voice_router
from routes.dashboard import router as dashboard_router
from routes.health import router as health_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)-25s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info("=" * 60)
    logger.info("FieldOps AI Backend — Starting up")
    logger.info("=" * 60)
    init_db()
    logger.info("Database initialized")
    yield
    logger.info("FieldOps AI Backend — Shutting down")


app = FastAPI(
    title="FieldOps AI",
    description="Zero-UI, Voice-Driven Autonomous ERP for Field Service Workers",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(health_router)
app.include_router(voice_router)
app.include_router(dashboard_router)


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "service": "FieldOps AI",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health",
    }
