from fastapi import APIRouter, Depends
from pathlib import Path
import os

from app.core.config import get_settings
from app.schemas.responses import SystemInfo, HealthCheck
from app.core.dependencies import get_processor_service
from app.services.processor_service import ProcessorService

router = APIRouter(prefix="/system", tags=["system"])

@router.get("/info", response_model=SystemInfo)
async def get_system_info():
    settings = get_settings()
    
    fpcalc_path = settings.get_fpcalc_path()
    
    return SystemInfo(
        fpcalc_installed=fpcalc_path is not None,
        fpcalc_path=fpcalc_path,
        app_dir=str(settings.get_app_dir()),
        log_dir=str(settings.get_log_dir()),
        default_output_dir=str(settings.get_default_output_dir()),
        system=os.name,
        version=settings.VERSION
    )

@router.get("/health", response_model=HealthCheck)
async def health_check():
    settings = get_settings()
    fpcalc_path = settings.get_fpcalc_path()
    
    return HealthCheck(
        status="healthy",
        version=settings.VERSION,
        fpcalc_available=fpcalc_path is not None and Path(fpcalc_path).exists()
    )

@router.get("/validate")
async def validate_setup(processor_service: ProcessorService = Depends(get_processor_service)):
    settings = get_settings()
    
    validations = {
        "api_key": len(settings.ACOUSTID_API_KEY) > 0,
        "fpcalc": settings.get_fpcalc_path() is not None
    }
    
    return {
        "valid": all(validations.values()),
        "validations": validations
    }

@router.get("/files")
async def list_files(directory: str):
    if '..' in directory or len(directory) > 4096:
        return {"error": "Invalid directory path"}
    
    dir_path = Path(directory)
    
    if not dir_path.exists() or not dir_path.is_dir():
        return {"error": "Directory not found"}
    
    settings = get_settings()
    audio_files = []
    
    for file_path in dir_path.rglob('*'):
        if file_path.is_file() and file_path.suffix.lower() in settings.SUPPORTED_AUDIO_FORMATS:
            rel_path = file_path.relative_to(dir_path)
            size = file_path.stat().st_size
            
            if size < 1024:
                size_str = f"{size} B"
            elif size < 1024 * 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size / (1024 * 1024):.1f} MB"
            
            audio_files.append({
                "name": file_path.name,
                "path": str(file_path),
                "relative_path": str(rel_path),
                "size": size,
                "size_human": size_str
            })
    
    return {
        "directory": directory,
        "file_count": len(audio_files),
        "files": audio_files
    }