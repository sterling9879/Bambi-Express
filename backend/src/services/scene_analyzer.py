"""
Serviço de análise de cenas usando Google Gemini.
"""

import json
import logging
from typing import Optional

import google.generativeai as genai

from ..models.video import Scene, MusicCue, SceneAnalysis, TranscriptionResult

logger = logging.getLogger(__name__)


class SceneAnalyzer:
    """
    Analisa transcrição e divide em cenas visuais.

    Features:
    - Divisão semântica em cenas de 3-6 segundos
    - Geração de prompts de imagem cinematográficos
    - Classificação de mood emocional
    - Identificação de transições musicais
    """

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)

    async def analyze(
        self,
        transcription: TranscriptionResult,
        min_scene_duration: float = 3.0,
        max_scene_duration: float = 6.0
    ) -> SceneAnalysis:
        """
        Analisa transcrição e gera cenas.

        Args:
            transcription: TranscriptionResult da AssemblyAI
            min_scene_duration: Duração mínima de cada cena (segundos)
            max_scene_duration: Duração máxima de cada cena (segundos)

        Returns:
            SceneAnalysis com cenas, prompts e music cues
        """
        # Preparar dados da transcrição
        transcription_data = {
            "segments": [
                {
                    "text": seg.text,
                    "start_ms": seg.start_ms,
                    "end_ms": seg.end_ms,
                    "words": [
                        {"text": w.text, "start_ms": w.start_ms, "end_ms": w.end_ms}
                        for w in seg.words
                    ]
                }
                for seg in transcription.segments
            ],
            "full_text": transcription.full_text,
            "duration_ms": transcription.duration_ms
        }

        prompt = self._build_prompt(
            transcription_data,
            min_scene_duration,
            max_scene_duration
        )

        logger.info("Sending transcription to Gemini for scene analysis")

        response = await self.model.generate_content_async(prompt)

        logger.info("Parsing Gemini response")

        return self._parse_response(response.text)

    def _build_prompt(
        self,
        transcription_data: dict,
        min_duration: float,
        max_duration: float
    ) -> str:
        """Constrói prompt para o Gemini."""

        return f"""Você é um diretor de arte criando um vídeo.

Receba esta transcrição com timestamps e divida em cenas visuais.

REGRAS OBRIGATÓRIAS:
1. Cada cena deve ter entre {min_duration} e {max_duration} segundos
2. NUNCA corte no meio de uma frase ou ideia
3. Use os timestamps das palavras para definir início/fim precisos
4. Ajuste os timestamps para coincidir com pausas naturais na fala
5. Gere um prompt de imagem cinematográfico para cada cena
6. Os prompts devem ser em INGLÊS, detalhados, no estilo: "cinematic shot of..., dramatic lighting, 8k, hyperrealistic"
7. Mantenha consistência visual entre todas as cenas (mesmo estilo, paleta de cores, atmosfera)
8. Classifique o mood emocional de cada cena: upbeat, dramatic, calm, emotional, inspiring, dark, neutral, epic, suspense
9. Identifique pontos onde o mood muda significativamente para transição musical

TRANSCRIÇÃO COM TIMESTAMPS:
{json.dumps(transcription_data, ensure_ascii=False, indent=2)}

RETORNE APENAS JSON VÁLIDO (sem markdown, sem ```):
{{
    "style_guide": "descrição do estilo visual geral a manter consistência",
    "scenes": [
        {{
            "scene_index": 0,
            "text": "texto falado nesta cena",
            "start_ms": 0,
            "end_ms": 4500,
            "duration_ms": 4500,
            "image_prompt": "cinematic shot of..., detailed description, dramatic lighting, 8k",
            "mood": "dramatic",
            "mood_intensity": 0.8,
            "is_mood_transition": false
        }}
    ],
    "music_cues": [
        {{
            "timestamp_ms": 0,
            "mood": "dramatic",
            "suggestion": "música épica orquestral"
        }},
        {{
            "timestamp_ms": 15000,
            "mood": "calm",
            "suggestion": "transição para piano suave"
        }}
    ]
}}"""

    def _parse_response(self, response_text: str) -> SceneAnalysis:
        """Converte resposta do Gemini em SceneAnalysis."""

        # Limpar resposta (remover possíveis ```json```)
        cleaned = response_text.strip()
        if cleaned.startswith("```"):
            # Find the content between ``` markers
            lines = cleaned.split("\n")
            start_idx = 0
            end_idx = len(lines)

            for i, line in enumerate(lines):
                if line.startswith("```") and i == 0:
                    start_idx = 1
                elif line.startswith("```"):
                    end_idx = i
                    break

            cleaned = "\n".join(lines[start_idx:end_idx])

        # Remove any leading "json" if present
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]

        cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            logger.error(f"Response text: {response_text[:500]}")
            raise ValueError(f"Invalid JSON response from Gemini: {e}")

        scenes = [
            Scene(
                scene_index=s["scene_index"],
                text=s["text"],
                start_ms=s["start_ms"],
                end_ms=s["end_ms"],
                duration_ms=s["duration_ms"],
                image_prompt=s["image_prompt"],
                mood=s["mood"],
                mood_intensity=s.get("mood_intensity", 0.5),
                is_mood_transition=s.get("is_mood_transition", False)
            )
            for s in data["scenes"]
        ]

        music_cues = [
            MusicCue(
                timestamp_ms=m["timestamp_ms"],
                mood=m["mood"],
                suggestion=m["suggestion"]
            )
            for m in data.get("music_cues", [])
        ]

        return SceneAnalysis(
            style_guide=data.get("style_guide", ""),
            scenes=scenes,
            music_cues=music_cues
        )

    async def test_connection(self) -> dict:
        """Testa conexão com a API."""
        try:
            response = await self.model.generate_content_async(
                "Say 'OK' if you can hear me."
            )
            return {
                "connected": True,
                "response": response.text[:50]
            }
        except Exception as e:
            return {
                "connected": False,
                "error": str(e)
            }
