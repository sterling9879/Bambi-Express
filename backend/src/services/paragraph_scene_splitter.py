"""
Serviço para dividir transcrição em cenas baseado em parágrafos.

Ao invés de deixar o Gemini decidir as divisões (que pode alucinar),
este serviço:
1. Agrupa palavras em parágrafos (sentenças terminando em .!?)
2. Agrupa parágrafos em cenas baseado na configuração do usuário
3. Usa timestamps exatos da transcrição (sem alucinação)
"""

import logging
from typing import List, Optional, Callable
from dataclasses import dataclass

from ..models.video import Scene, TranscriptionResult, Word

logger = logging.getLogger(__name__)


@dataclass
class Paragraph:
    """Um parágrafo (sentença) da transcrição."""
    text: str
    start_ms: int
    end_ms: int
    words: List[Word]


class ParagraphSceneSplitter:
    """
    Divide transcrição em cenas baseado em parágrafos.

    Fluxo:
    1. Recebe palavras com timestamps da AssemblyAI
    2. Agrupa em parágrafos (por pontuação: . ! ?)
    3. Agrupa parágrafos em cenas (baseado em paragraphs_per_scene)
    4. Retorna cenas com timestamps exatos
    """

    def __init__(
        self,
        paragraphs_per_scene: int = 3,
        log_callback: Optional[Callable[[str], None]] = None
    ):
        self.paragraphs_per_scene = paragraphs_per_scene
        self.log_callback = log_callback

    def _log(self, message: str):
        """Log message to both logger and callback if set."""
        logger.info(message)
        if self.log_callback:
            self.log_callback(message)

    def split_into_paragraphs(self, words: List[Word]) -> List[Paragraph]:
        """
        Agrupa palavras em parágrafos baseado em pontuação final.

        Uma sentença termina quando uma palavra termina com . ! ? ou ...
        """
        if not words:
            return []

        paragraphs = []
        current_words = []

        for word in words:
            current_words.append(word)

            # Verificar se é fim de sentença
            text = word.text.strip()
            if text.endswith(('.', '!', '?', '...', '。', '！', '？')):
                if current_words:
                    paragraph = Paragraph(
                        text=" ".join(w.text for w in current_words),
                        start_ms=current_words[0].start_ms,
                        end_ms=current_words[-1].end_ms,
                        words=current_words.copy()
                    )
                    paragraphs.append(paragraph)
                    current_words = []

        # Adicionar palavras restantes como último parágrafo
        if current_words:
            paragraph = Paragraph(
                text=" ".join(w.text for w in current_words),
                start_ms=current_words[0].start_ms,
                end_ms=current_words[-1].end_ms,
                words=current_words.copy()
            )
            paragraphs.append(paragraph)

        return paragraphs

    def split_into_scenes(
        self,
        transcription: TranscriptionResult
    ) -> List[Scene]:
        """
        Divide transcrição em cenas baseado em parágrafos.

        Args:
            transcription: Resultado da transcrição com palavras e timestamps

        Returns:
            Lista de cenas com timestamps exatos
        """
        # 1. Agrupar palavras em parágrafos
        paragraphs = self.split_into_paragraphs(transcription.words)

        self._log(f"Transcrição dividida em {len(paragraphs)} parágrafos")

        if not paragraphs:
            self._log("AVISO: Nenhum parágrafo encontrado!")
            return []

        # 2. Agrupar parágrafos em cenas
        scenes = []
        scene_index = 0

        for i in range(0, len(paragraphs), self.paragraphs_per_scene):
            # Pegar os próximos N parágrafos
            scene_paragraphs = paragraphs[i:i + self.paragraphs_per_scene]

            if not scene_paragraphs:
                continue

            # Calcular timestamps da cena
            start_ms = scene_paragraphs[0].start_ms
            end_ms = scene_paragraphs[-1].end_ms
            duration_ms = end_ms - start_ms

            # Texto da cena
            scene_text = " ".join(p.text for p in scene_paragraphs)

            # Criar cena (sem image_prompt ainda - Gemini vai gerar depois)
            scene = Scene(
                scene_index=scene_index,
                text=scene_text,
                start_ms=start_ms,
                end_ms=end_ms,
                duration_ms=duration_ms,
                image_prompt="",  # Será preenchido pelo Gemini
                mood="neutro",
                mood_intensity=0.5,
                is_mood_transition=False
            )
            scenes.append(scene)
            scene_index += 1

        self._log(f"Criadas {len(scenes)} cenas ({self.paragraphs_per_scene} parágrafos por cena)")

        # Log de diagnóstico
        if scenes:
            total_duration = sum(s.duration_ms for s in scenes)
            self._log(f"[SYNC] Duração total das cenas: {total_duration}ms")
            self._log(f"[SYNC] Duração do áudio: {transcription.duration_ms}ms")
            self._log(f"[SYNC] Primeira cena começa em: {scenes[0].start_ms}ms")
            self._log(f"[SYNC] Última cena termina em: {scenes[-1].end_ms}ms")

        return scenes
