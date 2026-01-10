"""
Serviço de geração de imagens usando WaveSpeed Flux.
"""

import httpx
import asyncio
import time
import random
from pathlib import Path
from typing import Optional, Callable, List
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import logging

from ..models.video import Scene, GeneratedImage

logger = logging.getLogger(__name__)


class RetryableError(Exception):
    """Erro que pode ser retentado."""
    pass


class NonRetryableError(Exception):
    """Erro que não deve ser retentado (ex: API key inválida)."""
    pass


class WaveSpeedGenerator:
    """
    Gera imagens usando WaveSpeed Flux API.

    Features:
    - Processamento em batch com fila
    - Retry automático com backoff
    - Retry de imagens falhas no final
    - Suporte a múltiplos modelos (schnell, dev)
    - Resolução configurável
    - Connection pooling para evitar exaustão de recursos
    """

    BASE_URL = "https://api.wavespeed.ai/api/v3"
    MAX_RETRIES = 5
    RETRY_DELAY_BASE = 2  # segundos

    def __init__(
        self,
        api_key: str,
        model: str = "flux-dev-ultra-fast",
        resolution: str = "1920x1080",
        output_dir: str = "temp",
        output_format: str = "png",
        log_callback: Optional[Callable[[str], None]] = None
    ):
        self.api_key = api_key
        self.model = model
        self.width, self.height = map(int, resolution.split("x"))
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.output_format = output_format
        self.log_callback = log_callback
        self._client: Optional[httpx.AsyncClient] = None

    def _log(self, message: str):
        """Log message to both logger and callback if set."""
        logger.info(message)
        if self.log_callback:
            self.log_callback(message)

    async def _get_client(self) -> httpx.AsyncClient:
        """Retorna cliente HTTP compartilhado com connection pooling."""
        if self._client is None or self._client.is_closed:
            # Limites de conexão para evitar exaustão de recursos
            limits = httpx.Limits(
                max_keepalive_connections=10,
                max_connections=20,
                keepalive_expiry=30.0
            )
            timeout = httpx.Timeout(
                connect=30.0,
                read=120.0,
                write=30.0,
                pool=60.0
            )
            self._client = httpx.AsyncClient(
                limits=limits,
                timeout=timeout,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )
        return self._client

    async def _close_client(self):
        """Fecha o cliente HTTP."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def generate_all(
        self,
        scenes: List[Scene],
        max_concurrent: int = 3,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[GeneratedImage]:
        """
        Gera imagens para todas as cenas.
        Continua mesmo se algumas imagens falharem.
        Tenta novamente as que falharam no final.

        Args:
            scenes: Lista de Scene do scene_analyzer
            max_concurrent: Máximo de requisições simultâneas
            progress_callback: Callback (completed, total)

        Returns:
            Lista de GeneratedImage (inclui placeholders para falhas)
        """
        # Para muitas cenas, reduzir concorrência para não sobrecarregar CPU
        if len(scenes) > 50:
            max_concurrent = min(max_concurrent, 2)
            self._log(f"Reduced concurrency to {max_concurrent} for {len(scenes)} scenes")

        semaphore = asyncio.Semaphore(max_concurrent)
        results: dict[int, GeneratedImage] = {}
        failed_scenes: List[Scene] = []
        completed = 0
        total = len(scenes)

        try:
            # Inicializar cliente HTTP compartilhado
            await self._get_client()
            self._log(f"HTTP client initialized with connection pooling")

            async def generate_with_semaphore(scene: Scene) -> None:
                nonlocal completed
                async with semaphore:
                    try:
                        # Pequeno delay aleatório para evitar rate limiting
                        await asyncio.sleep(random.uniform(0.1, 0.5))

                        result = await self._generate_with_retries(scene)
                        if result:
                            results[scene.scene_index] = result
                        else:
                            failed_scenes.append(scene)
                    except Exception as e:
                        # Captura qualquer erro não tratado
                        self._log(f"ERROR: Unexpected error generating scene {scene.scene_index}: {e}")
                        failed_scenes.append(scene)
                    finally:
                        completed += 1
                        if progress_callback:
                            progress_callback(completed, total)
                        # Yield control ao event loop para permitir que outras tarefas rodem
                        # (como responder requisições de status)
                        await asyncio.sleep(0)

            # Primeira rodada de geração
            tasks = [generate_with_semaphore(scene) for scene in scenes]
            await asyncio.gather(*tasks, return_exceptions=True)

            # Segunda rodada: tentar novamente as que falharam
            if failed_scenes:
                self._log(f"Retrying {len(failed_scenes)} failed images...")
                await asyncio.sleep(5)  # Esperar um pouco antes de retentar

                for scene in failed_scenes.copy():
                    try:
                        result = await self._generate_with_retries(scene, is_retry=True)
                        if result:
                            results[scene.scene_index] = result
                            failed_scenes.remove(scene)
                            self._log(f"Successfully generated scene {scene.scene_index} on retry")
                    except Exception as e:
                        self._log(f"WARNING: Retry failed for scene {scene.scene_index}: {e}")

            # Terceira rodada: última tentativa com delay maior
            if failed_scenes:
                self._log(f"Final retry for {len(failed_scenes)} remaining failed images...")
                await asyncio.sleep(10)

                for scene in failed_scenes.copy():
                    try:
                        result = await self._generate_with_retries(scene, is_retry=True, max_attempts=3)
                        if result:
                            results[scene.scene_index] = result
                            failed_scenes.remove(scene)
                            self._log(f"Successfully generated scene {scene.scene_index} on final retry")
                    except Exception as e:
                        self._log(f"WARNING: Final retry failed for scene {scene.scene_index}: {e}")

            # Criar placeholders para as que ainda falharam
            if failed_scenes:
                self._log(f"WARNING: Creating placeholders for {len(failed_scenes)} scenes that failed all retries")
                for scene in failed_scenes:
                    try:
                        results[scene.scene_index] = await self._create_placeholder_image(scene)
                    except Exception as e:
                        self._log(f"ERROR: Could not create placeholder for scene {scene.scene_index}: {e}")
                        # Criar um resultado mínimo para não quebrar o vídeo
                        results[scene.scene_index] = GeneratedImage(
                            scene_index=scene.scene_index,
                            image_path="",  # Vazio - video_composer vai lidar
                            prompt_used=f"[FAILED] {scene.image_prompt[:50]}...",
                            generation_time_ms=0
                        )

        finally:
            # SEMPRE fechar o cliente HTTP para liberar conexões
            await self._close_client()
            self._log(f"HTTP client closed, connections released")

        # Ordenar por índice de cena e garantir que não falta nenhuma
        # Se faltar alguma cena por algum bug, criar placeholder
        final_results = []
        for scene in scenes:
            if scene.scene_index in results:
                final_results.append(results[scene.scene_index])
            else:
                # Cena faltando - criar resultado mínimo
                self._log(f"WARNING: Scene {scene.scene_index} missing from results, creating empty entry")
                final_results.append(GeneratedImage(
                    scene_index=scene.scene_index,
                    image_path="",
                    prompt_used=f"[MISSING] {scene.image_prompt[:50]}...",
                    generation_time_ms=0
                ))

        return final_results

    async def _generate_with_retries(
        self,
        scene: Scene,
        is_retry: bool = False,
        max_attempts: int = None
    ) -> Optional[GeneratedImage]:
        """Tenta gerar imagem com múltiplas tentativas."""
        attempts = max_attempts or self.MAX_RETRIES
        last_error = None

        for attempt in range(attempts):
            try:
                if attempt > 0 or is_retry:
                    # Backoff exponencial com jitter
                    delay = self.RETRY_DELAY_BASE * (2 ** attempt) + random.uniform(0, 1)
                    self._log(f"Retry {attempt + 1}/{attempts} for scene {scene.scene_index} after {delay:.1f}s")
                    await asyncio.sleep(delay)

                return await self._generate_image(scene)

            except NonRetryableError as e:
                self._log(f"ERROR: Non-retryable error for scene {scene.scene_index}: {e}")
                return None

            except Exception as e:
                last_error = e
                self._log(f"WARNING: Attempt {attempt + 1}/{attempts} failed for scene {scene.scene_index}: {e}")

        self._log(f"ERROR: All {attempts} attempts failed for scene {scene.scene_index}: {last_error}")
        return None

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

        self._log(f"Created placeholder image for scene {scene.scene_index}")

        return GeneratedImage(
            scene_index=scene.scene_index,
            image_path=str(output_path),
            prompt_used=f"[PLACEHOLDER] {scene.image_prompt[:100]}...",
            generation_time_ms=0
        )

    def _get_model_params(self, prompt: str) -> dict:
        """Retorna parâmetros específicos para cada modelo."""
        base_params = {
            "prompt": prompt,
            "size": f"{self.width}*{self.height}",
            "num_images": 1,
            "enable_base64_output": False,
            "enable_sync_mode": False,
            "output_format": self.output_format,
            "seed": -1,
        }

        if self.model == "flux-schnell":
            # flux-schnell: modelo rápido, parâmetros simplificados
            return {
                **base_params,
                "strength": 0.8,
            }
        else:
            # flux-dev-ultra-fast e flux-dev: parâmetros avançados
            return {
                **base_params,
                "guidance_scale": 3.5,
                "num_inference_steps": 28,
                "strength": 0.8,
            }

    async def _generate_image(self, scene: Scene) -> GeneratedImage:
        """Gera imagem para uma única cena usando cliente compartilhado."""
        start_time = time.time()

        self._log(f"Generating image for scene {scene.scene_index} with {self.model}...")

        try:
            client = await self._get_client()

            # Obter parâmetros específicos do modelo
            params = self._get_model_params(scene.image_prompt)

            # Iniciar geração
            response = await client.post(
                f"{self.BASE_URL}/wavespeed-ai/{self.model}",
                json=params
            )

            # Erros que NÃO devem ser retentados
            if response.status_code == 401:
                raise NonRetryableError("WaveSpeed API: Chave de API inválida ou expirada")
            elif response.status_code == 402:
                raise NonRetryableError("WaveSpeed API: Créditos insuficientes")
            # Erros que DEVEM ser retentados
            elif response.status_code == 429:
                raise RetryableError("WaveSpeed API: Limite de requisições excedido, aguarde um momento")
            elif response.status_code >= 500:
                # Erros de servidor - sempre retentar
                error_detail = response.text[:200] if response.text else "Server error"
                raise RetryableError(f"WaveSpeed API erro {response.status_code}: {error_detail}")
            elif response.status_code >= 400:
                # Outros erros 4xx - retentar por segurança
                error_detail = response.text[:200] if response.text else "Client error"
                raise RetryableError(f"WaveSpeed API erro {response.status_code}: {error_detail}")

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

            # Salvar com extensão correta
            ext = self.output_format if self.output_format in ["png", "jpeg", "jpg"] else "png"
            output_path = self.output_dir / f"scene_{scene.scene_index}.{ext}"
            output_path.write_bytes(image_response.content)

            generation_time = int((time.time() - start_time) * 1000)

            self._log(f"Generated image for scene {scene.scene_index} in {generation_time}ms")

            return GeneratedImage(
                scene_index=scene.scene_index,
                image_path=str(output_path),
                prompt_used=scene.image_prompt,
                generation_time_ms=generation_time
            )

        except (NonRetryableError, RetryableError):
            # Re-raise para ser tratado pelo caller
            raise
        except httpx.HTTPStatusError as e:
            raise RetryableError(f"Erro HTTP na geração de imagem: {e.response.status_code}")
        except httpx.TimeoutException:
            raise RetryableError("Timeout na geração de imagem")
        except httpx.RequestError as e:
            raise RetryableError(f"Erro de conexão com WaveSpeed API: {str(e)}")
        except Exception as e:
            raise RetryableError(f"Erro inesperado: {str(e)}")

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
            # Headers já configurados no cliente compartilhado
            response = await client.get(url)
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


class LocalImageGenerator:
    """
    Gera imagens usando GPU local com Flux/SDXL.

    Features:
    - Suporte a GPUs com 4GB, 6GB e 8GB de VRAM
    - Fallback automatico para WaveSpeed API
    - Processamento em batch similar ao WaveSpeedGenerator
    """

    def __init__(
        self,
        vram_mode: str = "auto",
        output_dir: str = "temp",
        log_callback: Optional[Callable[[str], None]] = None,
        fallback_api_key: Optional[str] = None,
        fallback_model: str = "flux-dev-ultra-fast",
    ):
        self.vram_mode = vram_mode
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_callback = log_callback
        self.fallback_api_key = fallback_api_key
        self.fallback_model = fallback_model
        self._generator = None
        self._fallback_generator = None

    def _log(self, message: str):
        """Log message to both logger and callback if set."""
        logger.info(message)
        if self.log_callback:
            self.log_callback(message)

    def _get_generator(self):
        """Lazy initialization do gerador local."""
        if self._generator is None:
            try:
                from .flux_local import get_generator
                self._generator = get_generator(self.vram_mode)
            except Exception as e:
                self._log(f"WARNING: Falha ao inicializar gerador local: {e}")
                raise
        return self._generator

    def _get_fallback_generator(self) -> Optional['WaveSpeedGenerator']:
        """Retorna gerador WaveSpeed para fallback."""
        if self._fallback_generator is None and self.fallback_api_key:
            self._fallback_generator = WaveSpeedGenerator(
                api_key=self.fallback_api_key,
                model=self.fallback_model,
                output_dir=str(self.output_dir),
                log_callback=self.log_callback
            )
        return self._fallback_generator

    async def generate_all(
        self,
        scenes: List[Scene],
        max_concurrent: int = 2,  # Menor para GPU local
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[GeneratedImage]:
        """
        Gera imagens para todas as cenas usando GPU local.

        Args:
            scenes: Lista de Scene do scene_analyzer
            max_concurrent: Maximo de requisicoes simultaneas
            progress_callback: Callback (completed, total)

        Returns:
            Lista de GeneratedImage
        """
        results: dict[int, GeneratedImage] = {}
        failed_scenes: List[Scene] = []
        completed = 0
        total = len(scenes)

        try:
            generator = self._get_generator()
            if not generator.pipe:
                self._log("Carregando modelo local...")
                generator.load_model()
                self._log("Modelo local carregado!")

            # Obter resolucao do modelo (16:9)
            img_width = generator.config["width"]
            img_height = generator.config["height"]
            self._log(f"Usando modelo: {generator.config['name']} ({img_width}x{img_height})")

            # Gerar imagens uma a uma (GPU local e mais estavel assim)
            for scene in scenes:
                try:
                    start_time = time.time()
                    self._log(f"Gerando imagem local para cena {scene.scene_index}...")

                    output_path = self.output_dir / f"scene_{scene.scene_index}.png"

                    await generator.generate_to_file(
                        prompt=scene.image_prompt,
                        output_path=str(output_path),
                        width=img_width,
                        height=img_height,
                    )

                    generation_time = int((time.time() - start_time) * 1000)

                    results[scene.scene_index] = GeneratedImage(
                        scene_index=scene.scene_index,
                        image_path=str(output_path),
                        prompt_used=scene.image_prompt,
                        generation_time_ms=generation_time
                    )

                    self._log(f"Imagem local gerada para cena {scene.scene_index} em {generation_time}ms")

                except Exception as e:
                    self._log(f"WARNING: Erro na geracao local da cena {scene.scene_index}: {e}")
                    failed_scenes.append(scene)

                finally:
                    completed += 1
                    if progress_callback:
                        progress_callback(completed, total)

        except Exception as e:
            self._log(f"ERROR: Falha ao inicializar gerador local: {e}")
            # Todas as cenas falharam
            failed_scenes = list(scenes)

        # Tentar fallback para cenas que falharam
        if failed_scenes and self.fallback_api_key:
            self._log(f"Usando fallback WaveSpeed para {len(failed_scenes)} cenas...")
            fallback = self._get_fallback_generator()
            if fallback:
                try:
                    fallback_results = await fallback.generate_all(
                        failed_scenes,
                        max_concurrent=3,
                        progress_callback=None  # Ja contamos no progress principal
                    )
                    for result in fallback_results:
                        results[result.scene_index] = result
                        if result.scene_index in [s.scene_index for s in failed_scenes]:
                            failed_scenes = [s for s in failed_scenes if s.scene_index != result.scene_index]
                except Exception as e:
                    self._log(f"WARNING: Fallback tambem falhou: {e}")

        # Criar placeholders para as que ainda falharam
        if failed_scenes:
            self._log(f"WARNING: Criando placeholders para {len(failed_scenes)} cenas")
            for scene in failed_scenes:
                results[scene.scene_index] = await self._create_placeholder_image(scene)

        # Ordenar resultados
        return [results[scene.scene_index] for scene in scenes if scene.scene_index in results]

    async def _create_placeholder_image(self, scene: Scene) -> GeneratedImage:
        """Cria uma imagem placeholder quando a geracao falha."""
        from PIL import Image, ImageDraw, ImageFont

        # Cores baseadas no mood
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
        img = Image.new('RGB', (1024, 1024), bg_color)
        draw = ImageDraw.Draw(img)

        text = f"Cena {scene.scene_index + 1}"

        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 48)
        except:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (1024 - text_width) // 2
        y = (1024 - text_height) // 2

        text_color = (255, 255, 255) if sum(bg_color) < 400 else (0, 0, 0)
        draw.text((x, y), text, fill=text_color, font=font)

        output_path = self.output_dir / f"scene_{scene.scene_index}.png"
        img.save(output_path)

        self._log(f"Placeholder criado para cena {scene.scene_index}")

        return GeneratedImage(
            scene_index=scene.scene_index,
            image_path=str(output_path),
            prompt_used=f"[PLACEHOLDER] {scene.image_prompt[:100]}...",
            generation_time_ms=0
        )


def get_image_generator(
    config,
    output_dir: str = "temp",
    log_callback: Optional[Callable[[str], None]] = None,
):
    """
    Factory function para obter o gerador de imagens correto baseado na config.

    Args:
        config: FullConfig ou GPUConfig
        output_dir: Diretorio de saida
        log_callback: Callback para logs

    Returns:
        WaveSpeedGenerator ou LocalImageGenerator
    """
    # Extrair gpu config se for FullConfig
    gpu_config = getattr(config, 'gpu', None)

    if gpu_config and gpu_config.enabled and gpu_config.provider == "local":
        # Usar gerador local
        fallback_key = None
        fallback_model = "flux-dev-ultra-fast"

        # Configurar fallback se disponivel
        api_config = getattr(config, 'api', None)
        if api_config and gpu_config.auto_fallback_to_api:
            wavespeed = getattr(api_config, 'wavespeed', None)
            if wavespeed and wavespeed.api_key:
                fallback_key = wavespeed.api_key
                fallback_model = wavespeed.model

        return LocalImageGenerator(
            vram_mode=gpu_config.vram_mode if hasattr(gpu_config.vram_mode, 'value') else gpu_config.vram_mode,
            output_dir=output_dir,
            log_callback=log_callback,
            fallback_api_key=fallback_key,
            fallback_model=fallback_model,
        )
    else:
        # Usar WaveSpeed
        api_config = getattr(config, 'api', None)
        if api_config:
            wavespeed = api_config.wavespeed
            return WaveSpeedGenerator(
                api_key=wavespeed.api_key,
                model=wavespeed.model,
                resolution=wavespeed.resolution,
                output_dir=output_dir,
                output_format=getattr(wavespeed, 'output_format', 'png'),
                log_callback=log_callback,
            )
        else:
            raise ValueError("Configuracao de API nao encontrada")
