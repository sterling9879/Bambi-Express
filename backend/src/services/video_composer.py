"""
Serviço de composição de vídeo usando FFMPEG.

Para vídeos longos (>20 cenas), usa processamento em lotes para evitar
que o filter_complex fique muito grande e cause crash.

Otimizações:
- Limite de threads FFMPEG para evitar sobrecarga de CPU
- Processamento em lotes com transições suaves entre batches
- Ken Burns otimizado para memória
- Efeitos globais aplicados por batch
- Fallback para vídeos muito longos (sem Ken Burns)
"""

import subprocess
import shutil
from pathlib import Path
from typing import List, Optional, Callable, Tuple
import logging
import os
import hashlib

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

# Configurações de processamento
BATCH_SIZE = 10  # Cenas por lote (reduzido para processar mais rápido)
MAX_SCENES_FOR_KEN_BURNS = 80  # Limite reduzido - zoompan é muito pesado para CPU
MAX_SCENES_FOR_TRANSITIONS = 500  # Transições funcionam bem com batch processing
FFMPEG_THREADS = 2  # Limitar threads para evitar OOM
TIMEOUT_PER_SCENE = 45  # Segundos de timeout por cena (zoompan é muito pesado)


def _to_absolute_path(path: str) -> str:
    """Converte qualquer caminho para absoluto."""
    return str(Path(path).resolve())


