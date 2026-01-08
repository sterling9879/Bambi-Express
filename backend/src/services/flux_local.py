"""
Modulo de geracao de imagens local usando Flux/SDXL.
Suporta GPUs com 4GB, 6GB e 8GB de VRAM.

Modelos:
- 4GB: SDXL Turbo (stabilityai/sdxl-turbo) - 512x512
- 6GB: Flux Schnell NF4 (sayakpaul/flux.1-schnell-nf4-pkg) - 768x768
- 8GB: Flux Schnell Full (black-forest-labs/FLUX.1-schnell) - 1024x1024
"""

import gc
import io
import time
import asyncio
import logging
from typing import Optional, Literal
from pathlib import Path

logger = logging.getLogger(__name__)

# Constantes dos modelos
MODELS_CONFIG = {
    "4gb": {
        "name": "SDXL Turbo",
        "hf_id": "stabilityai/sdxl-turbo",
        "pipeline_class": "AutoPipelineForText2Image",
        "torch_dtype": "float16",
        "variant": "fp16",
        "default_steps": 1,
        "guidance_scale": 0.0,
        "max_resolution": 512,
        "quantized": False,
    },
    "6gb": {
        "name": "Flux Schnell NF4",
        "hf_id": "sayakpaul/flux.1-schnell-nf4-pkg",
        "hf_id_base": "black-forest-labs/FLUX.1-schnell",
        "pipeline_class": "FluxPipeline",
        "torch_dtype": "bfloat16",
        "default_steps": 4,
        "guidance_scale": 0.0,
        "max_resolution": 768,
        "quantized": True,
        "max_sequence_length": 256,
    },
    "8gb": {
        "name": "Flux Schnell NF4 Full",
        "hf_id": "black-forest-labs/FLUX.1-schnell",
        "pipeline_class": "FluxPipeline",
        "torch_dtype": "bfloat16",
        "default_steps": 4,
        "guidance_scale": 0.0,
        "max_resolution": 1024,
        "quantized": True,
        "max_sequence_length": 256,
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
    """
    Detecta VRAM disponivel e retorna o modo recomendado.

    Returns:
        "4gb", "6gb" ou "8gb"

    Raises:
        RuntimeError: Se CUDA nao estiver disponivel ou VRAM insuficiente
    """
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
    """
    Gerador de imagens local com suporte a multiplos modelos.

    Args:
        vram_mode: "4gb", "6gb", "8gb" ou "auto" (detecta automaticamente)
        device: "cuda" ou "cpu"
    """

    def __init__(
        self,
        vram_mode: Literal["4gb", "6gb", "8gb", "auto"] = "auto",
        device: str = "cuda"
    ):
        self.device = device
        self.pipe = None
        self.current_mode = None
        self._torch = None

        # Detectar modo se auto
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
        """Carrega o modelo apropriado para o modo de VRAM."""

        if self.pipe is not None and self.current_mode == self.vram_mode:
            logger.info("Modelo ja carregado")
            return

        # Limpar modelo anterior
        if self.pipe is not None:
            del self.pipe
            self.pipe = None
            flush_memory()

        logger.info(f"Carregando modelo: {self.config['name']}...")

        if self.vram_mode == "4gb":
            self._load_sdxl_turbo()
        elif self.vram_mode == "6gb":
            self._load_flux_6gb()
        elif self.vram_mode == "8gb":
            self._load_flux_8gb()

        self.current_mode = self.vram_mode
        flush_memory()
        logger.info("Modelo carregado com sucesso!")

    def _load_sdxl_turbo(self):
        """Carrega SDXL Turbo para 4GB VRAM."""
        from diffusers import AutoPipelineForText2Image

        torch = self._get_torch()

        self.pipe = AutoPipelineForText2Image.from_pretrained(
            self.config["hf_id"],
            torch_dtype=self._get_torch_dtype(self.config["torch_dtype"]),
            variant=self.config["variant"],
            safety_checker=None,
        )
        self.pipe.to(self.device)

        # Otimizacoes
        if hasattr(self.pipe, 'enable_attention_slicing'):
            self.pipe.enable_attention_slicing()

    def _load_flux_6gb(self):
        """Carrega Flux Schnell NF4 pre-quantizado para 6GB VRAM."""
        from diffusers import FluxPipeline, FluxTransformer2DModel
        from transformers import T5EncoderModel
        from diffusers import BitsAndBytesConfig as DiffusersBnBConfig
        from transformers import BitsAndBytesConfig as TransformersBnBConfig

        torch = self._get_torch()

        # Config quantizacao
        quant_config_t5 = TransformersBnBConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16
        )

        quant_config_transformer = DiffusersBnBConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16
        )

        # Carregar componentes quantizados
        text_encoder_2 = T5EncoderModel.from_pretrained(
            self.config["hf_id"],
            subfolder="text_encoder_2",
            quantization_config=quant_config_t5,
            torch_dtype=torch.bfloat16,
            device_map="auto"
        )

        transformer = FluxTransformer2DModel.from_pretrained(
            self.config["hf_id"],
            subfolder="transformer",
            quantization_config=quant_config_transformer,
            torch_dtype=torch.bfloat16,
            device_map="auto"
        )

        # Pipeline completo
        self.pipe = FluxPipeline.from_pretrained(
            self.config["hf_id_base"],
            transformer=transformer,
            text_encoder_2=text_encoder_2,
            torch_dtype=torch.bfloat16,
        )
        self.pipe.enable_model_cpu_offload()

    def _load_flux_8gb(self):
        """Carrega Flux Schnell com quantizacao on-the-fly para 8GB VRAM."""
        from diffusers import FluxPipeline, FluxTransformer2DModel
        from transformers import T5EncoderModel
        from diffusers import BitsAndBytesConfig as DiffusersBnBConfig
        from transformers import BitsAndBytesConfig as TransformersBnBConfig

        torch = self._get_torch()

        # Config quantizacao
        quant_config_t5 = TransformersBnBConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16
        )

        quant_config_transformer = DiffusersBnBConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16
        )

        # Carregar T5 quantizado
        text_encoder_2 = T5EncoderModel.from_pretrained(
            self.config["hf_id"],
            subfolder="text_encoder_2",
            quantization_config=quant_config_t5,
            torch_dtype=torch.bfloat16,
        )

        # Carregar transformer quantizado
        transformer = FluxTransformer2DModel.from_pretrained(
            self.config["hf_id"],
            subfolder="transformer",
            quantization_config=quant_config_transformer,
            torch_dtype=torch.bfloat16,
        )

        # Montar pipeline
        self.pipe = FluxPipeline.from_pretrained(
            self.config["hf_id"],
            transformer=transformer,
            text_encoder_2=text_encoder_2,
            torch_dtype=torch.bfloat16,
        )

        # Otimizacoes
        self.pipe.enable_model_cpu_offload()
        if hasattr(self.pipe, 'vae'):
            self.pipe.vae.enable_slicing()
            self.pipe.vae.enable_tiling()

    async def generate(
        self,
        prompt: str,
        width: Optional[int] = None,
        height: Optional[int] = None,
        num_inference_steps: Optional[int] = None,
        seed: Optional[int] = None,
    ) -> bytes:
        """
        Gera uma imagem a partir do prompt.

        Args:
            prompt: Texto descrevendo a imagem
            width: Largura (usa max_resolution do modelo se None)
            height: Altura (usa max_resolution do modelo se None)
            num_inference_steps: Numero de steps (usa default do modelo se None)
            seed: Seed para reprodutibilidade

        Returns:
            bytes: Imagem em formato PNG
        """
        # Carregar modelo se necessario
        if self.pipe is None:
            self.load_model()

        torch = self._get_torch()

        # Defaults baseados no modelo
        max_res = self.config["max_resolution"]
        width = min(width or max_res, max_res)
        height = min(height or max_res, max_res)
        steps = num_inference_steps or self.config["default_steps"]
        guidance = self.config["guidance_scale"]

        # Generator para seed
        generator = None
        if seed is not None:
            generator = torch.Generator(device=self.device).manual_seed(seed)

        # Parametros de geracao
        gen_kwargs = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "num_inference_steps": steps,
            "guidance_scale": guidance,
            "generator": generator,
        }

        # Adicionar max_sequence_length para Flux
        if "max_sequence_length" in self.config:
            gen_kwargs["max_sequence_length"] = self.config["max_sequence_length"]

        # Gerar em thread separada para nao bloquear
        def _generate():
            with torch.inference_mode():
                result = self.pipe(**gen_kwargs)
                return result.images[0]

        image = await asyncio.to_thread(_generate)

        # Converter para bytes PNG
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
        """
        Gera uma imagem e salva em arquivo.

        Args:
            prompt: Texto descrevendo a imagem
            output_path: Caminho para salvar a imagem
            width: Largura (usa max_resolution do modelo se None)
            height: Altura (usa max_resolution do modelo se None)
            num_inference_steps: Numero de steps (usa default do modelo se None)
            seed: Seed para reprodutibilidade

        Returns:
            str: Caminho do arquivo salvo
        """
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
            "max_resolution": self.config["max_resolution"],
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


# Singleton para reuso
_generator_instance: Optional[FluxLocalGenerator] = None


def get_generator(vram_mode: str = "auto") -> FluxLocalGenerator:
    """
    Obtem instancia singleton do gerador.

    Args:
        vram_mode: "4gb", "6gb", "8gb" ou "auto"

    Returns:
        FluxLocalGenerator instance
    """
    global _generator_instance

    if _generator_instance is None:
        _generator_instance = FluxLocalGenerator(vram_mode=vram_mode)
    elif vram_mode != "auto" and _generator_instance.vram_mode != vram_mode:
        # Modo diferente solicitado, recriar
        _generator_instance.unload()
        _generator_instance = FluxLocalGenerator(vram_mode=vram_mode)

    return _generator_instance


def unload_generator():
    """Descarrega o gerador singleton."""
    global _generator_instance
    if _generator_instance is not None:
        _generator_instance.unload()
        _generator_instance = None
