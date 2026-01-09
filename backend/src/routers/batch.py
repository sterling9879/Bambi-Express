"""
Router para processamento em batch de roteiros.
"""

import json
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ..models.config import FullConfig
from ..models.batch import (
    BatchStatusEnum,
    BatchItemStatusEnum,
    BatchItem,
    BatchStatus,
    BatchCreate,
    BatchResponse,
    BatchListItem,
    BatchListResponse,
    BatchItemUpdate
)
from ..services.batch_processor import (
    BatchProcessor,
    _batches_db,
    _cleanup_old_batches,
    get_batch,
    update_batch,
    get_batch_processor,
    store_batch_processor,
    remove_batch_processor
)
from ..services.text_processor import TextProcessor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/batch", tags=["batch"])


class BatchItemInput(BaseModel):
    """Input para um item do batch."""
    title: str = Field(..., description="Título do roteiro")
    text: str = Field(..., description="Conteúdo do roteiro")


class CreateBatchRequest(BaseModel):
    """Request para criar um novo batch."""
    name: str = Field(..., description="Nome do batch")
    items: List[BatchItemInput] = Field(..., description="Lista de roteiros")
    config_override: Optional[Dict[str, Any]] = None
    channel_id: Optional[str] = None


class BatchStatusResponse(BaseModel):
    """Resposta de status do batch."""
    batch_id: str
    name: str
    status: str
    total_items: int
    completed_items: int
    failed_items: int
    current_item_index: int
    current_item_title: Optional[str] = None
    current_item_step: Optional[str] = None
    progress: float
    items: List[Dict[str, Any]]
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None


class BatchAnalysisResponse(BaseModel):
    """Resposta da análise de batch."""
    total_items: int
    total_characters: int
    total_words: int
    estimated_total_duration_seconds: float
    estimated_processing_time_minutes: float
    items_analysis: List[Dict[str, Any]]


@router.post("/analyze")
async def analyze_batch(request: CreateBatchRequest) -> BatchAnalysisResponse:
    """
    Analisa roteiros do batch e retorna estimativas.
    Útil para preview antes de iniciar o processamento.
    """
    if not request.items:
        raise HTTPException(status_code=400, detail="Nenhum roteiro fornecido")

    processor = TextProcessor()
    items_analysis = []
    total_chars = 0
    total_words = 0
    total_duration = 0

    for idx, item in enumerate(request.items):
        text = item.text.strip()
        if not text:
            items_analysis.append({
                "index": idx,
                "title": item.title,
                "error": "Texto vazio"
            })
            continue

        chars = len(text)
        words = len(text.split())
        duration = processor.estimate_duration(text)

        items_analysis.append({
            "index": idx,
            "title": item.title,
            "char_count": chars,
            "word_count": words,
            "estimated_duration_seconds": duration,
            "estimated_chunks": len(processor.process(text))
        })

        total_chars += chars
        total_words += words
        total_duration += duration

    # Estimar tempo de processamento (aproximadamente 3-5x o tempo do vídeo)
    estimated_processing = (total_duration / 60) * 4

    return BatchAnalysisResponse(
        total_items=len(request.items),
        total_characters=total_chars,
        total_words=total_words,
        estimated_total_duration_seconds=total_duration,
        estimated_processing_time_minutes=estimated_processing,
        items_analysis=items_analysis
    )


@router.post("", response_model=BatchResponse)
async def create_batch(
    request: CreateBatchRequest,
    background_tasks: BackgroundTasks
):
    """
    Cria e inicia processamento de um batch de roteiros.
    Retorna imediatamente com um batch_id para acompanhamento.
    """
    if not request.items:
        raise HTTPException(status_code=400, detail="Nenhum roteiro fornecido")

    # Validar itens
    valid_items = []
    for item in request.items:
        text = item.text.strip()
        if not text:
            continue
        if len(text) > 50000:
            raise HTTPException(
                status_code=400,
                detail=f"Roteiro '{item.title}' excede 50.000 caracteres"
            )
        valid_items.append({"title": item.title, "text": text})

    if not valid_items:
        raise HTTPException(status_code=400, detail="Nenhum roteiro válido fornecido")

    # Cleanup batches antigos
    _cleanup_old_batches()

    # Gerar ID do batch
    batch_id = str(uuid.uuid4())

    # Calcular estimativa
    processor = TextProcessor()
    total_duration = sum(
        processor.estimate_duration(item["text"])
        for item in valid_items
    )

    # Armazenar batch
    _batches_db[batch_id] = {
        "id": batch_id,
        "name": request.name,
        "status": BatchStatusEnum.PENDING.value,
        "total_items": len(valid_items),
        "completed_items": 0,
        "failed_items": 0,
        "current_item_index": 0,
        "progress": 0.0,
        "items": [
            {
                "id": f"{batch_id}_{idx}",
                "title": item["title"],
                "text": item["text"][:100] + "..." if len(item["text"]) > 100 else item["text"],
                "status": BatchItemStatusEnum.PENDING.value,
                "progress": 0,
                "current_step": "Aguardando"
            }
            for idx, item in enumerate(valid_items)
        ],
        "config_override": request.config_override,
        "channel_id": request.channel_id,
        "created_at": datetime.now().isoformat(),
        "started_at": None,
        "completed_at": None,
        "error": None
    }

    # Iniciar processamento em background
    background_tasks.add_task(
        _run_batch_processing,
        batch_id,
        request.name,
        valid_items,
        request.channel_id,
        request.config_override
    )

    return BatchResponse(
        batch_id=batch_id,
        status=BatchStatusEnum.PENDING,
        message=f"Batch criado com {len(valid_items)} roteiros",
        total_items=len(valid_items),
        estimated_total_duration_seconds=total_duration
    )


