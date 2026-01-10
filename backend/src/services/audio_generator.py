"""
Serviço de geração de áudio usando ElevenLabs e Minimax (via WaveSpeed).
"""

import httpx
import asyncio
from pathlib import Path
from typing import Optional, Callable, List, Protocol
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log
import logging

from ..models.video import TextChunk, AudioChunk

logger = logging.getLogger(__name__)


class AudioGenerator(Protocol):
    """Interface para geradores de áudio."""

    async def generate_all(
        self,
        chunks: List[TextChunk],
        max_concurrent: int = 3,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[AudioChunk]:
        """Gera áudio para todos os chunks."""
        ...

    async def test_connection(self) -> dict:
        """Testa conexão com a API."""
        ...

    async def close(self):
        """Fecha o cliente HTTP."""
        ...


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


class MinimaxAudioGenerator:
    """
    Gera áudio usando a API Minimax via WaveSpeed.

    Features:
    - Processamento paralelo com controle de concorrência
    - Retry automático com exponential backoff
    - Suporte a múltiplas vozes e emoções
    - Controle de velocidade, pitch e volume
    - Tratamento de erros detalhado
    """

    BASE_URL = "https://api.wavespeed.ai/api/v3"

    # Erros HTTP que valem retry
    RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}

    # Vozes disponíveis no Minimax
    AVAILABLE_VOICES = [
        {"voice_id": "Energetic_Girl", "name": "Energetic Girl", "gender": "female", "language": "en"},
        {"voice_id": "Calm_Woman", "name": "Calm Woman", "gender": "female", "language": "en"},
        {"voice_id": "Friendly_Person", "name": "Friendly Person", "gender": "neutral", "language": "en"},
        {"voice_id": "Inspirational_girl", "name": "Inspirational Girl", "gender": "female", "language": "en"},
        {"voice_id": "Deep_Voice_Man", "name": "Deep Voice Man", "gender": "male", "language": "en"},
        {"voice_id": "Calm_Man", "name": "Calm Man", "gender": "male", "language": "en"},
        {"voice_id": "Narrator_Man", "name": "Narrator Man", "gender": "male", "language": "en"},
        {"voice_id": "Newsman", "name": "Newsman", "gender": "male", "language": "en"},
        {"voice_id": "Wise_Woman", "name": "Wise Woman", "gender": "female", "language": "en"},
        {"voice_id": "Gentle_Woman", "name": "Gentle Woman", "gender": "female", "language": "en"},
        {"voice_id": "Lively_Girl", "name": "Lively Girl", "gender": "female", "language": "en"},
        {"voice_id": "patient_Man", "name": "Patient Man", "gender": "male", "language": "en"},
        {"voice_id": "Young_Knight", "name": "Young Knight", "gender": "male", "language": "en"},
        {"voice_id": "Determined_Man", "name": "Determined Man", "gender": "male", "language": "en"},
        {"voice_id": "Lovely_Girl", "name": "Lovely Girl", "gender": "female", "language": "en"},
        {"voice_id": "Decent_Boy", "name": "Decent Boy", "gender": "male", "language": "en"},
        {"voice_id": "Imposing_Manner", "name": "Imposing Manner", "gender": "male", "language": "en"},
        {"voice_id": "Elegant_Man", "name": "Elegant Man", "gender": "male", "language": "en"},
        {"voice_id": "Abbess", "name": "Abbess", "gender": "female", "language": "en"},
        {"voice_id": "Sweet_Girl_2", "name": "Sweet Girl 2", "gender": "female", "language": "en"},
        {"voice_id": "Exuberant_Girl", "name": "Exuberant Girl", "gender": "female", "language": "en"},
    ]

    # Emoções disponíveis
    AVAILABLE_EMOTIONS = ["neutral", "happy", "sad", "angry", "fearful", "disgusted", "surprised"]

    def __init__(
        self,
        api_key: str,
        voice_id: str = "Narrator_Man",
        emotion: str = "neutral",
        speed: float = 1.0,
        pitch: int = 0,
        volume: float = 1.0,
        output_dir: str = "temp"
    ):
        self.api_key = api_key
        self.voice_id = voice_id
        self.emotion = emotion
        self.speed = speed
        self.pitch = pitch
        self.volume = volume
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
                    error_msg = error_body.get("message", "") or \
                               error_body.get("error", "") or \
                               str(error_body)
                except Exception:
                    error_msg = e.response.text[:200] if e.response.text else str(e)

                logger.warning(
                    f"Minimax API error (attempt {attempt}/{max_attempts}) - "
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
                elif status_code == 402:
                    raise AudioGenerationError("Créditos insuficientes", chunk.index, status_code)
                elif status_code == 403:
                    raise AudioGenerationError("Sem permissão de acesso", chunk.index, status_code)
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
        """Gera áudio para um único chunk usando Minimax via WaveSpeed."""
        logger.debug(f"Generating audio for chunk {chunk.index} ({len(chunk.text)} chars) with Minimax")

        client = await self._get_client()

        # Submit task
        submit_response = await client.post(
            f"{self.BASE_URL}/minimax/speech-02-turbo",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "text": chunk.text,
                "voice_id": self.voice_id,
                "emotion": self.emotion,
                "speed": self.speed,
                "pitch": self.pitch,
                "volume": self.volume,
                "enable_sync_mode": False,
                "english_normalization": False
            }
        )
        submit_response.raise_for_status()

        response_data = submit_response.json()

        # Verificar se o modo síncrono retornou diretamente
        if response_data.get("status") == "completed" and response_data.get("data", {}).get("audio_url"):
            audio_url = response_data["data"]["audio_url"]
        else:
            # Obter request_id e fazer polling
            request_id = response_data.get("data", {}).get("id") or response_data.get("id")
            if not request_id:
                raise AudioGenerationError("Resposta da API não contém request_id", chunk.index)

            # Poll for result
            audio_url = await self._poll_for_result(request_id, chunk.index)

        # Download audio file
        audio_response = await client.get(audio_url)
        audio_response.raise_for_status()

        # Salvar áudio
        output_path = self.output_dir / f"audio_chunk_{chunk.index}.mp3"
        output_path.write_bytes(audio_response.content)

        # Calcular duração
        duration_ms = self._get_audio_duration(output_path)

        logger.info(f"Generated audio chunk {chunk.index}: {duration_ms}ms ({len(chunk.text)} chars)")

        return AudioChunk(
            index=chunk.index,
            path=str(output_path),
            duration_ms=duration_ms,
            text=chunk.text
        )

    async def _poll_for_result(
        self,
        request_id: str,
        chunk_index: int,
        max_attempts: int = 60,
        poll_interval: float = 2.0
    ) -> str:
        """Faz polling até o áudio estar pronto."""
        client = await self._get_client()

        for attempt in range(max_attempts):
            response = await client.get(
                f"{self.BASE_URL}/predictions/{request_id}/result",
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            response.raise_for_status()

            data = response.json()
            status = data.get("status", "")

            if status == "completed":
                audio_url = data.get("data", {}).get("audio_url") or \
                           data.get("outputs", {}).get("audio_url") or \
                           data.get("output", {}).get("audio_url")
                if audio_url:
                    return audio_url
                raise AudioGenerationError("Resposta não contém audio_url", chunk_index)

            elif status == "failed":
                error_msg = data.get("error", "Geração de áudio falhou")
                raise AudioGenerationError(error_msg, chunk_index)

            elif status in ("pending", "processing", "starting"):
                await asyncio.sleep(poll_interval)
            else:
                logger.warning(f"Status desconhecido: {status}")
                await asyncio.sleep(poll_interval)

        raise AudioGenerationError("Timeout aguardando geração de áudio", chunk_index)

    def _get_audio_duration(self, path: Path) -> int:
        """Retorna duração do áudio em ms usando ffprobe."""
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
            # Fallback: estimate based on file size
            file_size = path.stat().st_size
            return int((file_size / 16000) * 1000)

    async def get_available_voices(self) -> List[dict]:
        """Lista vozes disponíveis."""
        return self.AVAILABLE_VOICES

    async def get_remaining_credits(self) -> float:
        """Retorna créditos restantes (usa mesma API do WaveSpeed)."""
        client = await self._get_client()
        try:
            response = await client.get(
                f"{self.BASE_URL}/balance",
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data", {}).get("balance", 0.0)
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to get credits: HTTP {e.response.status_code}")
            return 0.0
        finally:
            await self.close()

    async def test_connection(self) -> dict:
        """Testa conexão com a API."""
        try:
            credits = await self.get_remaining_credits()
            return {
                "connected": True,
                "voices_count": len(self.AVAILABLE_VOICES),
                "remaining_credits": credits
            }
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}"
            try:
                error_body = e.response.json()
                error_msg = error_body.get("message", error_msg)
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


def get_audio_generator(
    config,
    output_dir: str = "temp",
    log_callback: Optional[Callable[[str], None]] = None
) -> AudioGenerator:
    """
    Factory function para obter o gerador de áudio configurado.

    Args:
        config: FullConfig com configurações do sistema
        output_dir: Diretório para salvar os arquivos de áudio
        log_callback: Callback para logs

    Returns:
        Instância de ElevenLabsGenerator ou MinimaxAudioGenerator
    """
    # Determinar qual provider usar
    audio_provider = getattr(config.api, 'audio_provider', 'elevenlabs')

    if audio_provider == "minimax":
        if log_callback:
            log_callback("Usando Minimax para geração de áudio")
        return MinimaxAudioGenerator(
            api_key=config.api.wavespeed.api_key,  # Usa mesma key do WaveSpeed
            voice_id=config.api.minimax.voice_id if hasattr(config.api, 'minimax') else "Narrator_Man",
            emotion=config.api.minimax.emotion if hasattr(config.api, 'minimax') else "neutral",
            speed=config.api.minimax.speed if hasattr(config.api, 'minimax') else 1.0,
            pitch=config.api.minimax.pitch if hasattr(config.api, 'minimax') else 0,
            volume=config.api.minimax.volume if hasattr(config.api, 'minimax') else 1.0,
            output_dir=output_dir
        )
    else:
        if log_callback:
            log_callback("Usando ElevenLabs para geração de áudio")
        return ElevenLabsGenerator(
            api_key=config.api.elevenlabs.api_key,
            voice_id=config.api.elevenlabs.voice_id,
            model_id=config.api.elevenlabs.model_id,
            output_dir=output_dir
        )
