"""
Serviço de gerenciamento de música de fundo.
"""

from pathlib import Path
from typing import List, Optional
import random
import logging

from ..models.video import Scene, MusicCue, MusicSegment
from ..models.config import MusicConfig
from ..models.music import MusicTrack

logger = logging.getLogger(__name__)


class MusicManager:
    """
    Gerencia biblioteca de músicas e seleção automática por mood.

    Features:
    - Organização por mood
    - Seleção automática baseada nos music_cues
    - Cálculo de transições musicais
    """

    def __init__(self, library_path: str, db_session=None):
        self.library_path = Path(library_path)
        self.library_path.mkdir(parents=True, exist_ok=True)
        self.db_session = db_session
        self._tracks_cache: dict = {}

    def select_music(
        self,
        scenes: List[Scene],
        music_cues: List[MusicCue],
        total_duration_ms: int,
        config: MusicConfig
    ) -> List[MusicSegment]:
        """
        Seleciona músicas apropriadas para o vídeo.

        Args:
            scenes: Lista de Scene com moods
            music_cues: Lista de MusicCue indicando transições
            total_duration_ms: Duração total do vídeo
            config: MusicConfig com preferências

        Returns:
            Lista de MusicSegment para aplicar ao vídeo
        """
        if config.mode.value == "none":
            logger.info("Music mode is 'none', skipping music selection")
            return []

        if config.manual_track_id:
            # Usar música manual
            logger.info(f"Using manual track: {config.manual_track_id}")
            track = self._get_track_by_id(config.manual_track_id)
            if track:
                return [MusicSegment(
                    music_path=str(self.library_path / track.filename),
                    mood=track.mood.value,
                    start_ms=0,
                    end_ms=total_duration_ms,
                    fade_in_ms=config.fade_in_ms,
                    fade_out_ms=config.fade_out_ms,
                    volume=config.volume
                )]
            logger.warning(f"Manual track {config.manual_track_id} not found")

        if not config.auto_select_by_mood:
            # Selecionar aleatoriamente
            logger.info("Selecting random track")
            track_path = self._get_random_track()
            if track_path:
                return [MusicSegment(
                    music_path=str(track_path),
                    mood="neutral",
                    start_ms=0,
                    end_ms=total_duration_ms,
                    fade_in_ms=config.fade_in_ms,
                    fade_out_ms=config.fade_out_ms,
                    volume=config.volume
                )]
            return []

        # Seleção automática por mood
        logger.info("Selecting music by mood")
        segments = []

        # If no music cues, use predominant mood from scenes
        if not music_cues:
            mood_counts = {}
            for scene in scenes:
                mood_counts[scene.mood] = mood_counts.get(scene.mood, 0) + 1

            predominant_mood = max(mood_counts, key=mood_counts.get) if mood_counts else "neutral"
            music_cues = [MusicCue(
                timestamp_ms=0,
                mood=predominant_mood,
                suggestion=""
            )]

        for i, cue in enumerate(music_cues):
            # Determinar fim deste segmento
            if i < len(music_cues) - 1:
                end_ms = music_cues[i + 1].timestamp_ms
            else:
                end_ms = total_duration_ms

            # Encontrar música com mood apropriado
            track_path = self._get_track_by_mood(cue.mood)

            if track_path:
                segments.append(MusicSegment(
                    music_path=str(track_path),
                    mood=cue.mood,
                    start_ms=cue.timestamp_ms,
                    end_ms=end_ms,
                    fade_in_ms=config.fade_in_ms if i == 0 else config.crossfade_ms,
                    fade_out_ms=config.fade_out_ms if i == len(music_cues) - 1 else config.crossfade_ms,
                    volume=config.volume
                ))

        return segments

    def _get_track_by_mood(self, mood: str) -> Optional[Path]:
        """Retorna uma música aleatória com o mood especificado."""
        mood_dir = self.library_path / mood
        if not mood_dir.exists():
            # Try fallback to neutral
            mood_dir = self.library_path / "neutral"

        if not mood_dir.exists():
            # Try any available mood directory
            for subdir in self.library_path.iterdir():
                if subdir.is_dir():
                    mood_dir = subdir
                    break
            else:
                return None

        tracks = list(mood_dir.glob("*.mp3")) + list(mood_dir.glob("*.wav"))
        if not tracks:
            return None

        return random.choice(tracks)

    def _get_track_by_id(self, track_id: str) -> Optional[MusicTrack]:
        """Retorna música pelo ID."""
        # This would normally query a database
        # For now, search by filename
        for mood_dir in self.library_path.iterdir():
            if mood_dir.is_dir():
                for track_file in mood_dir.iterdir():
                    if track_file.stem == track_id:
                        from datetime import datetime
                        from ..models.config import MusicMood

                        return MusicTrack(
                            id=track_id,
                            filename=str(track_file.relative_to(self.library_path)),
                            original_name=track_file.name,
                            duration_ms=0,  # Would need to calculate
                            mood=MusicMood(mood_dir.name),
                            uploaded_at=datetime.now(),
                            file_size=track_file.stat().st_size
                        )
        return None

    def _get_random_track(self) -> Optional[Path]:
        """Retorna qualquer música aleatória."""
        all_tracks = (
            list(self.library_path.rglob("*.mp3")) +
            list(self.library_path.rglob("*.wav"))
        )
        if not all_tracks:
            return None
        return random.choice(all_tracks)

    def get_all_tracks(self, mood: Optional[str] = None) -> List[Path]:
        """Lista todas as músicas, opcionalmente filtradas por mood."""
        if mood:
            search_path = self.library_path / mood
            if not search_path.exists():
                return []
        else:
            search_path = self.library_path

        return (
            list(search_path.rglob("*.mp3")) +
            list(search_path.rglob("*.wav"))
        )

    def add_track(
        self,
        file_path: Path,
        mood: str,
        original_name: str
    ) -> Path:
        """Adiciona uma música à biblioteca."""
        mood_dir = self.library_path / mood
        mood_dir.mkdir(parents=True, exist_ok=True)

        destination = mood_dir / file_path.name
        if file_path != destination:
            import shutil
            shutil.copy2(file_path, destination)

        logger.info(f"Added track {original_name} to {mood} category")
        return destination

    def remove_track(self, track_path: Path) -> bool:
        """Remove uma música da biblioteca."""
        try:
            track_path.unlink()
            logger.info(f"Removed track: {track_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove track: {e}")
            return False