class VideoComposer:
    """
    Compõe vídeo final usando FFMPEG.

    Features:
    - Duração de cenas configurável (auto/fixa/range)
    - Múltiplos tipos de transição
    - Efeito Ken Burns (zoom/pan) com fallback para vídeos longos
    - Vinheta e grain
    - Normalização de áudio
    - Processamento em lotes para estabilidade
    """

    def __init__(self, config: FFmpegConfig, output_dir: str = "output"):
        self.config = config
        self.output_dir = Path(output_dir).resolve()  # Sempre usar caminho absoluto
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._temp_files: List[Path] = []  # Track temp files for cleanup

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
        """
        output_path = (self.output_dir / output_filename).resolve()
        audio_path_abs = _to_absolute_path(audio_path)
        self._temp_files = []

        try:
            logger.info(f"Composing video with {len(scenes)} scenes and {len(images)} images")
            logger.info(f"Output path: {output_path}")
            logger.info(f"Audio path: {audio_path_abs}")

            # Verificar que o áudio existe
            if not Path(audio_path_abs).exists():
                raise RuntimeError(f"Audio file not found: {audio_path_abs}")

            # Determinar modo de processamento baseado na quantidade de cenas
            use_ken_burns = len(scenes) <= MAX_SCENES_FOR_KEN_BURNS and self.config.effects.ken_burns.enabled
            use_transitions = len(scenes) <= MAX_SCENES_FOR_TRANSITIONS

            if not use_ken_burns and self.config.effects.ken_burns.enabled:
                logger.info(f"Disabling Ken Burns for {len(scenes)} scenes (max: {MAX_SCENES_FOR_KEN_BURNS})")

            if not use_transitions:
                logger.info(f"Using simple concat for {len(scenes)} scenes (max for transitions: {MAX_SCENES_FOR_TRANSITIONS})")

            # Calcular durações
            durations = self._calculate_durations(scenes)

            # Sort images by scene_index to match scenes
            sorted_images = sorted(images, key=lambda x: x.scene_index)

            # Verificar alinhamento entre cenas e imagens
            if len(scenes) != len(sorted_images):
                logger.warning(f"Mismatch: {len(scenes)} scenes but {len(sorted_images)} images")
                # Ajustar para o menor tamanho
                min_len = min(len(scenes), len(sorted_images))
                scenes = scenes[:min_len]
                sorted_images = sorted_images[:min_len]
                durations = durations[:min_len]

            total_duration = sum(durations)
            logger.info(f"Total video duration: {total_duration:.2f}s")

            # Para vídeos longos, usar processamento em lotes
            if len(scenes) > BATCH_SIZE:
                logger.info(f"Using batch processing for {len(scenes)} scenes (batch size: {BATCH_SIZE})")
                video_only_path = self._compose_in_batches(
                    scenes, sorted_images, durations, output_path,
                    use_ken_burns=use_ken_burns,
                    use_transitions=use_transitions
                )
                # Adicionar áudio ao vídeo final
                self._add_audio_to_video(video_only_path, audio_path_abs, output_path)
            else:
                # Processamento normal para vídeos curtos
                self._compose_single_pass(
                    scenes, sorted_images, durations, audio_path_abs, output_path,
                    use_ken_burns=use_ken_burns,
                    use_transitions=use_transitions
                )

            # Verificar se o arquivo foi criado
            if not output_path.exists():
                raise RuntimeError("Video file was not created")

            # Calcular metadados
            file_size = output_path.stat().st_size
            if file_size < 1000:
                raise RuntimeError(f"Video file too small ({file_size} bytes), likely corrupted")

            logger.info(f"Video composed successfully: {output_path} ({file_size / 1024 / 1024:.1f}MB)")

            return VideoResult(
                path=str(output_path),
                duration_seconds=total_duration,
                scenes_count=len(scenes),
                resolution=f"{self.config.resolution.width}x{self.config.resolution.height}",
                file_size=file_size
            )

        finally:
            # Cleanup temp files
            self._cleanup_temp_files()

    def _cleanup_temp_files(self):
        """Remove arquivos temporários."""
        for temp_file in self._temp_files:
            try:
                if temp_file.is_file():
                    temp_file.unlink(missing_ok=True)
                elif temp_file.is_dir():
                    shutil.rmtree(temp_file, ignore_errors=True)
            except Exception as e:
                logger.warning(f"Failed to cleanup {temp_file}: {e}")
        self._temp_files = []

    def _compose_in_batches(
        self,
        scenes: List[Scene],
        images: List[GeneratedImage],
        durations: List[float],
        output_path: Path,
        use_ken_burns: bool = True,
        use_transitions: bool = True
    ) -> str:
        """
        Processa vídeo em lotes para evitar filter_complex muito grande.
        """
        temp_dir = (output_path.parent / f"batch_temp_{output_path.stem}").resolve()
        temp_dir.mkdir(parents=True, exist_ok=True)
        self._temp_files.append(temp_dir)

        batch_videos = []
        num_batches = (len(scenes) + BATCH_SIZE - 1) // BATCH_SIZE

        for batch_idx in range(num_batches):
            start_idx = batch_idx * BATCH_SIZE
            end_idx = min(start_idx + BATCH_SIZE, len(scenes))

            batch_scenes = scenes[start_idx:end_idx]
            batch_images = images[start_idx:end_idx]
            batch_durations = durations[start_idx:end_idx]

            logger.info(f"Processing batch {batch_idx + 1}/{num_batches} (scenes {start_idx}-{end_idx - 1})")

            batch_output = (temp_dir / f"batch_{batch_idx:03d}.mp4").resolve()

            # Gerar vídeo do lote (sem áudio)
            self._compose_batch(
                batch_scenes, batch_images, batch_durations, batch_output,
                batch_index=batch_idx,
                is_first_batch=(batch_idx == 0),
                is_last_batch=(batch_idx == num_batches - 1),
                use_ken_burns=use_ken_burns,
                use_transitions=use_transitions
            )

            # Verificar que o arquivo foi criado e tem tamanho válido
            if not batch_output.exists():
                raise RuntimeError(f"Batch {batch_idx} failed to create output file at {batch_output}")

            file_size = batch_output.stat().st_size
            if file_size < 1000:
                raise RuntimeError(f"Batch {batch_idx} file too small ({file_size} bytes)")

            logger.info(f"Batch {batch_idx} created: {batch_output} ({file_size / 1024:.1f}KB)")
            batch_videos.append(batch_output)

        # Concatenar todos os lotes com transição suave
        logger.info(f"Concatenating {len(batch_videos)} batch videos...")
        video_only_path = (output_path.parent / f"video_only_{output_path.stem}.mp4").resolve()
        self._temp_files.append(video_only_path)

        self._concat_videos_with_fade(batch_videos, video_only_path)

        return str(video_only_path)

    def _compose_batch(
        self,
        scenes: List[Scene],
        images: List[GeneratedImage],
        durations: List[float],
        output_path: Path,
        batch_index: int = 0,
        is_first_batch: bool = True,
        is_last_batch: bool = True,
        use_ken_burns: bool = True,
        use_transitions: bool = True
    ):
        """Compõe um lote de cenas em um vídeo intermediário (sem áudio)."""
        cfg = self.config
        width = cfg.resolution.width
        height = cfg.resolution.height

        inputs = []
        filter_parts = []
        color_inputs = []

        # Add image inputs - SEMPRE usar caminhos absolutos
        for i, (img, duration) in enumerate(zip(images, durations)):
            if img.image_path:
                abs_image_path = _to_absolute_path(img.image_path)
                if os.path.exists(abs_image_path):
                    inputs.extend(["-loop", "1", "-t", str(duration), "-i", abs_image_path])
                    color_inputs.append(False)
                else:
                    logger.warning(f"Image not found: {abs_image_path}, using color fallback")
                    scene_mood = scenes[i].mood if i < len(scenes) else "neutro"
                    color = MOOD_COLORS.get(scene_mood, "0x646464")
                    inputs.extend([
                        "-f", "lavfi",
                        "-t", str(duration),
                        "-i", f"color=c={color}:s={width}x{height}:r={cfg.fps}"
                    ])
                    color_inputs.append(True)
            else:
                scene_mood = scenes[i].mood if i < len(scenes) else "neutro"
                color = MOOD_COLORS.get(scene_mood, "0x646464")
                inputs.extend([
                    "-f", "lavfi",
                    "-t", str(duration),
                    "-i", f"color=c={color}:s={width}x{height}:r={cfg.fps}"
                ])
                color_inputs.append(True)

        # Process each image
        processed_streams = []
        for i, duration in enumerate(durations):
            stream_name = f"v{i}"
            filters = []

            is_color_input = color_inputs[i] if i < len(color_inputs) else False

            # Scale and pad
            if not is_color_input:
                filters.append(
                    f"scale={width}:{height}:force_original_aspect_ratio=decrease:"
                    f"flags=lanczos,"
                    f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black"
                )

            # Ken Burns (otimizado)
            if use_ken_burns and cfg.effects.ken_burns.enabled and not is_color_input:
                # Índice global para consistência
                global_index = batch_index * BATCH_SIZE + i
                direction = self._get_ken_burns_direction(global_index)
                intensity = min(cfg.effects.ken_burns.intensity, 0.08)  # Limitar intensidade
                frames = int(duration * cfg.fps)

                # Zoompan simplificado e mais estável
                if direction == "in":
                    filters.append(
                        f"zoompan=z='1+{intensity}*on/{frames}':"
                        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                        f"d={frames}:s={width}x{height}:fps={cfg.fps}"
                    )
                else:
                    filters.append(
                        f"zoompan=z='{1+intensity}-{intensity}*on/{frames}':"
                        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                        f"d={frames}:s={width}x{height}:fps={cfg.fps}"
                    )

            filters.append(f"fps={cfg.fps}")
            filters.append("format=yuv420p")

            # Aplicar efeitos globais por cena (mais eficiente que no final)
            if cfg.effects.vignette.enabled:
                intensity = min(cfg.effects.vignette.intensity, 0.5)
                angle = 3.14159 * intensity / 2
                filters.append(f"vignette=angle={angle:.3f}")

            if cfg.effects.grain.enabled:
                strength = min(int(cfg.effects.grain.intensity * 20), 15)
                if strength > 0:
                    filters.append(f"noise=alls={strength}:allf=t")

            filter_str = f"[{i}:v]{','.join(filters)}[{stream_name}]"
            filter_parts.append(filter_str)
            processed_streams.append(f"[{stream_name}]")

        # Transições dentro do lote
        if len(processed_streams) > 1:
            if use_transitions and cfg.transition.type.value != "none":
                transition_duration = min(cfg.transition.duration, 0.3)  # Limitar duração
                current_stream = processed_streams[0]
                accumulated_offset = 0

                for i in range(1, len(processed_streams)):
                    global_index = batch_index * BATCH_SIZE + i
                    trans = self._get_transition_type(global_index - 1)
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
                # Simple concat
                concat_inputs = "".join(processed_streams)
                filter_parts.append(f"{concat_inputs}concat=n={len(processed_streams)}:v=1:a=0[vout]")
                final_video = "[vout]"
        else:
            final_video = processed_streams[0]

        filter_complex = ";".join(filter_parts)

        # Comando FFMPEG otimizado
        cmd = [
            "ffmpeg", "-y",
            "-threads", str(FFMPEG_THREADS),
            *inputs,
            "-filter_complex", filter_complex,
            "-map", final_video,
            "-c:v", "libx264",
            "-preset", cfg.preset,
            "-crf", str(cfg.crf),
            "-r", str(cfg.fps),
            "-pix_fmt", "yuv420p",
            "-max_muxing_queue_size", "1024",
            "-an",
            str(output_path)
        ]

        timeout = max(450, len(scenes) * TIMEOUT_PER_SCENE)
        self._run_ffmpeg(cmd, f"batch_{batch_index:03d}", timeout=timeout)

    def _concat_videos_with_fade(self, video_paths: List[Path], output_path: Path):
        """Concatena vídeos com fade suave entre eles."""
        if len(video_paths) == 1:
            # Apenas copiar
            shutil.copy2(video_paths[0], output_path)
            return

        # Para poucos vídeos, usar xfade. Para muitos, usar concat simples.
        if len(video_paths) <= 10:
            self._concat_with_xfade(video_paths, output_path)
        else:
            self._concat_simple(video_paths, output_path)

    def _concat_with_xfade(self, video_paths: List[Path], output_path: Path):
        """Concatena com crossfade entre batches."""
        fade_duration = 0.3

        # IMPORTANTE: Usar caminhos absolutos
        inputs = []
        for vp in video_paths:
            abs_path = str(vp.resolve())
            inputs.extend(["-i", abs_path])

        # Obter duração de cada vídeo
        durations = []
        for vp in video_paths:
            dur = self._get_video_duration(vp.resolve())
            durations.append(dur)

        # Construir filter para xfade entre todos
        filter_parts = []
        current = "[0:v]"
        accumulated_offset = 0

        for i in range(1, len(video_paths)):
            offset = max(0, accumulated_offset + durations[i-1] - fade_duration)
            out_name = f"[v{i}]"
            filter_parts.append(
                f"{current}[{i}:v]xfade=transition=fade:duration={fade_duration}:"
                f"offset={offset:.3f}{out_name}"
            )
            current = out_name
            accumulated_offset = offset

        filter_complex = ";".join(filter_parts)

        cmd = [
            "ffmpeg", "-y",
            "-threads", str(FFMPEG_THREADS),
            *inputs,
            "-filter_complex", filter_complex,
            "-map", current,
            "-c:v", "libx264",
            "-preset", self.config.preset,
            "-crf", str(self.config.crf),
            "-pix_fmt", "yuv420p",
            str(output_path.resolve())
        ]

        # Timeout maior para concat com xfade (re-encode)
        timeout = max(600, len(video_paths) * 120)
        self._run_ffmpeg(cmd, "concat_xfade", timeout=timeout)

    def _concat_simple(self, video_paths: List[Path], output_path: Path):
        """Concatena usando concat demuxer (mais rápido para muitos vídeos)."""
        list_file = (output_path.parent / f"concat_list_{output_path.stem}.txt").resolve()
        self._temp_files.append(list_file)

        # Verificar que todos os arquivos existem e têm tamanho válido
        logger.info(f"Verifying {len(video_paths)} batch files before concatenation...")
        for idx, video_path in enumerate(video_paths):
            abs_path = video_path.resolve()
            if not abs_path.exists():
                raise RuntimeError(f"Batch file {idx} not found: {abs_path}")
            file_size = abs_path.stat().st_size
            if file_size < 1000:
                raise RuntimeError(f"Batch file {idx} too small ({file_size} bytes): {abs_path}")
            logger.debug(f"Verified batch {idx}: {abs_path} ({file_size} bytes)")

        # Criar arquivo de lista para concat demuxer
        with open(list_file, "w", encoding="utf-8") as f:
            for video_path in video_paths:
                # Usar caminho absoluto e escapar aspas simples
                abs_path = str(video_path.resolve())
                # Para o concat demuxer, usar escape correto
                escaped_path = abs_path.replace("'", "'\\''")
                f.write(f"file '{escaped_path}'\n")

        # Log do conteúdo do arquivo de lista para debug
        logger.info(f"Concat list file created: {list_file}")
        with open(list_file, "r") as f:
            content = f.read()
            logger.debug(f"Concat list content:\n{content}")

        cmd = [
            "ffmpeg", "-y",
            "-threads", str(FFMPEG_THREADS),
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            str(output_path.resolve())
        ]

        self._run_ffmpeg(cmd, "concat_simple", timeout=600)

    def _get_video_duration(self, video_path: Path) -> float:
        """Obtém duração do vídeo usando ffprobe."""
        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    str(video_path.resolve())
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            duration = float(result.stdout.strip())
            logger.debug(f"Video duration for {video_path.name}: {duration:.2f}s")
            return duration
        except Exception as e:
            logger.warning(f"Failed to get duration for {video_path}: {e}")
            return 60.0  # Fallback

    def _add_audio_to_video(self, video_path: str, audio_path: str, output_path: Path):
        """Adiciona áudio ao vídeo final."""
        cfg = self.config

        # Garantir caminhos absolutos
        video_path_abs = _to_absolute_path(video_path)
        audio_path_abs = _to_absolute_path(audio_path)
        output_path_abs = str(output_path.resolve())

        logger.info(f"Adding audio to video:")
        logger.info(f"  Video: {video_path_abs}")
        logger.info(f"  Audio: {audio_path_abs}")
        logger.info(f"  Output: {output_path_abs}")

        # Verificar que os arquivos existem
        if not Path(video_path_abs).exists():
            raise RuntimeError(f"Video file not found: {video_path_abs}")
        if not Path(audio_path_abs).exists():
            raise RuntimeError(f"Audio file not found: {audio_path_abs}")

        cmd = [
            "ffmpeg", "-y",
            "-threads", str(FFMPEG_THREADS),
            "-i", video_path_abs,
            "-i", audio_path_abs,
            "-c:v", "copy",
            "-c:a", "aac" if cfg.audio.codec == "aac" else "libmp3lame",
            "-b:a", f"{cfg.audio.bitrate}k",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            "-movflags", "+faststart",
        ]

        if cfg.audio.normalize:
            cmd.extend(["-af", f"loudnorm=I={cfg.audio.target_lufs}:TP=-1.5:LRA=11"])

        cmd.append(output_path_abs)

        self._run_ffmpeg(cmd, "add_audio", timeout=600)

    def _compose_single_pass(
        self,
        scenes: List[Scene],
        images: List[GeneratedImage],
        durations: List[float],
        audio_path: str,
        output_path: Path,
        use_ken_burns: bool = True,
        use_transitions: bool = True
    ):
        """Composição em passagem única para vídeos curtos."""
        cmd = self._build_ffmpeg_command(
            scenes, images, durations, audio_path, output_path,
            use_ken_burns=use_ken_burns,
            use_transitions=use_transitions
        )
        timeout = max(450, len(scenes) * TIMEOUT_PER_SCENE)
        self._run_ffmpeg(cmd, "compose_single", timeout=timeout)

    def _run_ffmpeg(self, cmd: List[str], operation: str, timeout: int = 600):
        """Executa comando FFMPEG com tratamento de erro robusto."""
        stderr_log = self.output_dir / f"ffmpeg_{operation}.log"
        self._temp_files.append(stderr_log)

        logger.info(f"Running FFMPEG [{operation}] (timeout: {timeout}s)")
        logger.debug(f"Command: {' '.join(cmd[:20])}...")  # Log apenas início

        try:
            with open(stderr_log, "w") as stderr_file:
                process = subprocess.run(
                    cmd,
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=stderr_file,
                    timeout=timeout
                )

            # Log últimas linhas para debug
            try:
                with open(stderr_log, "r") as f:
                    content = f.read()
                    if "error" in content.lower():
                        logger.warning(f"FFMPEG [{operation}] warnings: {content[-500:]}")
                    else:
                        logger.debug(f"FFMPEG [{operation}] completed successfully")
            except Exception:
                pass

            # Limpar log após sucesso
            try:
                stderr_log.unlink(missing_ok=True)
                self._temp_files.remove(stderr_log)
            except Exception:
                pass

        except subprocess.TimeoutExpired:
            error_msg = f"FFMPEG [{operation}] timeout after {timeout}s"
            logger.error(error_msg)
            self._log_ffmpeg_error(stderr_log, operation)
            raise RuntimeError(error_msg)

        except subprocess.CalledProcessError as e:
            self._log_ffmpeg_error(stderr_log, operation)
            error_msg = self._get_ffmpeg_error(stderr_log)
            raise RuntimeError(f"FFMPEG failed [{operation}]: {error_msg}")

    def _log_ffmpeg_error(self, stderr_log: Path, operation: str):
        """Log detalhado de erro FFMPEG."""
        try:
            if stderr_log.exists():
                with open(stderr_log, "r") as f:
                    content = f.read()
                    # Encontrar linhas com erro
                    error_lines = [l for l in content.split('\n') if 'error' in l.lower()]
                    if error_lines:
                        logger.error(f"FFMPEG [{operation}] errors: {error_lines[-5:]}")
                    else:
                        logger.error(f"FFMPEG [{operation}] output: {content[-1000:]}")
        except Exception:
            pass

    def _get_ffmpeg_error(self, stderr_log: Path) -> str:
        """Extrai mensagem de erro do log FFMPEG."""
        try:
            if stderr_log.exists():
                with open(stderr_log, "r") as f:
                    content = f.read()
                    # Procurar por linhas de erro
                    for line in reversed(content.split('\n')):
                        if 'error' in line.lower():
                            return line[:200]
                    return content[-300:]
        except Exception:
            pass
        return "Unknown error"

    def _calculate_durations(self, scenes: List[Scene]) -> List[float]:
        """Calcula duração de cada cena baseado no modo."""
        mode = self.config.scene_duration.mode.value

        if mode == "auto":
            return [max(1.0, s.duration_ms / 1000) for s in scenes]  # Mínimo 1s

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

        return [max(1.0, s.duration_ms / 1000) for s in scenes]

    def _build_ffmpeg_command(
        self,
        scenes: List[Scene],
        images: List[GeneratedImage],
        durations: List[float],
        audio_path: str,
        output_path: Path,
        use_ken_burns: bool = True,
        use_transitions: bool = True
    ) -> List[str]:
        """Constrói comando FFMPEG completo para vídeos curtos."""

        cfg = self.config
        width = cfg.resolution.width
        height = cfg.resolution.height

        # Garantir caminhos absolutos
        audio_path_abs = _to_absolute_path(audio_path)
        output_path_abs = str(output_path.resolve())

        inputs = []
        filter_parts = []
        color_inputs = []

        # Add image inputs with loop for duration - SEMPRE usar caminhos absolutos
        for i, (img, duration) in enumerate(zip(images, durations)):
            if img.image_path:
                abs_image_path = _to_absolute_path(img.image_path)
                if os.path.exists(abs_image_path):
                    inputs.extend(["-loop", "1", "-t", str(duration), "-i", abs_image_path])
                    color_inputs.append(False)
                else:
                    scene_mood = scenes[i].mood if i < len(scenes) else "neutro"
                    color = MOOD_COLORS.get(scene_mood, "0x646464")
                    logger.warning(f"Scene {i} missing image at {abs_image_path}, using color {color}")
                    inputs.extend([
                        "-f", "lavfi",
                        "-t", str(duration),
                        "-i", f"color=c={color}:s={width}x{height}:r={cfg.fps}"
                    ])
                    color_inputs.append(True)
            else:
                scene_mood = scenes[i].mood if i < len(scenes) else "neutro"
                color = MOOD_COLORS.get(scene_mood, "0x646464")
                logger.warning(f"Scene {i} has no image path, using color {color}")
                inputs.extend([
                    "-f", "lavfi",
                    "-t", str(duration),
                    "-i", f"color=c={color}:s={width}x{height}:r={cfg.fps}"
                ])
                color_inputs.append(True)

        # Add audio input
        audio_index = len(images)
        inputs.extend(["-i", audio_path_abs])

        # Process each image
        processed_streams = []
        for i, duration in enumerate(durations):
            stream_name = f"v{i}"
            filters = []

            is_color_input = color_inputs[i] if i < len(color_inputs) else False

            if not is_color_input:
                filters.append(
                    f"scale={width}:{height}:force_original_aspect_ratio=decrease:"
                    f"flags=lanczos,"
                    f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black"
                )

            # Ken Burns
            if use_ken_burns and cfg.effects.ken_burns.enabled and not is_color_input:
                direction = self._get_ken_burns_direction(i)
                intensity = min(cfg.effects.ken_burns.intensity, 0.08)
                frames = int(duration * cfg.fps)

                if direction == "in":
                    filters.append(
                        f"zoompan=z='1+{intensity}*on/{frames}':"
                        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                        f"d={frames}:s={width}x{height}:fps={cfg.fps}"
                    )
                else:
                    filters.append(
                        f"zoompan=z='{1+intensity}-{intensity}*on/{frames}':"
                        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                        f"d={frames}:s={width}x{height}:fps={cfg.fps}"
                    )

            filters.append(f"fps={cfg.fps}")
            filters.append("format=yuv420p")

            filter_str = f"[{i}:v]{','.join(filters)}[{stream_name}]"
            filter_parts.append(filter_str)
            processed_streams.append(f"[{stream_name}]")

        # Build transitions
        if len(processed_streams) > 1:
            if use_transitions and cfg.transition.type.value != "none":
                transition_duration = min(cfg.transition.duration, 0.3)
                current_stream = processed_streams[0]
                accumulated_offset = 0

                for i in range(1, len(processed_streams)):
                    trans = self._get_transition_type(i - 1)
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
                concat_inputs = "".join(processed_streams)
                filter_parts.append(f"{concat_inputs}concat=n={len(processed_streams)}:v=1:a=0[vconcat]")
                final_video = "[vconcat]"
        else:
            final_video = processed_streams[0]

        # Apply global effects
        global_effects = []

        if cfg.effects.vignette.enabled:
            intensity = min(cfg.effects.vignette.intensity, 0.5)
            angle = 3.14159 * intensity / 2
            global_effects.append(f"vignette=angle={angle:.3f}")

        if cfg.effects.grain.enabled:
            strength = min(int(cfg.effects.grain.intensity * 20), 15)
            if strength > 0:
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

        filter_complex = ";".join(filter_parts)

        cmd = [
            "ffmpeg", "-y",
            "-threads", str(FFMPEG_THREADS),
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
            "-max_muxing_queue_size", "1024",
            output_path_abs
        ]

        return cmd

    def _get_transition_type(self, index: int) -> str:
        """Retorna tipo de transição para o índice."""
        if not self.config.transition.vary:
            trans = self.config.transition.type.value
            return "fade" if trans == "none" else trans

        allowed = self.config.transition.allowed_types or [self.config.transition.type]
        trans = allowed[index % len(allowed)].value
        return "fade" if trans == "none" else trans

    def _get_ken_burns_direction(self, index: int) -> str:
        """Retorna direção do Ken Burns de forma determinística."""
        direction = self.config.effects.ken_burns.direction

        if direction == "zoom_in":
            return "in"
        elif direction == "alternate":
            return "in" if index % 2 == 0 else "out"
        else:  # random - mas determinístico baseado no índice
            return "in" if index % 3 != 0 else "out"
