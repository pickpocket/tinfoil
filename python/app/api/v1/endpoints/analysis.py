from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pathlib import Path
from mutagen.flac import FLAC

router = APIRouter(prefix="/analyze", tags=["analysis"])

def validate_file_path(file_path: str) -> bool:
    if not file_path or len(file_path) > 4096:
        return False
    if '..' in file_path:
        return False
    return True

@router.get("/file")
async def analyze_file(file_path: str):
    if not validate_file_path(file_path):
        raise HTTPException(status_code=400, detail="Invalid file path")
    
    path = Path(file_path)
    
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    if not path.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")
    
    audio = FLAC(str(path))
    
    metadata = {}
    for key, value in audio.items():
        metadata[key.lower()] = value[0] if len(value) == 1 else value
    
    metadata['has_cover_art'] = len(audio.pictures) > 0
    
    return metadata

@router.get("/cover")
async def get_cover_art(file_path: str):
    if not validate_file_path(file_path):
        raise HTTPException(status_code=400, detail="Invalid file path")
    
    path = Path(file_path)
    
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    audio = FLAC(str(path))
    
    if not audio.pictures:
        raise HTTPException(status_code=404, detail="No cover art found")
    
    picture = audio.pictures[0]
    
    return Response(
        content=picture.data,
        media_type=picture.mime,
        headers={
            "Content-Disposition": f"inline; filename=cover.{picture.mime.split('/')[-1]}",
            "Cache-Control": "max-age=3600"
        }
    )

@router.post("/metadata")
async def update_metadata(file_path: str, metadata: dict):
    if not validate_file_path(file_path):
        raise HTTPException(status_code=400, detail="Invalid file path")
    
    path = Path(file_path)
    
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    audio = FLAC(str(path))
    
    had_cover_art = len(audio.pictures) > 0
    
    audio.clear()
    
    for key, value in metadata.items():
        if key == 'has_cover_art':
            continue
        if value is not None and value != "":
            audio[key] = str(value)
    
    audio.save()
    
    return {
        "success": True,
        "message": "Metadata updated successfully",
        "file_path": str(path),
        "has_cover_art": had_cover_art
    }