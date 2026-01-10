"""
Serviço para gerar e aplicar legendas estilo filme em vídeos.
"""

import subprocess
import json
import os
from pathlib import Path
from typing import Optional, Callable, List
from dataclasses import dataclass
import logging

from ..models.video import TranscriptionResult, Segment
from ..models.config import SubtitleConfig, SubtitlePosition

logger = logging.getLogger(__name__)


@dataclass
class SubtitleBurnResult:
    """Resultado da aplicação de legendas."""
    path: str
    duration_seconds: float
    file_size: int
    subtitle_count: int


class SubtitleBurner:
    """
    Gera e aplica legendas estilo filme em vídeos usando ffmpeg.

    Features:
    - Legendas com contorno (estilo filme/cinema)
    - Posição configurável (bottom, top, middle)
    - Fonte e cores personalizáveis
    - Geração de arquivo ASS para estilo avançado
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

    def _get_video_info(self, video_path: str) -> dict:
        """Obtém informações do vídeo (resolução)."""
        try:
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-of", "json",
                video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            stream = data["streams"][0]
            return {
                "width": stream["width"],
                "height": stream["height"]
            }
        except Exception as e:
            logger.error(f"Failed to get video info: {e}")
            return {"width": 1920, "height": 1080}

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
            return 0

    def _format_time_ass(self, ms: int) -> str:
        """Converte milissegundos para formato ASS (H:MM:SS.cc)."""
        total_seconds = ms / 1000
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = total_seconds % 60
        return f"{hours}:{minutes:02d}:{seconds:05.2f}"

    def _format_time_srt(self, ms: int) -> str:
        """Converte milissegundos para formato SRT (HH:MM:SS,mmm)."""
        total_seconds = ms / 1000
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        millis = int((total_seconds - int(total_seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"

    def _get_position_alignment(self, position: SubtitlePosition) -> int:
        """Retorna o alinhamento ASS para a posição."""
        # ASS alignment:
        # 1-3: bottom (left, center, right)
        # 4-6: middle (left, center, right)
        # 7-9: top (left, center, right)
        if position == SubtitlePosition.BOTTOM:
            return 2  # bottom center
        elif position == SubtitlePosition.TOP:
            return 8  # top center
        else:  # middle
            return 5  # middle center

    def _get_vertical_margin(self, position: SubtitlePosition, height: int, config: SubtitleConfig) -> int:
        """Calcula a margem vertical baseada na posição."""
        if position == SubtitlePosition.MIDDLE:
            return 0  # Centralizado
        return config.margin_vertical

    def _color_to_ass(self, color: str) -> str:
        """Converte cor para formato ASS (&HBBGGRR)."""
        colors = {
            "white": "&H00FFFFFF",
            "black": "&H00000000",
            "yellow": "&H0000FFFF",
            "red": "&H000000FF",
            "green": "&H0000FF00",
            "blue": "&H00FF0000",
            "cyan": "&H00FFFF00",
            "magenta": "&H00FF00FF",
        }
        return colors.get(color.lower(), "&H00FFFFFF")

    def generate_ass_file(
        self,
        transcription: TranscriptionResult,
        config: SubtitleConfig,
        video_width: int,
        video_height: int,
        output_path: str
    ) -> str:
        """
        Gera arquivo de legendas ASS (Advanced SubStation Alpha).

        ASS permite estilos avançados como contorno, sombra, e posicionamento preciso.
        """
        alignment = self._get_position_alignment(config.position)
        margin_v = self._get_vertical_margin(config.position, video_height, config)

        primary_color = self._color_to_ass(config.font_color)
        outline_color = self._color_to_ass(config.outline_color)

        # Calcular tamanho da fonte proporcional à resolução
        base_font_size = config.font_size
        if video_height < 720:
            base_font_size = int(base_font_size * 0.7)
        elif video_height > 1080:
            base_font_size = int(base_font_size * 1.2)

        # Header ASS
        ass_content = f"""[Script Info]
