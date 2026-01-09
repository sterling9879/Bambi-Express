"""
Modulo de geracao de imagens local usando Flux/SDXL.
Suporta GPUs com 4GB, 6GB e 8GB de VRAM.
"""

import gc
import io
import time
import asyncio
import logging
from typing import Optional, Literal
from pathlib import Path

logger = logging.getLogger(__name__)

# Constantes dos modelos - Otimizado para 16:9 (1280x720)
MODELS_CONFIG = {
    "4gb": {
        "name": "SDXL Turbo",
        "hf_id": "stabilityai/sdxl-turbo",
        "pipeline_class": "AutoPipelineForText2Image",
        "torch_dtype": "float16",
        "variant": "fp16",
        "default_steps": 1,
        "guidance_scale": 0.0,
        "width": 896,
        "height": 512,
        "quantized": False,
    },
    "6gb": {
        "name": "SDXL Turbo",
        "hf_id": "stabilityai/sdxl-turbo",
        "pipeline_class": "AutoPipelineForText2Image",
        "torch_dtype": "float16",
        "variant": "fp16",
        "default_steps": 1,
        "guidance_scale": 0.0,
        "width": 1024,
        "height": 576,
        "quantized": False,
    },
    "8gb": {
        "name": "SDXL Turbo",
        "hf_id": "stabilityai/sdxl-turbo",
        "pipeline_class": "AutoPipelineForText2Image",
        "torch_dtype": "float16",
        "variant": "fp16",
        "default_steps": 2,
        "guidance_scale": 0.0,
        "width": 1280,
        "height": 720,
        "quantized": False,
    },
}


def check_cuda_available() -> bool:
    """Verifica se CUDA esta disponivel."""
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


def flush_memory():
    """Limpa cache de memoria GPU."""
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.reset_peak_memory_stats()
    except ImportError:
        pass


def detect_vram() -> str:
    """Detecta VRAM disponivel e retorna o modo recomendado."""
    try:
        import torch
    except ImportError:
        raise RuntimeError("PyTorch nao instalado. Execute: pip install torch")

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA nao disponivel. GPU NVIDIA necessaria.")

    vram_bytes = torch.cuda.get_device_properties(0).total_memory
    vram_gb = vram_bytes / (1024 ** 3)

    logger.info(f"VRAM detectada: {vram_gb:.2f}GB")

    if vram_gb >= 8:
        return "8gb"
    elif vram_gb >= 6:
        return "6gb"
    elif vram_gb >= 4:
        return "4gb"
    else:
        raise RuntimeError(f"VRAM insuficiente: {vram_gb:.2f}GB. Minimo: 4GB")


def get_gpu_info() -> dict:
    """Retorna informacoes detalhadas da GPU."""
    try:
        import torch
    except ImportError:
        return {"available": False, "error": "PyTorch nao instalado"}

    if not torch.cuda.is_available():
        return {"available": False, "error": "CUDA nao disponivel"}

    try:
        props = torch.cuda.get_device_properties(0)
        vram_total = props.total_memory / (1024 ** 3)
        vram_allocated = torch.cuda.memory_allocated(0) / (1024 ** 3)
        vram_free = vram_total - vram_allocated

        return {
            "available": True,
            "name": props.name,
            "vram_total_gb": round(vram_total, 2),
            "vram_free_gb": round(vram_free, 2),
            "compute_capability": f"{props.major}.{props.minor}",
            "recommended_mode": detect_vram(),
        }
    except Exception as e:
        return {"available": False, "error": str(e)}


