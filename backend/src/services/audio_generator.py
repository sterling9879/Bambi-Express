"""
Serviço de geração de áudio usando ElevenLabs.
"""

import httpx
import asyncio
from pathlib import Path
from typing import Optional, Callable, List
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log
import logging

from ..models.video import TextChunk, AudioChunk

logger = logging.getLogger(__name__)


class AudioGenerationError(Exception):
    """Erro durante geração de áudio com detalhes."""
    def __init__(self, message: str, chunk_index: int = -1, status_code: int = 0):
        self.message = message
        self.chunk_index = chunk_index
        self.status_code = status_code
        super().__init__(f"Chunk {chunk_index}: {message} (HTTP {status_code})" if status_code else f"Chunk {chunk_index}: {message}")


class ElevenLabsGenerator:
    """
    Gera áudio usando a API do ElevenLabs.

    Features:
    - Processamento paralelo com controle de concorrência
    - Retry automático com exponential backoff
    - Suporte a múltiplas vozes e modelos
    - Tratamento de erros detalhado
    """

    BASE_URL = "https://api.elevenlabs.io/v1"

    # Erros HTTP que valem retry
    RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}

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
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Retorna cliente HTTP reutilizável."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(connect=30, read=120, write=30, pool=60),
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            )
        return self._client

    async def close(self):
        """Fecha o cliente HTTP."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

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
        errors = []

        async def generate_with_semaphore(chunk: TextChunk) -> Optional[AudioChunk]:
            nonlocal completed
            async with semaphore:
                try:
                    result = await self._generate_chunk_with_retry(chunk)
                    completed += 1
                    if progress_callback:
                        progress_callback(completed, len(chunks))
                    return result
                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"Failed to generate audio for chunk {chunk.index}: {error_msg}")
                    errors.append((chunk.index, error_msg))
                    completed += 1
                    if progress_callback:
                        progress_callback(completed, len(chunks))
                    return None

        try:
            tasks = [generate_with_semaphore(chunk) for chunk in chunks]
            results = await asyncio.gather(*tasks)

            # Filtrar None (falhas)
            valid_results = [r for r in results if r is not None]

            if errors:
                error_details = "; ".join([f"Chunk {idx}: {msg}" for idx, msg in errors[:3]])
                if len(errors) > 3:
                    error_details += f" ... e mais {len(errors) - 3} erros"

                if len(valid_results) == 0:
                    raise AudioGenerationError(f"Falha ao gerar todos os áudios: {error_details}")
                else:
                    logger.warning(f"Gerado {len(valid_results)}/{len(chunks)} chunks. Erros: {error_details}")

            # Ordenar por índice
            return sorted(valid_results, key=lambda x: x.index)

        finally:
            await self.close()

    async def _generate_chunk_with_retry(self, chunk: TextChunk, max_attempts: int = 3) -> AudioChunk:
        """Gera áudio com retry manual para melhor controle de erros."""
        last_error = None

        for attempt in range(1, max_attempts + 1):
            try:
                return await self._generate_chunk(chunk)
            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code

                # Extrair mensagem de erro da resposta
                try:
                    error_body = e.response.json()
                    error_msg = error_body.get("detail", {}).get("message", "") or \
                               error_body.get("message", "") or \
                               error_body.get("error", "") or \
                               str(error_body)
                except Exception:
                    error_msg = e.response.text[:200] if e.response.text else str(e)

                logger.warning(
                    f"ElevenLabs API error (attempt {attempt}/{max_attempts}) - "
                    f"Chunk {chunk.index}, HTTP {status_code}: {error_msg}"
                )

                # Verificar se vale tentar novamente
                if status_code in self.RETRYABLE_STATUS_CODES and attempt < max_attempts:
                    wait_time = min(4 * (2 ** (attempt - 1)), 60)  # 4s, 8s, 16s... max 60s
                    logger.info(f"Aguardando {wait_time}s antes de tentar novamente...")
                    await asyncio.sleep(wait_time)
                    last_error = AudioGenerationError(error_msg, chunk.index, status_code)
                    continue

                # Erro não recuperável ou último attempt
                if status_code == 401:
                    raise AudioGenerationError("API key inválida ou expirada", chunk.index, status_code)
                elif status_code == 403:
                    raise AudioGenerationError("Sem permissão ou créditos esgotados", chunk.index, status_code)
                elif status_code == 422:
                    raise AudioGenerationError(f"Texto inválido: {error_msg}", chunk.index, status_code)
                elif status_code == 429:
                    raise AudioGenerationError("Rate limit excedido, aguarde alguns minutos", chunk.index, status_code)
                else:
                    raise AudioGenerationError(error_msg or f"HTTP {status_code}", chunk.index, status_code)

            except httpx.TimeoutException as e:
                logger.warning(f"Timeout (attempt {attempt}/{max_attempts}) - Chunk {chunk.index}")
                if attempt < max_attempts:
                    await asyncio.sleep(5)
                    last_error = AudioGenerationError("Timeout na requisição", chunk.index)
                    continue
                raise AudioGenerationError("Timeout após várias tentativas", chunk.index)

            except httpx.RequestError as e:
                logger.warning(f"Request error (attempt {attempt}/{max_attempts}) - Chunk {chunk.index}: {e}")
                if attempt < max_attempts:
                    await asyncio.sleep(5)
                    last_error = AudioGenerationError(str(e), chunk.index)
                    continue
                raise AudioGenerationError(f"Erro de conexão: {str(e)}", chunk.index)

        # Se chegou aqui, todas as tentativas falharam
        if last_error:
            raise last_error
        raise AudioGenerationError("Falha após todas as tentativas", chunk.index)

    async def _generate_chunk(self, chunk: TextChunk) -> AudioChunk:
        """Gera áudio para um único chunk."""
        logger.debug(f"Generating audio for chunk {chunk.index} ({len(chunk.text)} chars)")

        client = await self._get_client()

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

        logger.info(f"Generated audio chunk {chunk.index}: {duration_ms}ms ({len(chunk.text)} chars)")

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
            ], capture_output=True, text=True, check=True, timeout=30)
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
        client = await self._get_client()
        try:
            response = await client.get(
                f"{self.BASE_URL}/voices",
                headers={"xi-api-key": self.api_key}
            )
            response.raise_for_status()
            return response.json()["voices"]
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get voices: HTTP {e.response.status_code}")
            raise

    async def get_remaining_credits(self) -> int:
        """Retorna créditos restantes."""
        client = await self._get_client()
        try:
            response = await client.get(
                f"{self.BASE_URL}/user/subscription",
                headers={"xi-api-key": self.api_key}
            )
            response.raise_for_status()
            data = response.json()
            return data.get("character_limit", 0) - data.get("character_count", 0)
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get credits: HTTP {e.response.status_code}")
            return 0

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
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}"
            try:
                error_body = e.response.json()
                error_msg = error_body.get("detail", {}).get("message", error_msg)
            except Exception:
                pass
            return {
                "connected": False,
                "error": error_msg
            }
        except Exception as e:
            return {
                "connected": False,
                "error": str(e)
            }
        finally:
            await self.close()
