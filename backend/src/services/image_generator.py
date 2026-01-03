"""
Serviço de geração de imagens usando WaveSpeed Flux.
"""

import httpx
import asyncio
import time
from pathlib import Path
from typing import Optional, Callable, List
from tenacity import retry, stop_after_attempt, wait_exponential
import logging

from ..models.video import Scene, GeneratedImage

logger = logging.getLogger(__name__)


class WaveSpeedGenerator:
    """
    Gera imagens usando WaveSpeed Flux API.

    Features:
    - Processamento em batch com fila
    - Retry automático com backoff
    - Suporte a múltiplos modelos (schnell, dev)
    - Resolução configurável
    """

    BASE_URL = "https://api.wavespeed.ai/api/v3"

    def __init__(
        self,
        api_key: str,
        model: str = "flux-dev-ultra-fast",
        resolution: str = "1920x1080",
        output_dir: str = "temp"
    ):
        self.api_key = api_key
        self.model = model
        self.width, self.height = map(int, resolution.split("x"))
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def generate_all(
        self,
        scenes: List[Scene],
        max_concurrent: int = 3,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[GeneratedImage]:
        """
        Gera imagens para todas as cenas.

        Args:
            scenes: Lista de Scene do scene_analyzer
            max_concurrent: Máximo de requisições simultâneas
            progress_callback: Callback (completed, total)

        Returns:
            Lista de GeneratedImage
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        completed = 0

        async def generate_with_semaphore(scene: Scene) -> GeneratedImage:
            nonlocal completed
            async with semaphore:
                result = await self._generate_image(scene)
                completed += 1
                if progress_callback:
                    progress_callback(completed, len(scenes))
                return result

        tasks = [generate_with_semaphore(scene) for scene in scenes]
        results = await asyncio.gather(*tasks)

        return sorted(results, key=lambda x: x.scene_index)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60)
    )
    async def _generate_image(self, scene: Scene) -> GeneratedImage:
        """Gera imagem para uma única cena."""
        start_time = time.time()

        logger.info(f"Generating image for scene {scene.scene_index}")

        async with httpx.AsyncClient(timeout=120) as client:
            # Iniciar geração
            response = await client.post(
                f"{self.BASE_URL}/wavespeed-ai/{self.model}/txt2img",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "prompt": scene.image_prompt,
                    "width": self.width,
                    "height": self.height,
                    "num_images": 1
                }
            )
            response.raise_for_status()

            data = response.json()

            # Check if we need to poll for result
            if "requestId" in data:
                # Need to poll for result
                request_id = data["requestId"]
                image_url = await self._poll_for_result(client, request_id)
            elif "images" in data:
                image_url = data["images"][0]["url"]
            elif "output" in data and "images" in data["output"]:
                image_url = data["output"]["images"][0]
            else:
                raise ValueError(f"Unexpected response format: {data}")

            # Baixar imagem
            image_response = await client.get(image_url)
            image_response.raise_for_status()

            # Salvar
            output_path = self.output_dir / f"scene_{scene.scene_index}.png"
            output_path.write_bytes(image_response.content)

            generation_time = int((time.time() - start_time) * 1000)

            logger.info(f"Generated image for scene {scene.scene_index} in {generation_time}ms")

            return GeneratedImage(
                scene_index=scene.scene_index,
                image_path=str(output_path),
                prompt_used=scene.image_prompt,
                generation_time_ms=generation_time
            )

    async def _poll_for_result(
        self,
        client: httpx.AsyncClient,
        request_id: str,
        max_attempts: int = 60
    ) -> str:
        """Poll for image generation result."""
        for _ in range(max_attempts):
            response = await client.get(
                f"{self.BASE_URL}/predictions/{request_id}/result",
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            response.raise_for_status()

            data = response.json()
            status = data.get("status")

            if status == "completed":
                if "output" in data and "images" in data["output"]:
                    return data["output"]["images"][0]
                elif "images" in data:
                    return data["images"][0]["url"]
                else:
                    raise ValueError(f"Unexpected completed response: {data}")

            elif status == "failed":
                raise RuntimeError(f"Image generation failed: {data.get('error')}")

            await asyncio.sleep(2)

        raise TimeoutError("Image generation timed out")

    async def get_remaining_credits(self) -> float:
        """Retorna créditos restantes em dólares."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/account",
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            response.raise_for_status()
            return response.json().get("credits", 0)

    async def test_connection(self) -> dict:
        """Testa conexão com a API."""
        try:
            credits = await self.get_remaining_credits()
            return {
                "connected": True,
                "remaining_credits": credits
            }
        except Exception as e:
            return {
                "connected": False,
                "error": str(e)
            }