async def _run_batch_processing(
    batch_id: str,
    name: str,
    items: List[Dict[str, str]],
    channel_id: Optional[str],
    config_override: Optional[Dict[str, Any]]
):
    """Background task para processar o batch."""
    try:
        # Carregar configuração
        config_file = Path("storage/config.json")
        if config_file.exists():
            with open(config_file) as f:
                config_data = json.load(f)
        else:
            config_data = {}

        # Aplicar overrides
        if config_override:
            for key, value in config_override.items():
                if isinstance(value, dict) and key in config_data:
                    config_data[key].update(value)
                else:
                    config_data[key] = value

        config = FullConfig(**config_data)

        # Callback para atualizar status no storage
        def status_callback(status: BatchStatus):
            try:
                _batches_db[batch_id].update({
                    "status": status.status.value,
                    "completed_items": status.completed_items,
                    "failed_items": status.failed_items,
                    "current_item_index": status.current_item_index,
                    "progress": status.progress,
                    "started_at": status.started_at.isoformat() if status.started_at else None,
                    "completed_at": status.completed_at.isoformat() if status.completed_at else None,
                    "error": status.error,
                    "items": [
                        {
                            "id": item.id,
                            "title": item.title,
                            "status": item.status.value,
                            "job_id": item.job_id,
                            "progress": item.progress,
                            "current_step": item.current_step,
                            "video_path": item.video_path,
                            "error": item.error,
                            "started_at": item.started_at.isoformat() if item.started_at else None,
                            "completed_at": item.completed_at.isoformat() if item.completed_at else None,
                            "duration_seconds": item.duration_seconds
                        }
                        for item in status.items
                    ]
                })
            except Exception as e:
                logger.error(f"Error updating batch status: {e}")

        # Criar processor e armazenar referência
        processor = BatchProcessor(config=config, status_callback=status_callback)
        store_batch_processor(batch_id, processor)

        # Processar batch
        await processor.process(
            batch_id=batch_id,
            name=name,
            items=items,
            channel_id=channel_id,
            config_override=config_override
        )

    except Exception as e:
        logger.error(f"Batch processing failed: {e}")
        if batch_id in _batches_db:
            _batches_db[batch_id].update({
                "status": BatchStatusEnum.FAILED.value,
                "error": str(e)[:500],
                "completed_at": datetime.now().isoformat()
            })

    finally:
        # Remover processor da memória
        remove_batch_processor(batch_id)


@router.get("", response_model=BatchListResponse)
async def list_batches(
    status: Optional[str] = None,
    limit: int = 20
):
    """Lista todos os batches recentes."""
    batches = list(_batches_db.values())

    # Filtrar por status
    if status:
        batches = [b for b in batches if b.get("status") == status]

    # Ordenar por data de criação
    batches.sort(key=lambda b: b.get("created_at", ""), reverse=True)

    # Limitar
    batches = batches[:limit]

    batch_items = [
        BatchListItem(
            batch_id=b["id"],
            name=b.get("name", ""),
            status=BatchStatusEnum(b.get("status", "pending")),
            total_items=b.get("total_items", 0),
            completed_items=b.get("completed_items", 0),
            failed_items=b.get("failed_items", 0),
            progress=b.get("progress", 0),
            created_at=b.get("created_at", ""),
            completed_at=b.get("completed_at")
        )
        for b in batches
    ]

    return BatchListResponse(
        batches=batch_items,
        total=len(_batches_db)
    )


