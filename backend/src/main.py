"""
FastAPI main application for Video Generator.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .routers import config_router, music_router, video_router, jobs_router
from .routers.history import router as history_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting Video Generator API...")

    # Ensure required directories exist
    directories = [
        "storage/music",
        "storage/temp",
        "storage/outputs",
        "storage/cache",
    ]
    for dir_path in directories:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        logger.info(f"Ensured directory exists: {dir_path}")

    yield

    # Shutdown
    logger.info("Shutting down Video Generator API...")


# Create FastAPI app
app = FastAPI(
    title="Video Generator API",
    description="API para geração automática de vídeos com IA",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(config_router)
app.include_router(music_router)
app.include_router(video_router)
app.include_router(jobs_router)
app.include_router(history_router)

# Mount static files for outputs
outputs_dir = Path("storage/outputs")
outputs_dir.mkdir(parents=True, exist_ok=True)
app.mount("/outputs", StaticFiles(directory=str(outputs_dir)), name="outputs")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Video Generator API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/api")
async def api_info():
    """API information."""
    return {
        "endpoints": {
            "config": "/api/config",
            "music": "/api/music",
            "video": "/api/video",
            "jobs": "/api/jobs",
            "history": "/api/history",
        },
        "documentation": "/docs",
    }
