"""
Router para gerenciamento de jobs.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime

from .video import _jobs_db, get_job
from ..models.job import JobStatusEnum

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: float
    current_step: str
    details: Dict[str, Any] = {}
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None


class JobResultResponse(BaseModel):
    job_id: str
    status: str
    video_path: Optional[str] = None
    video_url: Optional[str] = None
    duration_seconds: Optional[float] = None
    scenes_count: Optional[int] = None
    file_size: Optional[int] = None
    processing_time_seconds: Optional[float] = None


class JobListItem(BaseModel):
    job_id: str
    status: str
    progress: float
    current_step: str
    created_at: str
    completed_at: Optional[str] = None


class JobListResponse(BaseModel):
    jobs: List[JobListItem]
    total: int


@router.get("", response_model=JobListResponse)
async def list_jobs(
    status: Optional[str] = None,
    limit: int = 20
):
    """
    Lista todos os jobs recentes.
    """
    jobs = list(_jobs_db.values())

    # Filter by status
    if status:
        jobs = [j for j in jobs if j.get("status") == status]

    # Sort by created_at (newest first)
    jobs.sort(key=lambda j: j.get("created_at", ""), reverse=True)

    # Limit
    jobs = jobs[:limit]

    job_items = [
        JobListItem(
            job_id=j["id"],
            status=j.get("status", "unknown"),
            progress=j.get("progress", 0),
            current_step=j.get("current_step", ""),
            created_at=j.get("created_at", ""),
            completed_at=j.get("completed_at")
        )
        for j in jobs
    ]

    return JobListResponse(
        jobs=job_items,
        total=len(_jobs_db)
    )


@router.get("/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Retorna status atual do job.
    """
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")

    return JobStatusResponse(
        job_id=job["id"],
        status=job.get("status", "unknown"),
        progress=job.get("progress", 0),
        current_step=job.get("current_step", ""),
        details=job.get("details", {}),
        created_at=job.get("created_at", ""),
        started_at=job.get("started_at"),
        completed_at=job.get("completed_at"),
        error=job.get("error")
    )


@router.get("/{job_id}/result", response_model=JobResultResponse)
async def get_job_result(job_id: str):
    """
    Retorna resultado do job (se completo).
    """
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")

    status = job.get("status")
    if status != JobStatusEnum.COMPLETED.value:
        return JobResultResponse(
            job_id=job_id,
            status=status
        )

    result = job.get("result", {})
    details = job.get("details", {})

    # Calculate processing time
    processing_time = None
    if job.get("started_at") and job.get("completed_at"):
        try:
            started = datetime.fromisoformat(job["started_at"])
            completed = datetime.fromisoformat(job["completed_at"])
            processing_time = (completed - started).total_seconds()
        except Exception:
            pass

    # Generate video URL
    video_path = result.get("video_path")
    video_url = f"/api/jobs/{job_id}/download" if video_path else None

    return JobResultResponse(
        job_id=job_id,
        status=status,
        video_path=video_path,
        video_url=video_url,
        duration_seconds=details.get("duration"),
        scenes_count=details.get("scenes"),
        file_size=details.get("file_size"),
        processing_time_seconds=processing_time
    )


@router.get("/{job_id}/download")
async def download_video(job_id: str):
    """
    Download do vídeo gerado.
    """
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")

    if job.get("status") != JobStatusEnum.COMPLETED.value:
        raise HTTPException(status_code=400, detail="Job ainda não concluído")

    result = job.get("result", {})
    video_path = result.get("video_path")

    if not video_path:
        raise HTTPException(status_code=404, detail="Vídeo não encontrado")

    path = Path(video_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    return FileResponse(
        path,
        media_type="video/mp4",
        filename=path.name
    )


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str):
    """
    Cancela um job em execução.
    """
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")

    status = job.get("status")
    if status in [JobStatusEnum.COMPLETED.value, JobStatusEnum.FAILED.value]:
        raise HTTPException(status_code=400, detail="Job já finalizado")

    # Update job status
    _jobs_db[job_id]["status"] = JobStatusEnum.CANCELLED.value
    _jobs_db[job_id]["completed_at"] = datetime.now().isoformat()

    return {"status": "cancelled", "job_id": job_id}


@router.delete("/{job_id}")
async def delete_job(job_id: str):
    """
    Remove um job e seus arquivos.
    """
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado")

    # Delete video file if exists
    result = job.get("result", {})
    video_path = result.get("video_path")
    if video_path:
        path = Path(video_path)
        if path.exists():
            path.unlink()

    # Remove from database
    del _jobs_db[job_id]

    return {"status": "deleted", "job_id": job_id}
