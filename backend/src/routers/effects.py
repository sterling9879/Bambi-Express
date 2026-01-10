"""
API endpoints para gerenciamento de efeitos de vídeo.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
from pathlib import Path

from ..services.effects_manager import get_effects_manager, VideoEffect

router = APIRouter(prefix="/api/effects", tags=["effects"])


class EffectResponse(BaseModel):
    id: str
    name: str
    filename: str
    duration_ms: int
    description: str
    category: str
    thumbnail_url: Optional[str]
    created_at: str
    file_size: int


class EffectCreateRequest(BaseModel):
    name: str
    description: str = ""
    category: str = "geral"


class EffectUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None


def effect_to_response(effect: VideoEffect) -> EffectResponse:
    """Converte VideoEffect para response."""
    thumbnail_url = None
    if effect.thumbnail_path:
        thumbnail_url = f"/api/effects/{effect.id}/thumbnail"

    return EffectResponse(
        id=effect.id,
        name=effect.name,
        filename=effect.filename,
        duration_ms=effect.duration_ms,
        description=effect.description,
        category=effect.category,
        thumbnail_url=thumbnail_url,
        created_at=effect.created_at,
        file_size=effect.file_size
    )


@router.get("", response_model=List[EffectResponse])
async def list_effects(category: Optional[str] = None):
    """Lista todos os efeitos disponíveis."""
    manager = get_effects_manager()
    effects = manager.list_effects(category=category)
    return [effect_to_response(e) for e in effects]


@router.get("/categories", response_model=List[str])
async def list_categories():
    """Lista todas as categorias de efeitos."""
    manager = get_effects_manager()
    return manager.get_categories()


@router.get("/{effect_id}", response_model=EffectResponse)
async def get_effect(effect_id: str):
    """Obtém detalhes de um efeito."""
    manager = get_effects_manager()
    effect = manager.get_effect(effect_id)
    if not effect:
        raise HTTPException(status_code=404, detail="Efeito não encontrado")
    return effect_to_response(effect)


@router.get("/{effect_id}/thumbnail")
async def get_effect_thumbnail(effect_id: str):
    """Retorna thumbnail do efeito."""
    manager = get_effects_manager()
    effect = manager.get_effect(effect_id)
    if not effect or not effect.thumbnail_path:
        raise HTTPException(status_code=404, detail="Thumbnail não encontrada")

    thumb_path = Path(effect.thumbnail_path)
    if not thumb_path.exists():
        raise HTTPException(status_code=404, detail="Thumbnail não encontrada")

    return FileResponse(thumb_path, media_type="image/jpeg")


@router.get("/{effect_id}/preview")
async def get_effect_preview(effect_id: str):
    """Retorna vídeo de preview do efeito."""
    manager = get_effects_manager()
    effect_path = manager.get_effect_path(effect_id)
    if not effect_path:
        raise HTTPException(status_code=404, detail="Efeito não encontrado")

    return FileResponse(effect_path, media_type="video/mp4")


@router.post("", response_model=EffectResponse)
async def upload_effect(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(""),
    category: str = Form("geral")
):
    """
    Faz upload de um novo efeito de vídeo.

    O vídeo deve ter fundo preto para funcionar corretamente como overlay.
    """
    # Validar tipo de arquivo
    if not file.content_type or not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="Arquivo deve ser um vídeo")

    try:
        content = await file.read()
        manager = get_effects_manager()
        effect = manager.add_effect_from_upload(
            file_content=content,
            original_filename=file.filename or "effect.mp4",
            name=name,
            description=description,
            category=category
        )
        return effect_to_response(effect)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar efeito: {str(e)}")


@router.put("/{effect_id}", response_model=EffectResponse)
async def update_effect(effect_id: str, request: EffectUpdateRequest):
    """Atualiza metadados de um efeito."""
    manager = get_effects_manager()
    effect = manager.update_effect(
        effect_id=effect_id,
        name=request.name,
        description=request.description,
        category=request.category
    )
    if not effect:
        raise HTTPException(status_code=404, detail="Efeito não encontrado")
    return effect_to_response(effect)


@router.delete("/{effect_id}")
async def delete_effect(effect_id: str):
    """Remove um efeito da biblioteca."""
    manager = get_effects_manager()
    if not manager.delete_effect(effect_id):
        raise HTTPException(status_code=404, detail="Efeito não encontrado")
    return {"status": "ok", "message": "Efeito removido"}
