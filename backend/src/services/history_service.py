"""
Serviço para gerenciar histórico de vídeos e elementos.
"""

import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Optional
import logging

from ..models.history import (
    Channel, ChannelCreate, ChannelUpdate,
    VideoHistory, VideoHistoryCreate,
    Element, ElementCreate, ElementType,
    HistoryStats
)

logger = logging.getLogger(__name__)


class HistoryService:
    """
    Gerencia histórico de vídeos e elementos usando arquivos JSON.
    """

    def __init__(self, storage_dir: str = "storage"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.channels_file = self.storage_dir / "channels.json"
        self.videos_file = self.storage_dir / "video_history.json"
        self.elements_file = self.storage_dir / "element_history.json"

        self._ensure_files()

    def _ensure_files(self):
        """Cria arquivos de dados se não existirem."""
        for file_path in [self.channels_file, self.videos_file, self.elements_file]:
            if not file_path.exists():
                file_path.write_text("[]")

    def _read_json(self, file_path: Path) -> List[dict]:
        """Lê dados de um arquivo JSON."""
        try:
            return json.loads(file_path.read_text())
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _write_json(self, file_path: Path, data: List[dict]):
        """Escreve dados em um arquivo JSON."""
        file_path.write_text(json.dumps(data, indent=2, default=str))

    # ============== CHANNELS ==============

    def list_channels(self) -> List[Channel]:
        """Lista todos os canais."""
        channels_data = self._read_json(self.channels_file)
        videos_data = self._read_json(self.videos_file)

        # Count videos per channel
        video_counts = {}
        for video in videos_data:
            channel_id = video.get("channel_id")
            if channel_id:
                video_counts[channel_id] = video_counts.get(channel_id, 0) + 1

        channels = []
        for ch in channels_data:
            ch["video_count"] = video_counts.get(ch["id"], 0)
            channels.append(Channel(**ch))

        return sorted(channels, key=lambda x: x.name)

    def get_channel(self, channel_id: str) -> Optional[Channel]:
        """Busca um canal pelo ID."""
        channels = self._read_json(self.channels_file)
        for ch in channels:
            if ch["id"] == channel_id:
                videos = self._read_json(self.videos_file)
                ch["video_count"] = sum(1 for v in videos if v.get("channel_id") == channel_id)
                return Channel(**ch)
        return None

    def create_channel(self, data: ChannelCreate) -> Channel:
        """Cria um novo canal."""
        channels = self._read_json(self.channels_file)

        channel = Channel(
            id=str(uuid.uuid4()),
            name=data.name,
            description=data.description,
            color=data.color,
            created_at=datetime.now(),
            video_count=0
        )

        channels.append(channel.model_dump())
        self._write_json(self.channels_file, channels)

        logger.info(f"Created channel: {channel.name}")
        return channel

    def update_channel(self, channel_id: str, data: ChannelUpdate) -> Optional[Channel]:
        """Atualiza um canal."""
        channels = self._read_json(self.channels_file)

        for i, ch in enumerate(channels):
            if ch["id"] == channel_id:
                if data.name is not None:
                    ch["name"] = data.name
                if data.description is not None:
                    ch["description"] = data.description
                if data.color is not None:
                    ch["color"] = data.color

                channels[i] = ch
                self._write_json(self.channels_file, channels)

                return self.get_channel(channel_id)

        return None

    def delete_channel(self, channel_id: str) -> bool:
        """Deleta um canal (vídeos ficam sem canal)."""
        channels = self._read_json(self.channels_file)

        new_channels = [ch for ch in channels if ch["id"] != channel_id]
        if len(new_channels) == len(channels):
            return False

        self._write_json(self.channels_file, new_channels)

        # Remove channel reference from videos
        videos = self._read_json(self.videos_file)
        for video in videos:
            if video.get("channel_id") == channel_id:
                video["channel_id"] = None
        self._write_json(self.videos_file, videos)

        logger.info(f"Deleted channel: {channel_id}")
        return True

    # ============== VIDEO HISTORY ==============

    def list_videos(
        self,
        channel_id: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
        search: Optional[str] = None
    ) -> tuple[List[VideoHistory], int]:
        """Lista histórico de vídeos com filtros."""
        videos_data = self._read_json(self.videos_file)
        channels_data = {ch["id"]: ch["name"] for ch in self._read_json(self.channels_file)}

        # Filter by channel
        if channel_id:
            videos_data = [v for v in videos_data if v.get("channel_id") == channel_id]

        # Filter by search
        if search:
            search_lower = search.lower()
            videos_data = [
                v for v in videos_data
                if search_lower in v.get("title", "").lower()
                or search_lower in v.get("text_preview", "").lower()
            ]

        # Sort by created_at desc
        videos_data.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        total = len(videos_data)

        # Paginate
        start = (page - 1) * limit
        end = start + limit
        paginated = videos_data[start:end]

        # Add channel names and URLs
        videos = []
        for v in paginated:
            v["channel_name"] = channels_data.get(v.get("channel_id"))
            v["video_url"] = f"/api/history/videos/{v['id']}/stream"
            if v.get("thumbnail_path"):
                v["thumbnail_url"] = f"/api/history/videos/{v['id']}/thumbnail"
            videos.append(VideoHistory(**v))

        return videos, total

    def get_video(self, video_id: str) -> Optional[VideoHistory]:
        """Busca um vídeo pelo ID."""
        videos = self._read_json(self.videos_file)
        channels_data = {ch["id"]: ch["name"] for ch in self._read_json(self.channels_file)}

        for v in videos:
            if v["id"] == video_id:
                v["channel_name"] = channels_data.get(v.get("channel_id"))
                v["video_url"] = f"/api/history/videos/{v['id']}/stream"
                if v.get("thumbnail_path"):
                    v["thumbnail_url"] = f"/api/history/videos/{v['id']}/thumbnail"
                return VideoHistory(**v)
        return None

    def add_video(self, data: VideoHistoryCreate) -> VideoHistory:
        """Adiciona um vídeo ao histórico."""
        videos = self._read_json(self.videos_file)

        video_dict = {
            "id": str(uuid.uuid4()),
            "job_id": data.job_id,
            "title": data.title,
            "channel_id": data.channel_id,
            "text_preview": data.text_preview[:200] if data.text_preview else "",
            "video_path": data.video_path,
            "thumbnail_path": None,
            "duration_seconds": data.duration_seconds,
            "scenes_count": data.scenes_count,
            "file_size": data.file_size,
            "resolution": data.resolution,
            "created_at": datetime.now().isoformat()
        }

        videos.append(video_dict)
        self._write_json(self.videos_file, videos)

        logger.info(f"Added video to history: {data.title}")
        return self.get_video(video_dict["id"])

    def update_video_channel(self, video_id: str, channel_id: Optional[str]) -> Optional[VideoHistory]:
        """Move um vídeo para outro canal."""
        videos = self._read_json(self.videos_file)

        for i, v in enumerate(videos):
            if v["id"] == video_id:
                v["channel_id"] = channel_id
                videos[i] = v
                self._write_json(self.videos_file, videos)
                return self.get_video(video_id)

        return None

    def delete_video(self, video_id: str, delete_files: bool = False) -> bool:
        """Deleta um vídeo do histórico."""
        videos = self._read_json(self.videos_file)

        video_to_delete = None
        for v in videos:
            if v["id"] == video_id:
                video_to_delete = v
                break

        if not video_to_delete:
            return False

        if delete_files:
            # Delete video file
            video_path = Path(video_to_delete.get("video_path", ""))
            if video_path.exists():
                video_path.unlink()

            # Delete thumbnail
            thumbnail_path = video_to_delete.get("thumbnail_path")
            if thumbnail_path:
                thumb = Path(thumbnail_path)
                if thumb.exists():
                    thumb.unlink()

            # Delete associated elements
            self.delete_elements_by_job(video_to_delete["job_id"])

        new_videos = [v for v in videos if v["id"] != video_id]
        self._write_json(self.videos_file, new_videos)

        logger.info(f"Deleted video: {video_id}")
        return True

    # ============== ELEMENT HISTORY ==============

    def list_elements(
        self,
        job_id: Optional[str] = None,
        element_type: Optional[ElementType] = None,
        page: int = 1,
        limit: int = 50
    ) -> tuple[List[Element], int]:
        """Lista elementos com filtros."""
        elements_data = self._read_json(self.elements_file)

        # Filter
        if job_id:
            elements_data = [e for e in elements_data if e.get("job_id") == job_id]

        if element_type:
            elements_data = [e for e in elements_data if e.get("element_type") == element_type.value]

        # Sort by created_at desc
        elements_data.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        total = len(elements_data)

        # Paginate
        start = (page - 1) * limit
        end = start + limit
        paginated = elements_data[start:end]

        # Add URLs
        elements = []
        for e in paginated:
            e["file_url"] = f"/api/history/elements/{e['id']}/file"
            elements.append(Element(**e))

        return elements, total

    def add_element(self, data: ElementCreate) -> Element:
        """Adiciona um elemento ao histórico."""
        elements = self._read_json(self.elements_file)

        element_dict = {
            "id": str(uuid.uuid4()),
            "job_id": data.job_id,
            "element_type": data.element_type.value,
            "file_path": data.file_path,
            "scene_index": data.scene_index,
            "prompt": data.prompt,
            "duration_ms": data.duration_ms,
            "metadata": data.metadata,
            "created_at": datetime.now().isoformat()
        }

        elements.append(element_dict)
        self._write_json(self.elements_file, elements)

        return Element(**element_dict)

    def add_elements_batch(self, elements: List[ElementCreate]) -> List[Element]:
        """Adiciona múltiplos elementos de uma vez."""
        existing = self._read_json(self.elements_file)

        new_elements = []
        for data in elements:
            element_dict = {
                "id": str(uuid.uuid4()),
                "job_id": data.job_id,
                "element_type": data.element_type.value,
                "file_path": data.file_path,
                "scene_index": data.scene_index,
                "prompt": data.prompt,
                "duration_ms": data.duration_ms,
                "metadata": data.metadata,
                "created_at": datetime.now().isoformat()
            }
            existing.append(element_dict)
            new_elements.append(Element(**element_dict))

        self._write_json(self.elements_file, existing)
        return new_elements

    def delete_elements_by_job(self, job_id: str) -> int:
        """Deleta todos os elementos de um job."""
        elements = self._read_json(self.elements_file)

        # Find elements to delete
        to_delete = [e for e in elements if e.get("job_id") == job_id]

        # Delete files
        for e in to_delete:
            file_path = Path(e.get("file_path", ""))
            if file_path.exists():
                try:
                    file_path.unlink()
                except Exception:
                    pass

        # Remove from list
        new_elements = [e for e in elements if e.get("job_id") != job_id]
        self._write_json(self.elements_file, new_elements)

        return len(to_delete)

    # ============== STATS ==============

    def get_stats(self) -> HistoryStats:
        """Retorna estatísticas do histórico."""
        videos = self._read_json(self.videos_file)
        channels = {ch["id"]: ch["name"] for ch in self._read_json(self.channels_file)}

        total_duration = sum(v.get("duration_seconds", 0) for v in videos)
        total_size = sum(v.get("file_size", 0) for v in videos)

        # Count by channel
        by_channel = {"Sem canal": 0}
        for v in videos:
            ch_id = v.get("channel_id")
            ch_name = channels.get(ch_id, "Sem canal") if ch_id else "Sem canal"
            by_channel[ch_name] = by_channel.get(ch_name, 0) + 1

        # Recent videos
        sorted_videos = sorted(videos, key=lambda x: x.get("created_at", ""), reverse=True)[:5]
        recent = []
        for v in sorted_videos:
            v["channel_name"] = channels.get(v.get("channel_id"))
            v["video_url"] = f"/api/history/videos/{v['id']}/stream"
            recent.append(VideoHistory(**v))

        return HistoryStats(
            total_videos=len(videos),
            total_duration_seconds=total_duration,
            total_size_bytes=total_size,
            videos_by_channel=by_channel,
            recent_videos=recent
        )


# Singleton instance
_history_service: Optional[HistoryService] = None


def get_history_service() -> HistoryService:
    """Retorna instância singleton do serviço de histórico."""
    global _history_service
    if _history_service is None:
        _history_service = HistoryService()
    return _history_service
