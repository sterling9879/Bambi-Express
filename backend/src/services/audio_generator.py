"""
Serviço de geração de áudio usando ElevenLabs.
"""

import httpx
import asyncio
from pathlib import Path
from typing import Optional, Callable, List
from tenacity import retry, stop_after_attempt, wait_exponential
import logging

from ..models.video import TextChunk, AudioChunk

logger = logging.getLogger(__name__)


class ElevenLabsGenerator:
    """
    Gera áudio usando a API do ElevenLabs.

    Features:
    - Processamento paralelo com controle de concorrência
    - Retry automático com exponential backoff
    - Suporte a múltiplas vozes e modelos
    """

    BASE_URL = "https://api.elevenlabs.io/v1"

    def __init__(
        self,
        api_key: str,
        voice_id: str,
        model_id: str = "eleven_multilingual_v2",
        output_dir: str = "temp"
    ):
        self.api_key = api_key
        self.voice_id = voice_id
        self.model_id = model_id
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def generate_all(
        self,
        chunks: List[TextChunk],
        max_concurrent: int = 3,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[AudioChunk]:
        """
        Gera áudio para todos os chunks em paralelo.

        Args:
            chunks: Lista de TextChunk do text_processor
            max_concurrent: Máximo de requisições simultâneas
            progress_callback: Callback (completed, total)

        Returns:
            Lista de AudioChunk com paths dos arquivos
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        completed = 0

        async def generate_with_semaphore(chunk: TextChunk) -> AudioChunk:
            nonlocal completed
            async with semaphore:
                result = await self._generate_chunk(chunk)
                completed += 1
                if progress_callback:
                    progress_callback(completed, len(chunks))
                return result

        tasks = [generate_with_semaphore(chunk) for chunk in chunks]
        results = await asyncio.gather(*tasks)

        # Ordenar por índice
        return sorted(results, key=lambda x: x.index)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60)
    )
    async def _generate_chunk(self, chunk: TextChunk) -> AudioChunk:
        """Gera áudio para um único chunk."""
        logger.info(f"Generating audio for chunk {chunk.index}")

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{self.BASE_URL}/text-to-speech/{self.voice_id}",
                headers={
                    "xi-api-key": self.api_key,
                    "Content-Type": "application/json"
                },
                json={
                    "text": chunk.text,
                    "model_id": self.model_id,
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75
                    }
                }
            )
            response.raise_for_status()

            # Salvar áudio
            output_path = self.output_dir / f"audio_chunk_{chunk.index}.mp3"
            output_path.write_bytes(response.content)

            # Calcular duração
            duration_ms = self._get_audio_duration(output_path)

            logger.info(f"Generated audio chunk {chunk.index}: {duration_ms}ms")

            return AudioChunk(
                index=chunk.index,
                path=str(output_path),
                duration_ms=duration_ms,
                text=chunk.text
            )

    def _get_audio_duration(self, path: Path) -> int:
        """Retorna duração do áudio em ms usando ffprobe (não carrega na RAM)."""
        import subprocess
        try:
            result = subprocess.run([
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(path)
            ], capture_output=True, text=True, check=True)
            duration_seconds = float(result.stdout.strip())
            return int(duration_seconds * 1000)
        except Exception as e:
            logger.warning(f"Could not get audio duration with ffprobe: {e}")
            # Fallback: estimate based on file size (rough approximation)
            # Assuming ~128kbps MP3, 16KB per second
            file_size = path.stat().st_size
            return int((file_size / 16000) * 1000)

    async def get_available_voices(self) -> List[dict]:
        """Lista vozes disponíveis na conta."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/voices",
                headers={"xi-api-key": self.api_key}
            )
            response.raise_for_status()
            return response.json()["voices"]

    async def get_remaining_credits(self) -> int:
        """Retorna créditos restantes."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/user/subscription",
                headers={"xi-api-key": self.api_key}
            )
            response.raise_for_status()
            data = response.json()
            return data.get("character_limit", 0) - data.get("character_count", 0)

    async def test_connection(self) -> dict:
        """Testa conexão com a API."""
        try:
            voices = await self.get_available_voices()
            credits = await self.get_remaining_credits()
            return {
                "connected": True,
                "voices_count": len(voices),
                "remaining_credits": credits
            }
        except Exception as e:
            return {
                "connected": False,
                "error": str(e)
            }
