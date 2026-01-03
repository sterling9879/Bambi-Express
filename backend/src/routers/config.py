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
    FFmpegConfig,
    MusicConfig,
)
from ..services.audio_generator import ElevenLabsGenerator
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
    api: Literal["elevenlabs", "assemblyai", "gemini", "wavespeed", "suno"]


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
