"""
Modelos para processamento em batch de roteiros.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class BatchStatusEnum(str, Enum):
    """Status do batch."""
    PENDING = "pending"
    PROCESSING = "processing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BatchItemStatusEnum(str, Enum):
    """Status de cada item do batch."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class BatchItem(BaseModel):
    """Um roteiro individual dentro do batch."""
    id: str
    title: str
    text: str
    status: BatchItemStatusEnum = BatchItemStatusEnum.PENDING
    job_id: Optional[str] = None  # ID do job de video quando iniciado
    error: Optional[str] = None
    video_path: Optional[str] = None
    progress: float = 0.0
    current_step: str = "Aguardando"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class BatchCreate(BaseModel):
    """Dados para criação de um batch."""
    name: str = Field(..., description="Nome do batch")
    items: List[Dict[str, str]] = Field(
        ...,
        description="Lista de roteiros com 'title' e 'text'"
    )
    config_override: Optional[Dict[str, Any]] = None
    channel_id: Optional[str] = None


class BatchResponse(BaseModel):
    """Resposta após criação de batch."""
    batch_id: str
    status: BatchStatusEnum
    message: str
    total_items: int
    estimated_total_duration_seconds: Optional[float] = None


class BatchStatus(BaseModel):
    """Status completo do batch."""
    batch_id: str
    name: str
    status: BatchStatusEnum
    total_items: int
    completed_items: int
    failed_items: int
    current_item_index: int
    current_item: Optional[BatchItem] = None
    progress: float  # 0-100
    items: List[BatchItem]
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class BatchListItem(BaseModel):
    """Item resumido para listagem de batches."""
    batch_id: str
    name: str
    status: BatchStatusEnum
    total_items: int
    completed_items: int
    failed_items: int
    progress: float
    created_at: str
    completed_at: Optional[str] = None


class BatchListResponse(BaseModel):
    """Lista de batches."""
    batches: List[BatchListItem]
    total: int


class BatchItemUpdate(BaseModel):
    """Atualização de um item do batch."""
    title: Optional[str] = None
    text: Optional[str] = None
