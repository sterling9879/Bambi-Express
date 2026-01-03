"""
Modelos para histórico de vídeos e elementos.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ElementType(str, Enum):
    IMAGE = "image"
    AUDIO = "audio"
    NARRATION = "narration"
    MUSIC = "music"


# ============== CHANNEL ==============


class ChannelBase(BaseModel):
    name: str
    description: Optional[str] = ""
    color: str = "#3B82F6"  # Default blue


class ChannelCreate(ChannelBase):
    pass


class ChannelUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None


class Channel(ChannelBase):
    id: str
    created_at: datetime
    video_count: int = 0


# ============== VIDEO HISTORY ==============


class VideoHistoryBase(BaseModel):
    title: str
    channel_id: Optional[str] = None
    text_preview: str = ""  # First 200 chars of the text


class VideoHistoryCreate(VideoHistoryBase):
    job_id: str
    video_path: str
    duration_seconds: float
    scenes_count: int
    file_size: int
    resolution: str


class VideoHistory(VideoHistoryBase):
    id: str
    job_id: str
    video_path: str
    video_url: Optional[str] = None
    thumbnail_path: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration_seconds: float
    scenes_count: int
    file_size: int
    resolution: str
    created_at: datetime
    channel_name: Optional[str] = None


class VideoHistoryList(BaseModel):
    videos: List[VideoHistory]
    total: int
    page: int
    limit: int


# ============== ELEMENT HISTORY ==============


class ElementBase(BaseModel):
    job_id: str
    element_type: ElementType
    file_path: str


class ElementCreate(ElementBase):
    scene_index: Optional[int] = None
    prompt: Optional[str] = None
    duration_ms: Optional[int] = None
    metadata: Optional[dict] = None


class Element(ElementBase):
    id: str
    scene_index: Optional[int] = None
    prompt: Optional[str] = None
    duration_ms: Optional[int] = None
    file_url: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: datetime


class ElementList(BaseModel):
    elements: List[Element]
    total: int


# ============== STATS ==============


class HistoryStats(BaseModel):
    total_videos: int
    total_duration_seconds: float
    total_size_bytes: int
    videos_by_channel: dict
    recent_videos: List[VideoHistory]
