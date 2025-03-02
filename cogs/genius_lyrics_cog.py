"""
@file genius_lyrics_cog.py
@brief Cog for fetching and processing lyrics from Genius API.
"""
import logging
import requests
from typing import Optional, Dict, Any
import re

from base_cog import BaseCog
from song import Song
from config import Config


class GeniusLyricsCog(BaseCog):
    """Handle lyrics operations using the Genius API."""
    
    # Define what tags this cog needs as input
    input_tags = ['artist', 'title']
    
    # Define what tags this cog provides as output
    output_tags = ['lyrics', 'unsyncedlyrics']
    
    def __init__(self, api_key: Optional[str] = None, logger: Optional[logging.Logger] = None):
        """Initialize GeniusLyricsCog.
        
        Args:
            api_key: Genius API key (optional)
            logger: Logger instance
        """
        super().__init__(logger)
        self.api_key = api_key or Config.GENIUS_API_KEY
    
    def process(self, song: Song) -> bool:
        """Process lyrics for a song.
        
        This method fetches lyrics for the song from Genius and adds them to the metadata.
        
        Args:
            song: The Song object to process
            
        Returns:
            bool: True if processing was successful, False otherwise
        """
        if not self.can_process(song):
            self.logger.warning(f"Missing required metadata for lyrics processing")
            return False
        
        try:
            # Get artist and title
            artist = song.all_metadata.get('artist', '')
            title = song.all_metadata.get('title', '')
            
            # Try to get lyrics
            lyrics = self.get_lyrics(artist, title)
            
            if not lyrics:
                self.logger.warning(f"Could not find lyrics for {artist} - {title}")
                return False
            
            # Update metadata
            metadata = {'lyrics': lyrics, 'unsyncedlyrics': lyrics}
            self.merge_metadata(song, metadata)
            
            self.logger.info(f"Successfully added lyrics for {song.filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing lyrics for {song.filepath}: {e}")
            return False
    
    def get_lyrics(self, artist: str, title: str) -> Optional[str]:
        """Fetch lyrics for a song from Genius.
        
        Args:
            artist: Artist name
            title: Song title
            
        Returns:
            Optional[str]: Lyrics if found, None otherwise
        """
        self.logger.info(f"Searching for lyrics on Genius: {artist} - {title}")
        
        # First search for the song
        song_id = self._search_song(artist, title)
        
        if not song_id:
            self.logger.warning(f"Could not find song on Genius: {artist} - {title}")
            return None
        
        # Then fetch the lyrics using the song ID
        lyrics = self._fetch_lyrics(song_id)
        
        return lyrics
    
    def _search_song(self, artist: str, title: str) -> Optional[int]:
        """Search for a song on Genius.
        
        Args:
            artist: Artist name
            title: Song title
            
        Returns:
            Optional[int]: Song ID if found, None otherwise
        """
        try:
            # Skip API call if no API key
            if not self.api_key:
                self.logger.warning("No Genius API key provided")
                return None
                
            # Clean search query
            query = f"{artist} {title}".replace(' ', '%20')
            
            url = f"https://api.genius.com/search?q={query}"
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'User-Agent': Config.USER_AGENT
            }
            
            # Make API request
            # response = requests.get(url, headers=headers)
            # if response.status_code != 200:
            #     self.logger.warning(f"Genius API returned status code {response.status_code}")
            #     return None
            
            # data = response.json()
            # hits = data.get('response', {}).get('hits', [])
            
            # if not hits:
            #     return None
            
            # # Look for a good match
            # for hit in hits:
            #     hit_artist = hit.get('result', {}).get('primary_artist', {}).get('name', '')
            #     hit_title = hit.get('result', {}).get('title', '')
            #     
            #     # Simple matching heuristic
            #     if (hit_artist.lower() in artist.lower() or artist.lower() in hit_artist.lower()) and \
            #        (hit_title.lower() in title.lower() or title.lower() in hit_title.lower()):
            #         return hit.get('result', {}).get('id')
            
            # If we got here, no good match was found
            return None
            
        except Exception as e:
            self.logger.error(f"Error searching for song on Genius: {e}")
            return None
    
    def _fetch_lyrics(self, song_id: int) -> Optional[str]:
        """Fetch lyrics for a song from Genius using the song ID.
        
        Args:
            song_id: Genius song ID
            
        Returns:
            Optional[str]: Lyrics if found, None otherwise
        """
        try:
            # Skip API call if no API key
            if not self.api_key:
                return None
                
            # url = f"https://api.genius.com/songs/{song_id}"
            # headers = {
            #     'Authorization': f'Bearer {self.api_key}',
            #     'User-Agent': Config.USER_AGENT
            # }
            
            # Make API request
            # response = requests.get(url, headers=headers)
            # if response.status_code != 200:
            #     return None
            
            # data = response.json()
            # song_url = data.get('response', {}).get('song', {}).get('url')
            
            # if not song_url:
            #     return None
            
            # Now we need to scrape the lyrics from the HTML page
            # page_response = requests.get(song_url, headers={'User-Agent': Config.USER_AGENT})
            # if page_response.status_code != 200:
            #     return None
            
            # Use a proper HTML parser in a real implementation
            # lyrics = self._extract_lyrics_from_html(page_response.text)
            
            # Placeholder
            return None
            
        except Exception as e:
            self.logger.error(f"Error fetching lyrics from Genius: {e}")
            return None
    
    def _extract_lyrics_from_html(self, html: str) -> Optional[str]:
        """Extract lyrics from Genius HTML page.
        
        Args:
            html: HTML content
            
        Returns:
            Optional[str]: Extracted lyrics if found, None otherwise
        """
        # In a real implementation, this would use a proper HTML parser like BeautifulSoup
        # to extract the lyrics from the page. This is just a placeholder.
        return None