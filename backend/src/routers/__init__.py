"""
Routers package for the video generator API.
"""

from .config import router as config_router
from .music import router as music_router
from .video import router as video_router
from .jobs import router as jobs_router

__all__ = [
    "config_router",
    "music_router",
    "video_router",
    "jobs_router",
]
