"""
Models package for the video generator.
"""

from .config import (
    ApiConfig,
    ElevenLabsConfig,
    AssemblyAIConfig,
    GeminiConfig,
    WaveSpeedConfig,
    SunoConfig,
    FFmpegConfig,
    MusicConfig,
    FullConfig,
    TransitionType,
    MusicMood,
    MusicMode,
    SceneDurationMode,
)
from .video import (
    TextChunk,
    AudioChunk,
    MergedAudio,
    TranscriptionResult,
    Word,
    Segment,
    Scene,
    SceneAnalysis,
    MusicCue,
    GeneratedImage,
    MusicSegment,
    MixedAudio,
    VideoResult,
)
from .job import JobStatus, JobCreate, JobResponse
from .music import MusicTrack, MusicTrackCreate, MusicTrackUpdate

__all__ = [
    # Config
    "ApiConfig",
    "ElevenLabsConfig",
    "AssemblyAIConfig",
    "GeminiConfig",
    "WaveSpeedConfig",
    "SunoConfig",
    "FFmpegConfig",
    "MusicConfig",
    "FullConfig",
    "TransitionType",
    "MusicMood",
    "MusicMode",
    "SceneDurationMode",
    # Video
    "TextChunk",
    "AudioChunk",
    "MergedAudio",
    "TranscriptionResult",
    "Word",
    "Segment",
    "Scene",
    "SceneAnalysis",
    "MusicCue",
    "GeneratedImage",
    "MusicSegment",
    "MixedAudio",
    "VideoResult",
    # Job
    "JobStatus",
    "JobCreate",
    "JobResponse",
    # Music
    "MusicTrack",
    "MusicTrackCreate",
    "MusicTrackUpdate",
]
