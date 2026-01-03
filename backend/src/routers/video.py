"""
Router para geração de vídeos.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uuid
from datetime import datetime

from ..models.config import FullConfig
from ..models.job import JobCreate, JobResponse, JobStatusEnum
from ..services.text_processor import TextProcessor

router = APIRouter(prefix="/api/video", tags=["video"])


class TextAnalysisRequest(BaseModel):
    text: str


class TextAnalysisResponse(BaseModel):
    char_count: int
    word_count: int
    estimated_duration_seconds: float
    estimated_chunks: int


@router.post("/analyze-text", response_model=TextAnalysisResponse)
async def analyze_text(request: TextAnalysisRequest):
    """
    Analisa texto e retorna estatísticas e estimativas.
    """
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Texto não pode estar vazio")

    processor = TextProcessor()
    chunks = processor.process(text)

    return TextAnalysisResponse(
        char_count=len(text),
        word_count=len(text.split()),
        estimated_duration_seconds=processor.estimate_duration(text),
        estimated_chunks=len(chunks)
    )


class GenerateVideoRequest(BaseModel):
    text: str
    title: Optional[str] = None
    channel_id: Optional[str] = None
    config_override: Optional[Dict[str, Any]] = None


class GenerateVideoResponse(BaseModel):
    job_id: str
    status: str
    message: str
    estimated_duration_seconds: Optional[float] = None


# In-memory job storage (in production, use Redis or database)
_jobs_db: Dict[str, Dict] = {}


@router.post("/generate", response_model=GenerateVideoResponse)
async def generate_video(
    request: GenerateVideoRequest,
    background_tasks: BackgroundTasks
):
    """
    Inicia geração de vídeo a partir do texto.
    Retorna imediatamente com um job_id para acompanhamento.
    """
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Texto não pode estar vazio")

    # Validate text length
    if len(text) > 50000:
        raise HTTPException(
            status_code=400,
            detail="Texto muito longo. Máximo de 50.000 caracteres."
        )

    # Generate job ID
    job_id = str(uuid.uuid4())

    # Calculate estimated duration
    processor = TextProcessor()
    estimated_duration = processor.estimate_duration(text)

    # Generate title if not provided
    title = request.title or f"Vídeo {datetime.now().strftime('%d/%m %H:%M')}"

    # Store job info
    _jobs_db[job_id] = {
        "id": job_id,
        "text": text,
        "title": title,
        "channel_id": request.channel_id,
        "config_override": request.config_override,
        "status": JobStatusEnum.PENDING.value,
        "progress": 0,
        "current_step": "Aguardando",
        "created_at": datetime.now().isoformat(),
        "started_at": None,
        "completed_at": None,
        "error": None,
        "result": None
    }

    # Start background task
    background_tasks.add_task(
        _run_video_generation,
        job_id,
        text,
        title,
        request.channel_id,
        request.config_override
    )

    return GenerateVideoResponse(
        job_id=job_id,
        status="pending",
        message="Geração de vídeo iniciada",
        estimated_duration_seconds=estimated_duration
    )


async def _run_video_generation(
    job_id: str,
    text: str,
    title: str,
    channel_id: Optional[str],
    config_override: Optional[Dict[str, Any]] = None
):
    """
    Background task para executar a geração de vídeo.
    """
    import json
    from pathlib import Path
    from ..services.job_orchestrator import JobOrchestrator
    from ..services.history_service import get_history_service
    from ..models.job import JobStatus
    from ..models.history import VideoHistoryCreate

    def status_callback(status: JobStatus):
        """Update job status in memory."""
        if job_id in _jobs_db:
            _jobs_db[job_id].update({
                "status": status.status.value,
                "progress": status.progress,
                "current_step": status.current_step,
                "updated_at": status.updated_at.isoformat(),
                "error": status.error,
                "details": status.details
            })

    try:
        # Load config
        config_file = Path("storage/config.json")
        if config_file.exists():
            with open(config_file) as f:
                config_data = json.load(f)
        else:
            config_data = {}

        # Apply overrides
        if config_override:
            for key, value in config_override.items():
                if isinstance(value, dict) and key in config_data:
                    config_data[key].update(value)
                else:
                    config_data[key] = value

        config = FullConfig(**config_data)

        # Update job as started
        _jobs_db[job_id]["started_at"] = datetime.now().isoformat()

        # Run orchestrator
        orchestrator = JobOrchestrator(
            config=config,
            status_callback=status_callback
        )

        result = await orchestrator.run(job_id, text)

        # Get video info
        video_path = result if isinstance(result, str) else result.get("video_path", result)
        video_file = Path(video_path)

        # Update job as completed
        _jobs_db[job_id].update({
            "status": JobStatusEnum.COMPLETED.value,
            "progress": 1.0,
            "completed_at": datetime.now().isoformat(),
            "result": {
                "video_path": video_path
            }
        })

        # Save to history
        try:
            history_service = get_history_service()

            # Get video file stats
            file_size = video_file.stat().st_size if video_file.exists() else 0

            # Get details from orchestrator if available
            details = _jobs_db[job_id].get("details", {})
            duration = details.get("duration_seconds", 0)
            scenes_count = details.get("scenes_count", 0)
            resolution = f"{config.ffmpeg.resolution.width}x{config.ffmpeg.resolution.height}"

            history_service.add_video(VideoHistoryCreate(
                job_id=job_id,
                title=title,
                channel_id=channel_id,
                text_preview=text[:200],
                video_path=video_path,
                duration_seconds=duration,
                scenes_count=scenes_count,
                file_size=file_size,
                resolution=resolution
            ))
        except Exception as hist_error:
            # Log but don't fail the job
            import logging
            logging.error(f"Failed to save video to history: {hist_error}")

    except Exception as e:
        # Update job as failed
        _jobs_db[job_id].update({
            "status": JobStatusEnum.FAILED.value,
            "error": str(e),
            "completed_at": datetime.now().isoformat()
        })


def get_job(job_id: str) -> Optional[Dict]:
    """Get job from storage."""
    return _jobs_db.get(job_id)


def update_job(job_id: str, updates: Dict):
    """Update job in storage."""
    if job_id in _jobs_db:
        _jobs_db[job_id].update(updates)