@router.get("/{batch_id}", response_model=BatchStatusResponse)
async def get_batch_status(batch_id: str):
    """Retorna status detalhado do batch."""
    batch = get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch não encontrado")

    current_item = None
    current_step = None
    items = batch.get("items", [])

    if batch.get("current_item_index") is not None and items:
        idx = batch.get("current_item_index", 0)
        if 0 <= idx < len(items):
            current_item = items[idx].get("title")
            current_step = items[idx].get("current_step")

    return BatchStatusResponse(
        batch_id=batch["id"],
        name=batch.get("name", ""),
        status=batch.get("status", "unknown"),
        total_items=batch.get("total_items", 0),
        completed_items=batch.get("completed_items", 0),
        failed_items=batch.get("failed_items", 0),
        current_item_index=batch.get("current_item_index", 0),
        current_item_title=current_item,
        current_item_step=current_step,
        progress=batch.get("progress", 0),
        items=items,
        created_at=batch.get("created_at", ""),
        started_at=batch.get("started_at"),
        completed_at=batch.get("completed_at"),
        error=batch.get("error")
    )


@router.post("/{batch_id}/pause")
async def pause_batch(batch_id: str):
    """Pausa o processamento do batch após o item atual."""
    batch = get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch não encontrado")

    if batch.get("status") not in [BatchStatusEnum.PROCESSING.value, BatchStatusEnum.PENDING.value]:
        raise HTTPException(status_code=400, detail="Batch não está em processamento")

    processor = get_batch_processor(batch_id)
    if processor:
        processor.pause()
        _batches_db[batch_id]["status"] = BatchStatusEnum.PAUSED.value

    return {"status": "paused", "batch_id": batch_id}


@router.post("/{batch_id}/resume")
async def resume_batch(batch_id: str, background_tasks: BackgroundTasks):
    """Retoma o processamento do batch pausado."""
    batch = get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch não encontrado")

    if batch.get("status") != BatchStatusEnum.PAUSED.value:
        raise HTTPException(status_code=400, detail="Batch não está pausado")

    processor = get_batch_processor(batch_id)
    if processor:
        processor.resume()
        _batches_db[batch_id]["status"] = BatchStatusEnum.PROCESSING.value
        return {"status": "resumed", "batch_id": batch_id}

    # Se não tem processor, precisa reiniciar
    raise HTTPException(
        status_code=400,
        detail="Processador não encontrado. O batch precisa ser reiniciado."
    )


@router.post("/{batch_id}/cancel")
async def cancel_batch(batch_id: str):
    """Cancela o processamento do batch."""
    batch = get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch não encontrado")

    if batch.get("status") in [BatchStatusEnum.COMPLETED.value, BatchStatusEnum.FAILED.value, BatchStatusEnum.CANCELLED.value]:
        raise HTTPException(status_code=400, detail="Batch já finalizado")

    processor = get_batch_processor(batch_id)
    if processor:
        processor.cancel()

    _batches_db[batch_id]["status"] = BatchStatusEnum.CANCELLED.value
    _batches_db[batch_id]["completed_at"] = datetime.now().isoformat()

    return {"status": "cancelled", "batch_id": batch_id}


@router.delete("/{batch_id}")
async def delete_batch(batch_id: str):
    """Remove um batch e seus vídeos."""
    batch = get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch não encontrado")

    # Deletar vídeos gerados
    for item in batch.get("items", []):
        video_path = item.get("video_path")
        if video_path:
            path = Path(video_path)
            if path.exists():
                path.unlink()

    # Remover processor se existir
    remove_batch_processor(batch_id)

    # Remover do storage
    del _batches_db[batch_id]

    return {"status": "deleted", "batch_id": batch_id}


@router.get("/{batch_id}/items/{item_index}/download")
async def download_batch_item(batch_id: str, item_index: int):
    """Download do vídeo de um item específico do batch."""
    batch = get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch não encontrado")

    items = batch.get("items", [])
    if item_index < 0 or item_index >= len(items):
        raise HTTPException(status_code=404, detail="Item não encontrado")

    item = items[item_index]
    if item.get("status") != BatchItemStatusEnum.COMPLETED.value:
        raise HTTPException(status_code=400, detail="Item ainda não concluído")

    video_path = item.get("video_path")
    if not video_path:
        raise HTTPException(status_code=404, detail="Vídeo não encontrado")

    path = Path(video_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    return FileResponse(
        path,
        media_type="video/mp4",
        filename=f"{item.get('title', 'video')}.mp4"
    )


@router.get("/{batch_id}/download-all")
async def download_all_batch_items(batch_id: str):
    """
    Retorna lista de URLs para download de todos os vídeos do batch.
    """
    batch = get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch não encontrado")

    downloads = []
    for idx, item in enumerate(batch.get("items", [])):
        if item.get("status") == BatchItemStatusEnum.COMPLETED.value and item.get("video_path"):
            path = Path(item.get("video_path"))
            if path.exists():
                downloads.append({
                    "index": idx,
                    "title": item.get("title"),
                    "download_url": f"/api/batch/{batch_id}/items/{idx}/download",
                    "file_size": path.stat().st_size
                })

    return {
        "batch_id": batch_id,
        "total_available": len(downloads),
        "downloads": downloads
    }