class FluxLocalGenerator:
    """Gerador de imagens local com suporte a multiplos modelos."""

    def __init__(
        self,
        vram_mode: Literal["4gb", "6gb", "8gb", "auto"] = "auto",
        device: str = "cuda"
    ):
        self.device = device
        self.pipe = None
        self.current_mode = None
        self._torch = None

        if vram_mode == "auto":
            self.vram_mode = detect_vram()
        else:
            self.vram_mode = vram_mode

        self.config = MODELS_CONFIG[self.vram_mode]
        logger.info(f"Modo selecionado: {self.vram_mode} ({self.config['name']})")

    def _get_torch(self):
        """Lazy import do torch."""
        if self._torch is None:
            import torch
            self._torch = torch
        return self._torch

    def _get_torch_dtype(self, dtype_str: str):
        """Converte string para torch dtype."""
        torch = self._get_torch()
        if dtype_str == "float16":
            return torch.float16
        elif dtype_str == "bfloat16":
            return torch.bfloat16
        elif dtype_str == "float32":
            return torch.float32
        else:
            return torch.float16

    def load_model(self) -> None:
        """Carrega o modelo SDXL Turbo."""
        if self.pipe is not None and self.current_mode == self.vram_mode:
            logger.info("Modelo ja carregado")
            return

        if self.pipe is not None:
            del self.pipe
            self.pipe = None
            flush_memory()

        logger.info(f"Carregando modelo: {self.config['name']}...")

        from diffusers import AutoPipelineForText2Image
        torch = self._get_torch()

        self.pipe = AutoPipelineForText2Image.from_pretrained(
            self.config["hf_id"],
            torch_dtype=self._get_torch_dtype(self.config["torch_dtype"]),
            variant=self.config.get("variant"),
            safety_checker=None,
        )
        self.pipe.to(self.device)

        if hasattr(self.pipe, 'enable_attention_slicing'):
            self.pipe.enable_attention_slicing()

        self.current_mode = self.vram_mode
        flush_memory()
        logger.info("Modelo carregado com sucesso!")

    async def generate(
        self,
        prompt: str,
        width: Optional[int] = None,
        height: Optional[int] = None,
        num_inference_steps: Optional[int] = None,
        seed: Optional[int] = None,
    ) -> bytes:
        """Gera uma imagem a partir do prompt."""
        if self.pipe is None:
            self.load_model()

        torch = self._get_torch()

        # Usar dimensoes do config (16:9) se nao especificado
        cfg_width = self.config["width"]
        cfg_height = self.config["height"]
        width = width or cfg_width
        height = height or cfg_height
        steps = num_inference_steps or self.config["default_steps"]
        guidance = self.config["guidance_scale"]

        generator = None
        if seed is not None:
            generator = torch.Generator(device=self.device).manual_seed(seed)

        gen_kwargs = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "num_inference_steps": steps,
            "guidance_scale": guidance,
            "generator": generator,
        }

        def _generate():
            with torch.inference_mode():
                result = self.pipe(**gen_kwargs)
                return result.images[0]

        image = await asyncio.to_thread(_generate)

        buffer = io.BytesIO()
        image.save(buffer, format="PNG", optimize=True)
        buffer.seek(0)

        flush_memory()

        return buffer.getvalue()

    async def generate_to_file(
        self,
        prompt: str,
        output_path: str,
        width: Optional[int] = None,
        height: Optional[int] = None,
        num_inference_steps: Optional[int] = None,
        seed: Optional[int] = None,
    ) -> str:
        """Gera uma imagem e salva em arquivo."""
        image_bytes = await self.generate(
            prompt=prompt,
            width=width,
            height=height,
            num_inference_steps=num_inference_steps,
            seed=seed,
        )

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(image_bytes)

        return str(output_path)

    def get_model_info(self) -> dict:
        """Retorna informacoes sobre o modelo atual."""
        return {
            "mode": self.vram_mode,
            "model_name": self.config["name"],
            "hf_id": self.config["hf_id"],
            "width": self.config["width"],
            "height": self.config["height"],
            "resolution": f"{self.config['width']}x{self.config['height']}",
            "default_steps": self.config["default_steps"],
            "loaded": self.pipe is not None,
            "quantized": self.config.get("quantized", False),
        }

    def unload(self):
        """Descarrega o modelo da memoria."""
        if self.pipe is not None:
            del self.pipe
            self.pipe = None
            self.current_mode = None
            flush_memory()
            logger.info("Modelo descarregado")


# Singleton
_generator_instance: Optional[FluxLocalGenerator] = None


def get_generator(vram_mode: str = "auto") -> FluxLocalGenerator:
    """Obtem instancia singleton do gerador."""
    global _generator_instance

    if _generator_instance is None:
        _generator_instance = FluxLocalGenerator(vram_mode=vram_mode)
    elif vram_mode != "auto" and _generator_instance.vram_mode != vram_mode:
        _generator_instance.unload()
        _generator_instance = FluxLocalGenerator(vram_mode=vram_mode)

    return _generator_instance


def unload_generator():
    """Descarrega o gerador singleton."""
    global _generator_instance
    if _generator_instance is not None:
        _generator_instance.unload()
        _generator_instance = None
