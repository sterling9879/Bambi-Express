"""
Modelos de configuração do sistema.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


# ============== ENUMS ==============


class TransitionType(str, Enum):
    FADE = "fade"
    WIPELEFT = "wipeleft"
    WIPERIGHT = "wiperight"
    SLIDEUP = "slideup"
    SLIDEDOWN = "slidedown"
    CIRCLEOPEN = "circleopen"
    CIRCLECLOSE = "circleclose"
    DISSOLVE = "dissolve"
    PIXELIZE = "pixelize"
    RADIAL = "radial"
    NONE = "none"


class MusicMood(str, Enum):
    ALEGRE = "alegre"
    ANIMADO = "animado"
    CALMO = "calmo"
    DRAMATICO = "dramatico"
    INSPIRADOR = "inspirador"
    MELANCOLICO = "melancolico"
    RAIVA = "raiva"
    ROMANTICO = "romantico"
    SOMBRIO = "sombrio"
    VIBRANTE = "vibrante"


class MusicMode(str, Enum):
    NONE = "none"
    LIBRARY = "library"
    AI_GENERATED = "ai_generated"


class AudioProvider(str, Enum):
    ELEVENLABS = "elevenlabs"
    MINIMAX = "minimax"


class SceneDurationMode(str, Enum):
    AUTO = "auto"
    FIXED = "fixed"
    RANGE = "range"


# ============== API CONFIGS ==============


class ApiConfigItem(BaseModel):
    api_key: str = ""
    enabled: bool = True


class ElevenLabsConfig(ApiConfigItem):
    voice_id: str = ""
    model_id: str = "eleven_multilingual_v2"


class AssemblyAIConfig(ApiConfigItem):
    language_code: str = "pt"


class GeminiConfig(ApiConfigItem):
    model: str = "gemini-2.0-flash"
    scene_context: str = ""  # Contexto visual para as imagens (ex: "futurista", "medieval")


class WaveSpeedConfig(ApiConfigItem):
    model: str = "flux-dev-ultra-fast"  # flux-dev-ultra-fast, flux-schnell, flux-dev
    resolution: str = "1920x1080"
    image_style: str = "cinematic, dramatic lighting, 8k, hyperrealistic, professional photography"
    output_format: str = "png"  # png ou jpeg


class SunoConfig(ApiConfigItem):
    pass


class CustomVoice(BaseModel):
    """Voz personalizada para Minimax."""
    id: str  # ID único interno
    voice_id: str  # ID da voz na API (ex: "Narrator_Man")
    name: str  # Nome de exibição
    gender: str = "neutral"  # male, female, neutral
    description: str = ""


class MinimaxConfig(BaseModel):
    """Configuração para Minimax Audio (via WaveSpeed)."""
    voice_id: str = "Narrator_Man"
    emotion: str = "neutral"  # neutral, happy, sad, angry, fearful, disgusted, surprised
    speed: float = 1.0  # 0.5 - 2.0
    pitch: int = 0  # -12 to 12
    volume: float = 1.0  # 0.0 - 1.0
    custom_voices: List[CustomVoice] = []


class ApiConfig(BaseModel):
    elevenlabs: ElevenLabsConfig = ElevenLabsConfig()
    assemblyai: AssemblyAIConfig = AssemblyAIConfig()
    gemini: GeminiConfig = GeminiConfig()
    wavespeed: WaveSpeedConfig = WaveSpeedConfig()
    suno: Optional[SunoConfig] = None
    minimax: MinimaxConfig = MinimaxConfig()
    audio_provider: AudioProvider = AudioProvider.ELEVENLABS


# ============== FFMPEG CONFIGS ==============


class Resolution(BaseModel):
    width: int = 1920
    height: int = 1080
    preset: Optional[str] = "1080p_landscape"


class SceneDurationConfig(BaseModel):
    mode: SceneDurationMode = SceneDurationMode.AUTO
    fixed_duration: Optional[float] = 4.0
    min_duration: Optional[float] = 3.0
    max_duration: Optional[float] = 6.0


class SceneSplitMode(str, Enum):
    """Modo de divisão de cenas."""
    PARAGRAPHS = "paragraphs"  # Baseado em parágrafos da AssemblyAI (menos cenas)
    SENTENCES = "sentences"  # Baseado em pontuação/sentenças (mais cenas)
    GEMINI = "gemini"  # Gemini decide (pode alucinar)


class SceneConfig(BaseModel):
    """Configuração de como as cenas são divididas."""
    split_mode: SceneSplitMode = SceneSplitMode.SENTENCES  # Padrão: sentenças (mais controle)
    paragraphs_per_scene: int = Field(default=3, ge=1, le=10)  # Quantos parágrafos por cena
    sentences_per_scene: int = Field(default=2, ge=1, le=10)  # Quantas sentenças por cena


class TransitionConfig(BaseModel):
    type: TransitionType = TransitionType.FADE
    duration: float = Field(default=0.5, ge=0.1, le=2.0)
    vary: bool = False
    allowed_types: Optional[List[TransitionType]] = None


class KenBurnsConfig(BaseModel):
    enabled: bool = True
    intensity: float = Field(default=0.05, ge=0, le=0.2)
    direction: str = "alternate"


class VignetteConfig(BaseModel):
    enabled: bool = False
    intensity: float = Field(default=0.3, ge=0, le=1)


class GrainConfig(BaseModel):
    enabled: bool = False
    intensity: float = Field(default=0.1, ge=0, le=0.5)


class EffectsConfig(BaseModel):
    ken_burns: KenBurnsConfig = KenBurnsConfig()
    vignette: VignetteConfig = VignetteConfig()
    grain: GrainConfig = GrainConfig()


class AudioConfig(BaseModel):
    codec: str = "aac"
    bitrate: int = 192
    narration_volume: float = Field(default=1.0, ge=0, le=2)
    normalize: bool = True
    target_lufs: int = -14


class FFmpegConfig(BaseModel):
    resolution: Resolution = Resolution()
    fps: int = 30
    crf: int = Field(default=23, ge=18, le=28)
    preset: str = "medium"
    scene_config: SceneConfig = SceneConfig()
    scene_duration: SceneDurationConfig = SceneDurationConfig()
    transition: TransitionConfig = TransitionConfig()
    effects: EffectsConfig = EffectsConfig()
    audio: AudioConfig = AudioConfig()


# ============== MUSIC CONFIGS ==============


class AIMusicConfig(BaseModel):
    style_prompt: str = ""
    preset: Optional[str] = None
    generate_variations: bool = False
    variations_count: int = 3
    instrumental_only: bool = True


class MusicConfig(BaseModel):
    mode: MusicMode = MusicMode.NONE
    volume: float = Field(default=0.08, ge=0, le=1)  # Reduzido de 0.15 para 0.08
    ducking_enabled: bool = True
    ducking_intensity: float = Field(default=0.9, ge=0, le=1)  # Aumentado para ducking mais agressivo
    fade_in_ms: int = 1000
    fade_out_ms: int = 2000
    crossfade_ms: int = 1500
    auto_select_by_mood: bool = True
    manual_track_id: Optional[str] = None
    secondary_track_id: Optional[str] = None
    ai_config: Optional[AIMusicConfig] = None


# ============== GPU / LOCAL IMAGE GENERATION ==============


class ImageProvider(str, Enum):
    WAVESPEED = "wavespeed"
    LOCAL = "local"


class WaveSpeedModel(str, Enum):
    """Modelos disponíveis no WaveSpeed para geração de imagens."""
    FLUX_DEV_ULTRA_FAST = "flux-dev-ultra-fast"  # Alta qualidade, mais lento
    FLUX_SCHNELL = "flux-schnell"  # Rápido, menor qualidade
    FLUX_DEV = "flux-dev"  # Balanço entre qualidade e velocidade


class VramMode(str, Enum):
    AUTO = "auto"
    VRAM_4GB = "4gb"
    VRAM_6GB = "6gb"
    VRAM_8GB = "8gb"


class GPUConfig(BaseModel):
    """Configuracao para geracao de imagens local com GPU."""
    enabled: bool = False
    provider: ImageProvider = ImageProvider.WAVESPEED
    vram_mode: VramMode = VramMode.AUTO
    auto_fallback_to_api: bool = True  # Se local falhar, usa WaveSpeed


# ============== VIDEO EFFECTS ==============


class EffectsConfig(BaseModel):
    """Configuração para efeitos de overlay em vídeos."""
    enabled: bool = False
    effect_id: Optional[str] = None  # ID do efeito selecionado
    blend_mode: str = "lighten"  # lighten, screen, add
    opacity: float = 1.0  # 0.0 a 1.0


# ============== SUBTITLES ==============


class SubtitlePosition(str, Enum):
    """Posição das legendas no vídeo."""
    BOTTOM = "bottom"  # Estilo filme tradicional
    TOP = "top"
    MIDDLE = "middle"


class SubtitleLanguage(str, Enum):
    """Idioma das legendas."""
    PT = "pt"  # Português
    EN = "en"  # English
    ES = "es"  # Español
    AUTO = "auto"  # Auto-detectar (usar idioma do áudio)


class SubtitleConfig(BaseModel):
    """Configuração para legendas estilo filme."""
    enabled: bool = False
    language: SubtitleLanguage = SubtitleLanguage.AUTO
    position: SubtitlePosition = SubtitlePosition.BOTTOM
    font_size: int = 48  # Tamanho da fonte
    font_color: str = "white"  # Cor do texto
    outline_color: str = "black"  # Cor do contorno
    outline_width: int = 3  # Espessura do contorno
    background_opacity: float = 0.0  # Opacidade do fundo (0 = sem fundo)
    margin_vertical: int = 50  # Margem vertical em pixels


# ============== FULL CONFIG ==============


class FullConfig(BaseModel):
    api: ApiConfig = ApiConfig()
    music: MusicConfig = MusicConfig()
    ffmpeg: FFmpegConfig = FFmpegConfig()
    gpu: GPUConfig = GPUConfig()
    effects: EffectsConfig = EffectsConfig()
    subtitles: SubtitleConfig = SubtitleConfig()
