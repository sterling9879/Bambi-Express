"""
Serviço de mixagem de áudio (narração + música).
"""

import subprocess
from pathlib import Path
from typing import List
import logging

from ..models.video import MusicSegment, MixedAudio
from ..models.config import MusicConfig

logger = logging.getLogger(__name__)


class AudioMixer:
    """
    Mixa narração com música de fundo usando FFMPEG.

    Features:
    - Volume ajustável da música
    - Ducking (abaixar música durante fala)
    - Fades nas transições musicais
    - Crossfade entre músicas diferentes
    """

    def __init__(self, output_dir: str = "temp"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def mix(
        self,
        narration_path: str,
        music_segments: List[MusicSegment],
        config: MusicConfig,
        output_filename: str = "audio_mixed.mp3"
    ) -> MixedAudio:
        """
        Mixa narração com música.

        Args:
            narration_path: Caminho da narração
            music_segments: Lista de MusicSegment
            config: MusicConfig com preferências
            output_filename: Nome do arquivo de saída

        Returns:
            MixedAudio com path do resultado
        """
        output_path = self.output_dir / output_filename

        if not music_segments:
            # Sem música, apenas copiar narração
            logger.info("No music segments, copying narration only")
            subprocess.run([
                "ffmpeg", "-y",
                "-i", narration_path,
                "-c", "copy",
                str(output_path)
            ], check=True, capture_output=True)

            return MixedAudio(
                path=str(output_path),
                duration_ms=self._get_duration(narration_path)
            )

        if config.ducking_enabled:
            logger.info("Mixing with ducking enabled")
            return self._mix_with_ducking(
                narration_path,
                music_segments,
                config,
                output_path
            )
        else:
            logger.info("Mixing without ducking")
            return self._mix_simple(
                narration_path,
                music_segments,
                config,
                output_path
            )

    def _mix_simple(
        self,
        narration_path: str,
        music_segments: List[MusicSegment],
        config: MusicConfig,
        output_path: Path
    ) -> MixedAudio:
        """Mixagem simples sem ducking."""

        # Para simplificar, usar apenas primeiro segmento de música
        music_segment = music_segments[0]
        narration_duration = self._get_duration(narration_path) / 1000  # seconds

        # Calculate fade timings
        fade_out_start = max(0, narration_duration - music_segment.fade_out_ms / 1000)

        filter_complex = (
            f"[1:a]volume={config.volume},"
            f"afade=t=in:st=0:d={music_segment.fade_in_ms / 1000},"
            f"afade=t=out:st={fade_out_start}:d={music_segment.fade_out_ms / 1000}[music];"
            f"[0:a][music]amix=inputs=2:duration=first:dropout_transition=0[out]"
        )

        cmd = [
            "ffmpeg", "-y",
            "-i", narration_path,
            "-i", music_segment.music_path,
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            str(output_path)
        ]

        logger.debug(f"Running command: {' '.join(cmd)}")

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.debug(f"FFMPEG output: {result.stderr}")
        except subprocess.CalledProcessError as e:
            logger.error(f"FFMPEG error: {e.stderr}")
            raise RuntimeError(f"Failed to mix audio: {e.stderr}")

        return MixedAudio(
            path=str(output_path),
            duration_ms=self._get_duration(narration_path)
        )

    def _mix_with_ducking(
        self,
        narration_path: str,
        music_segments: List[MusicSegment],
        config: MusicConfig,
        output_path: Path
    ) -> MixedAudio:
        """Mixagem com ducking (música abaixa durante fala)."""

        music_segment = music_segments[0]
        narration_duration = self._get_duration(narration_path) / 1000

        # Calculate parameters based on ducking intensity
        # Higher intensity = more compression (lower music during speech)
        threshold = 0.02
        ratio = 4 + config.ducking_intensity * 8  # Range: 4-12
        attack = 50  # ms
        release = 500  # ms

        fade_out_start = max(0, narration_duration - music_segment.fade_out_ms / 1000)

        # Build filter complex with sidechaincompress for ducking
        filter_complex = (
            f"[1:a]volume={config.volume},"
            f"afade=t=in:st=0:d={music_segment.fade_in_ms / 1000},"
            f"afade=t=out:st={fade_out_start}:d={music_segment.fade_out_ms / 1000}[music_prepared];"
            f"[music_prepared][0:a]sidechaincompress="
            f"threshold={threshold}:"
            f"ratio={ratio}:"
            f"attack={attack}:"
            f"release={release}[music_ducked];"
            f"[0:a][music_ducked]amix=inputs=2:duration=first:dropout_transition=0[out]"
        )

        cmd = [
            "ffmpeg", "-y",
            "-i", narration_path,
            "-i", music_segment.music_path,
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            str(output_path)
        ]

        logger.debug(f"Running command: {' '.join(cmd)}")

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.debug(f"FFMPEG output: {result.stderr}")
        except subprocess.CalledProcessError as e:
            logger.error(f"FFMPEG error: {e.stderr}")
            # Fallback to simple mix if ducking fails
            logger.warning("Ducking failed, falling back to simple mix")
            return self._mix_simple(
                narration_path,
                music_segments,
                config,
                output_path
            )

        return MixedAudio(
            path=str(output_path),
            duration_ms=self._get_duration(narration_path)
        )

    def _get_duration(self, audio_path: str) -> int:
        """Retorna duração do áudio em ms."""
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(audio_path)
            return len(audio)
        except Exception as e:
            logger.warning(f"Could not get duration with pydub: {e}")
            # Fallback: use ffprobe
            try:
                result = subprocess.run([
                    "ffprobe",
                    "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    audio_path
                ], capture_output=True, text=True, check=True)
                duration_seconds = float(result.stdout.strip())
                return int(duration_seconds * 1000)
            except Exception as e2:
                logger.error(f"Could not get duration: {e2}")
                return 0
