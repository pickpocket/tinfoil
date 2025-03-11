"""
@file netease_lyrics_cog.py
@brief Cog for fetching and processing lyrics from NetEase Music API.
"""
import logging
import requests
from typing import Optional, Dict, Any

from base_cog import BaseCog
from song import Song
from config import Config


class NeteaseLyricsCog(BaseCog):
    """Handle lyrics operations using the NetEase Music API."""
    
    # Define what tags this cog needs as input
    input_tags = ['artist', 'title']
    
    # Define what tags this cog provides as output
    output_tags = ['lyrics', 'syncedlyrics']
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize NeteaseLyricsCog.
        
        Args:
            logger: Logger instance
        """
        super().__init__(logger)
    
    def process(self, song: Song) -> bool:
        """Process lyrics for a song.
        
        This method fetches lyrics for the song from NetEase Music API and adds them to the metadata.
        
        Args:
            song: The Song object to process
            
        Returns:
            bool: True if processing was successful, False otherwise
        """
        if not self.can_process(song):
            self.logger.warning(f"Missing required metadata for NetEase lyrics processing")
            return False
        
        try:
            # Get artist and title
            artist = song.all_metadata.get('artist', '')
            title = song.all_metadata.get('title', '')
            
            # Try to get lyrics
            lyrics = self.get_lyrics(title, artist)
            
            if not lyrics:
                self.logger.warning(f"Could not find lyrics from NetEase for {artist} - {title}")
                return False
            
            # Update metadata
            metadata = {
                'lyrics': lyrics,
                'syncedlyrics': lyrics  # NetEase can provide synced lyrics
            }
            self.merge_metadata(song, metadata)
            
            self.logger.info(f"Successfully added NetEase lyrics for {song.filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing NetEase lyrics for {song.filepath}: {e}")
            return False
    
    def get_lyrics(self, track_name: str, artist_name: str) -> Optional[str]:
        """Fetch lyrics for a song from NetEase Music API.
        
        Args:
            track_name: Track name
            artist_name: Artist name
            
        Returns:
            Optional[str]: Lyrics if found, None otherwise
        """
        self.logger.info(f"Searching for lyrics on NetEase: {artist_name} - {track_name}")
        
        try:
            # Step 1: Search for the song
            netease_url = (
                f"https://music.163.com/api/search/get?"
                f"offset=0&type=1&s={requests.utils.quote(f'{artist_name} {track_name}')}"
            )
            
            self.logger.debug(f"NetEase search URL: {netease_url}")
            
            # Set user agent to avoid blocking
            headers = {'User-Agent': Config.USER_AGENT}
            netease_response = requests.get(netease_url, headers=headers, timeout=10)
            
            if netease_response.status_code == 200:
                json_data = netease_response.json()
                
                if json_data.get("result", {}).get("songs"):
                    # Check each song in search results
                    for song in json_data["result"]["songs"]:
                        # Check if title matches
                        if song["name"].lower() == track_name.lower():
                            # Check if any artist matches
                            if any(artist["name"].lower() == artist_name.lower() 
                                   for artist in song["artists"]):
                                
                                # Get lyrics for this song
                                song_id = song['id']
                                lyrics = self._get_song_lyrics(song_id)
                                
                                if lyrics:
                                    self.logger.info(f"Found lyrics from NetEase for {track_name}")
                                    return lyrics
            
            self.logger.debug("No matching songs found in NetEase search results")
            return None
            
        except Exception as e:
            self.logger.error(f"Error searching for song on NetEase: {e}")
            return None
    
    def _get_song_lyrics(self, song_id: int) -> Optional[str]:
        """Get lyrics for a specific song by ID.
        
        Args:
            song_id: NetEase song ID
            
        Returns:
            Optional[str]: Lyrics if found, None otherwise
        """
        try:
            lyric_url = f"https://music.163.com/api/song/lyric?id={song_id}&kv=-1&lv=-1"
            headers = {'User-Agent': Config.USER_AGENT}
            
            self.logger.debug(f"NetEase lyrics URL: {lyric_url}")
            lyric_response = requests.get(lyric_url, headers=headers, timeout=10)
            
            if lyric_response.status_code == 200:
                js = lyric_response.json()
                
                # Try to get klyric (synced lyrics) first, then fall back to lrc (regular lyrics)
                lyrics = js.get("klyric", {}).get("lyric") or js.get('lrc', {}).get("lyric")
                
                if lyrics:
                    return lyrics
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting lyrics from NetEase: {e}")
            return None