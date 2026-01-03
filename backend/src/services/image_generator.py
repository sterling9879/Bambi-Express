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
        Continua mesmo se algumas imagens falharem.

        Args:
            scenes: Lista de Scene do scene_analyzer
            max_concurrent: Máximo de requisições simultâneas
            progress_callback: Callback (completed, total)

        Returns:
            Lista de GeneratedImage (inclui placeholders para falhas)
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        completed = 0
        failed_scenes = []

        async def generate_with_semaphore(scene: Scene) -> GeneratedImage:
            nonlocal completed
            async with semaphore:
                try:
                    result = await self._generate_image(scene)
                    completed += 1
                    if progress_callback:
                        progress_callback(completed, len(scenes))
                    return result
                except Exception as e:
                    logger.error(f"Failed to generate image for scene {scene.scene_index} after all retries: {e}")
                    failed_scenes.append(scene.scene_index)
                    completed += 1
                    if progress_callback:
                        progress_callback(completed, len(scenes))
                    # Retornar placeholder para manter a ordem das cenas
                    return await self._create_placeholder_image(scene)

        tasks = [generate_with_semaphore(scene) for scene in scenes]
        results = await asyncio.gather(*tasks)

        if failed_scenes:
            logger.warning(f"Failed to generate images for scenes: {failed_scenes}. Used placeholders.")

        return sorted(results, key=lambda x: x.scene_index)

    async def _create_placeholder_image(self, scene: Scene) -> GeneratedImage:
        """Cria uma imagem placeholder quando a geração falha."""
        from PIL import Image, ImageDraw, ImageFont

        # Criar imagem com cor de fundo baseada no mood
        mood_colors = {
            "alegre": (255, 223, 128),
            "animado": (255, 165, 79),
            "calmo": (135, 206, 235),
            "dramatico": (70, 70, 100),
            "inspirador": (255, 215, 0),
            "melancolico": (105, 105, 135),
            "raiva": (178, 34, 34),
            "romantico": (255, 182, 193),
            "sombrio": (47, 47, 61),
            "vibrante": (255, 99, 71),
        }

        bg_color = mood_colors.get(scene.mood, (100, 100, 100))
        img = Image.new('RGB', (self.width, self.height), bg_color)
        draw = ImageDraw.Draw(img)

        # Adicionar texto indicando que é placeholder
        text = f"Cena {scene.scene_index + 1}"

        # Tentar usar uma fonte, se falhar usa default
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 48)
        except:
            font = ImageFont.load_default()

        # Centralizar texto
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (self.width - text_width) // 2
        y = (self.height - text_height) // 2

        # Cor do texto (contraste com fundo)
        text_color = (255, 255, 255) if sum(bg_color) < 400 else (0, 0, 0)
        draw.text((x, y), text, fill=text_color, font=font)

        # Salvar
        output_path = self.output_dir / f"scene_{scene.scene_index}.png"
        img.save(output_path)

        logger.info(f"Created placeholder image for scene {scene.scene_index}")

        return GeneratedImage(
            scene_index=scene.scene_index,
            image_path=str(output_path),
            prompt_used=f"[PLACEHOLDER] {scene.image_prompt[:100]}...",
            generation_time_ms=0
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        reraise=True
    )
    async def _generate_image(self, scene: Scene) -> GeneratedImage:
        """Gera imagem para uma única cena."""
        start_time = time.time()

        logger.info(f"Generating image for scene {scene.scene_index}")

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                # Iniciar geração
                response = await client.post(
                    f"{self.BASE_URL}/wavespeed-ai/{self.model}",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "prompt": scene.image_prompt,
                        "size": f"{self.width}*{self.height}",
                        "num_images": 1,
                        "enable_base64_output": False,
                        "enable_sync_mode": False,
                        "guidance_scale": 3.5,
                        "num_inference_steps": 28,
                        "output_format": "png",
                        "seed": -1,
                        "strength": 0.8
                    }
                )

                if response.status_code == 401:
                    raise RuntimeError("WaveSpeed API: Chave de API inválida ou expirada")
                elif response.status_code == 402:
                    raise RuntimeError("WaveSpeed API: Créditos insuficientes")
                elif response.status_code == 429:
                    raise RuntimeError("WaveSpeed API: Limite de requisições excedido, aguarde um momento")
                elif response.status_code >= 400:
                    error_detail = response.text
                    raise RuntimeError(f"WaveSpeed API erro {response.status_code}: {error_detail}")

                data = response.json()

                # Check response format and get image URL
                if "data" in data and "id" in data["data"]:
                    # Async mode - need to poll for result
                    request_id = data["data"]["id"]
                    poll_url = data["data"]["urls"]["get"]
                    image_url = await self._poll_for_result(client, request_id, poll_url)
                elif "data" in data and "outputs" in data["data"] and data["data"]["outputs"]:
                    # Sync mode - result available immediately
                    image_url = data["data"]["outputs"][0]
                elif "requestId" in data:
                    # Legacy format
                    request_id = data["requestId"]
                    image_url = await self._poll_for_result(client, request_id)
                elif "images" in data:
                    image_url = data["images"][0]["url"]
                elif "output" in data and "images" in data["output"]:
                    image_url = data["output"]["images"][0]
                else:
                    raise ValueError(f"Formato de resposta inesperado: {data}")

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

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error generating image: {e}")
            raise RuntimeError(f"Erro HTTP na geração de imagem: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"Request error generating image: {e}")
            raise RuntimeError(f"Erro de conexão com WaveSpeed API: {str(e)}")

    async def _poll_for_result(
        self,
        client: httpx.AsyncClient,
        request_id: str,
        poll_url: Optional[str] = None,
        max_attempts: int = 60
    ) -> str:
        """Poll for image generation result."""
        url = poll_url or f"{self.BASE_URL}/predictions/{request_id}/result"

        for attempt in range(max_attempts):
            response = await client.get(
                url,
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            response.raise_for_status()

            data = response.json()

            # Handle nested data structure
            inner_data = data.get("data", data)
            status = inner_data.get("status")

            logger.debug(f"Poll attempt {attempt + 1}: status={status}")

            if status == "completed":
                # Check various output formats
                if "outputs" in inner_data and inner_data["outputs"]:
                    return inner_data["outputs"][0]
                elif "output" in inner_data and "images" in inner_data["output"]:
                    return inner_data["output"]["images"][0]
                elif "images" in inner_data:
                    return inner_data["images"][0]["url"] if isinstance(inner_data["images"][0], dict) else inner_data["images"][0]
                else:
                    raise ValueError(f"Formato de resposta completa inesperado: {data}")

            elif status == "failed":
                error_msg = inner_data.get("error") or data.get("message", "Erro desconhecido")
                raise RuntimeError(f"Geração de imagem falhou: {error_msg}")

            await asyncio.sleep(2)

        raise TimeoutError("Tempo limite excedido na geração de imagem")

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
