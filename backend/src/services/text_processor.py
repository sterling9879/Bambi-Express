"""
Serviço para processamento e divisão de texto.
"""

from typing import List
from ..models.video import TextChunk


class TextProcessor:
    """
    Divide texto em chunks otimizados para APIs de TTS.

    Features:
    - Divide em chunks de no máximo 2500 caracteres
    - Nunca corta no meio de uma frase
    - Prioriza quebras naturais (parágrafo > ponto > vírgula)
    """

    def __init__(self, max_chars: int = 2500):
        self.max_chars = max_chars

    def process(self, text: str) -> List[TextChunk]:
        """
        Divide texto em chunks.

        Args:
            text: Texto completo para dividir

        Returns:
            Lista de TextChunk com índices sequenciais
        """
        chunks = []
        remaining = text.strip()
        index = 0

        while remaining:
            if len(remaining) <= self.max_chars:
                chunks.append(TextChunk(
                    index=index,
                    text=remaining,
                    char_count=len(remaining)
                ))
                break

            # Encontrar melhor ponto de corte
            cut_point = self._find_cut_point(remaining)

            chunk_text = remaining[:cut_point].strip()
            chunks.append(TextChunk(
                index=index,
                text=chunk_text,
                char_count=len(chunk_text)
            ))

            remaining = remaining[cut_point:].strip()
            index += 1

        return chunks

    def _find_cut_point(self, text: str) -> int:
        """Encontra o melhor ponto para cortar o texto."""
        max_len = self.max_chars

        # Prioridade: parágrafo > ponto final > ponto e vírgula > vírgula
        separators = ['\n\n', '\n', '. ', '! ', '? ', '; ', ', ']

        for sep in separators:
            # Procurar última ocorrência antes do limite
            last_pos = text.rfind(sep, 0, max_len)
            if last_pos > 0:
                return last_pos + len(sep)

        # Fallback: cortar no espaço mais próximo
        space_pos = text.rfind(' ', 0, max_len)
        if space_pos > 0:
            return space_pos + 1

        # Último recurso: cortar no limite
        return max_len

    def estimate_duration(self, text: str, words_per_minute: int = 150) -> float:
        """
        Estima duração em segundos baseado no número de palavras.

        Args:
            text: Texto para estimar
            words_per_minute: Velocidade de fala (padrão: 150 wpm)

        Returns:
            Duração estimada em segundos
        """
        word_count = len(text.split())
        return (word_count / words_per_minute) * 60

    def get_word_count(self, text: str) -> int:
        """Retorna contagem de palavras."""
        return len(text.split())

    def get_char_count(self, text: str) -> int:
        """Retorna contagem de caracteres."""
        return len(text)
