"""
@file combined_lyrics_cog.py
@brief Cog that combines multiple lyrics services.
"""
import logging
from typing import Optional, List, Dict, Any

from base_cog import BaseCog
from song import Song
from config import Config
from cogs.lrclib_lyrics_cog import LrclibLyricsCog
from cogs.netease_lyrics_cog import NeteaseLyricsCog
from cogs.genius_lyrics_cog import GeniusLyricsCog


class CombinedLyricsCog(BaseCog):
    """Combined lyrics cog that tries multiple services in sequence."""
    
    # Define what tags this cog needs as input
    input_tags = ['artist', 'title']  # Minimum required tags
    
    # Define what tags this cog provides as output
    output_tags = ['lyrics', 'syncedlyrics']
    
    def __init__(self, genius_api_key: Optional[str] = None, logger: Optional[logging.Logger] = None):
        """Initialize CombinedLyricsCog.
        
        Args:
            genius_api_key: Genius API key (optional)
            logger: Logger instance
        """
        super().__init__(logger)
        
        # Initialize child cogs
        self.lrclib_cog = LrclibLyricsCog(logger)
        self.netease_cog = NeteaseLyricsCog(logger)
        self.genius_cog = GeniusLyricsCog(genius_api_key, logger)
        
        # List of cogs to try in order
        self.lyrics_cogs = [
            self.lrclib_cog,   # Try LRCLIB first (has synced lyrics)
            self.netease_cog,  # Try NetEase second (has synced lyrics)
            self.genius_cog    # Try Genius last (text-only lyrics)
        ]
    
    def process(self, song: Song) -> bool:
        """Process lyrics for a song.
        
        This method tries each lyrics service in sequence until one succeeds.
        
        Args:
            song: The Song object to process
            
        Returns:
            bool: True if processing was successful, False otherwise
        """
        if not self.can_process(song):
            self.logger.warning(f"Missing required metadata for lyrics processing")
            return False
        
        try:
            # Try each lyrics cog in sequence
            for cog in self.lyrics_cogs:
                cog_name = cog.__class__.__name__
                
                # Check if cog can process this song
                if not cog.can_process(song):
                    self.logger.debug(f"{cog_name} cannot process {song.filepath}, missing required metadata")
                    continue
                
                # Try to process with this cog
                self.logger.info(f"Trying to fetch lyrics with {cog_name}")
                if cog.process(song):
                    self.logger.info(f"Successfully found lyrics with {cog_name}")
                    return True
                
                self.logger.debug(f"No lyrics found with {cog_name}")
            
            # If we get here, all cogs failed
            self.logger.warning(f"Could not find lyrics from any source for {song.filepath}")
            return False
            
        except Exception as e:
            self.logger.error(f"Error processing lyrics for {song.filepath}: {e}")
            return False