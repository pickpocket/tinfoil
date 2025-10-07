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
    }```

### FILE: python\app\core\config.py
```python
from pydantic_settings import BaseSettings
from pathlib import Path
from functools import lru_cache
import os

class Settings(BaseSettings):
    APP_NAME: str = "Tinfoil"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "FLAC Audio Fingerprinting and Metadata Management"
    API_V1_PREFIX: str = "/api/v1"
    
    ACOUSTID_API_KEY: str = ""
    FPCALC_PATH: str | None = None
    
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "file://"
    ]
    
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    DEFAULT_OUTPUT_PATTERN: str = "{artist}/{year} - {album}/{track:02d} - {title}"
    SUPPORTED_AUDIO_FORMATS: list[str] = [".flac"]
    MAX_FILENAME_LENGTH: int = 250
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024
    
    USER_AGENT: str = "tinfoil/1.0"
    MB_APP_NAME: str = "tinfoil"
    MB_VERSION: str = "1.0"
    MB_CONTACT: str = "imsoupp@protonmail.com"
    
    ACOUSTID_API_URL: str = "https://api.acoustid.org/v2/lookup"
    MUSICBRAINZ_API_URL: str = "https://musicbrainz.org/ws/2/"
    COVERART_API_URL: str = "https://coverartarchive.org"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    def get_app_dir(self) -> Path:
        if os.name == 'nt':
            base_dir = os.path.join(os.environ.get('APPDATA', ''), 'Tinfoil')
        else:
            base_dir = os.path.join(
                os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config')),
                'tinfoil'
            )
        
        path = Path(base_dir)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
        return path
    
    def get_log_dir(self) -> Path:
        log_dir = self.get_app_dir() / 'logs'
        if not log_dir.exists():
            log_dir.mkdir(exist_ok=True)
        return log_dir
    
    def get_cog_settings_dir(self) -> Path:
        settings_dir = self.get_app_dir() / 'cog_settings'
        if not settings_dir.exists():
            settings_dir.mkdir(parents=True, exist_ok=True)
        return settings_dir
    
    def get_fpcalc_path(self) -> str | None:
        if self.FPCALC_PATH and os.path.isfile(self.FPCALC_PATH):
            return self.FPCALC_PATH
        
        if os.name == 'nt':
            paths = [
                os.path.join(os.environ.get('ProgramFiles', ''), 'Chromaprint', 'fpcalc.exe'),
                os.path.join(os.environ.get('ProgramFiles(x86)', ''), 'Chromaprint', 'fpcalc.exe')
            ]
        else:
            paths = [
                '/usr/bin/fpcalc',
                '/usr/local/bin/fpcalc',
                '/opt/homebrew/bin/fpcalc'
            ]
        
        for path in paths:
            if os.path.isfile(path):
                return path
        
        return None
    
    def get_default_output_dir(self) -> Path:
        if os.name == 'nt':
            base_dir = os.path.join(os.environ.get('USERPROFILE', ''), 'Music', 'Tinfoil')
        else:
            base_dir = os.path.expanduser('~/Music/Tinfoil')
        
        path = Path(base_dir)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
        return path

@lru_cache()
def get_settings() -> Settings:
    return Settings()