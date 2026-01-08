"""
Modelos de jobs e status.
"""

from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class JobStatusEnum(str, Enum):
    PENDING = "pending"
    PROCESSING_TEXT = "processing_text"
    GENERATING_AUDIO = "generating_audio"
    MERGING_AUDIO = "merging_audio"
    TRANSCRIBING = "transcribing"
    ANALYZING_SCENES = "analyzing_scenes"
    SELECTING_MUSIC = "selecting_music"
    GENERATING_IMAGES = "generating_images"
    MIXING_AUDIO = "mixing_audio"
    COMPOSING_VIDEO = "composing_video"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobStatus(BaseModel):
    """Status atual do job."""
    job_id: str
    status: JobStatusEnum
    progress: float
    current_step: str
    details: Dict[str, Any] = {}
    logs: list[str] = []
    started_at: datetime
    updated_at: datetime
    error: Optional[str] = None


class JobCreate(BaseModel):
    """Dados para criação de um job."""
    text: str
    config_override: Optional[Dict[str, Any]] = None


class JobResponse(BaseModel):
    """Resposta após criação de job."""
    job_id: str
    status: JobStatusEnum
    message: str
    estimated_duration_seconds: Optional[int] = None


class JobResult(BaseModel):
    """Resultado final do job."""
    job_id: str
    status: JobStatusEnum
    video_path: Optional[str] = None
    video_url: Optional[str] = None
    duration_seconds: Optional[float] = None
    scenes_count: Optional[int] = None
    file_size: Optional[int] = None
    processing_time_seconds: Optional[float] = None
    error: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
