"""
Serviço para aplicar efeitos de overlay em vídeos.
"""

import subprocess
import json
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class EffectApplicationResult:
    """Resultado da aplicação de efeito."""
    path: str
    duration_seconds: float
    file_size: int
    effect_applied: str


class EffectsApplier:
    """
    Aplica efeitos de overlay com fundo preto em vídeos.

    Features:
    - Overlay com blend mode para fundo preto (lighten/screen)
    - Loop automático de efeitos menores que o vídeo
    - Corte automático de efeitos maiores que o vídeo
    - Preservação de qualidade do vídeo original
    """

    def __init__(
        self,
        output_dir: str = "temp",
        log_callback: Optional[Callable[[str], None]] = None
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_callback = log_callback

    def _log(self, message: str):
        """Log message to both logger and callback if set."""
        logger.info(message)
        if self.log_callback:
            self.log_callback(message)

    def _get_video_duration(self, video_path: str) -> float:
        """Obtém duração do vídeo em segundos."""
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
            return float(data["format"]["duration"])
        except Exception as e:
            logger.error(f"Failed to get video duration: {e}")
            raise

    def _get_video_info(self, video_path: str) -> dict:
        """Obtém informações do vídeo (resolução, fps, etc)."""
        try:
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height,r_frame_rate",
                "-of", "json",
                video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            stream = data["streams"][0]

            # Parse frame rate (pode ser "30/1" ou "29.97")
            fps_str = stream.get("r_frame_rate", "30/1")
            if "/" in fps_str:
                num, den = map(int, fps_str.split("/"))
                fps = num / den if den > 0 else 30
            else:
                fps = float(fps_str)

            return {
                "width": stream["width"],
                "height": stream["height"],
                "fps": fps
            }
        except Exception as e:
            logger.error(f"Failed to get video info: {e}")
            return {"width": 1920, "height": 1080, "fps": 30}

    def apply_effect(
        self,
        video_path: str,
        effect_path: str,
        output_filename: str = "video_with_effect.mp4",
        blend_mode: str = "lighten",
        effect_opacity: float = 1.0
    ) -> EffectApplicationResult:
        """
        Aplica efeito de overlay no vídeo.

        O efeito é ajustado para ter a mesma duração do vídeo:
        - Se menor: é repetido em loop
        - Se maior: é cortado

        O fundo preto é tratado como transparente usando blend mode.

        Args:
            video_path: Caminho do vídeo original
            effect_path: Caminho do vídeo de efeito
            output_filename: Nome do arquivo de saída
            blend_mode: Modo de blend (lighten, screen, add)
            effect_opacity: Opacidade do efeito (0.0 a 1.0)

        Returns:
            EffectApplicationResult com informações do vídeo resultante
        """
        video_duration = self._get_video_duration(video_path)
        effect_duration = self._get_video_duration(effect_path)
        video_info = self._get_video_info(video_path)

        self._log(f"Aplicando efeito ao vídeo ({video_duration:.1f}s)...")
        self._log(f"Duração do efeito: {effect_duration:.1f}s")

        output_path = self.output_dir / output_filename

        # Construir filtro complex
        # 1. Ajustar duração do efeito (loop ou trim)
        # 2. Redimensionar efeito para match do vídeo
        # 3. Aplicar blend mode para fundo preto

        if effect_duration < video_duration:
            # Efeito menor - fazer loop
            loops_needed = int(video_duration / effect_duration) + 1
            self._log(f"Efeito será repetido {loops_needed}x para cobrir o vídeo")
            effect_input = f"[1:v]loop=loop={loops_needed}:size=999999:start=0,setpts=PTS-STARTPTS,trim=0:{video_duration},setpts=PTS-STARTPTS"
        else:
            # Efeito maior ou igual - cortar
            self._log(f"Efeito será cortado para {video_duration:.1f}s")
            effect_input = f"[1:v]trim=0:{video_duration},setpts=PTS-STARTPTS"

        # Redimensionar efeito para mesma resolução do vídeo
        scale_filter = f"scale={video_info['width']}:{video_info['height']}:force_original_aspect_ratio=increase,crop={video_info['width']}:{video_info['height']}"

        # Aplicar opacidade se necessário
        opacity_filter = ""
        if effect_opacity < 1.0:
            opacity_filter = f",format=rgba,colorchannelmixer=aa={effect_opacity}"

        # Construir filtro de blend
        # Para fundo preto, usamos "lighten" ou "screen" que mantém apenas pixels mais claros
        filter_complex = (
            f"{effect_input},{scale_filter}{opacity_filter}[effect];"
            f"[0:v][effect]blend=all_mode={blend_mode}:shortest=1[outv]"
        )

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", effect_path,
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-map", "0:a?",  # Manter áudio do vídeo original se existir
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            str(output_path)
        ]

        try:
            self._log("Processando overlay de efeito...")
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True
            )

            # Obter informações do resultado
            final_duration = self._get_video_duration(str(output_path))
            file_size = output_path.stat().st_size

            self._log(f"Efeito aplicado com sucesso: {final_duration:.1f}s, {file_size/1024/1024:.1f}MB")

            return EffectApplicationResult(
                path=str(output_path),
                duration_seconds=final_duration,
                file_size=file_size,
                effect_applied=Path(effect_path).stem
            )

        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg error: {e.stderr}")
            raise RuntimeError(f"Falha ao aplicar efeito: {e.stderr}")

    def apply_multiple_effects(
        self,
        video_path: str,
        effect_paths: list[str],
        output_filename: str = "video_with_effects.mp4",
        blend_mode: str = "lighten"
    ) -> EffectApplicationResult:
        """
        Aplica múltiplos efeitos em sequência.

        Args:
            video_path: Caminho do vídeo original
            effect_paths: Lista de caminhos dos efeitos
            output_filename: Nome do arquivo de saída
            blend_mode: Modo de blend

        Returns:
            EffectApplicationResult do vídeo final
        """
        if not effect_paths:
            # Sem efeitos, retorna informações do vídeo original
            duration = self._get_video_duration(video_path)
            file_size = Path(video_path).stat().st_size
            return EffectApplicationResult(
                path=video_path,
                duration_seconds=duration,
                file_size=file_size,
                effect_applied="none"
            )

        current_video = video_path
        temp_outputs = []

        for i, effect_path in enumerate(effect_paths):
            is_last = (i == len(effect_paths) - 1)
            temp_filename = output_filename if is_last else f"temp_effect_{i}.mp4"

            result = self.apply_effect(
                video_path=current_video,
                effect_path=effect_path,
                output_filename=temp_filename,
                blend_mode=blend_mode
            )

            # Limpar vídeo temporário anterior (exceto o original)
            if current_video != video_path and Path(current_video).exists():
                Path(current_video).unlink()

            current_video = result.path
            if not is_last:
                temp_outputs.append(result.path)

        return result

    def preview_effect(
        self,
        video_path: str,
        effect_path: str,
        output_filename: str = "preview.mp4",
        preview_duration: float = 5.0,
        blend_mode: str = "lighten"
    ) -> str:
        """
        Gera preview rápido do efeito (primeiros segundos).

        Args:
            video_path: Caminho do vídeo
            effect_path: Caminho do efeito
            output_filename: Nome do arquivo de saída
            preview_duration: Duração do preview em segundos
            blend_mode: Modo de blend

        Returns:
            Caminho do vídeo de preview
        """
        video_info = self._get_video_info(video_path)
        output_path = self.output_dir / output_filename

        filter_complex = (
            f"[1:v]scale={video_info['width']}:{video_info['height']}:force_original_aspect_ratio=increase,"
            f"crop={video_info['width']}:{video_info['height']}[effect];"
            f"[0:v][effect]blend=all_mode={blend_mode}:shortest=1[outv]"
        )

        cmd = [
            "ffmpeg", "-y",
            "-t", str(preview_duration),
            "-i", video_path,
            "-t", str(preview_duration),
            "-i", effect_path,
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "23",
            "-an",  # Sem áudio no preview
            str(output_path)
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)
            return str(output_path)
        except subprocess.CalledProcessError as e:
            logger.error(f"Preview generation failed: {e.stderr}")
            raise RuntimeError(f"Falha ao gerar preview: {e.stderr}")
