"""
Serviço de transcrição usando AssemblyAI.
Retorna timestamps precisos palavra por palavra.
"""

import httpx
import asyncio
from typing import Optional, Callable, List
import logging

from ..models.video import Word, Segment, Paragraph, TranscriptionResult

logger = logging.getLogger(__name__)


class TranscriptionError(Exception):
    """Erro durante transcrição."""
    pass


class AssemblyAITranscriber:
    """
    Transcreve áudio usando AssemblyAI com timestamps palavra por palavra.

    Features:
    - Upload de áudio para AssemblyAI
    - Transcrição com timestamps precisos
    - Detecção automática de idioma (ou forçar português)
    - Pontuação automática
    - Segmentação por sentenças
    """

    BASE_URL = "https://api.assemblyai.com/v2"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "authorization": api_key,
            "content-type": "application/json"
        }

    async def transcribe(
        self,
        audio_path: str,
        language_code: str = "pt",
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> TranscriptionResult:
        """
        Transcreve um arquivo de áudio.

        Args:
            audio_path: Caminho do arquivo de áudio
            language_code: Código do idioma (pt, en, es, etc.) ou "auto"
            progress_callback: Callback para atualizar progresso (status, percentual)

        Returns:
            TranscriptionResult com timestamps palavra por palavra
        """
        async with httpx.AsyncClient(timeout=300) as client:
            # 1. Upload do áudio
            if progress_callback:
                progress_callback("uploading", 0.1)

            logger.info("Uploading audio to AssemblyAI")
            upload_url = await self._upload_audio(client, audio_path)

            # 2. Iniciar transcrição
            if progress_callback:
                progress_callback("queued", 0.2)

            logger.info("Starting transcription")
            transcript_id = await self._start_transcription(
                client,
                upload_url,
                language_code
            )

            # 3. Aguardar conclusão
            result = await self._poll_transcription(
                client,
                transcript_id,
                progress_callback
            )

            logger.info(f"Transcription completed: {len(result.words)} words")
            return result

    async def _upload_audio(
        self,
        client: httpx.AsyncClient,
        audio_path: str
    ) -> str:
        """Faz upload do áudio para AssemblyAI e retorna URL (streaming)."""
        import os

        file_size = os.path.getsize(audio_path)
        logger.info(f"Uploading audio file: {file_size / 1024 / 1024:.1f}MB")

        # Usar streaming para não carregar arquivo inteiro na RAM
        async def file_stream():
            chunk_size = 1024 * 1024  # 1MB chunks
            with open(audio_path, "rb") as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk

        response = await client.post(
            f"{self.BASE_URL}/upload",
            headers={
                "authorization": self.api_key,
                "content-type": "application/octet-stream",
                "transfer-encoding": "chunked"
            },
            content=file_stream()
        )
        response.raise_for_status()

        return response.json()["upload_url"]

    async def _start_transcription(
        self,
        client: httpx.AsyncClient,
        audio_url: str,
        language_code: str
    ) -> str:
        """Inicia job de transcrição e retorna ID."""

        payload = {
            "audio_url": audio_url,
            "punctuate": True,
            "format_text": True,
        }

        if language_code != "auto":
            payload["language_code"] = language_code
        else:
            payload["language_detection"] = True

        response = await client.post(
            f"{self.BASE_URL}/transcript",
            headers=self.headers,
            json=payload
        )
        response.raise_for_status()

        return response.json()["id"]

    async def _poll_transcription(
        self,
        client: httpx.AsyncClient,
        transcript_id: str,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> TranscriptionResult:
        """Aguarda conclusão da transcrição com polling."""

        url = f"{self.BASE_URL}/transcript/{transcript_id}"

        while True:
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()

            data = response.json()
            status = data["status"]

            logger.debug(f"Transcription status: {status}")

            if status == "completed":
                if progress_callback:
                    progress_callback("fetching_paragraphs", 0.9)

                # Buscar parágrafos do endpoint dedicado
                paragraphs = await self._fetch_paragraphs(client, transcript_id)

                if progress_callback:
                    progress_callback("completed", 1.0)
                return self._parse_result(data, paragraphs)

            elif status == "error":
                raise TranscriptionError(
                    f"Transcrição falhou: {data.get('error', 'Unknown error')}"
                )

            else:
                if progress_callback:
                    progress = 0.3 if status == "queued" else 0.6
                    progress_callback(status, progress)

                await asyncio.sleep(3)

    async def _fetch_paragraphs(
        self,
        client: httpx.AsyncClient,
        transcript_id: str
    ) -> List[Paragraph]:
        """Busca parágrafos do endpoint /paragraphs da AssemblyAI."""
        try:
            url = f"{self.BASE_URL}/transcript/{transcript_id}/paragraphs"
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()

            data = response.json()
            paragraphs = [
                Paragraph(
                    text=p["text"],
                    start_ms=p["start"],
                    end_ms=p["end"]
                )
                for p in data.get("paragraphs", [])
            ]

            logger.info(f"Fetched {len(paragraphs)} paragraphs from AssemblyAI")
            return paragraphs

        except Exception as e:
            logger.warning(f"Failed to fetch paragraphs: {e}. Will use fallback.")
            return []

    def _parse_result(
        self,
        data: dict,
        paragraphs: List[Paragraph] = None
    ) -> TranscriptionResult:
        """Converte resposta da API em TranscriptionResult."""

        words = [
            Word(
                text=w["text"],
                start_ms=w["start"],
                end_ms=w["end"],
                confidence=w["confidence"]
            )
            for w in data.get("words", [])
        ]

        segments = self._group_into_segments(words, data.get("text", ""))

        duration_ms = words[-1].end_ms if words else 0

        avg_confidence = (
            sum(w.confidence for w in words) / len(words)
            if words else 0
        )

        return TranscriptionResult(
            segments=segments,
            words=words,
            paragraphs=paragraphs or [],
            full_text=data.get("text", ""),
            duration_ms=duration_ms,
            confidence=avg_confidence,
            language=data.get("language_code", "pt")
        )

    def _group_into_segments(
        self,
        words: List[Word],
        full_text: str
    ) -> List[Segment]:
        """
        Agrupa palavras em segmentos baseado em pontuação.
        Cada segmento termina em . ! ? ou tem no máximo 15 palavras.
        """
        segments = []
        current_words = []

        sentence_endings = {'.', '!', '?'}

        for word in words:
            current_words.append(word)

            is_sentence_end = any(
                word.text.rstrip().endswith(p)
                for p in sentence_endings
            )

            if is_sentence_end or len(current_words) >= 15:
                segment = Segment(
                    text=" ".join(w.text for w in current_words),
                    start_ms=current_words[0].start_ms,
                    end_ms=current_words[-1].end_ms,
                    words=current_words.copy()
                )
                segments.append(segment)
                current_words = []

        if current_words:
            segment = Segment(
                text=" ".join(w.text for w in current_words),
                start_ms=current_words[0].start_ms,
                end_ms=current_words[-1].end_ms,
                words=current_words.copy()
            )
            segments.append(segment)

        return segments

    async def test_connection(self) -> dict:
        """Testa conexão com a API."""
        try:
            async with httpx.AsyncClient() as client:
                # AssemblyAI doesn't have a simple health endpoint,
                # so we'll just verify the API key format
                response = await client.get(
                    f"{self.BASE_URL}/transcript",
                    headers=self.headers,
                    params={"limit": 1}
                )
                response.raise_for_status()
                return {"connected": True}
        except Exception as e:
            return {
                "connected": False,
                "error": str(e)
            }
