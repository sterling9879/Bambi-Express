"""
Router para configurações do sistema.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Literal
import os
import json
from pathlib import Path

from ..models.config import (
    FullConfig,
    ApiConfig,
    ElevenLabsConfig,
    AssemblyAIConfig,
    GeminiConfig,
    WaveSpeedConfig,
    SunoConfig,
    MinimaxConfig,
    CustomVoice,
    FFmpegConfig,
    MusicConfig,
)
from ..services.audio_generator import ElevenLabsGenerator, MinimaxAudioGenerator
from ..services.transcriber import AssemblyAITranscriber
from ..services.scene_analyzer import SceneAnalyzer
from ..services.image_generator import WaveSpeedGenerator

router = APIRouter(prefix="/api/config", tags=["config"])

# Config file path
CONFIG_FILE = Path("storage/config.json")


def get_config() -> FullConfig:
    """Load configuration from file or return defaults."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                data = json.load(f)
                return FullConfig(**data)
        except Exception:
            pass
    return FullConfig()


def save_config(config: FullConfig):
    """Save configuration to file."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config.model_dump(), f, indent=2)


@router.get("", response_model=FullConfig)
async def get_configuration():
    """
    Retorna configurações atuais do usuário.
    """
    return get_config()


@router.put("", response_model=FullConfig)
async def update_configuration(config: FullConfig):
    """
    Atualiza configurações do usuário.
    """
    save_config(config)
    return config


@router.patch("/api", response_model=ApiConfig)
async def update_api_config(api_config: ApiConfig):
    """
    Atualiza apenas configurações de API.
    """
    config = get_config()
    config.api = api_config
    save_config(config)
    return config.api


@router.patch("/music", response_model=MusicConfig)
async def update_music_config(music_config: MusicConfig):
    """
    Atualiza apenas configurações de música.
    """
    config = get_config()
    config.music = music_config
    save_config(config)
    return config.music


@router.patch("/ffmpeg", response_model=FFmpegConfig)
async def update_ffmpeg_config(ffmpeg_config: FFmpegConfig):
    """
    Atualiza apenas configurações de FFMPEG.
    """
    config = get_config()
    config.ffmpeg = ffmpeg_config
    save_config(config)
    return config.ffmpeg


class TestApiRequest(BaseModel):
    api: Literal["elevenlabs", "assemblyai", "gemini", "wavespeed", "suno", "minimax"]


class TestApiResponse(BaseModel):
    connected: bool
    error: Optional[str] = None
    details: Optional[dict] = None


@router.post("/test-api", response_model=TestApiResponse)
async def test_api_connection(request: TestApiRequest):
    """
    Testa conexão com uma API específica.
    """
    config = get_config()

    try:
        if request.api == "elevenlabs":
            if not config.api.elevenlabs.api_key:
                return TestApiResponse(connected=False, error="API key não configurada")

            generator = ElevenLabsGenerator(
                api_key=config.api.elevenlabs.api_key,
                voice_id=config.api.elevenlabs.voice_id or "default"
            )
            result = await generator.test_connection()
            return TestApiResponse(
                connected=result.get("connected", False),
                error=result.get("error"),
                details=result
            )

        elif request.api == "assemblyai":
            if not config.api.assemblyai.api_key:
                return TestApiResponse(connected=False, error="API key não configurada")

            transcriber = AssemblyAITranscriber(
                api_key=config.api.assemblyai.api_key
            )
            result = await transcriber.test_connection()
            return TestApiResponse(
                connected=result.get("connected", False),
                error=result.get("error"),
                details=result
            )

        elif request.api == "gemini":
            if not config.api.gemini.api_key:
                return TestApiResponse(connected=False, error="API key não configurada")

            analyzer = SceneAnalyzer(
                api_key=config.api.gemini.api_key,
                model=config.api.gemini.model
            )
            result = await analyzer.test_connection()
            return TestApiResponse(
                connected=result.get("connected", False),
                error=result.get("error"),
                details=result
            )

        elif request.api == "wavespeed":
            if not config.api.wavespeed.api_key:
                return TestApiResponse(connected=False, error="API key não configurada")

            generator = WaveSpeedGenerator(
                api_key=config.api.wavespeed.api_key,
                model=config.api.wavespeed.model
            )
            result = await generator.test_connection()
            return TestApiResponse(
                connected=result.get("connected", False),
                error=result.get("error"),
                details=result
            )

        elif request.api == "suno":
            if not config.api.suno or not config.api.suno.api_key:
                return TestApiResponse(connected=False, error="API key não configurada")

            from ..services.ai_music_generator import AIMusicGenerator
            generator = AIMusicGenerator(api_key=config.api.suno.api_key)
            result = await generator.test_connection()
            return TestApiResponse(
                connected=result.get("connected", False),
                error=result.get("error"),
                details=result
            )

        elif request.api == "minimax":
            # Minimax usa a API key do WaveSpeed
            if not config.api.wavespeed.api_key:
                return TestApiResponse(connected=False, error="WaveSpeed API key não configurada (necessária para Minimax)")

            generator = MinimaxAudioGenerator(
                api_key=config.api.wavespeed.api_key,
                voice_id=config.api.minimax.voice_id if config.api.minimax else "Narrator_Man"
            )
            result = await generator.test_connection()
            return TestApiResponse(
                connected=result.get("connected", False),
                error=result.get("error"),
                details=result
            )

        else:
            return TestApiResponse(connected=False, error=f"API desconhecida: {request.api}")

    except Exception as e:
        return TestApiResponse(connected=False, error=str(e))


class CreditsResponse(BaseModel):
    elevenlabs: Optional[int] = None
    wavespeed: Optional[float] = None
    errors: dict = {}


@router.get("/credits", response_model=CreditsResponse)
async def get_credits():
    """
    Retorna créditos disponíveis de cada API.
    """
    config = get_config()
    response = CreditsResponse()

    # ElevenLabs credits
    if config.api.elevenlabs.api_key:
        try:
            generator = ElevenLabsGenerator(
                api_key=config.api.elevenlabs.api_key,
                voice_id=config.api.elevenlabs.voice_id or "default"
            )
            response.elevenlabs = await generator.get_remaining_credits()
        except Exception as e:
            response.errors["elevenlabs"] = str(e)

    # WaveSpeed credits
    if config.api.wavespeed.api_key:
        try:
            generator = WaveSpeedGenerator(
                api_key=config.api.wavespeed.api_key
            )
            response.wavespeed = await generator.get_remaining_credits()
        except Exception as e:
            response.errors["wavespeed"] = str(e)

    return response


class VoicesResponse(BaseModel):
    voices: list


@router.get("/voices", response_model=VoicesResponse)
async def get_available_voices():
    """
    Lista vozes disponíveis no ElevenLabs.
    """
    config = get_config()

    if not config.api.elevenlabs.api_key:
        raise HTTPException(status_code=400, detail="ElevenLabs API key não configurada")

    try:
        generator = ElevenLabsGenerator(
            api_key=config.api.elevenlabs.api_key,
            voice_id="default"
        )
        voices = await generator.get_available_voices()
        return VoicesResponse(voices=voices)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/minimax-voices", response_model=VoicesResponse)
async def get_minimax_voices():
    """
    Lista vozes disponíveis no Minimax.
    """
    # Minimax tem vozes predefinidas, não precisa de API key
    voices = MinimaxAudioGenerator.AVAILABLE_VOICES
    return VoicesResponse(voices=voices)


@router.get("/minimax-emotions")
async def get_minimax_emotions():
    """
    Lista emoções disponíveis no Minimax.
    """
    return {"emotions": MinimaxAudioGenerator.AVAILABLE_EMOTIONS}


# ============== CUSTOM VOICES MANAGEMENT ==============


class CustomVoiceCreate(BaseModel):
    voice_id: str
    name: str
    gender: str = "neutral"
    description: str = ""


class CustomVoiceUpdate(BaseModel):
    voice_id: Optional[str] = None
    name: Optional[str] = None
    gender: Optional[str] = None
    description: Optional[str] = None


@router.get("/custom-voices")
async def get_custom_voices():
    """
    Lista todas as vozes personalizadas do Minimax.
    """
    config = get_config()
    custom_voices = config.api.minimax.custom_voices if config.api.minimax else []
    # Também inclui as vozes padrão
    default_voices = MinimaxAudioGenerator.AVAILABLE_VOICES
    return {
        "custom_voices": [v.model_dump() for v in custom_voices],
        "default_voices": default_voices
    }


@router.post("/custom-voices")
async def create_custom_voice(voice: CustomVoiceCreate):
    """
    Adiciona uma nova voz personalizada.
    """
    import uuid
    config = get_config()

    # Criar nova voz com ID único
    new_voice = CustomVoice(
        id=str(uuid.uuid4())[:8],
        voice_id=voice.voice_id,
        name=voice.name,
        gender=voice.gender,
        description=voice.description
    )

    # Adicionar à lista
    if not config.api.minimax:
        config.api.minimax = MinimaxConfig()
    config.api.minimax.custom_voices.append(new_voice)

    save_config(config)
    return new_voice.model_dump()


@router.put("/custom-voices/{voice_id}")
async def update_custom_voice(voice_id: str, update: CustomVoiceUpdate):
    """
    Atualiza uma voz personalizada existente.
    """
    config = get_config()

    if not config.api.minimax:
        raise HTTPException(status_code=404, detail="Voz não encontrada")

    # Encontrar e atualizar a voz
    for voice in config.api.minimax.custom_voices:
        if voice.id == voice_id:
            if update.voice_id is not None:
                voice.voice_id = update.voice_id
            if update.name is not None:
                voice.name = update.name
            if update.gender is not None:
                voice.gender = update.gender
            if update.description is not None:
                voice.description = update.description

            save_config(config)
            return voice.model_dump()

    raise HTTPException(status_code=404, detail="Voz não encontrada")


@router.delete("/custom-voices/{voice_id}")
async def delete_custom_voice(voice_id: str):
    """
    Remove uma voz personalizada.
    """
    config = get_config()

    if not config.api.minimax:
        raise HTTPException(status_code=404, detail="Voz não encontrada")

    # Encontrar e remover a voz
    original_len = len(config.api.minimax.custom_voices)
    config.api.minimax.custom_voices = [
        v for v in config.api.minimax.custom_voices if v.id != voice_id
    ]

    if len(config.api.minimax.custom_voices) == original_len:
        raise HTTPException(status_code=404, detail="Voz não encontrada")

    save_config(config)
    return {"deleted": True, "voice_id": voice_id}


# ============== GPU / LOCAL IMAGE GENERATION ==============


class GPUInfoResponse(BaseModel):
    available: bool
    name: Optional[str] = None
    vram_total_gb: Optional[float] = None
    vram_free_gb: Optional[float] = None
    compute_capability: Optional[str] = None
    recommended_mode: Optional[str] = None
    error: Optional[str] = None


class ImageProviderRequest(BaseModel):
    provider: Literal["local", "wavespeed"]
    vram_mode: str = "auto"  # "4gb", "6gb", "8gb", "auto"


class ModelInfoResponse(BaseModel):
    mode: str
    model_name: str
    hf_id: str
    width: Optional[int] = None
    height: Optional[int] = None
    resolution: Optional[str] = None
    max_resolution: Optional[int] = None  # Backwards compat
    default_steps: int
    loaded: bool
    quantized: bool


class TestGenerationResponse(BaseModel):
    status: str
    time_seconds: float
    image_size_bytes: int
    model: ModelInfoResponse


@router.get("/gpu", response_model=GPUInfoResponse)
async def get_gpu_config():
    """Retorna informacoes da GPU disponivel."""
    try:
        from ..services.flux_local import get_gpu_info
        info = get_gpu_info()
        return GPUInfoResponse(**info)
    except Exception as e:
        return GPUInfoResponse(available=False, error=str(e))


@router.get("/gpu/models")
async def list_available_models():
    """Lista todos os modelos disponiveis por VRAM."""
    from ..services.flux_local import MODELS_CONFIG

    return {
        mode: {
            "name": config["name"],
            "hf_id": config["hf_id"],
            "width": config["width"],
            "height": config["height"],
            "resolution": f"{config['width']}x{config['height']}",
            "default_steps": config["default_steps"],
            "vram_required": mode,
            "quantized": config.get("quantized", False),
        }
        for mode, config in MODELS_CONFIG.items()
    }


@router.post("/image-provider")
async def set_image_provider(request: ImageProviderRequest):
    """Configura o provider de imagens (local ou wavespeed)."""
    config = get_config()

    if request.provider == "local":
        try:
            from ..services.flux_local import get_generator
            generator = get_generator(request.vram_mode)
            generator.load_model()  # Pre-carrega o modelo

            # Atualizar config
            config.gpu.provider = "local"
            config.gpu.vram_mode = request.vram_mode
            config.gpu.enabled = True
            save_config(config)

            return {
                "status": "ok",
                "provider": "local",
                "model": generator.get_model_info()
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        # Descarregar modelo local se estiver carregado
        try:
            from ..services.flux_local import unload_generator
            unload_generator()
        except Exception:
            pass

        config.gpu.provider = "wavespeed"
        config.gpu.enabled = False
        save_config(config)

        return {"status": "ok", "provider": "wavespeed"}


@router.post("/gpu/load-model", response_model=ModelInfoResponse)
async def load_local_model(vram_mode: str = "auto"):
    """Carrega modelo local na GPU."""
    try:
        from ..services.flux_local import get_generator
        generator = get_generator(vram_mode)
        generator.load_model()

        info = generator.get_model_info()
        return ModelInfoResponse(**info)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/gpu/unload-model")
async def unload_local_model():
    """Descarrega modelo da GPU para liberar memoria."""
    try:
        from ..services.flux_local import unload_generator
        unload_generator()
        return {"status": "unloaded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/gpu/test-generation")
async def test_generation(prompt: str = "A beautiful sunset over mountains, cinematic lighting, 8k"):
    """Testa geracao de imagem local."""
    try:
        from ..services.flux_local import get_generator
        import time

        generator = get_generator()
        if not generator.pipe:
            generator.load_model()

        start = time.time()
        image_bytes = await generator.generate(prompt, width=512, height=512)
        elapsed = time.time() - start

        return {
            "status": "ok",
            "time_seconds": round(elapsed, 2),
            "image_size_bytes": len(image_bytes),
            "model": generator.get_model_info()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
