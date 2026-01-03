"""
Serviço de composição de vídeo usando FFMPEG.
"""

import subprocess
import random
from pathlib import Path
from typing import List, Optional, Callable
import logging

from ..models.video import Scene, GeneratedImage, VideoResult
from ..models.config import FFmpegConfig

logger = logging.getLogger(__name__)


class VideoComposer:
    """
    Compõe vídeo final usando FFMPEG.

    Features:
    - Duração de cenas configurável (auto/fixa/range)
    - Múltiplos tipos de transição
    - Efeito Ken Burns (zoom/pan)
    - Vinheta e grain
    - Normalização de áudio
    """

    def __init__(self, config: FFmpegConfig, output_dir: str = "output"):
        self.config = config
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def compose(
        self,
        scenes: List[Scene],
        images: List[GeneratedImage],
        audio_path: str,
        output_filename: str = "video.mp4",
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> VideoResult:
        """
        Compõe o vídeo final.

        Args:
            scenes: Lista de Scene com durações
            images: Lista de GeneratedImage com paths
            audio_path: Caminho do áudio (mixado ou só narração)
            output_filename: Nome do arquivo de saída
            progress_callback: Callback para progresso

        Returns:
            VideoResult com path e metadados
        """
        output_path = self.output_dir / output_filename

        logger.info(f"Composing video with {len(scenes)} scenes")

        # Calcular durações
        durations = self._calculate_durations(scenes)

        # Sort images by scene_index to match scenes
        sorted_images = sorted(images, key=lambda x: x.scene_index)

        # Construir comando FFMPEG
        cmd = self._build_ffmpeg_command(
            scenes,
            sorted_images,
            durations,
            audio_path,
            output_path
        )

        logger.debug(f"Running FFMPEG command with {len(cmd)} arguments")

        # Executar
        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True
            )
            logger.debug(f"FFMPEG output: {result.stderr[-1000:]}")
        except subprocess.CalledProcessError as e:
            logger.error(f"FFMPEG error: {e.stderr[-2000:]}")
            raise RuntimeError(f"Failed to compose video: {e.stderr[-500:]}")

        # Calcular metadados
        total_duration = sum(durations)
        file_size = output_path.stat().st_size

        logger.info(f"Video composed successfully: {output_path}")

        return VideoResult(
            path=str(output_path),
            duration_seconds=total_duration,
            scenes_count=len(scenes),
            resolution=f"{self.config.resolution.width}x{self.config.resolution.height}",
            file_size=file_size
        )

    def _calculate_durations(self, scenes: List[Scene]) -> List[float]:
        """Calcula duração de cada cena baseado no modo."""
        mode = self.config.scene_duration.mode.value

        if mode == "auto":
            return [s.duration_ms / 1000 for s in scenes]

        elif mode == "fixed":
            fixed = self.config.scene_duration.fixed_duration or 4.0
            return [fixed] * len(scenes)

        elif mode == "range":
            min_d = self.config.scene_duration.min_duration or 3.0
            max_d = self.config.scene_duration.max_duration or 6.0
            return [
                max(min_d, min(max_d, s.duration_ms / 1000))
                for s in scenes
            ]

        return [s.duration_ms / 1000 for s in scenes]

    def _build_ffmpeg_command(
        self,
        scenes: List[Scene],
        images: List[GeneratedImage],
        durations: List[float],
        audio_path: str,
        output_path: Path
    ) -> List[str]:
        """Constrói comando FFMPEG completo."""

        cfg = self.config
        width = cfg.resolution.width
        height = cfg.resolution.height

        # Build a simpler approach: create each scene as input, then concat
        inputs = []
        filter_parts = []

        # Add image inputs with loop for duration
        for i, (img, duration) in enumerate(zip(images, durations)):
            inputs.extend([
                "-loop", "1",
                "-t", str(duration),
                "-i", img.image_path
            ])

        # Add audio input
        audio_index = len(images)
        inputs.extend(["-i", audio_path])

        # Process each image
        processed_streams = []
        for i, duration in enumerate(durations):
            stream_name = f"v{i}"

            # Build filter for this image
            filters = []

            # Scale and pad to exact resolution
            filters.append(
                f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black"
            )

            # Apply Ken Burns if enabled
            if cfg.effects.ken_burns.enabled:
                direction = self._get_ken_burns_direction(i)
                intensity = cfg.effects.ken_burns.intensity
                frames = int(duration * cfg.fps)

                # Ken Burns zoom effect
                if direction == "in":
                    # Zoom in: start at 1.0, end at 1+intensity
                    filters.append(
                        f"zoompan=z='min(zoom+{intensity/frames:.6f},{1+intensity})':"
                        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                        f"d={frames}:s={width}x{height}:fps={cfg.fps}"
                    )
                else:
                    # Zoom out: start at 1+intensity, end at 1.0
                    filters.append(
                        f"zoompan=z='if(eq(on,1),{1+intensity},max(zoom-{intensity/frames:.6f},1))':"
                        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                        f"d={frames}:s={width}x{height}:fps={cfg.fps}"
                    )

            # Set fps
            filters.append(f"fps={cfg.fps}")

            # Format
            filters.append("format=yuv420p")

            filter_str = f"[{i}:v]{','.join(filters)}[{stream_name}]"
            filter_parts.append(filter_str)
            processed_streams.append(f"[{stream_name}]")

        # Build xfade transitions between streams
        if len(processed_streams) > 1:
            transition_duration = cfg.transition.duration
            current_stream = processed_streams[0]
            accumulated_offset = 0

            for i in range(1, len(processed_streams)):
                transition_type = self._get_transition_type(i - 1)
                offset = accumulated_offset + durations[i - 1] - transition_duration

                next_stream_name = f"x{i}"
                filter_parts.append(
                    f"{current_stream}{processed_streams[i]}xfade="
                    f"transition={transition_type}:duration={transition_duration}:"
                    f"offset={offset:.3f}[{next_stream_name}]"
                )
                current_stream = f"[{next_stream_name}]"
                accumulated_offset = offset

            final_video = current_stream
        else:
            final_video = processed_streams[0]

        # Apply global effects
        global_effects = []

        if cfg.effects.vignette.enabled:
            intensity = cfg.effects.vignette.intensity
            # vignette angle: PI/4 for subtle, PI/2 for strong
            angle = 3.14159 / (4 / max(0.1, intensity))
            global_effects.append(f"vignette=angle={angle}")

        if cfg.effects.grain.enabled:
            strength = int(cfg.effects.grain.intensity * 30)
            global_effects.append(f"noise=alls={strength}:allf=t")

        if global_effects:
            final_name = "vfinal"
            filter_parts.append(f"{final_video}{','.join(global_effects)}[{final_name}]")
            final_video = f"[{final_name}]"

        # Audio processing
        audio_filter = f"[{audio_index}:a]"
        if cfg.audio.normalize:
            audio_name = "aout"
            filter_parts.append(
                f"{audio_filter}loudnorm=I={cfg.audio.target_lufs}:TP=-1.5:LRA=11[{audio_name}]"
            )
            audio_output = f"[{audio_name}]"
        else:
            audio_output = f"{audio_index}:a"

        # Join all filters
        filter_complex = ";".join(filter_parts)

        # Build final command
        cmd = [
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", final_video,
            "-map", audio_output,
            "-c:v", "libx264",
            "-preset", cfg.preset,
            "-crf", str(cfg.crf),
            "-c:a", "aac" if cfg.audio.codec == "aac" else "libmp3lame",
            "-b:a", f"{cfg.audio.bitrate}k",
            "-r", str(cfg.fps),
            "-movflags", "+faststart",
            "-pix_fmt", "yuv420p",
            str(output_path)
        ]

        return cmd

    def _get_transition_type(self, index: int) -> str:
        """Retorna tipo de transição para o índice."""
        if not self.config.transition.vary:
            return self.config.transition.type.value

        allowed = self.config.transition.allowed_types or [self.config.transition.type]
        return allowed[index % len(allowed)].value

    def _get_ken_burns_direction(self, index: int) -> str:
        """Retorna direção do Ken Burns."""
        direction = self.config.effects.ken_burns.direction

        if direction == "zoom_in":
            return "in"
        elif direction == "alternate":
            return "in" if index % 2 == 0 else "out"
        else:  # random
            return random.choice(["in", "out"])
