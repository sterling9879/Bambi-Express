"""
Serviço de geração de música usando IA (Suno/Udio).
"""

import httpx
import asyncio
from pathlib import Path
from typing import Optional, List
import logging
import time

from ..models.video import GeneratedMusic, Scene
from ..models.config import MusicConfig

logger = logging.getLogger(__name__)


class AIMusicGenerator:
    """
    Gera música usando APIs de IA (Suno/Udio).

    Features:
    - Geração baseada em prompt descritivo
    - Presets de estilo
    - Múltiplas variações
    - Modo instrumental
    """

    # Note: Suno API endpoints may vary - this is a generic implementation
    BASE_URL = "https://api.suno.ai/v1"

    def __init__(self, api_key: str, output_dir: str = "temp"):
        self.api_key = api_key
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def generate(
        self,
        prompt: str,
        duration_seconds: float,
        style_preset: Optional[str] = None,
        instrumental: bool = True,
        variations: int = 1
    ) -> List[GeneratedMusic]:
        """
        Gera música baseada no prompt.

        Args:
            prompt: Descrição do estilo desejado
            duration_seconds: Duração alvo
            style_preset: Preset opcional (corporate, epic, etc)
            instrumental: Se True, gera sem vocais
            variations: Número de variações a gerar

        Returns:
            Lista de músicas geradas
        """
        # Construir prompt completo
        full_prompt = self._build_prompt(prompt, style_preset, instrumental)

        logger.info(f"Generating music with prompt: {full_prompt[:100]}...")

        results = []

        for i in range(variations):
            try:
                result = await self._generate_single(
                    full_prompt,
                    duration_seconds,
                    i
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to generate variation {i}: {e}")

        return results

    async def _generate_single(
        self,
        prompt: str,
        duration_seconds: float,
        variation_index: int
    ) -> GeneratedMusic:
        """Gera uma única música."""
        start_time = time.time()

        async with httpx.AsyncClient(timeout=300) as client:
            # Start generation
            response = await client.post(
                f"{self.BASE_URL}/generate",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "prompt": prompt,
                    "duration": int(duration_seconds),
                    "make_instrumental": True
                }
            )
            response.raise_for_status()

            data = response.json()
            generation_id = data.get("id") or data.get("generation_id")

            # Poll for completion
            audio_url = await self._poll_generation(client, generation_id)

            # Download audio
            audio_response = await client.get(audio_url)
            audio_response.raise_for_status()

            output_path = self.output_dir / f"music_{generation_id}_{variation_index}.mp3"
            output_path.write_bytes(audio_response.content)

            generation_time = int((time.time() - start_time) * 1000)

            return GeneratedMusic(
                id=generation_id,
                audio_path=str(output_path),
                duration_ms=int(duration_seconds * 1000),
                prompt_used=prompt,
                style=self._extract_style(prompt),
                generation_time_ms=generation_time
            )

    async def _poll_generation(
        self,
        client: httpx.AsyncClient,
        generation_id: str,
        max_attempts: int = 120
    ) -> str:
        """Poll for music generation completion."""
        for _ in range(max_attempts):
            response = await client.get(
                f"{self.BASE_URL}/generations/{generation_id}",
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            response.raise_for_status()

            data = response.json()
            status = data.get("status")

            if status == "completed":
                return data.get("audio_url") or data.get("output", {}).get("audio_url")
            elif status == "failed":
                raise RuntimeError(f"Music generation failed: {data.get('error')}")

            await asyncio.sleep(5)

        raise TimeoutError("Music generation timed out")

    async def generate_for_video(
        self,
        scenes: List[Scene],
        total_duration_ms: int,
        config: MusicConfig
    ) -> List[GeneratedMusic]:
        """
        Gera música otimizada para o vídeo.
        Analisa os moods das cenas e gera música apropriada.
        """
        # Analisar moods predominantes
        mood_counts = {}
        for scene in scenes:
            mood_counts[scene.mood] = mood_counts.get(scene.mood, 0) + 1

        predominant_mood = max(mood_counts, key=mood_counts.get) if mood_counts else "neutral"

        # Gerar música baseada no mood predominante
        prompt = self._mood_to_prompt(predominant_mood)

        ai_config = config.ai_config
        if ai_config and ai_config.style_prompt:
            prompt = f"{ai_config.style_prompt}, {prompt}"

        return await self.generate(
            prompt=prompt,
            duration_seconds=total_duration_ms / 1000,
            style_preset=ai_config.preset if ai_config else None,
            instrumental=ai_config.instrumental_only if ai_config else True,
            variations=ai_config.variations_count if ai_config else 1
        )

    def _build_prompt(
        self,
        base_prompt: str,
        preset: Optional[str],
        instrumental: bool
    ) -> str:
        """Constrói prompt completo para geração."""
        parts = []

        if preset:
            parts.append(self._preset_to_prompt(preset))

        parts.append(base_prompt)

        if instrumental:
            parts.append("instrumental, no vocals")

        return ", ".join(filter(None, parts))

    def _preset_to_prompt(self, preset: str) -> str:
        """Converte preset em descrição."""
        presets = {
            "corporate": "professional corporate background music, upbeat, modern",
            "cinematic_epic": "epic cinematic orchestral music, dramatic, powerful",
            "lofi_chill": "lo-fi chill beats, relaxing, ambient",
            "upbeat_pop": "upbeat pop music, energetic, positive",
            "ambient": "ambient atmospheric music, soft, ethereal"
        }
        return presets.get(preset, "")

    def _mood_to_prompt(self, mood: str) -> str:
        """Converte mood em descrição musical."""
        moods = {
            "upbeat": "upbeat energetic music, positive vibes",
            "dramatic": "dramatic intense music, building tension",
            "calm": "calm peaceful music, relaxing",
            "emotional": "emotional touching music, heartfelt",
            "inspiring": "inspiring motivational music, uplifting",
            "dark": "dark mysterious music, suspenseful",
            "neutral": "neutral background music, corporate",
            "epic": "epic orchestral music, cinematic",
            "suspense": "suspenseful music, tension building"
        }
        return moods.get(mood, "background music")

    def _extract_style(self, prompt: str) -> str:
        """Extrai estilo do prompt."""
        # Simple extraction - take first few words
        words = prompt.split(",")[0].strip()
        return words[:50] if len(words) > 50 else words

    async def test_connection(self) -> dict:
        """Testa conexão com a API."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/account",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                response.raise_for_status()
                return {"connected": True}
        except Exception as e:
            return {
                "connected": False,
                "error": str(e)
            }
