"""
Serviço de análise de cenas usando Google Gemini.
O Gemini recebe a transcrição completa com timestamps e decide
autonomamente onde dividir as cenas.
"""

import json
import logging
import re
from typing import Optional, List

import google.generativeai as genai

from ..models.video import Scene, MusicCue, SceneAnalysis, TranscriptionResult

logger = logging.getLogger(__name__)


class SceneAnalyzer:
    """
    Analisa transcrição e divide em cenas visuais.

    O Gemini recebe:
    - Lista de palavras com timestamps exatos (da AssemblyAI)
    - Texto completo
    - Duração total

    O Gemini decide:
    - Onde cada cena começa e termina (usando os timestamps das palavras)
    - O prompt de imagem para cada cena
    - O mood de cada cena
    - Onde a música deve mudar
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
                        "image_prompt": {"type": "string"},
                        "mood": {"type": "string"}
                    },
                    "required": ["scene_index", "text", "start_ms", "end_ms", "image_prompt", "mood"]
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

    # Máximo de palavras por chunk (para transcrições muito longas)
    MAX_WORDS_PER_CHUNK = 500

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.0-flash",
        image_style: str = "",
        log_callback: Optional[callable] = None
    ):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=self.RESPONSE_SCHEMA,
                temperature=0.7,
                max_output_tokens=65536,
            )
        )
        self.image_style = image_style
        self._model_name = model
        self.log_callback = log_callback

    def _log(self, message: str):
        """Log message to both logger and callback if set."""
        logger.info(message)
        if self.log_callback:
            self.log_callback(message)

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
            min_scene_duration: Duração mínima sugerida (segundos)
            max_scene_duration: Duração máxima sugerida (segundos)

        Returns:
            SceneAnalysis com cenas definidas pelo Gemini
        """
        # Preparar dados - enviar TODAS as palavras com timestamps
        words_data = [
            {
                "word": w.text,
                "start": w.start_ms,
                "end": w.end_ms
            }
            for w in transcription.words
        ]

        total_words = len(words_data)
        self._log(f"Processing {total_words} words for scene analysis")

        # Se transcrição é muito longa, dividir em chunks
        if total_words > self.MAX_WORDS_PER_CHUNK:
            return await self._analyze_in_chunks(
                words_data,
                transcription.full_text,
                transcription.duration_ms,
                min_scene_duration,
                max_scene_duration
            )

        # Transcrição curta - processar de uma vez
        prompt = self._build_prompt(
            words=words_data,
            full_text=transcription.full_text,
            total_duration_ms=transcription.duration_ms,
            min_duration=min_scene_duration,
            max_duration=max_scene_duration
        )

        self._log("Sending to Gemini for scene analysis...")
        response = await self.model.generate_content_async(prompt)
        result = self._parse_response(response.text)

        self._log(f"Generated {len(result.scenes)} scenes")
        return result

    async def _analyze_in_chunks(
        self,
        words_data: List[dict],
        full_text: str,
        total_duration_ms: int,
        min_scene_duration: float,
        max_scene_duration: float
    ) -> SceneAnalysis:
        """Processa transcrições longas em chunks."""

        # Dividir palavras em chunks
        chunks = []
        for i in range(0, len(words_data), self.MAX_WORDS_PER_CHUNK):
            chunk = words_data[i:i + self.MAX_WORDS_PER_CHUNK]
            chunks.append(chunk)

        self._log(f"Splitting into {len(chunks)} chunks for processing")

        all_scenes = []
        all_music_cues = []
        style_guide = ""

        for i, chunk in enumerate(chunks):
            self._log(f"Processing chunk {i+1}/{len(chunks)} with Gemini...")

            try:
                # Extrair texto do chunk
                chunk_text = " ".join(w["word"] for w in chunk)
                chunk_start = chunk[0]["start"]
                chunk_end = chunk[-1]["end"]

                prompt = self._build_prompt(
                    words=chunk,
                    full_text=chunk_text,
                    total_duration_ms=chunk_end - chunk_start,
                    min_duration=min_scene_duration,
                    max_duration=max_scene_duration,
                    chunk_info={"index": i, "total": len(chunks)}
                )

                response = await self.model.generate_content_async(prompt)
                chunk_result = self._parse_response(response.text)

                # Usar style_guide do primeiro chunk
                if not style_guide and chunk_result.style_guide:
                    style_guide = chunk_result.style_guide

                all_scenes.extend(chunk_result.scenes)
                all_music_cues.extend(chunk_result.music_cues)

            except Exception as e:
                self._log(f"ERROR: Chunk {i+1} failed: {e}")
                # Criar cena fallback para o chunk
                fallback_scene = Scene(
                    scene_index=len(all_scenes),
                    text=" ".join(w["word"] for w in chunk[:50]) + "...",
                    start_ms=chunk[0]["start"],
                    end_ms=chunk[-1]["end"],
                    duration_ms=chunk[-1]["end"] - chunk[0]["start"],
                    image_prompt=f"Cinematic visualization, dramatic lighting, 8k quality, {self.image_style}",
                    mood="neutral",
                    mood_intensity=0.5,
                    is_mood_transition=False
                )
                all_scenes.append(fallback_scene)

        # Re-indexar cenas
        for idx, scene in enumerate(all_scenes):
            scene.scene_index = idx

        self._log(f"Total scenes generated: {len(all_scenes)}")

        return SceneAnalysis(
            style_guide=style_guide,
            scenes=all_scenes,
            music_cues=all_music_cues
        )

    def _build_prompt(
        self,
        words: List[dict],
        full_text: str,
        total_duration_ms: int,
        min_duration: float,
        max_duration: float,
        chunk_info: Optional[dict] = None
    ) -> str:
        """Constrói prompt para o Gemini."""

        style_instruction = ""
        if self.image_style:
            style_instruction = f'\nESTILO VISUAL OBRIGATÓRIO: Todos os prompts devem terminar com: "{self.image_style}"'

        chunk_note = ""
        if chunk_info:
            chunk_note = f"\n(Este é o chunk {chunk_info['index']+1} de {chunk_info['total']})"

        return f"""Você é um diretor de arte profissional criando um vídeo narrado.{chunk_note}

## SUA TAREFA

Analise a transcrição com timestamps EXATOS de cada palavra e divida em CENAS VISUAIS.
Cada cena terá uma imagem gerada que deve ILUSTRAR VISUALMENTE o que está sendo falado.

## DADOS DE ENTRADA

**Texto completo:**
{full_text}

**Duração total:** {total_duration_ms}ms ({total_duration_ms/1000:.1f} segundos)

**Palavras com timestamps (ms):**
{json.dumps(words, ensure_ascii=False)}

## REGRAS CRÍTICAS PARA DIVISÃO DE CENAS

1. **USE TIMESTAMPS REAIS** - start_ms e end_ms DEVEM ser timestamps de palavras da lista acima
2. **DURAÇÃO: {min_duration}-{max_duration} segundos** - Pode variar se necessário para não cortar ideias
3. **NUNCA CORTE NO MEIO DE UMA FRASE** - Cada cena deve ter sentido completo
4. **SEM GAPS** - O start_ms da cena N+1 deve ser igual ao end_ms da cena N
5. **COBERTURA TOTAL** - Primeira cena começa no primeiro timestamp, última termina no último

## REGRAS PARA PROMPTS DE IMAGEM

1. **ILUSTRE O CONTEÚDO** - A imagem deve representar visualmente o que está sendo falado
   - Se fala de "tecnologia", mostre computadores, circuitos, telas
   - Se fala de "natureza", mostre paisagens, plantas, animais
   - Se fala de "pessoas", mostre pessoas em contexto relevante
2. **ESCREVA EM INGLÊS**
3. **SEJA ESPECÍFICO** - Mínimo 25 palavras descrevendo a cena
4. **SEJA CINEMATOGRÁFICO** - Use termos como "cinematic shot", "dramatic lighting", "8k", "wide angle"
5. **MANTENHA CONSISTÊNCIA** - Mesmo estilo visual em todas as cenas{style_instruction}

## EXEMPLO

Se o texto diz: "A inteligência artificial está transformando o mercado de trabalho"
BOM prompt: "Modern office environment with holographic AI interfaces floating above desks, diverse professionals collaborating with digital assistants, warm ambient lighting mixed with blue tech glow, wide angle cinematic shot, 8k, photorealistic"
RUIM prompt: "Abstract AI concept" (muito genérico!)

## MOODS PERMITIDOS

Use apenas: alegre, animado, calmo, dramatico, inspirador, melancolico, neutro, epico, suspense

## FORMATO DE SAÍDA (JSON)

{{
    "style_guide": "Descrição do estilo visual geral",
    "scenes": [
        {{
            "scene_index": 0,
            "text": "Texto exato falado nesta cena",
            "start_ms": 0,
            "end_ms": 4520,
            "image_prompt": "Detailed cinematic description...",
            "mood": "inspirador"
        }}
    ],
    "music_cues": [
        {{"timestamp_ms": 0, "mood": "inspirador", "suggestion": "Música épica orquestral"}}
    ]
}}"""

    def _parse_response(self, response_text: str) -> SceneAnalysis:
        """Converte resposta do Gemini em SceneAnalysis."""

        # Limpar resposta
        cleaned = response_text.strip()
        if cleaned.startswith("```"):
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

        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()

        # Extrair objeto JSON
        cleaned = self._extract_json_object(cleaned)

        # Tentar parse
        data = None
        parse_errors = []

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            parse_errors.append(f"Direct parse: {e}")
            try:
                repaired = self._repair_json(cleaned)
                data = json.loads(repaired)
            except json.JSONDecodeError as e2:
                parse_errors.append(f"After repair: {e2}")

        if data is None:
            logger.error(f"JSON parse failed: {parse_errors}")
            raise ValueError(f"Invalid JSON from Gemini: {parse_errors}")

        # Converter para objetos Scene
        scenes = []
        for s in data["scenes"]:
            duration_ms = s["end_ms"] - s["start_ms"]
            if duration_ms < 1000:
                duration_ms = 1000

            scenes.append(Scene(
                scene_index=s["scene_index"],
                text=s["text"],
                start_ms=s["start_ms"],
                end_ms=s["end_ms"],
                duration_ms=duration_ms,
                image_prompt=s["image_prompt"],
                mood=s["mood"],
                mood_intensity=0.7,
                is_mood_transition=False
            ))

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

    def _extract_json_object(self, text: str) -> str:
        """Extrai o primeiro objeto JSON completo do texto."""
        start = text.find('{')
        if start == -1:
            return text

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

        return text[start:]

    def _repair_json(self, json_str: str) -> str:
        """Tenta reparar JSON malformado."""
        repaired = json_str
        repaired = re.sub(r',(\s*[}\]])', r'\1', repaired)
        repaired = re.sub(r'}\s*{', '},{', repaired)
        repaired = re.sub(r']\s*\[', '],[', repaired)
        repaired = re.sub(r'(\{|\,)\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', repaired)
        repaired = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', repaired)
        return repaired

    async def test_connection(self) -> dict:
        """Testa conexão com a API."""
        try:
            test_model = genai.GenerativeModel(self._model_name)
            response = await test_model.generate_content_async("Say 'OK'")
            return {"connected": True, "response": response.text[:50]}
        except Exception as e:
            return {"connected": False, "error": str(e)}
