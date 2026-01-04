"""
Serviço de composição de vídeo usando FFMPEG.

Para vídeos longos (>30 cenas), usa processamento em lotes para evitar
que o filter_complex fique muito grande e cause crash.
"""

import subprocess
import random
import shutil
from pathlib import Path
from typing import List, Optional, Callable
import logging
import os
import tempfile

from ..models.video import Scene, GeneratedImage, VideoResult
from ..models.config import FFmpegConfig

logger = logging.getLogger(__name__)

# Cores de fallback baseadas no mood
MOOD_COLORS = {
    "alegre": "0xFFDF80",
    "animado": "0xFFA54F",
    "calmo": "0x87CEEB",
    "dramatico": "0x464664",
    "inspirador": "0xFFD700",
    "melancolico": "0x696987",
    "neutro": "0x646464",
    "epico": "0x8B4513",
    "suspense": "0x2F2F3D",
}

# Limite de cenas por lote para evitar filter_complex muito grande
BATCH_SIZE = 20


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

        Para vídeos longos (>BATCH_SIZE cenas), usa processamento em lotes
        para evitar que o filter_complex do FFMPEG fique muito grande.

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

        logger.info(f"Composing video with {len(scenes)} scenes and {len(images)} images")

        # Calcular durações
        durations = self._calculate_durations(scenes)

        # Sort images by scene_index to match scenes
        sorted_images = sorted(images, key=lambda x: x.scene_index)

        # Verificar alinhamento entre cenas e imagens
        if len(scenes) != len(sorted_images):
            logger.warning(f"Mismatch: {len(scenes)} scenes but {len(sorted_images)} images")

        total_duration = sum(durations)
        logger.info(f"Total video duration: {total_duration:.2f}s")

        # Para vídeos longos, usar processamento em lotes
        if len(scenes) > BATCH_SIZE:
            logger.info(f"Using batch processing for {len(scenes)} scenes (batch size: {BATCH_SIZE})")
            video_only_path = self._compose_in_batches(
                scenes, sorted_images, durations, output_path
            )
            # Adicionar áudio ao vídeo final
            self._add_audio_to_video(video_only_path, audio_path, output_path)
            # Limpar vídeo intermediário
            try:
                Path(video_only_path).unlink(missing_ok=True)
            except Exception:
                pass
        else:
            # Processamento normal para vídeos curtos
            self._compose_single_pass(
                scenes, sorted_images, durations, audio_path, output_path
            )

        # Calcular metadados
        file_size = output_path.stat().st_size

        logger.info(f"Video composed successfully: {output_path}")

        return VideoResult(
            path=str(output_path),
            duration_seconds=total_duration,
            scenes_count=len(scenes),
            resolution=f"{self.config.resolution.width}x{self.config.resolution.height}",
            file_size=file_size
        )

    def _compose_in_batches(
        self,
        scenes: List[Scene],
        images: List[GeneratedImage],
        durations: List[float],
        output_path: Path
    ) -> str:
        """
        Processa vídeo em lotes para evitar filter_complex muito grande.

        1. Divide cenas em lotes de BATCH_SIZE
        2. Cada lote gera um vídeo intermediário
        3. Concatena todos os vídeos intermediários

        Returns:
            Path do vídeo sem áudio
        """
        temp_dir = output_path.parent / f"batch_temp_{output_path.stem}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        try:
            batch_videos = []
            num_batches = (len(scenes) + BATCH_SIZE - 1) // BATCH_SIZE

            for batch_idx in range(num_batches):
                start_idx = batch_idx * BATCH_SIZE
                end_idx = min(start_idx + BATCH_SIZE, len(scenes))

                batch_scenes = scenes[start_idx:end_idx]
                batch_images = images[start_idx:end_idx]
                batch_durations = durations[start_idx:end_idx]

                logger.info(f"Processing batch {batch_idx + 1}/{num_batches} (scenes {start_idx}-{end_idx - 1})")

                batch_output = temp_dir / f"batch_{batch_idx:03d}.mp4"

                # Gerar vídeo do lote (sem áudio)
                self._compose_batch(
                    batch_scenes, batch_images, batch_durations, batch_output
                )

                batch_videos.append(batch_output)

            # Concatenar todos os lotes
            logger.info(f"Concatenating {len(batch_videos)} batch videos...")
            video_only_path = output_path.parent / f"video_only_{output_path.stem}.mp4"
            self._concat_videos(batch_videos, video_only_path)

            return str(video_only_path)

        finally:
            # Limpar diretório temporário
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                logger.warning(f"Failed to cleanup batch temp dir: {e}")

    def _compose_batch(
        self,
        scenes: List[Scene],
        images: List[GeneratedImage],
        durations: List[float],
        output_path: Path
    ):
        """Compõe um lote de cenas em um vídeo intermediário (sem áudio)."""
        cfg = self.config
        width = cfg.resolution.width
        height = cfg.resolution.height

        inputs = []
        filter_parts = []
        color_inputs = []

        # Add image inputs
        for i, (img, duration) in enumerate(zip(images, durations)):
            if img.image_path and os.path.exists(img.image_path):
                inputs.extend(["-loop", "1", "-t", str(duration), "-i", img.image_path])
                color_inputs.append(False)
            else:
                scene_mood = scenes[i].mood if i < len(scenes) else "neutro"
                color = MOOD_COLORS.get(scene_mood, "0x646464")
                inputs.extend(["-f", "lavfi", "-t", str(duration), "-i", f"color=c={color}:s={width}x{height}:r={cfg.fps}"])
                color_inputs.append(True)

        # Process each image
        processed_streams = []
        for i, duration in enumerate(durations):
            stream_name = f"v{i}"
            filters = []

            is_color_input = color_inputs[i] if i < len(color_inputs) else False
            if not is_color_input:
                filters.append(f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black")

            # Ken Burns para lotes (simplificado se muitas cenas)
            if cfg.effects.ken_burns.enabled and not is_color_input:
                direction = self._get_ken_burns_direction(i)
                intensity = cfg.effects.ken_burns.intensity
                frames = int(duration * cfg.fps)

                if direction == "in":
                    filters.append(f"zoompan=z='min(zoom+{intensity/frames:.6f},{1+intensity})':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={width}x{height}:fps={cfg.fps}")
                else:
                    filters.append(f"zoompan=z='if(eq(on,1),{1+intensity},max(zoom-{intensity/frames:.6f},1))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={width}x{height}:fps={cfg.fps}")

            filters.append(f"fps={cfg.fps}")
            filters.append("format=yuv420p")

            filter_str = f"[{i}:v]{','.join(filters)}[{stream_name}]"
            filter_parts.append(filter_str)
            processed_streams.append(f"[{stream_name}]")

        # Transições dentro do lote
        if len(processed_streams) > 1:
            transition_type = cfg.transition.type.value
            transition_duration = cfg.transition.duration

            if transition_type == "none":
                concat_inputs = "".join(processed_streams)
                filter_parts.append(f"{concat_inputs}concat=n={len(processed_streams)}:v=1:a=0[vout]")
                final_video = "[vout]"
            else:
                current_stream = processed_streams[0]
                accumulated_offset = 0

                for i in range(1, len(processed_streams)):
                    trans = self._get_transition_type(i - 1)
                    offset = max(0, accumulated_offset + durations[i - 1] - transition_duration)
                    next_stream_name = f"x{i}"
                    filter_parts.append(f"{current_stream}{processed_streams[i]}xfade=transition={trans}:duration={transition_duration}:offset={offset:.3f}[{next_stream_name}]")
                    current_stream = f"[{next_stream_name}]"
                    accumulated_offset = offset

                final_video = current_stream
        else:
            final_video = processed_streams[0]

        filter_complex = ";".join(filter_parts)

        cmd = [
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", final_video,
            "-c:v", "libx264",
            "-preset", cfg.preset,
            "-crf", str(cfg.crf),
            "-r", str(cfg.fps),
            "-pix_fmt", "yuv420p",
            "-an",  # Sem áudio para lotes intermediários
            str(output_path)
        ]

        self._run_ffmpeg(cmd, f"batch_{output_path.stem}")

    def _concat_videos(self, video_paths: List[Path], output_path: Path):
        """Concatena múltiplos vídeos usando concat demuxer."""
        # Criar arquivo de lista para concat
        list_file = output_path.parent / f"concat_list_{output_path.stem}.txt"

        try:
            with open(list_file, "w") as f:
                for video_path in video_paths:
                    # Escapar aspas simples no path
                    escaped_path = str(video_path).replace("'", "'\\''")
                    f.write(f"file '{escaped_path}'\n")

            cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(list_file),
                "-c", "copy",
                str(output_path)
            ]

            self._run_ffmpeg(cmd, "concat_videos")

        finally:
            try:
                list_file.unlink(missing_ok=True)
            except Exception:
                pass

    def _add_audio_to_video(self, video_path: str, audio_path: str, output_path: Path):
        """Adiciona áudio ao vídeo final."""
        cfg = self.config

        audio_filter = ""
        if cfg.audio.normalize:
            audio_filter = f"-af loudnorm=I={cfg.audio.target_lufs}:TP=-1.5:LRA=11"

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac" if cfg.audio.codec == "aac" else "libmp3lame",
            "-b:a", f"{cfg.audio.bitrate}k",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            "-movflags", "+faststart",
        ]

        if audio_filter:
            cmd.extend(["-af", f"loudnorm=I={cfg.audio.target_lufs}:TP=-1.5:LRA=11"])

        cmd.append(str(output_path))

        self._run_ffmpeg(cmd, "add_audio")

    def _compose_single_pass(
        self,
        scenes: List[Scene],
        images: List[GeneratedImage],
        durations: List[float],
        audio_path: str,
        output_path: Path
    ):
        """Composição em passagem única para vídeos curtos."""
        cmd = self._build_ffmpeg_command(
            scenes, images, durations, audio_path, output_path
        )
        self._run_ffmpeg(cmd, "compose_single")

    def _run_ffmpeg(self, cmd: List[str], operation: str):
        """Executa comando FFMPEG com tratamento de erro robusto."""
        stderr_log = self.output_dir / f"ffmpeg_{operation}.log"

        logger.debug(f"Running FFMPEG [{operation}] with {len(cmd)} arguments")

        try:
            with open(stderr_log, "w") as stderr_file:
                result = subprocess.run(
                    cmd,
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=stderr_file,
                    timeout=600  # 10 minutos timeout por operação
                )

            # Log últimas linhas para debug
            try:
                with open(stderr_log, "r") as f:
                    f.seek(0, 2)
                    file_size = f.tell()
                    f.seek(max(0, file_size - 1000))
                    last_lines = f.read()
                    logger.debug(f"FFMPEG [{operation}] output: {last_lines[-500:]}")
            except Exception:
                pass

            stderr_log.unlink(missing_ok=True)

        except subprocess.TimeoutExpired:
            logger.error(f"FFMPEG [{operation}] timeout after 600s")
            raise RuntimeError(f"FFMPEG timeout: {operation}")
        except subprocess.CalledProcessError as e:
            error_msg = "Unknown error"
            try:
                with open(stderr_log, "r") as f:
                    f.seek(0, 2)
                    file_size = f.tell()
                    f.seek(max(0, file_size - 2000))
                    error_msg = f.read()
            except Exception:
                pass
            logger.error(f"FFMPEG [{operation}] error: {error_msg[-500:]}")
            raise RuntimeError(f"FFMPEG failed [{operation}]: {error_msg[-300:]}")

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
        color_inputs = []  # Track which inputs are color sources

        # Add image inputs with loop for duration
        for i, (img, duration) in enumerate(zip(images, durations)):
            # Check if image exists
            if img.image_path and os.path.exists(img.image_path):
                inputs.extend([
                    "-loop", "1",
                    "-t", str(duration),
                    "-i", img.image_path
                ])
                color_inputs.append(False)
            else:
                # Use color source as fallback
                scene_mood = scenes[i].mood if i < len(scenes) else "neutro"
                color = MOOD_COLORS.get(scene_mood, "0x646464")
                logger.warning(f"Scene {i} missing image, using color {color} for mood '{scene_mood}'")
                inputs.extend([
                    "-f", "lavfi",
                    "-t", str(duration),
                    "-i", f"color=c={color}:s={width}x{height}:r={cfg.fps}"
                ])
                color_inputs.append(True)

        # Add audio input
        audio_index = len(images)
        inputs.extend(["-i", audio_path])

        # Process each image
        processed_streams = []
        for i, duration in enumerate(durations):
            stream_name = f"v{i}"

            # Build filter for this image
            filters = []

            # Scale and pad to exact resolution (skip for color inputs - already correct size)
            is_color_input = color_inputs[i] if i < len(color_inputs) else False
            if not is_color_input:
                filters.append(
                    f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                    f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black"
                )

            # Apply Ken Burns if enabled (skip for color inputs)
            if cfg.effects.ken_burns.enabled and not is_color_input:
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

        # Build transitions between streams
        if len(processed_streams) > 1:
            transition_type = cfg.transition.type.value
            transition_duration = cfg.transition.duration

            # If transition is "none", use concat instead of xfade
            if transition_type == "none":
                # Simple concat - no crossfade
                concat_inputs = "".join(processed_streams)
                filter_parts.append(
                    f"{concat_inputs}concat=n={len(processed_streams)}:v=1:a=0[vconcat]"
                )
                final_video = "[vconcat]"
            else:
                # Use xfade for transitions
                current_stream = processed_streams[0]
                accumulated_offset = 0

                for i in range(1, len(processed_streams)):
                    trans = self._get_transition_type(i - 1)
                    # Ensure offset doesn't go negative
                    offset = max(0, accumulated_offset + durations[i - 1] - transition_duration)

                    next_stream_name = f"x{i}"
                    filter_parts.append(
                        f"{current_stream}{processed_streams[i]}xfade="
                        f"transition={trans}:duration={transition_duration}:"
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
        """Retorna tipo de transição para o índice (nunca 'none' para xfade)."""
        if not self.config.transition.vary:
            trans = self.config.transition.type.value
            # 'none' is not valid for xfade, use 'fade' as fallback
            return "fade" if trans == "none" else trans

        allowed = self.config.transition.allowed_types or [self.config.transition.type]
        trans = allowed[index % len(allowed)].value
        return "fade" if trans == "none" else trans

    def _get_ken_burns_direction(self, index: int) -> str:
        """Retorna direção do Ken Burns."""
        direction = self.config.effects.ken_burns.direction

        if direction == "zoom_in":
            return "in"
        elif direction == "alternate":
            return "in" if index % 2 == 0 else "out"
        else:  # random
            return random.choice(["in", "out"])
