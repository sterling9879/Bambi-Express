"""
Gerenciador de biblioteca de efeitos de vídeo.
"""

import os
import json
import uuid
import subprocess
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class VideoEffect:
    """Representa um efeito de vídeo na biblioteca."""
    id: str
    name: str
    filename: str
    duration_ms: int
    description: str = ""
    category: str = "geral"
    thumbnail_path: Optional[str] = None
    created_at: str = ""
    file_size: int = 0


class EffectsManager:
    """
    Gerencia biblioteca de efeitos de vídeo com fundo preto.

    Features:
    - Upload e armazenamento de efeitos
    - Listagem com metadados
    - Geração de thumbnails
    - Validação de formatos
    """

    SUPPORTED_FORMATS = [".mp4", ".mov", ".webm", ".avi", ".mkv"]
    METADATA_FILE = "effects_metadata.json"

    def __init__(self, library_path: str = "storage/effects"):
        self.library_path = Path(library_path)
        self.library_path.mkdir(parents=True, exist_ok=True)
        self.thumbnails_path = self.library_path / "thumbnails"
        self.thumbnails_path.mkdir(parents=True, exist_ok=True)
        self._metadata: dict[str, VideoEffect] = {}
        self._load_metadata()

    def _load_metadata(self):
        """Carrega metadados dos efeitos."""
        metadata_path = self.library_path / self.METADATA_FILE
        if metadata_path.exists():
            try:
                with open(metadata_path) as f:
                    data = json.load(f)
                    self._metadata = {
                        k: VideoEffect(**v) for k, v in data.items()
                    }
            except Exception as e:
                logger.error(f"Failed to load effects metadata: {e}")
                self._metadata = {}
        else:
            self._metadata = {}

    def _save_metadata(self):
        """Salva metadados dos efeitos."""
        metadata_path = self.library_path / self.METADATA_FILE
        try:
            with open(metadata_path, "w") as f:
                data = {k: asdict(v) for k, v in self._metadata.items()}
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save effects metadata: {e}")

    def _get_video_duration_ms(self, video_path: str) -> int:
        """Obtém duração do vídeo em milissegundos."""
        try:
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "json",
                video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            duration_s = float(data["format"]["duration"])
            return int(duration_s * 1000)
        except Exception as e:
            logger.error(f"Failed to get video duration: {e}")
            return 0

    def _generate_thumbnail(self, video_path: str, effect_id: str) -> Optional[str]:
        """Gera thumbnail do efeito."""
        thumbnail_path = self.thumbnails_path / f"{effect_id}.jpg"
        try:
            cmd = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-ss", "00:00:01",
                "-vframes", "1",
                "-vf", "scale=320:-1",
                str(thumbnail_path)
            ]
            subprocess.run(cmd, capture_output=True, check=True)
            return str(thumbnail_path)
        except Exception as e:
            logger.warning(f"Failed to generate thumbnail: {e}")
            return None

    def list_effects(self, category: Optional[str] = None) -> List[VideoEffect]:
        """Lista todos os efeitos disponíveis."""
        effects = list(self._metadata.values())
        if category:
            effects = [e for e in effects if e.category == category]
        return sorted(effects, key=lambda e: e.name)

    def get_effect(self, effect_id: str) -> Optional[VideoEffect]:
        """Obtém um efeito pelo ID."""
        return self._metadata.get(effect_id)

    def get_effect_path(self, effect_id: str) -> Optional[str]:
        """Obtém o caminho do arquivo de efeito."""
        effect = self._metadata.get(effect_id)
        if effect:
            path = self.library_path / effect.filename
            if path.exists():
                return str(path)
        return None

    def add_effect(
        self,
        file_path: str,
        name: str,
        description: str = "",
        category: str = "geral"
    ) -> VideoEffect:
        """
        Adiciona um novo efeito à biblioteca.

        Args:
            file_path: Caminho do arquivo de vídeo
            name: Nome do efeito
            description: Descrição opcional
            category: Categoria do efeito

        Returns:
            VideoEffect criado
        """
        source_path = Path(file_path)

        # Validar formato
        if source_path.suffix.lower() not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Formato não suportado: {source_path.suffix}")

        # Gerar ID único
        effect_id = str(uuid.uuid4())[:8]

        # Copiar arquivo para biblioteca
        new_filename = f"{effect_id}{source_path.suffix.lower()}"
        dest_path = self.library_path / new_filename

        # Copiar arquivo
        import shutil
        shutil.copy2(source_path, dest_path)

        # Obter metadados
        duration_ms = self._get_video_duration_ms(str(dest_path))
        file_size = dest_path.stat().st_size
        thumbnail_path = self._generate_thumbnail(str(dest_path), effect_id)

        # Criar efeito
        effect = VideoEffect(
            id=effect_id,
            name=name,
            filename=new_filename,
            duration_ms=duration_ms,
            description=description,
            category=category,
            thumbnail_path=thumbnail_path,
            created_at=datetime.now().isoformat(),
            file_size=file_size
        )

        # Salvar metadados
        self._metadata[effect_id] = effect
        self._save_metadata()

        logger.info(f"Added effect: {name} ({effect_id})")
        return effect

    def add_effect_from_upload(
        self,
        file_content: bytes,
        original_filename: str,
        name: str,
        description: str = "",
        category: str = "geral"
    ) -> VideoEffect:
        """
        Adiciona efeito a partir de upload.

        Args:
            file_content: Conteúdo do arquivo
            original_filename: Nome original do arquivo
            name: Nome do efeito
            description: Descrição opcional
            category: Categoria do efeito

        Returns:
            VideoEffect criado
        """
        # Validar extensão
        ext = Path(original_filename).suffix.lower()
        if ext not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Formato não suportado: {ext}")

        # Gerar ID único
        effect_id = str(uuid.uuid4())[:8]
        new_filename = f"{effect_id}{ext}"
        dest_path = self.library_path / new_filename

        # Salvar arquivo
        with open(dest_path, "wb") as f:
            f.write(file_content)

        # Obter metadados
        duration_ms = self._get_video_duration_ms(str(dest_path))
        file_size = dest_path.stat().st_size
        thumbnail_path = self._generate_thumbnail(str(dest_path), effect_id)

        # Criar efeito
        effect = VideoEffect(
            id=effect_id,
            name=name,
            filename=new_filename,
            duration_ms=duration_ms,
            description=description,
            category=category,
            thumbnail_path=thumbnail_path,
            created_at=datetime.now().isoformat(),
            file_size=file_size
        )

        # Salvar metadados
        self._metadata[effect_id] = effect
        self._save_metadata()

        logger.info(f"Added effect from upload: {name} ({effect_id})")
        return effect

    def delete_effect(self, effect_id: str) -> bool:
        """Remove um efeito da biblioteca."""
        effect = self._metadata.get(effect_id)
        if not effect:
            return False

        # Remover arquivo de vídeo
        video_path = self.library_path / effect.filename
        if video_path.exists():
            video_path.unlink()

        # Remover thumbnail
        if effect.thumbnail_path:
            thumb_path = Path(effect.thumbnail_path)
            if thumb_path.exists():
                thumb_path.unlink()

        # Remover metadados
        del self._metadata[effect_id]
        self._save_metadata()

        logger.info(f"Deleted effect: {effect.name} ({effect_id})")
        return True

    def update_effect(
        self,
        effect_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None
    ) -> Optional[VideoEffect]:
        """Atualiza metadados de um efeito."""
        effect = self._metadata.get(effect_id)
        if not effect:
            return None

        if name is not None:
            effect.name = name
        if description is not None:
            effect.description = description
        if category is not None:
            effect.category = category

        self._save_metadata()
        return effect

    def get_categories(self) -> List[str]:
        """Retorna lista de categorias disponíveis."""
        categories = set(e.category for e in self._metadata.values())
        return sorted(categories)


# Instância global do gerenciador
_effects_manager: Optional[EffectsManager] = None


def get_effects_manager() -> EffectsManager:
    """Retorna instância global do gerenciador de efeitos."""
    global _effects_manager
    if _effects_manager is None:
        _effects_manager = EffectsManager()
    return _effects_manager
