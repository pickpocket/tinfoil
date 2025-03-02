"""
@file base_cog.py
@brief Base class for all cogs in the Tinfoil application.
"""
import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

from song import Song


class BaseCog(ABC):
    """Base class that all cogs must inherit from.
    
    A cog is a modular component that provides specific functionality
    for the Tinfoil application. Each cog defines what tags it can process
    (input_tags) and what tags it can provide (output_tags).
    """
    
    # Tags this cog can read and process
    input_tags: List[str] = []
    
    # Tags this cog can generate and write
    output_tags: List[str] = []
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize BaseCog.
        
        Args:
            logger: Logger instance for this cog
        """
        self.logger = logger or logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def process(self, song: Song) -> bool:
        """Process a song using this cog's functionality.
        
        This method is the main entry point for a cog's functionality.
        It should read necessary data from the song, perform its operations,
        and update the song's metadata as appropriate.
        
        Args:
            song: The Song object to process
            
        Returns:
            bool: True if processing was successful, False otherwise
        """
        pass
    
    def can_process(self, song: Song) -> bool:
        """Check if this cog has the required input data to process the song.
        
        Args:
            song: The Song object to check
            
        Returns:
            bool: True if this cog can process the song, False otherwise
        """
        # Check if all required input tags are present in the song's metadata
        for tag in self.input_tags:
            if tag not in song.all_metadata:
                self.logger.debug(f"Missing required tag: {tag}")
                return False
        return True
    
    def merge_metadata(self, song: Song, new_metadata: Dict[str, Any]) -> None:
        """Merge new metadata into the song's metadata.
        
        Args:
            song: The Song object to update
            new_metadata: New metadata to merge into the song
        """
        # Add new metadata to all_metadata
        song.all_metadata.update(new_metadata)
        
        # Add output tags to base_metadata for writing to file
        for tag in self.output_tags:
            if tag in new_metadata:
                song.base_metadata[tag] = new_metadata[tag]
        
        self.logger.debug(f"Updated metadata with tags: {list(new_metadata.keys())}")