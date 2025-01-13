import os
from typing import Optional

class Config:
    
    # API Keys and Authentication
    ACOUSTID_API_KEY = os.getenv('ACOUSTID_API_KEY')

    # Header/musicbrainz configuration
    USER_AGENT = "tinfoil/1.0"
    MB_APP_NAME = "tinfoil"
    MB_VERSION = "1.0"
    MB_CONTACT = "imsoupp@protonmail.com"
    
    # API Endpoints
    ACOUSTID_API_URL = "https://api.acoustid.org/v2/lookup"
    MUSICBRAINZ_API_URL = "https://musicbrainz.org/ws/2/"
    COVERART_API_URL = "https://coverartarchive.org"
    
    # File Processing
    MAX_FILENAME_LENGTH = 250
    SUPPORTED_FORMATS = ['.flac']
    
    # Logging
    LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
    DEFAULT_LOG_LEVEL = 'INFO'