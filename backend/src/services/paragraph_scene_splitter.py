"""
Serviço para dividir transcrição em cenas.

Modos disponíveis:
1. PARAGRAPHS - Usa parágrafos da AssemblyAI (menos cenas, mais longas)
2. SENTENCES - Divide por pontuação/sentenças (mais cenas, mais curtas)
3. GEMINI - Deixa o Gemini decidir (pode alucinar)

Todos usam timestamps exatos da transcrição para sincronização perfeita.
"""

import logging
from typing import List, Optional, Callable
from dataclasses import dataclass

from ..models.video import Scene, TranscriptionResult, Word, Paragraph as APIParagraph

logger = logging.getLogger(__name__)


@dataclass
class TextSegment:
    """Um segmento de texto (parágrafo ou sentença)."""
    text: str
    start_ms: int
    end_ms: int


class SceneSplitter:
    """
    Divide transcrição em cenas.

    Suporta dois modos:
    - Parágrafos: Usa parágrafos da AssemblyAI (menos cenas)
    - Sentenças: Divide por pontuação (mais cenas)
    """

    def __init__(
        self,
        paragraphs_per_scene: int = 3,
        sentences_per_scene: int = 2,
        log_callback: Optional[Callable[[str], None]] = None
    ):
        self.paragraphs_per_scene = paragraphs_per_scene
        self.sentences_per_scene = sentences_per_scene
        self.log_callback = log_callback

    def _log(self, message: str):
        """Log message to both logger and callback if set."""
        logger.info(message)
        if self.log_callback:
            self.log_callback(message)

    def _split_into_sentences(self, words: List[Word]) -> List[TextSegment]:
        """
        Divide palavras em sentenças baseado em pontuação final.
        Uma sentença termina quando uma palavra termina com . ! ? ou ...
        """
        if not words:
            return []

        sentences = []
        current_words = []

        for word in words:
            current_words.append(word)

            # Verificar se é fim de sentença
            text = word.text.strip()
            if text.endswith(('.', '!', '?', '...', '。', '！', '？')):
                if current_words:
                    sentence = TextSegment(
                        text=" ".join(w.text for w in current_words),
                        start_ms=current_words[0].start_ms,
                        end_ms=current_words[-1].end_ms
                    )
                    sentences.append(sentence)
                    current_words = []

        # Adicionar palavras restantes como última sentença
        if current_words:
            sentence = TextSegment(
                text=" ".join(w.text for w in current_words),
                start_ms=current_words[0].start_ms,
                end_ms=current_words[-1].end_ms
            )
            sentences.append(sentence)

        return sentences

    def _get_paragraphs(self, transcription: TranscriptionResult) -> List[TextSegment]:
        """
        Obtém parágrafos da AssemblyAI ou faz fallback para sentenças.
        """
        if transcription.paragraphs:
            paragraphs = [
                TextSegment(
                    text=p.text,
                    start_ms=p.start_ms,
                    end_ms=p.end_ms
                )
                for p in transcription.paragraphs
            ]
            self._log(f"Usando {len(paragraphs)} parágrafos da AssemblyAI")
            return paragraphs
        else:
            # Fallback: usar sentenças como parágrafos
            sentences = self._split_into_sentences(transcription.words)
            self._log(f"Fallback: {len(sentences)} sentenças (sem parágrafos da API)")
            return sentences

    def _group_into_scenes(
        self,
        segments: List[TextSegment],
        segments_per_scene: int,
        segment_type: str
    ) -> List[Scene]:
        """
        Agrupa segmentos (parágrafos ou sentenças) em cenas.
        """
        if not segments:
            self._log("AVISO: Nenhum segmento encontrado!")
            return []

        scenes = []
        scene_index = 0

        for i in range(0, len(segments), segments_per_scene):
            scene_segments = segments[i:i + segments_per_scene]

            if not scene_segments:
                continue

            start_ms = scene_segments[0].start_ms
            end_ms = scene_segments[-1].end_ms
            duration_ms = end_ms - start_ms

            scene_text = " ".join(s.text for s in scene_segments)

            scene = Scene(
                scene_index=scene_index,
                text=scene_text,
                start_ms=start_ms,
                end_ms=end_ms,
                duration_ms=duration_ms,
                image_prompt="",
                mood="neutro",
                mood_intensity=0.5,
                is_mood_transition=False
            )
            scenes.append(scene)
            scene_index += 1

        self._log(f"Criadas {len(scenes)} cenas ({segments_per_scene} {segment_type} por cena)")
        return scenes

    def split_by_paragraphs(self, transcription: TranscriptionResult) -> List[Scene]:
        """
        Divide em cenas usando parágrafos da AssemblyAI.
        Resulta em menos cenas, mais longas.
        """
        paragraphs = self._get_paragraphs(transcription)
        scenes = self._group_into_scenes(
            paragraphs,
            self.paragraphs_per_scene,
            "parágrafos"
        )
        self._log_sync_info(scenes, transcription)
        return scenes

    def split_by_sentences(self, transcription: TranscriptionResult) -> List[Scene]:
        """
        Divide em cenas usando sentenças (pontuação).
        Resulta em mais cenas, mais curtas.
        """
        sentences = self._split_into_sentences(transcription.words)
        self._log(f"Dividindo {len(sentences)} sentenças em cenas")

        scenes = self._group_into_scenes(
            sentences,
            self.sentences_per_scene,
            "sentenças"
        )
        self._log_sync_info(scenes, transcription)
        return scenes

    def _log_sync_info(self, scenes: List[Scene], transcription: TranscriptionResult):
        """Log de diagnóstico de sincronização."""
        if scenes:
            total_duration = sum(s.duration_ms for s in scenes)
            self._log(f"[SYNC] Duração total das cenas: {total_duration}ms")
            self._log(f"[SYNC] Duração do áudio: {transcription.duration_ms}ms")
            self._log(f"[SYNC] Primeira cena começa em: {scenes[0].start_ms}ms")
            self._log(f"[SYNC] Última cena termina em: {scenes[-1].end_ms}ms")


# Alias para compatibilidade
ParagraphSceneSplitter = SceneSplitter
