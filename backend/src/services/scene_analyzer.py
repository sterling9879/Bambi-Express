"""
Serviço de análise de cenas usando Google Gemini.
"""

import json
import logging
import re
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

    # Schema JSON para a resposta do Gemini
    RESPONSE_SCHEMA = {
        "type": "object",
        "properties": {
            "style_guide": {"type": "string"},
            "scenes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "scene_index": {"type": "integer"},
                        "text": {"type": "string"},
                        "start_ms": {"type": "integer"},
                        "end_ms": {"type": "integer"},
                        "duration_ms": {"type": "integer"},
                        "image_prompt": {"type": "string"},
                        "mood": {"type": "string"},
                        "mood_intensity": {"type": "number"},
                        "is_mood_transition": {"type": "boolean"}
                    },
                    "required": ["scene_index", "text", "start_ms", "end_ms", "duration_ms", "image_prompt", "mood"]
                }
            },
            "music_cues": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "timestamp_ms": {"type": "integer"},
                        "mood": {"type": "string"},
                        "suggestion": {"type": "string"}
                    },
                    "required": ["timestamp_ms", "mood", "suggestion"]
                }
            }
        },
        "required": ["scenes"]
    }

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash", image_style: str = ""):
        genai.configure(api_key=api_key)
        # Configurar modelo com JSON mode para garantir resposta válida
        # Usando snake_case para SDK google-generativeai >= 0.8.0
        self.model = genai.GenerativeModel(
            model,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=self.RESPONSE_SCHEMA,
                temperature=0.7,
                max_output_tokens=65536,  # Máximo para evitar truncamento
            )
        )
        self.image_style = image_style
        self._model_name = model  # Salvar para uso em test_connection

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
            max_scene_duration,
            self.image_style
        )

        logger.info("Sending transcription to Gemini for scene analysis")

        response = await self.model.generate_content_async(prompt)

        logger.info("Parsing Gemini response")

        return self._parse_response(response.text)

    def _build_prompt(
        self,
        transcription_data: dict,
        min_duration: float,
        max_duration: float,
        image_style: str = ""
    ) -> str:
        """Constrói prompt para o Gemini."""

        style_instruction = ""
        if image_style:
            style_instruction = f"""
ESTILO VISUAL OBRIGATÓRIO:
Todos os prompts de imagem DEVEM incluir este estilo no final: "{image_style}"
"""

        return f"""Você é um diretor de arte criando um vídeo.

Receba esta transcrição com timestamps e divida em cenas visuais.
{style_instruction}
REGRAS OBRIGATÓRIAS:
1. Cada cena deve ter entre {min_duration} e {max_duration} segundos
2. NUNCA corte no meio de uma frase ou ideia
3. Use os timestamps das palavras para definir início/fim precisos
4. Ajuste os timestamps para coincidir com pausas naturais na fala
5. Gere um prompt de imagem cinematográfico para cada cena
6. Os prompts devem ser em INGLÊS, detalhados, descrevendo a cena visualmente
7. IMPORTANTE: Cada prompt DEVE terminar com o estilo visual definido acima
8. Mantenha consistência visual entre todas as cenas (mesmo estilo, paleta de cores, atmosfera)
9. Classifique o mood emocional de cada cena usando APENAS estes valores: alegre, animado, calmo, dramatico, inspirador, melancolico, raiva, romantico, sombrio, vibrante
10. Identifique pontos onde o mood muda significativamente para transição musical

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
            "mood": "dramatico",
            "mood_intensity": 0.8,
            "is_mood_transition": false
        }}
    ],
    "music_cues": [
        {{
            "timestamp_ms": 0,
            "mood": "dramatico",
            "suggestion": "música épica orquestral"
        }},
        {{
            "timestamp_ms": 15000,
            "mood": "calmo",
            "suggestion": "transição para piano suave"
        }}
    ]
}}"""

    def _fix_unescaped_quotes_in_strings(self, json_str: str) -> str:
        """
        Tenta corrigir aspas não escapadas dentro de strings JSON.
        Esta é uma operação complexa que processa caractere por caractere.
        """
        result = []
        i = 0
        in_string = False
        string_start = -1

        while i < len(json_str):
            char = json_str[i]

            if char == '\\' and i + 1 < len(json_str):
                # Caractere de escape - adiciona os dois caracteres
                result.append(char)
                result.append(json_str[i + 1])
                i += 2
                continue

            if char == '"':
                if not in_string:
                    # Início de uma string
                    in_string = True
                    string_start = i
                    result.append(char)
                else:
                    # Pode ser fim da string ou aspas não escapadas
                    # Verifica se o próximo caractere indica fim de string
                    next_chars = json_str[i+1:i+20].lstrip()
                    if next_chars and next_chars[0] in ':,}]\n':
                        # Provavelmente é o fim da string
                        in_string = False
                        result.append(char)
                    elif next_chars and next_chars[0] == '"':
                        # Próximo é outra aspas, provavelmente fim desta + início de outra
                        in_string = False
                        result.append(char)
                    else:
                        # Aspas no meio da string - escapar
                        result.append('\\')
                        result.append(char)
                i += 1
            else:
                result.append(char)
                i += 1

        return ''.join(result)

    def _repair_json(self, json_str: str) -> str:
        """Tenta reparar JSON malformado comum do Gemini."""
        repaired = json_str

        # Remove trailing commas before } or ]
        repaired = re.sub(r',(\s*[}\]])', r'\1', repaired)

        # Fix missing commas between objects/arrays
        repaired = re.sub(r'}\s*{', '},{', repaired)
        repaired = re.sub(r']\s*\[', '],[', repaired)

        # Fix missing quotes on keys (common LLM error)
        repaired = re.sub(r'(\{|\,)\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', repaired)

        # Remove any control characters except \n, \r, \t
        repaired = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', repaired)

        # Replace newlines inside strings with spaces (common issue)
        # This is a simplified approach - replace \n that are not after a comma or brace
        repaired = re.sub(r'(?<=[a-zA-Z,.])\n(?=[a-zA-Z])', ' ', repaired)

        return repaired

    def _extract_json_object(self, text: str) -> str:
        """Extrai o primeiro objeto JSON completo do texto."""
        # Encontrar o início do JSON
        start = text.find('{')
        if start == -1:
            return text

        # Contar chaves para encontrar o fim
        depth = 0
        in_string = False
        escape_next = False

        for i, char in enumerate(text[start:], start):
            if escape_next:
                escape_next = False
                continue
            if char == '\\':
                escape_next = True
                continue
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            if in_string:
                continue
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    return text[start:i+1]

        # Se não encontrou o fim, retorna do início até o final
        return text[start:]

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

        # Extrair apenas o objeto JSON
        cleaned = self._extract_json_object(cleaned)

        # Tentar fazer parse do JSON
        data = None
        parse_errors = []

        # Tentativa 1: JSON direto
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            parse_errors.append(f"Direct parse: {e}")

            # Tentativa 2: Reparar JSON básico
            try:
                repaired = self._repair_json(cleaned)
                data = json.loads(repaired)
                logger.info("JSON was repaired successfully (basic)")
            except json.JSONDecodeError as e2:
                parse_errors.append(f"After basic repair: {e2}")

                # Tentativa 3: Corrigir aspas não escapadas
                try:
                    quote_fixed = self._fix_unescaped_quotes_in_strings(cleaned)
                    quote_fixed = self._repair_json(quote_fixed)
                    data = json.loads(quote_fixed)
                    logger.info("JSON was repaired successfully (quote fix)")
                except json.JSONDecodeError as e3:
                    parse_errors.append(f"After quote fix: {e3}")

                    # Tentativa 4: Truncar até último } válido
                    try:
                        last_brace = cleaned.rfind('}')
                        if last_brace > 0:
                            truncated = cleaned[:last_brace+1]
                            truncated = self._repair_json(truncated)
                            data = json.loads(truncated)
                            logger.warning("JSON was truncated and repaired")
                    except json.JSONDecodeError as e4:
                        parse_errors.append(f"After truncation: {e4}")

        if data is None:
            logger.error(f"All JSON parse attempts failed: {parse_errors}")
            logger.error(f"Response text (first 1000 chars): {response_text[:1000]}")
            logger.error(f"Response text (last 500 chars): {response_text[-500:]}")
            raise ValueError(f"Invalid JSON response from Gemini. Errors: {parse_errors}")

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
            # Usar modelo sem JSON mode para teste simples
            test_model = genai.GenerativeModel(self._model_name)
            response = await test_model.generate_content_async(
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
