"""
Serviço para detectar e remover silêncios de áudio.
"""

import subprocess
import json
import re
from pathlib import Path
from typing import Optional, Callable, List, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class SilenceInfo:
    """Informação sobre silêncio detectado."""
    start: float  # segundos
    end: float  # segundos
    duration: float  # segundos


@dataclass
class SilenceRemovalResult:
    """Resultado da remoção de silêncios."""
    path: str
    original_duration_ms: int
    new_duration_ms: int
    silences_removed: int
    time_saved_ms: int


class SilenceRemover:
    """
    Remove silêncios longos de arquivos de áudio usando FFMPEG.

    Features:
    - Detecção de silêncios com threshold configurável
    - Remove apenas silêncios acima de duração mínima
    - Mantém qualidade do áudio original
    - Log detalhado das operações
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

    def detect_silences(
        self,
        audio_path: str,
        silence_threshold_db: float = -40,
        min_silence_duration: float = 0.5
    ) -> List[SilenceInfo]:
        """
        Detecta silêncios no áudio usando ffmpeg silencedetect.

        Args:
            audio_path: Caminho para o arquivo de áudio
            silence_threshold_db: Threshold em dB para considerar silêncio (default: -40dB)
            min_silence_duration: Duração mínima em segundos para considerar silêncio (default: 0.5s)

        Returns:
            Lista de SilenceInfo com os silêncios detectados
        """
        cmd = [
            "ffmpeg", "-y",
            "-i", audio_path,
            "-af", f"silencedetect=noise={silence_threshold_db}dB:d={min_silence_duration}",
            "-f", "null", "-"
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )

            # Parse output para encontrar silêncios
            silences = []
            output = result.stderr

            # Padrão: [silencedetect @ 0x...] silence_start: X.XXX
            # Padrão: [silencedetect @ 0x...] silence_end: X.XXX | silence_duration: X.XXX
            silence_start_pattern = r"silence_start: ([\d.]+)"
            silence_end_pattern = r"silence_end: ([\d.]+) \| silence_duration: ([\d.]+)"

            starts = re.findall(silence_start_pattern, output)
            ends = re.findall(silence_end_pattern, output)

            for i, (start, (end, duration)) in enumerate(zip(starts, ends)):
                silences.append(SilenceInfo(
                    start=float(start),
                    end=float(end),
                    duration=float(duration)
                ))

            logger.debug(f"Detected {len(silences)} silences in {audio_path}")
            return silences

        except subprocess.CalledProcessError as e:
            logger.error(f"Silence detection failed: {e.stderr}")
            return []

    def get_audio_duration(self, audio_path: str) -> float:
        """Obtém a duração do áudio em segundos."""
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "json",
            audio_path
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            return float(data["format"]["duration"])
        except Exception as e:
            logger.warning(f"Could not get audio duration: {e}")
            return 0

    def remove_silences(
        self,
        audio_path: str,
        output_filename: str = "audio_no_silence.mp3",
        silence_threshold_db: float = -40,
        min_silence_duration: float = 0.5,
        keep_silence_ms: int = 200
    ) -> SilenceRemovalResult:
        """
        Remove silêncios longos do áudio, mantendo pausas curtas naturais.

        Args:
            audio_path: Caminho para o arquivo de áudio
            output_filename: Nome do arquivo de saída
            silence_threshold_db: Threshold em dB para considerar silêncio
            min_silence_duration: Duração mínima em segundos para remover
            keep_silence_ms: Quantidade de silêncio em ms para manter nas bordas

        Returns:
            SilenceRemovalResult com informações sobre a remoção
        """
        original_duration = self.get_audio_duration(audio_path)
        original_duration_ms = int(original_duration * 1000)

        self._log(f"Analisando silêncios no áudio ({original_duration:.1f}s)...")

        # Detectar silêncios
        silences = self.detect_silences(
            audio_path,
            silence_threshold_db=silence_threshold_db,
            min_silence_duration=min_silence_duration
        )

        if not silences:
            self._log("Nenhum silêncio significativo detectado")
            # Retornar o arquivo original
            return SilenceRemovalResult(
                path=audio_path,
                original_duration_ms=original_duration_ms,
                new_duration_ms=original_duration_ms,
                silences_removed=0,
                time_saved_ms=0
            )

        total_silence_duration = sum(s.duration for s in silences)
        self._log(f"Detectados {len(silences)} silêncios ({total_silence_duration:.1f}s total)")

        # Calcular segmentos de áudio para manter
        keep_silence_s = keep_silence_ms / 1000
        segments = self._calculate_segments(silences, original_duration, keep_silence_s)

        if not segments:
            self._log("Nenhum segmento de áudio encontrado após análise")
            return SilenceRemovalResult(
                path=audio_path,
                original_duration_ms=original_duration_ms,
                new_duration_ms=original_duration_ms,
                silences_removed=0,
                time_saved_ms=0
            )

        # Criar filtro complex para extrair e concatenar segmentos
        output_path = self.output_dir / output_filename

        # Usar filtro trim + concat
        filter_parts = []
        concat_inputs = []

        for i, (start, end) in enumerate(segments):
            filter_parts.append(f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a{i}]")
            concat_inputs.append(f"[a{i}]")

        filter_complex = ";".join(filter_parts)
        filter_complex += f";{''.join(concat_inputs)}concat=n={len(segments)}:v=0:a=1[out]"

        cmd = [
            "ffmpeg", "-y",
            "-i", audio_path,
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-c:a", "libmp3lame",
            "-q:a", "2",  # Alta qualidade
            str(output_path)
        ]

        try:
            self._log("Removendo silêncios...")
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True
            )

            new_duration = self.get_audio_duration(str(output_path))
            new_duration_ms = int(new_duration * 1000)
            time_saved_ms = original_duration_ms - new_duration_ms

            self._log(
                f"Silêncios removidos: {original_duration:.1f}s -> {new_duration:.1f}s "
                f"({time_saved_ms/1000:.1f}s economizados)"
            )

            return SilenceRemovalResult(
                path=str(output_path),
                original_duration_ms=original_duration_ms,
                new_duration_ms=new_duration_ms,
                silences_removed=len(silences),
                time_saved_ms=time_saved_ms
            )

        except subprocess.CalledProcessError as e:
            logger.error(f"Silence removal failed: {e.stderr}")
            self._log(f"Falha ao remover silêncios, usando áudio original")
            return SilenceRemovalResult(
                path=audio_path,
                original_duration_ms=original_duration_ms,
                new_duration_ms=original_duration_ms,
                silences_removed=0,
                time_saved_ms=0
            )

    def _calculate_segments(
        self,
        silences: List[SilenceInfo],
        total_duration: float,
        keep_silence: float
    ) -> List[Tuple[float, float]]:
        """
        Calcula os segmentos de áudio para manter (não-silêncio).

        Args:
            silences: Lista de silêncios detectados
            total_duration: Duração total do áudio
            keep_silence: Quantidade de silêncio para manter nas bordas (segundos)

        Returns:
            Lista de tuplas (start, end) dos segmentos a manter
        """
        if not silences:
            return [(0, total_duration)]

        segments = []
        current_pos = 0

        for silence in silences:
            # Segmento antes do silêncio (incluindo um pouco do início do silêncio)
            segment_end = min(silence.start + keep_silence, silence.end)

            if segment_end > current_pos:
                segments.append((current_pos, segment_end))

            # Próximo segmento começa um pouco antes do fim do silêncio
            current_pos = max(silence.end - keep_silence, silence.start)

        # Segmento final após o último silêncio
        if current_pos < total_duration:
            segments.append((current_pos, total_duration))

        # Filtrar segmentos muito pequenos (< 50ms)
        segments = [(s, e) for s, e in segments if e - s > 0.05]

        return segments

    def remove_silences_simple(
        self,
        audio_path: str,
        output_filename: str = "audio_no_silence.mp3",
        silence_threshold_db: float = -40,
        min_silence_duration: float = 0.3
    ) -> SilenceRemovalResult:
        """
        Remove silêncios usando o filtro silenceremove do ffmpeg (método mais simples).

        Este método é mais rápido mas pode ser menos preciso.

        Args:
            audio_path: Caminho para o arquivo de áudio
            output_filename: Nome do arquivo de saída
            silence_threshold_db: Threshold em dB para considerar silêncio
            min_silence_duration: Duração mínima para considerar silêncio

        Returns:
            SilenceRemovalResult com informações sobre a remoção
        """
        original_duration = self.get_audio_duration(audio_path)
        original_duration_ms = int(original_duration * 1000)

        self._log(f"Removendo silêncios do áudio ({original_duration:.1f}s)...")

        output_path = self.output_dir / output_filename

        # silenceremove filter:
        # stop_periods=-1: remove todos os silêncios
        # stop_duration: duração mínima para considerar silêncio
        # stop_threshold: threshold de amplitude
        cmd = [
            "ffmpeg", "-y",
            "-i", audio_path,
            "-af", f"silenceremove=stop_periods=-1:stop_duration={min_silence_duration}:stop_threshold={silence_threshold_db}dB",
            "-c:a", "libmp3lame",
            "-q:a", "2",
            str(output_path)
        ]

        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True
            )

            new_duration = self.get_audio_duration(str(output_path))
            new_duration_ms = int(new_duration * 1000)
            time_saved_ms = original_duration_ms - new_duration_ms

            self._log(
                f"Silêncios removidos: {original_duration:.1f}s -> {new_duration:.1f}s "
                f"({time_saved_ms/1000:.1f}s economizados)"
            )

            return SilenceRemovalResult(
                path=str(output_path),
                original_duration_ms=original_duration_ms,
                new_duration_ms=new_duration_ms,
                silences_removed=-1,  # Não sabemos quantos exatamente
                time_saved_ms=time_saved_ms
            )

        except subprocess.CalledProcessError as e:
            logger.error(f"Silence removal failed: {e.stderr}")
            self._log(f"Falha ao remover silêncios, usando áudio original")
            return SilenceRemovalResult(
                path=audio_path,
                original_duration_ms=original_duration_ms,
                new_duration_ms=original_duration_ms,
                silences_removed=0,
                time_saved_ms=0
            )
