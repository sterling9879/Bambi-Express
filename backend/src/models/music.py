"""
Modelos de música e biblioteca.
"""

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from .config import MusicMood


class MusicTrack(BaseModel):
    """Representa uma música na biblioteca."""
    id: str
    filename: str
    original_name: str
    duration_ms: int
    mood: MusicMood
    tags: List[str] = []
    loop_start_ms: Optional[int] = None
    loop_end_ms: Optional[int] = None
    uploaded_at: datetime
    file_size: int
    waveform_data: Optional[List[float]] = None
    user_id: Optional[str] = None


class MusicTrackCreate(BaseModel):
    """Dados para upload de música."""
    original_name: str
    mood: MusicMood
    tags: List[str] = []
    loop_start_ms: Optional[int] = None
    loop_end_ms: Optional[int] = None


class MusicTrackUpdate(BaseModel):
    """Dados para atualização de música."""
    mood: Optional[MusicMood] = None
    tags: Optional[List[str]] = None
    loop_start_ms: Optional[int] = None
    loop_end_ms: Optional[int] = None


class MusicLibraryStats(BaseModel):
    """Estatísticas da biblioteca de música."""
    total_tracks: int
    total_duration_ms: int
    tracks_by_mood: dict
    total_size_bytes: int
