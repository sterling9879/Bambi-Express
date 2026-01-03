"""
Router para gerenciamento de músicas.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
from datetime import datetime
import uuid
import shutil

from ..models.music import MusicTrack, MusicTrackCreate, MusicTrackUpdate, MusicLibraryStats
from ..models.config import MusicMood

router = APIRouter(prefix="/api/music", tags=["music"])

# Music library path
MUSIC_LIBRARY_PATH = Path("storage/music")
MUSIC_LIBRARY_PATH.mkdir(parents=True, exist_ok=True)

# In-memory track database (in production, use a real database)
_tracks_db: dict = {}


def _get_audio_duration(file_path: Path) -> int:
    """Get audio duration in milliseconds."""
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_file(file_path)
        return len(audio)
    except Exception:
        return 0


def _generate_waveform(file_path: Path) -> List[float]:
    """Generate waveform data for visualization."""
    try:
        from pydub import AudioSegment
        import struct

        audio = AudioSegment.from_file(file_path)
        # Reduce to mono and downsample for visualization
        audio = audio.set_channels(1)

        # Get raw data
        raw_data = audio.raw_data
        sample_width = audio.sample_width

        # Sample every N samples to get ~100 points
        total_samples = len(raw_data) // sample_width
        step = max(1, total_samples // 100)

        waveform = []
        for i in range(0, total_samples, step):
            offset = i * sample_width
            if sample_width == 2:
                sample = struct.unpack_from('<h', raw_data, offset)[0]
            else:
                sample = raw_data[offset]
            # Normalize to 0-1
            normalized = abs(sample) / (2 ** (8 * sample_width - 1))
            waveform.append(normalized)

        return waveform[:100]  # Limit to 100 points
    except Exception:
        return []


class PaginatedTracks(BaseModel):
    tracks: List[MusicTrack]
    total: int
    page: int
    limit: int


@router.get("", response_model=PaginatedTracks)
async def list_music(
    mood: Optional[MusicMood] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Lista todas as músicas do usuário.
    """
    # Scan music library and build track list
    tracks = []

    for mood_dir in MUSIC_LIBRARY_PATH.iterdir():
        if not mood_dir.is_dir():
            continue

        current_mood = mood_dir.name
        if mood and current_mood != mood.value:
            continue

        for track_file in mood_dir.iterdir():
            if track_file.suffix.lower() not in ['.mp3', '.wav', '.ogg']:
                continue

            track_id = track_file.stem

            # Check if we have cached metadata
            if track_id in _tracks_db:
                track = _tracks_db[track_id]
            else:
                # Build track metadata
                try:
                    track_mood = MusicMood(current_mood)
                except ValueError:
                    track_mood = MusicMood.NEUTRAL

                track = MusicTrack(
                    id=track_id,
                    filename=str(track_file.relative_to(MUSIC_LIBRARY_PATH)),
                    original_name=track_file.name,
                    duration_ms=_get_audio_duration(track_file),
                    mood=track_mood,
                    tags=[],
                    uploaded_at=datetime.fromtimestamp(track_file.stat().st_mtime),
                    file_size=track_file.stat().st_size
                )
                _tracks_db[track_id] = track

            # Apply search filter
            if search:
                search_lower = search.lower()
                if (search_lower not in track.original_name.lower() and
                    not any(search_lower in tag.lower() for tag in track.tags)):
                    continue

            tracks.append(track)

    # Sort by upload date (newest first)
    tracks.sort(key=lambda t: t.uploaded_at, reverse=True)

    # Paginate
    total = len(tracks)
    start = (page - 1) * limit
    end = start + limit
    paginated_tracks = tracks[start:end]

    return PaginatedTracks(
        tracks=paginated_tracks,
        total=total,
        page=page,
        limit=limit
    )


@router.post("/upload", response_model=MusicTrack)
async def upload_music(
    file: UploadFile = File(...),
    mood: MusicMood = Form(...),
    tags: str = Form("")  # Comma-separated tags
):
    """
    Upload de nova música.
    """
    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="Arquivo sem nome")

    ext = Path(file.filename).suffix.lower()
    if ext not in ['.mp3', '.wav', '.ogg']:
        raise HTTPException(
            status_code=400,
            detail="Formato não suportado. Use MP3, WAV ou OGG."
        )

    # Generate unique ID
    track_id = str(uuid.uuid4())[:8]

    # Create mood directory if needed
    mood_dir = MUSIC_LIBRARY_PATH / mood.value
    mood_dir.mkdir(parents=True, exist_ok=True)

    # Save file
    destination = mood_dir / f"{track_id}{ext}"
    with open(destination, "wb") as f:
        content = await file.read()
        f.write(content)

    # Parse tags
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    # Create track metadata
    track = MusicTrack(
        id=track_id,
        filename=str(destination.relative_to(MUSIC_LIBRARY_PATH)),
        original_name=file.filename,
        duration_ms=_get_audio_duration(destination),
        mood=mood,
        tags=tag_list,
        uploaded_at=datetime.now(),
        file_size=destination.stat().st_size,
        waveform_data=_generate_waveform(destination)
    )

    # Cache metadata
    _tracks_db[track_id] = track

    return track


