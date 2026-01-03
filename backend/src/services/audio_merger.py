"""
Serviço para concatenação de arquivos de áudio.
"""

import subprocess
from pathlib import Path
from typing import List
import logging

from ..models.video import AudioChunk, MergedAudio

logger = logging.getLogger(__name__)


class AudioMerger:
    """
    Concatena múltiplos arquivos de áudio usando FFMPEG.

    Features:
    - Concatenação sem reencoding (preserva qualidade)
    - Mantém ordem correta dos chunks
    """

    def __init__(self, output_dir: str = "temp"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def merge(
        self,
        audio_chunks: List[AudioChunk],
        output_filename: str = "audio_complete.mp3"
    ) -> MergedAudio:
        """
        Concatena todos os chunks de áudio.

        Args:
            audio_chunks: Lista de AudioChunk ordenados
            output_filename: Nome do arquivo de saída

        Returns:
            MergedAudio com path e duração total
        """
        # Ordenar por índice
        sorted_chunks = sorted(audio_chunks, key=lambda x: x.index)

        logger.info(f"Merging {len(sorted_chunks)} audio chunks")

        # Criar arquivo de lista para ffmpeg
        list_path = self.output_dir / "concat_list.txt"
        with open(list_path, "w") as f:
            for chunk in sorted_chunks:
                # Usar caminho absoluto para evitar problemas
                abs_path = Path(chunk.path).absolute()
                f.write(f"file '{abs_path}'\n")

        output_path = self.output_dir / output_filename

        # Executar ffmpeg
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_path),
            "-c", "copy",
            str(output_path)
        ]

        logger.debug(f"Running command: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True
            )
            logger.debug(f"FFMPEG output: {result.stderr}")
        except subprocess.CalledProcessError as e:
            logger.error(f"FFMPEG error: {e.stderr}")
            raise RuntimeError(f"Failed to merge audio: {e.stderr}")

        # Calcular duração total
        total_duration = sum(chunk.duration_ms for chunk in sorted_chunks)

        # Limpar arquivo de lista
        try:
            list_path.unlink()
        except Exception:
            pass

        logger.info(f"Audio merged successfully: {output_path} ({total_duration}ms)")

        return MergedAudio(
            path=str(output_path),
            duration_ms=total_duration,
            chunk_count=len(sorted_chunks)
        )

    def cleanup_chunks(self, audio_chunks: List[AudioChunk]) -> None:
        """Remove arquivos de chunks após merge."""
        for chunk in audio_chunks:
            try:
                Path(chunk.path).unlink()
                logger.debug(f"Cleaned up chunk: {chunk.path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup chunk {chunk.path}: {e}")
