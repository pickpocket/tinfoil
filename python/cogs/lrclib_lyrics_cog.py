"""
@file lrclib_lyrics_cog.py
@brief Cog for fetching and processing lyrics from LRCLIB API.
"""
import logging
import requests
from typing import Optional, Dict, Any

from base_cog import BaseCog
from song import Song
from config import Config


class LrclibLyricsCog(BaseCog):
    """Handle lyrics operations using the LRCLIB API."""
    
    # Define what tags this cog needs as input
    input_tags = ['artist', 'title', 'album']
    
    # Define what tags this cog provides as output
    output_tags = ['lyrics', 'syncedlyrics']
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize LrclibLyricsCog.
        
        Args:
            logger: Logger instance
        """
        super().__init__(logger)
    
    def process(self, song: Song) -> bool:
        """Process lyrics for a song.
        
        This method fetches lyrics for the song from LRCLIB and adds them to the metadata.
        
        Args:
            song: The Song object to process
            
        Returns:
            bool: True if processing was successful, False otherwise
        """
        if not self.can_process(song):
            self.logger.warning(f"Missing required metadata for LRCLIB lyrics processing")
            return False
        
        try:
            # Get required metadata
            artist = song.all_metadata.get('artist', '')
            title = song.all_metadata.get('title', '')
            album = song.all_metadata.get('album', '')
            duration = float(song.all_metadata.get('length', 0))
            
            # Try to get lyrics
            lyrics = self.get_lyrics(title, artist, album, duration)
            
            if not lyrics:
                self.logger.warning(f"Could not find lyrics from LRCLIB for {artist} - {title}")
                return False
            
            # Update metadata
            metadata = {
                'lyrics': lyrics, 
                'syncedlyrics': lyrics  # LRCLIB provides synced lyrics
            }
            self.merge_metadata(song, metadata)
            
            self.logger.info(f"Successfully added LRCLIB lyrics for {song.filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing LRCLIB lyrics for {song.filepath}: {e}")
            return False
    
    def get_lyrics(self, track_name: str, artist_name: str, album_name: str, duration: float) -> Optional[str]:
        """Fetch lyrics for a song from LRCLIB.
        
        Args:
            track_name: Track name
            artist_name: Artist name
            album_name: Album name
            duration: Track duration in seconds
            
        Returns:
            Optional[str]: Lyrics if found, None otherwise
        """
        self.logger.info(f"Searching for lyrics on LRCLIB: {artist_name} - {track_name}")
        
        # Handle artists with multiple names
        artist_name_get = artist_name
        if ";" in artist_name:
            artist_name_get = ", ".join(artist_name.split(";"))
            artist_name = artist_name.split(";")[0]
        
        # Method 1: Direct get request
        try:
            lrclib_get_url = (
                f"https://lrclib.net/api/get?"
                f"track_name={requests.utils.quote(track_name)}&"
                f"artist_name={requests.utils.quote(artist_name_get)}&"
                f"album_name={requests.utils.quote(album_name)}&"
                f"duration={duration}"
            )
            
            self.logger.debug(f"LRCLIB direct request URL: {lrclib_get_url}")
            lrclib_get_response = requests.get(lrclib_get_url, timeout=10)

            if lrclib_get_response.status_code == 200:
                json_data = lrclib_get_response.json()
                if json_data and json_data.get("syncedLyrics"):
                    self.logger.info(f"Found lyrics from LRCLIB Get for {track_name}")
                    return json_data["syncedLyrics"]
        except Exception as e:
            self.logger.error(f"Error in LRCLIB direct request: {e}")
        
        # Method 2: Search request
        try:
            lrclib_search_url = (
                f"https://lrclib.net/api/search?"
                f"q={requests.utils.quote(f'{artist_name} {track_name}')}"
            )
            
            self.logger.debug(f"LRCLIB search request URL: {lrclib_search_url}")
            lrclib_search_response = requests.get(lrclib_search_url, timeout=10)
            
            if lrclib_search_response.status_code == 200:
                json_data = lrclib_search_response.json()
                
                if json_data and len(json_data) > 0:
                    for song in json_data:
                        # Check if the song matches
                        if ((song["name"].lower() == track_name.lower() or 
                             song["trackName"].lower() == track_name.lower()) and 
                            song["artistName"].lower() == artist_name.lower() and 
                            song["syncedLyrics"]):
                            self.logger.info(f"Found lyrics from LRCLIB Search for {track_name}")
                            return song["syncedLyrics"]
        except Exception as e:
            self.logger.error(f"Error in LRCLIB search request: {e}")
        
        return None