@router.get("/{track_id}", response_model=MusicTrack)
async def get_music(track_id: str):
    """
    Obtém detalhes de uma música.
    """
    if track_id in _tracks_db:
        return _tracks_db[track_id]

    # Search in filesystem
    for mood_dir in MUSIC_LIBRARY_PATH.iterdir():
        if not mood_dir.is_dir():
            continue
        for track_file in mood_dir.iterdir():
            if track_file.stem == track_id:
                try:
                    track_mood = MusicMood(mood_dir.name)
                except ValueError:
                    track_mood = MusicMood.NEUTRAL

                track = MusicTrack(
                    id=track_id,
                    filename=str(track_file.relative_to(MUSIC_LIBRARY_PATH)),
                    original_name=track_file.name,
                    duration_ms=_get_audio_duration(track_file),
                    mood=track_mood,
                    tags=[],
                    uploaded_at=datetime.fromtimestamp(track_file.stat().st_mtime),
                    file_size=track_file.stat().st_size
                )
                _tracks_db[track_id] = track
                return track

    raise HTTPException(status_code=404, detail="Música não encontrada")


@router.put("/{track_id}", response_model=MusicTrack)
async def update_music(track_id: str, update: MusicTrackUpdate):
    """
    Atualiza metadados da música.
    """
    # Find the track
    track = None
    track_file = None

    for mood_dir in MUSIC_LIBRARY_PATH.iterdir():
        if not mood_dir.is_dir():
            continue
        for file in mood_dir.iterdir():
            if file.stem == track_id:
                track_file = file
                if track_id in _tracks_db:
                    track = _tracks_db[track_id]
                else:
                    try:
                        track_mood = MusicMood(mood_dir.name)
                    except ValueError:
                        track_mood = MusicMood.NEUTRAL

                    track = MusicTrack(
                        id=track_id,
                        filename=str(file.relative_to(MUSIC_LIBRARY_PATH)),
                        original_name=file.name,
                        duration_ms=_get_audio_duration(file),
                        mood=track_mood,
                        tags=[],
                        uploaded_at=datetime.fromtimestamp(file.stat().st_mtime),
                        file_size=file.stat().st_size
                    )
                break
        if track:
            break

    if not track or not track_file:
        raise HTTPException(status_code=404, detail="Música não encontrada")

    # Update fields
    if update.mood is not None:
        # Move file to new mood directory
        new_mood_dir = MUSIC_LIBRARY_PATH / update.mood.value
        new_mood_dir.mkdir(parents=True, exist_ok=True)
        new_path = new_mood_dir / track_file.name
        shutil.move(str(track_file), str(new_path))
        track.mood = update.mood
        track.filename = str(new_path.relative_to(MUSIC_LIBRARY_PATH))

    if update.tags is not None:
        track.tags = update.tags

    if update.loop_start_ms is not None:
        track.loop_start_ms = update.loop_start_ms

    if update.loop_end_ms is not None:
        track.loop_end_ms = update.loop_end_ms

    # Update cache
    _tracks_db[track_id] = track

    return track


@router.delete("/{track_id}")
async def delete_music(track_id: str):
    """
    Remove música.
    """
    # Find and delete the file
    for mood_dir in MUSIC_LIBRARY_PATH.iterdir():
        if not mood_dir.is_dir():
            continue
        for track_file in mood_dir.iterdir():
            if track_file.stem == track_id:
                track_file.unlink()
                if track_id in _tracks_db:
                    del _tracks_db[track_id]
                return {"status": "deleted", "id": track_id}

    raise HTTPException(status_code=404, detail="Música não encontrada")


@router.get("/{track_id}/waveform")
async def get_waveform(track_id: str):
    """
    Retorna dados de waveform para visualização.
    """
    if track_id in _tracks_db and _tracks_db[track_id].waveform_data:
        return {"waveform": _tracks_db[track_id].waveform_data}

    # Find the file and generate waveform
    for mood_dir in MUSIC_LIBRARY_PATH.iterdir():
        if not mood_dir.is_dir():
            continue
        for track_file in mood_dir.iterdir():
            if track_file.stem == track_id:
                waveform = _generate_waveform(track_file)
                return {"waveform": waveform}

    raise HTTPException(status_code=404, detail="Música não encontrada")


@router.get("/{track_id}/preview")
async def preview_music(track_id: str):
    """
    Retorna o arquivo de áudio para preview.
    """
    for mood_dir in MUSIC_LIBRARY_PATH.iterdir():
        if not mood_dir.is_dir():
            continue
        for track_file in mood_dir.iterdir():
            if track_file.stem == track_id:
                return FileResponse(
                    track_file,
                    media_type="audio/mpeg",
                    filename=track_file.name
                )

    raise HTTPException(status_code=404, detail="Música não encontrada")


@router.get("/stats", response_model=MusicLibraryStats)
async def get_library_stats():
    """
    Retorna estatísticas da biblioteca de música.
    """
    total_tracks = 0
    total_duration_ms = 0
    total_size_bytes = 0
    tracks_by_mood = {}

    for mood_dir in MUSIC_LIBRARY_PATH.iterdir():
        if not mood_dir.is_dir():
            continue

        mood_name = mood_dir.name
        mood_count = 0

        for track_file in mood_dir.iterdir():
            if track_file.suffix.lower() in ['.mp3', '.wav', '.ogg']:
                total_tracks += 1
                mood_count += 1
                total_size_bytes += track_file.stat().st_size
                total_duration_ms += _get_audio_duration(track_file)

        tracks_by_mood[mood_name] = mood_count

    return MusicLibraryStats(
        total_tracks=total_tracks,
        total_duration_ms=total_duration_ms,
        tracks_by_mood=tracks_by_mood,
        total_size_bytes=total_size_bytes
    )
