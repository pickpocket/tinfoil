"""
@file combined_lyrics_cog.py
@brief Combined cog that tries multiple lyrics sources in sequence.
"""
import logging
from typing import Optional

from base_cog import BaseCog
from song import Song
from cogs.genius_lyrics_cog import GeniusLyricsCog
from cogs.lrclib_lyrics_cog import LrclibLyricsCog
from cogs.netease_lyrics_cog import NeteaseLyricsCog

class CombinedLyricsCog(BaseCog):
    """Try multiple lyrics sources in sequence until one succeeds."""
    
    # Define the output tags so the processor can check for missing lyrics metadata
    output_tags = ['lyrics', 'syncedlyrics']

    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize CombinedLyricsCog.
        
        Args:
            logger: Logger instance
        """
        super().__init__(logger)
        
        # Initialize individual lyrics cogs
        self.lrclib_lyrics_cog = LrclibLyricsCog(logger)
        self.netease_lyrics_cog = NeteaseLyricsCog(logger)
        self.genius_lyrics_cog = GeniusLyricsCog(logger)
    
    def process(self, song: Song) -> bool:
        """Process lyrics for a song using multiple sources.
        
        Args:
            song: The Song object to process
            
        Returns:
            bool: True if processing was successful, False otherwise
        """
        # Try Lrclib first (for synchronized lyrics)
        if self.lrclib_lyrics_cog.can_process(song):
            self.logger.info("Trying to fetch lyrics with LrclibLyricsCog")
            if self.lrclib_lyrics_cog.process(song):
                self.logger.info("Successfully found lyrics with LrclibLyricsCog")
                return True
            else:
                self.logger.debug("No lyrics found with LrclibLyricsCog")
        else:
            self.logger.debug(f"LrclibLyricsCog cannot process {song.filepath}, missing required metadata")
        
        # Try NetEase second (also good for synchronized lyrics)
        self.logger.info("Trying to fetch lyrics with NeteaseLyricsCog")
        if self.netease_lyrics_cog.process(song):
            self.logger.info("Successfully found lyrics with NeteaseLyricsCog")
            return True
        else:
            self.logger.debug("No lyrics found with NeteaseLyricsCog")
        
        # Try Genius last (good for plain text lyrics)
        self.logger.info("Trying to fetch lyrics with GeniusLyricsCog")
        if self.genius_lyrics_cog.process(song):
            self.logger.info("Successfully found lyrics with GeniusLyricsCog")
            return True
        else:
            self.logger.debug("No lyrics found with GeniusLyricsCog")
        
        # If we reach here, all sources failed
        self.logger.warning(f"Could not find lyrics from any source for {song.filepath}")
        return False
