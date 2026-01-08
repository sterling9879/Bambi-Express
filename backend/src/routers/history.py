"""
Router para histórico de vídeos e elementos.
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from typing import Optional
from pathlib import Path

from ..models.history import (
    Channel, ChannelCreate, ChannelUpdate,
    VideoHistory, VideoHistoryList,
    Element, ElementList, ElementType,
    HistoryStats
)
from ..services.history_service import get_history_service

router = APIRouter(prefix="/api/history", tags=["history"])


# ============== CHANNELS ==============


@router.get("/channels", response_model=list[Channel])
async def list_channels():
    """Lista todos os canais."""
    service = get_history_service()
    return service.list_channels()


@router.get("/channels/{channel_id}", response_model=Channel)
async def get_channel(channel_id: str):
    """Busca um canal pelo ID."""
    service = get_history_service()
    channel = service.get_channel(channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Canal não encontrado")
    return channel


@router.post("/channels", response_model=Channel)
async def create_channel(data: ChannelCreate):
    """Cria um novo canal."""
    service = get_history_service()
    return service.create_channel(data)


@router.put("/channels/{channel_id}", response_model=Channel)
async def update_channel(channel_id: str, data: ChannelUpdate):
    """Atualiza um canal."""
    service = get_history_service()
    channel = service.update_channel(channel_id, data)
    if not channel:
        raise HTTPException(status_code=404, detail="Canal não encontrado")
    return channel


@router.delete("/channels/{channel_id}")
async def delete_channel(channel_id: str):
    """Deleta um canal."""
    service = get_history_service()
    if not service.delete_channel(channel_id):
        raise HTTPException(status_code=404, detail="Canal não encontrado")
    return {"message": "Canal deletado"}


# ============== VIDEO HISTORY ==============


@router.get("/videos", response_model=VideoHistoryList)
async def list_videos(
    channel_id: Optional[str] = Query(None, description="Filtrar por canal"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="Buscar por título ou texto")
):
    """Lista histórico de vídeos."""
    service = get_history_service()
    videos, total = service.list_videos(
        channel_id=channel_id,
        page=page,
        limit=limit,
        search=search
    )
    return VideoHistoryList(videos=videos, total=total, page=page, limit=limit)


@router.get("/videos/{video_id}", response_model=VideoHistory)
async def get_video(video_id: str):
    """Busca um vídeo pelo ID."""
    service = get_history_service()
    video = service.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Vídeo não encontrado")
    return video


@router.get("/videos/{video_id}/stream")
async def stream_video(video_id: str):
    """Stream do arquivo de vídeo."""
    service = get_history_service()
    video = service.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Vídeo não encontrado")

    video_path = Path(video.video_path)
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo de vídeo não encontrado")

    return FileResponse(
        video_path,
        media_type="video/mp4",
        filename=f"{video.title}.mp4"
    )


@router.get("/videos/{video_id}/thumbnail")
async def get_thumbnail(video_id: str):
    """Retorna thumbnail do vídeo."""
    service = get_history_service()
    video = service.get_video(video_id)
    if not video or not video.thumbnail_path:
        raise HTTPException(status_code=404, detail="Thumbnail não encontrada")

    thumb_path = Path(video.thumbnail_path)
    if not thumb_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo de thumbnail não encontrado")

    return FileResponse(thumb_path, media_type="image/jpeg")


@router.get("/videos/{video_id}/download")
async def download_video(video_id: str):
    """Download do arquivo de vídeo."""
    service = get_history_service()
    video = service.get_video(video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Vídeo não encontrado")

    video_path = Path(video.video_path)
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo de vídeo não encontrado")

    return FileResponse(
        video_path,
        media_type="video/mp4",
        filename=f"{video.title}.mp4",
        headers={"Content-Disposition": f'attachment; filename="{video.title}.mp4"'}
    )


@router.patch("/videos/{video_id}/channel")
async def move_video_to_channel(video_id: str, channel_id: Optional[str] = None):
    """Move um vídeo para outro canal."""
    service = get_history_service()
    video = service.update_video_channel(video_id, channel_id)
    if not video:
        raise HTTPException(status_code=404, detail="Vídeo não encontrado")
    return video


@router.delete("/videos/{video_id}")
async def delete_video(
    video_id: str,
    delete_files: bool = Query(False, description="Também deletar arquivos físicos")
):
    """Deleta um vídeo do histórico."""
    service = get_history_service()
    if not service.delete_video(video_id, delete_files):
        raise HTTPException(status_code=404, detail="Vídeo não encontrado")
    return {"message": "Vídeo deletado"}


# ============== ELEMENT HISTORY ==============


@router.get("/elements", response_model=ElementList)
async def list_elements(
    job_id: Optional[str] = Query(None, description="Filtrar por job"),
    element_type: Optional[ElementType] = Query(None, description="Filtrar por tipo"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200)
):
    """Lista elementos (imagens e áudios) gerados."""
    service = get_history_service()
    elements, total = service.list_elements(
        job_id=job_id,
        element_type=element_type,
        page=page,
        limit=limit
    )
    return ElementList(elements=elements, total=total)


@router.get("/elements/{element_id}/file")
async def get_element_file(element_id: str):
    """Retorna arquivo do elemento."""
    service = get_history_service()
    elements, _ = service.list_elements()

    element = None
    for e in elements:
        if e.id == element_id:
            element = e
            break

    if not element:
        raise HTTPException(status_code=404, detail="Elemento não encontrado")

    file_path = Path(element.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    # Determine media type
    suffix = file_path.suffix.lower()
    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".m4a": "audio/mp4"
    }
    media_type = media_types.get(suffix, "application/octet-stream")

    return FileResponse(file_path, media_type=media_type)


@router.delete("/elements/job/{job_id}")
async def delete_job_elements(job_id: str):
    """Deleta todos os elementos de um job."""
    service = get_history_service()
    count = service.delete_elements_by_job(job_id)
    return {"message": f"{count} elementos deletados"}


# ============== STATS ==============


@router.get("/stats", response_model=HistoryStats)
async def get_stats():
    """Retorna estatísticas do histórico."""
    service = get_history_service()
    return service.get_stats()