Title: Video Subtitles
ScriptType: v4.00+
PlayResX: {video_width}
PlayResY: {video_height}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,{base_font_size},{primary_color},&H000000FF,{outline_color},&H80000000,-1,0,0,0,100,100,0,0,1,{config.outline_width},1,{alignment},20,20,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        # Adicionar legendas dos segmentos
        for segment in transcription.segments:
            start_time = self._format_time_ass(segment.start_ms)
            end_time = self._format_time_ass(segment.end_ms)

            # Limpar texto (remover caracteres especiais do ASS)
            text = segment.text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")
            text = text.replace("\n", "\\N")

            ass_content += f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}\n"

        # Salvar arquivo
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(ass_content)

        return output_path

    def generate_srt_file(
        self,
        transcription: TranscriptionResult,
        output_path: str
    ) -> str:
        """Gera arquivo de legendas SRT (mais simples, menos estilos)."""
        srt_content = ""

        for i, segment in enumerate(transcription.segments, 1):
            start_time = self._format_time_srt(segment.start_ms)
            end_time = self._format_time_srt(segment.end_ms)

            srt_content += f"{i}\n"
            srt_content += f"{start_time} --> {end_time}\n"
            srt_content += f"{segment.text}\n\n"

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(srt_content)

        return output_path

    def burn_subtitles(
        self,
        video_path: str,
        transcription: TranscriptionResult,
        config: SubtitleConfig,
        output_filename: str = "video_with_subtitles.mp4"
    ) -> SubtitleBurnResult:
        """
        Aplica legendas permanentemente no vídeo (hard burn).

        Args:
            video_path: Caminho do vídeo original
            transcription: Resultado da transcrição com segmentos
            config: Configuração das legendas
            output_filename: Nome do arquivo de saída

        Returns:
            SubtitleBurnResult com informações do vídeo resultante
        """
        video_info = self._get_video_info(video_path)
        output_path = self.output_dir / output_filename

        self._log(f"Gerando legendas ({len(transcription.segments)} segmentos)...")

        # Gerar arquivo ASS
        ass_path = self.output_dir / "subtitles.ass"
        self.generate_ass_file(
            transcription=transcription,
            config=config,
            video_width=video_info["width"],
            video_height=video_info["height"],
            output_path=str(ass_path)
        )

        self._log(f"Aplicando legendas na posição: {config.position.value}...")

        # Usar ffmpeg para queimar legendas
        # Nota: O caminho do ASS precisa ter barras escapadas no Windows
        ass_path_escaped = str(ass_path).replace("\\", "/").replace(":", "\\:")

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", f"ass='{ass_path_escaped}'",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-c:a", "copy",
            str(output_path)
        ]

        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True
            )

            # Limpar arquivo ASS temporário
            try:
                ass_path.unlink()
            except Exception:
                pass

            # Obter informações do resultado
            final_duration = self._get_video_duration(str(output_path))
            file_size = output_path.stat().st_size

            self._log(f"Legendas aplicadas com sucesso: {len(transcription.segments)} segmentos")

            return SubtitleBurnResult(
                path=str(output_path),
                duration_seconds=final_duration,
                file_size=file_size,
                subtitle_count=len(transcription.segments)
            )

        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg error: {e.stderr}")

            # Tentar método alternativo com subtitles filter
            self._log("Tentando método alternativo de legendas...")
            return self._burn_subtitles_alternative(
                video_path, transcription, config, output_filename
            )

    def _burn_subtitles_alternative(
        self,
        video_path: str,
        transcription: TranscriptionResult,
        config: SubtitleConfig,
        output_filename: str
    ) -> SubtitleBurnResult:
        """
        Método alternativo usando filtro subtitles do ffmpeg com SRT.
        """
        output_path = self.output_dir / output_filename

        # Gerar arquivo SRT
        srt_path = self.output_dir / "subtitles.srt"
        self.generate_srt_file(transcription, str(srt_path))

        # Determinar posição Y
        video_info = self._get_video_info(video_path)
        height = video_info["height"]

        if config.position == SubtitlePosition.TOP:
            y_expr = f"{config.margin_vertical}"
        elif config.position == SubtitlePosition.MIDDLE:
            y_expr = f"(h-text_h)/2"
        else:  # bottom
            y_expr = f"h-text_h-{config.margin_vertical}"

        # Construir filtro drawtext para cada segmento (fallback mais básico)
        # Mas vamos tentar com subtitles filter primeiro
        srt_path_escaped = str(srt_path).replace("\\", "/").replace(":", "\\:")

        # Usar force_style para posição
        force_style = f"FontSize={config.font_size},PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline={config.outline_width}"

        if config.position == SubtitlePosition.TOP:
            force_style += ",Alignment=8,MarginV=" + str(config.margin_vertical)
        elif config.position == SubtitlePosition.MIDDLE:
            force_style += ",Alignment=5"
        else:
            force_style += ",Alignment=2,MarginV=" + str(config.margin_vertical)

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", f"subtitles='{srt_path_escaped}':force_style='{force_style}'",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-c:a", "copy",
            str(output_path)
        ]

        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True
            )

            # Limpar arquivo SRT temporário
            try:
                srt_path.unlink()
            except Exception:
                pass

            final_duration = self._get_video_duration(str(output_path))
            file_size = output_path.stat().st_size

            return SubtitleBurnResult(
                path=str(output_path),
                duration_seconds=final_duration,
                file_size=file_size,
                subtitle_count=len(transcription.segments)
            )

        except subprocess.CalledProcessError as e:
            logger.error(f"Alternative method also failed: {e.stderr}")
            raise RuntimeError(f"Falha ao aplicar legendas: {e.stderr}")
