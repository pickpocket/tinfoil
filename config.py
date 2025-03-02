"""
@file config.py
@brief Configuration settings for the Tinfoil application.
"""
import os
import logging
from pathlib import Path
from typing import List, Optional


class Config:
    """Configuration settings for the Tinfoil application."""
    
    # Application information
    APP_NAME = "Tinfoil"
    VERSION = "1.0.0"
    DESCRIPTION = "FLAC Audio Fingerprinting and Metadata Management"
    
    # API Keys and Authentication
    ACOUSTID_API_KEY = os.getenv('ACOUSTID_API_KEY')
    GENIUS_API_KEY = os.getenv('GENIUS_API_KEY')
    
    # Header configuration
    USER_AGENT = "tinfoil/1.0"
    MB_APP_NAME = "tinfoil"
    MB_VERSION = "1.0"
    MB_CONTACT = "imsoupp@protonmail.com"
    
    # API Endpoints
    ACOUSTID_API_URL = "https://api.acoustid.org/v2/lookup"
    MUSICBRAINZ_API_URL = "https://musicbrainz.org/ws/2/"
    COVERART_API_URL = "https://coverartarchive.org"
    GENIUS_API_URL = "https://api.genius.com"
    
    # File Processing
    MAX_FILENAME_LENGTH = 250
    SUPPORTED_AUDIO_FORMATS = ['.flac']
    
    # Directory structure
    DEFAULT_OUTPUT_PATTERN = "{artist}/{year} - {album}/{track:02d} - {title}"
    
    # Logging
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    DEFAULT_LOG_LEVEL = logging.INFO
    
    # Paths
    @classmethod
    def get_app_dir(cls) -> Path:
        """Get the application directory.
        
        Returns:
            Path: Application directory
        """
        # For Linux/macOS: ~/.config/tinfoil
        # For Windows: %APPDATA%\Tinfoil
        if os.name == 'nt':  # Windows
            base_dir = os.path.join(os.environ.get('APPDATA', ''), 'Tinfoil')
        else:  # Linux/macOS
            base_dir = os.path.join(
                os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config')),
                'tinfoil'
            )
        
        path = Path(base_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @classmethod
    def get_log_dir(cls) -> Path:
        """Get the log directory.
        
        Returns:
            Path: Log directory
        """
        log_dir = cls.get_app_dir() / 'logs'
        log_dir.mkdir(exist_ok=True)
        return log_dir
    
    @classmethod
    def get_fpcalc_path(cls) -> Optional[str]:
        """Get the path to the fpcalc executable.
        
        Returns:
            Optional[str]: Path to fpcalc executable
        """
        # Check environment variable
        path = os.getenv('FPCALC_PATH')
        if path and os.path.isfile(path):
            return path
        
        # Check common locations
        if os.name == 'nt':  # Windows
            paths = [
                os.path.join(os.environ.get('ProgramFiles', ''), 'Chromaprint', 'fpcalc.exe'),
                os.path.join(os.environ.get('ProgramFiles(x86)', ''), 'Chromaprint', 'fpcalc.exe')
            ]
        else:  # Linux/macOS
            paths = [
                '/usr/bin/fpcalc',
                '/usr/local/bin/fpcalc',
                '/opt/homebrew/bin/fpcalc'
            ]
        
        for path in paths:
            if os.path.isfile(path):
                return path
        
        return None
    
    @classmethod
    def get_default_output_dir(cls) -> Path:
        """Get the default output directory.
        
        Returns:
            Path: Default output directory
        """
        if os.name == 'nt':  # Windows
            base_dir = os.path.join(os.environ.get('USERPROFILE', ''), 'Music', 'Tinfoil')
        else:  # Linux/macOS
            base_dir = os.path.expanduser('~/Music/Tinfoil')
        
        path = Path(base_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path