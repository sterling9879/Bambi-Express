"""
Serviço para processamento em batch de roteiros.

Permite processar múltiplos roteiros sequencialmente,
gerando um vídeo para cada roteiro.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable

from ..models.batch import (
    BatchStatusEnum,
    BatchItemStatusEnum,
    BatchItem,
    BatchStatus,
    BatchCreate
)
from ..models.config import FullConfig
from ..models.job import JobStatus, JobStatusEnum
from .job_orchestrator import JobOrchestrator
from .text_processor import TextProcessor
from .history_service import get_history_service
from ..models.history import VideoHistoryCreate

logger = logging.getLogger(__name__)


class BatchProcessor:
    """
    Processa múltiplos roteiros em sequência.

    Features:
    - Processamento sequencial (um por vez)
    - Possibilidade de pausar/retomar
    - Tracking de progresso individual e total
    - Logs detalhados para cada item
    - Continua mesmo se um item falhar
    """

    def __init__(
        self,
        config: FullConfig,
        status_callback: Optional[Callable[[BatchStatus], Any]] = None
    ):
        self.config = config
        self.status_callback = status_callback
        self._is_paused = False
        self._is_cancelled = False
        self._current_batch: Optional[BatchStatus] = None

    def pause(self):
        """Pausa o processamento após o item atual terminar."""
        self._is_paused = True
        logger.info("Batch processing paused")

    def resume(self):
        """Retoma o processamento."""
        self._is_paused = False
        logger.info("Batch processing resumed")

    def cancel(self):
        """Cancela o processamento."""
        self._is_cancelled = True
        logger.info("Batch processing cancelled")

    async def process(
        self,
        batch_id: str,
        name: str,
        items: List[Dict[str, str]],
        channel_id: Optional[str] = None,
        config_override: Optional[Dict[str, Any]] = None
    ) -> BatchStatus:
        """
        Processa todos os itens do batch sequencialmente.

        Args:
            batch_id: ID único do batch
            name: Nome do batch
            items: Lista de dicts com 'title' e 'text'
            channel_id: ID do canal (opcional)
            config_override: Override de configuração (opcional)

        Returns:
            BatchStatus com resultado final
        """
        started_at = datetime.now()

        # Criar itens do batch
        batch_items = []
        for idx, item in enumerate(items):
            batch_items.append(BatchItem(
                id=f"{batch_id}_{idx}",
                title=item.get("title", f"Roteiro {idx + 1}"),
                text=item.get("text", ""),
                status=BatchItemStatusEnum.PENDING
            ))

        # Criar status inicial do batch
        self._current_batch = BatchStatus(
            batch_id=batch_id,
            name=name,
            status=BatchStatusEnum.PROCESSING,
            total_items=len(batch_items),
            completed_items=0,
            failed_items=0,
            current_item_index=0,
            current_item=None,
            progress=0.0,
            items=batch_items,
            created_at=started_at,
            started_at=started_at
        )

        await self._notify_status()

        # Processar cada item
        for idx, item in enumerate(batch_items):
            # Verificar se foi cancelado
            if self._is_cancelled:
                self._current_batch.status = BatchStatusEnum.CANCELLED
                for remaining in batch_items[idx:]:
                    if remaining.status == BatchItemStatusEnum.PENDING:
                        remaining.status = BatchItemStatusEnum.SKIPPED
                break

            # Verificar se está pausado
            while self._is_paused and not self._is_cancelled:
                self._current_batch.status = BatchStatusEnum.PAUSED
                await self._notify_status()
                await asyncio.sleep(1)

            if self._is_cancelled:
                continue

            # Atualizar status do batch
            self._current_batch.status = BatchStatusEnum.PROCESSING
            self._current_batch.current_item_index = idx
            self._current_batch.current_item = item
            item.status = BatchItemStatusEnum.PROCESSING
            item.started_at = datetime.now()

            await self._notify_status()

            # Processar item
            try:
                logger.info(f"Processing batch item {idx + 1}/{len(batch_items)}: {item.title}")

                # Validar texto
                if not item.text.strip():
                    raise ValueError("Texto vazio")

                # Criar job ID para este item
                job_id = str(uuid.uuid4())
                item.job_id = job_id

                # Callback para atualizar progresso do item
                def item_status_callback(status: JobStatus):
                    item.progress = status.progress
                    item.current_step = status.current_step
                    # Atualizar progresso geral
                    self._update_batch_progress()
                    # Chamar callback externo de forma síncrona
                    if self.status_callback:
                        try:
                            self.status_callback(self._current_batch)
                        except Exception as e:
                            logger.warning(f"Batch status callback error: {e}")

                # Aplicar config override
                effective_config = self._apply_config_override(config_override)

                # Executar orquestrador
                orchestrator = JobOrchestrator(
                    config=effective_config,
                    status_callback=item_status_callback
                )

                video_path = await orchestrator.run(job_id, item.text)

                # Marcar como concluído
                item.status = BatchItemStatusEnum.COMPLETED
                item.completed_at = datetime.now()
                item.video_path = video_path
                item.progress = 1.0
                item.current_step = "Concluído"

                # Calcular duração de processamento
                if item.started_at:
                    item.duration_seconds = (item.completed_at - item.started_at).total_seconds()

                self._current_batch.completed_items += 1

                # Salvar no histórico
                await self._save_to_history(item, channel_id, effective_config)

                logger.info(f"Batch item {idx + 1} completed: {video_path}")

            except Exception as e:
                logger.error(f"Batch item {idx + 1} failed: {str(e)}")
                item.status = BatchItemStatusEnum.FAILED
                item.completed_at = datetime.now()
                item.error = str(e)[:500]
                item.current_step = "Erro"
                self._current_batch.failed_items += 1

            self._update_batch_progress()
            await self._notify_status()

        # Finalizar batch
        self._current_batch.completed_at = datetime.now()
        self._current_batch.current_item = None

        if self._is_cancelled:
            self._current_batch.status = BatchStatusEnum.CANCELLED
        elif self._current_batch.failed_items == len(batch_items):
            self._current_batch.status = BatchStatusEnum.FAILED
        else:
            self._current_batch.status = BatchStatusEnum.COMPLETED

        self._update_batch_progress()
        await self._notify_status()

        logger.info(
            f"Batch {batch_id} finished: "
            f"{self._current_batch.completed_items} completed, "
            f"{self._current_batch.failed_items} failed"
        )

        return self._current_batch

    def _update_batch_progress(self):
        """Atualiza o progresso geral do batch."""
        if not self._current_batch:
            return

        total = self._current_batch.total_items
        if total == 0:
            self._current_batch.progress = 0
            return

        # Calcular progresso baseado em itens completos + progresso do atual
        completed = self._current_batch.completed_items + self._current_batch.failed_items
        current_progress = 0

        if self._current_batch.current_item:
            current_progress = self._current_batch.current_item.progress

        # Progresso geral: (itens_completos + progresso_atual) / total
        self._current_batch.progress = ((completed + current_progress) / total) * 100

    async def _notify_status(self):
        """Notifica o callback de status."""
        if self.status_callback and self._current_batch:
            try:
                result = self.status_callback(self._current_batch)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.warning(f"Status callback error: {e}")

        # Yield control
        await asyncio.sleep(0)

    def _apply_config_override(self, override: Optional[Dict[str, Any]]) -> FullConfig:
        """Aplica override de configuração."""
        if not override:
            return self.config

        # Criar cópia do config
        config_dict = self.config.model_dump()

        # Aplicar overrides
        for key, value in override.items():
            if isinstance(value, dict) and key in config_dict:
                config_dict[key].update(value)
            else:
                config_dict[key] = value

        return FullConfig(**config_dict)

    async def _save_to_history(
        self,
        item: BatchItem,
        channel_id: Optional[str],
        config: FullConfig
    ):
        """Salva item no histórico."""
        try:
            if not item.video_path:
                return

            history_service = get_history_service()
            video_file = Path(item.video_path)
            file_size = video_file.stat().st_size if video_file.exists() else 0
            resolution = f"{config.ffmpeg.resolution.width}x{config.ffmpeg.resolution.height}"

            history_service.add_video(VideoHistoryCreate(
                job_id=item.job_id or item.id,
                title=item.title,
                channel_id=channel_id,
                text_preview=item.text[:200],
                video_path=item.video_path,
                duration_seconds=item.duration_seconds or 0,
                scenes_count=0,
                file_size=file_size,
                resolution=resolution
            ))
        except Exception as e:
            logger.error(f"Failed to save to history: {e}")


# Storage em memória para batches
_batches_db: Dict[str, Dict] = {}
_batch_processors: Dict[str, BatchProcessor] = {}
_MAX_BATCHES_IN_MEMORY = 20


def _cleanup_old_batches():
    """Remove batches antigos para evitar vazamento de memória."""
    global _batches_db
    if len(_batches_db) > _MAX_BATCHES_IN_MEMORY:
        sorted_batches = sorted(
            _batches_db.items(),
            key=lambda x: x[1].get("created_at", ""),
            reverse=True
        )
        _batches_db = dict(sorted_batches[:_MAX_BATCHES_IN_MEMORY])


def get_batch(batch_id: str) -> Optional[Dict]:
    """Obtém batch do storage."""
    return _batches_db.get(batch_id)


def update_batch(batch_id: str, updates: Dict):
    """Atualiza batch no storage."""
    if batch_id in _batches_db:
        _batches_db[batch_id].update(updates)


def get_batch_processor(batch_id: str) -> Optional[BatchProcessor]:
    """Obtém processor de um batch."""
    return _batch_processors.get(batch_id)


def store_batch_processor(batch_id: str, processor: BatchProcessor):
    """Armazena processor de um batch."""
    _batch_processors[batch_id] = processor


def remove_batch_processor(batch_id: str):
    """Remove processor de um batch."""
    if batch_id in _batch_processors:
        del _batch_processors[batch_id]
