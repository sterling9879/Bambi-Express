"""
Modelos de vídeo e componentes do pipeline.
"""

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class TextChunk(BaseModel):
    """Representa um chunk de texto."""
    index: int
    text: str
    char_count: int


class AudioChunk(BaseModel):
    """Representa um chunk de áudio gerado."""
    index: int
    path: str
    duration_ms: int
    text: str


class MergedAudio(BaseModel):
    """Resultado da concatenação de áudio."""
    path: str
    duration_ms: int
    chunk_count: int


class Word(BaseModel):
    """Representa uma palavra com timestamps."""
    text: str
    start_ms: int
    end_ms: int
    confidence: float


class Segment(BaseModel):
    """Segmento de transcrição (frase/sentença)."""
    text: str
    start_ms: int
    end_ms: int
    words: List[Word]


class Paragraph(BaseModel):
    """Parágrafo da transcrição (retornado pela AssemblyAI)."""
    text: str
    start_ms: int
    end_ms: int


class TranscriptionResult(BaseModel):
    """Resultado completo da transcrição."""
    segments: List[Segment]
    words: List[Word]
    paragraphs: List[Paragraph] = []  # Parágrafos da AssemblyAI
    full_text: str
    duration_ms: int
    confidence: float
    language: str


class Scene(BaseModel):
    """Representa uma cena do vídeo."""
    scene_index: int
    text: str
    start_ms: int
    end_ms: int
    duration_ms: int
    image_prompt: str
    mood: str
    mood_intensity: float = 0.5
    is_mood_transition: bool = False


class MusicCue(BaseModel):
    """Ponto de mudança musical."""
    timestamp_ms: int
    mood: str
    suggestion: str


class SceneAnalysis(BaseModel):
    """Resultado da análise de cenas."""
    style_guide: str
    scenes: List[Scene]
    music_cues: List[MusicCue]


class GeneratedImage(BaseModel):
    """Imagem gerada."""
    scene_index: int
    image_path: str
    prompt_used: str
    generation_time_ms: int


class MusicSegment(BaseModel):
    """Segmento de música a ser aplicado."""
    music_path: str
    mood: str
    start_ms: int
    end_ms: int
    fade_in_ms: int
    fade_out_ms: int
    volume: float


class MixedAudio(BaseModel):
    """Resultado da mixagem."""
    path: str
    duration_ms: int


class VideoResult(BaseModel):
    """Resultado da composição de vídeo."""
    path: str
    duration_seconds: float
    scenes_count: int
    resolution: str
    file_size: int


class GeneratedMusic(BaseModel):
    """Música gerada por IA."""
    id: str
    audio_path: str
    duration_ms: int
    prompt_used: str
    style: str
    generation_time_ms: int
