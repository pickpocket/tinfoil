from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from song import Song
import logging

class BaseCog(ABC):
    input_tags: List[str] = []
    output_tags: List[str] = []
    
    # New class attribute to declare required settings.
    # Each setting is a dictionary defining its name, a user-friendly label, and its type.
    required_settings: List[Dict[str, str]] = []
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger if logger else logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def process(self, song: Song) -> bool:
        pass
    
    def can_process(self, song: Song) -> bool:
        if not song or not hasattr(song, 'all_metadata'):
            return False
        
        if not isinstance(song.all_metadata, dict):
            return False
        
        for tag in self.input_tags:
            if not tag or tag not in song.all_metadata:
                self.logger.debug(f"Missing required tag: {tag}")
                return False
        
        return True
    
    def merge_metadata(self, song: Song, new_metadata: Dict[str, Any]) -> None:
        if not song or not hasattr(song, 'all_metadata'):
            self.logger.error("Invalid song object")
            return
        
        if not isinstance(new_metadata, dict):
            self.logger.error("Invalid metadata format")
            return
        
        song.all_metadata.update(new_metadata)
        
        for tag in self.output_tags:
            if tag in new_metadata:
                song.base_metadata[tag] = new_metadata[tag]
        
        self.logger.debug(f"Updated metadata with tags: {list(new_metadata.keys())}")