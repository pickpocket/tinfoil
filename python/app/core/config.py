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