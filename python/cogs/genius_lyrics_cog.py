"""
@file genius_lyrics_cog.py
@brief Cog for fetching lyrics from Genius using their search API and web scraping.
"""
import logging
import requests
import json
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any, List
import traceback
import re
import urllib.parse

from base_cog import BaseCog
from song import Song


class GeniusLyricsCog(BaseCog):
    """Handle fetching lyrics from Genius using their search API and web scraping."""
    
    # Define input and output tags for automatic dependency resolution
    input_tags = ['artist', 'title']
    output_tags = ['lyrics']
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize GeniusLyricsCog.
        
        Args:
            logger: Logger instance
        """
        super().__init__(logger)
        self.base_url = "https://genius.com"
        self.search_url = "https://genius.com/api/search/multi"
        # Modern Firefox user agent
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:136.0) Gecko/20100101 Firefox/136.0',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.5',
            'X-Requested-With': 'XMLHttpRequest',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-GPC': '1'
        }
    
    def process(self, song: Song) -> bool:
        """Process lyrics for a song.
        
        Args:
            song: The Song object to process
            
        Returns:
            bool: True if processing was successful, False otherwise
        """
        try:
            # Extract artist and title
            artist = song.all_metadata.get('artist', '')
            title = song.all_metadata.get('title', '')
            
            if not artist or not title:
                self.logger.warning(f"Missing artist or title for Genius lyrics search")
                return False
            
            # Log search
            self.logger.info(f"Searching for lyrics on Genius: {artist} - {title}")
            
            # Try different search approaches
            lyrics = None
            
            # 1. Try with title only (often works best for non-English songs)
            lyrics = self.get_lyrics_by_title(title)
            
            # 2. If that fails, try with artist and title
            if not lyrics:
                lyrics = self.get_lyrics_by_combined(artist, title)
            
            # 3. Try with just the artist as a last resort
            if not lyrics and len(title) > 3:  # Only if title is substantial
                lyrics = self.get_lyrics_by_artist(artist)
            
            if not lyrics:
                self.logger.warning(f"Could not find song on Genius: {artist} - {title}")
                return False
            
            # Debug log the lyrics content
            self.logger.debug(f"Found lyrics (first 100 chars): {lyrics[:100]}...")
            self.logger.debug(f"Lyrics length: {len(lyrics)} characters")
            
            # Update metadata
            song.all_metadata['lyrics'] = lyrics
            self.logger.info(f"Successfully added Genius lyrics for {song.filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing Genius lyrics for {song.filepath}: {e}")
            self.logger.error(traceback.format_exc())
            return False
    
    def get_lyrics_by_title(self, title: str) -> Optional[str]:
        """Search for lyrics using only the title.
        
        Args:
            title: Song title
            
        Returns:
            Optional[str]: Lyrics if found
        """
        try:
            # Encode the search term
            search_term = urllib.parse.quote(title)
            
            # Set up the API endpoint with query
            api_url = f"{self.search_url}?per_page=5&q={search_term}"
            
            # Set up the referrer for the API request
            referrer = f"{self.base_url}/search?q={search_term}"
            headers = self.headers.copy()
            headers['Referer'] = referrer
            
            self.logger.debug(f"Searching Genius API with title only: {api_url}")
            
            # Get search results from the API
            response = requests.get(
                api_url, 
                headers=headers
            )
            response.raise_for_status()
            
            # Parse the JSON response
            search_data = response.json()
            
            # Extract song URLs from the API response
            song_urls = self._extract_song_urls_from_api(search_data)
            
            if not song_urls:
                self.logger.debug("No song URLs found in API response")
                return None
            
            # Try the first result
            first_url = song_urls[0]
            self.logger.debug(f"Found song URL: {first_url}")
            
            # Get the lyrics
            lyrics = self._scrape_lyrics_from_url(first_url)
            
            # Debug log for lyrics content
            if lyrics:
                self.logger.debug(f"Fetched lyrics of length {len(lyrics)} from {first_url}")
            else:
                self.logger.debug(f"No lyrics found at {first_url}")
                
            return lyrics
            
        except Exception as e:
            self.logger.error(f"Error searching Genius by title: {e}")
            return None
    
    def _extract_song_urls_from_api(self, search_data: Dict) -> List[str]:
        """Extract song URLs from the Genius API response.
        
        Args:
            search_data: JSON data from the API
            
        Returns:
            List[str]: List of song URLs
        """
        song_urls = []
        
        try:
            # Check if the response has the expected structure
            if 'response' not in search_data or 'sections' not in search_data['response']:
                self.logger.warning("Unexpected API response structure")
                self.logger.debug(f"API response keys: {search_data.keys()}")
                return []
            
            # Process top hit section first
            sections = search_data['response']['sections']
            
            # Look for top hit section
            top_hit_section = next((s for s in sections if s['type'] == 'top_hit'), None)
            if top_hit_section and 'hits' in top_hit_section and top_hit_section['hits']:
                for hit in top_hit_section['hits']:
                    if hit.get('type') == 'song' and 'result' in hit and 'url' in hit['result']:
                        song_urls.append(hit['result']['url'])
            
            # Look for songs section
            song_section = next((s for s in sections if s['type'] == 'song'), None)
            if song_section and 'hits' in song_section:
                for hit in song_section['hits']:
                    if 'result' in hit and 'url' in hit['result']:
                        song_urls.append(hit['result']['url'])
            
            # Look for lyric section
            lyric_section = next((s for s in sections if s['type'] == 'lyric'), None)
            if lyric_section and 'hits' in lyric_section:
                for hit in lyric_section['hits']:
                    if hit.get('type') == 'song' and 'result' in hit and 'url' in hit['result']:
                        song_urls.append(hit['result']['url'])
            
            self.logger.debug(f"Found {len(song_urls)} song URLs in API response")
            if song_urls:
                self.logger.debug(f"First URL: {song_urls[0]}")
            
        except Exception as e:
            self.logger.error(f"Error extracting song URLs from API response: {e}")
        
        return song_urls
    
    def get_lyrics_by_combined(self, artist: str, title: str) -> Optional[str]:
        """Search for lyrics using artist and title.
        
        Args:
            artist: Artist name
            title: Song title
            
        Returns:
            Optional[str]: Lyrics if found
        """
        try:
            # Encode the search term
            search_term = urllib.parse.quote(f"{artist} {title}")
            
            # Set up the API endpoint with query
            api_url = f"{self.search_url}?per_page=5&q={search_term}"
            
            # Set up the referrer for the API request
            referrer = f"{self.base_url}/search?q={search_term}"
            headers = self.headers.copy()
            headers['Referer'] = referrer
            
            self.logger.debug(f"Searching Genius API with artist and title: {api_url}")
            
            # Get search results from the API
            response = requests.get(
                api_url, 
                headers=headers
            )
            response.raise_for_status()
            
            # Parse the JSON response
            search_data = response.json()
            
            # Extract song URLs from the API response
            song_urls = self._extract_song_urls_from_api(search_data)
            
            if not song_urls:
                self.logger.debug("No song URLs found in API response")
                return None
            
            # Try the first result
            first_url = song_urls[0]
            self.logger.debug(f"Found song URL: {first_url}")
            
            # Get the lyrics
            lyrics = self._scrape_lyrics_from_url(first_url)
            
            # Debug log for lyrics content
            if lyrics:
                self.logger.debug(f"Fetched lyrics of length {len(lyrics)} from {first_url}")
            else:
                self.logger.debug(f"No lyrics found at {first_url}")
                
            return lyrics
            
        except Exception as e:
            self.logger.error(f"Error searching Genius by artist and title: {e}")
            return None
    
    def get_lyrics_by_artist(self, artist: str) -> Optional[str]:
        """Search for lyrics using only the artist.
        
        Args:
            artist: Artist name
            
        Returns:
            Optional[str]: Lyrics if found
        """
        try:
            # Encode the search term
            search_term = urllib.parse.quote(artist)
            
            # Set up the API endpoint with query
            api_url = f"{self.search_url}?per_page=5&q={search_term}"
            
            # Set up the referrer for the API request
            referrer = f"{self.base_url}/search?q={search_term}"
            headers = self.headers.copy()
            headers['Referer'] = referrer
            
            self.logger.debug(f"Searching Genius API with artist only: {api_url}")
            
            # Get search results from the API
            response = requests.get(
                api_url, 
                headers=headers
            )
            response.raise_for_status()
            
            # Parse the JSON response
            search_data = response.json()
            
            # Extract song URLs from the API response
            song_urls = self._extract_song_urls_from_api(search_data)
            
            if not song_urls:
                self.logger.debug("No song URLs found in API response")
                return None
            
            # Try the first result
            first_url = song_urls[0]
            self.logger.debug(f"Found song URL: {first_url}")
            
            # Get the lyrics
            lyrics = self._scrape_lyrics_from_url(first_url)
            
            # Debug log for lyrics content
            if lyrics:
                self.logger.debug(f"Fetched lyrics of length {len(lyrics)} from {first_url}")
            else:
                self.logger.debug(f"No lyrics found at {first_url}")
                
            return lyrics
            
        except Exception as e:
            self.logger.error(f"Error searching Genius by artist: {e}")
            return None
    
    def _scrape_lyrics_from_url(self, url: str) -> Optional[str]:
        """Scrape lyrics from Genius URL.
        
        Args:
            url: Genius song URL
            
        Returns:
            Optional[str]: Lyrics if found
        """
        try:
            # Make sure URL is absolute
            if not url.startswith('http'):
                url = f"https://genius.com{url if url.startswith('/') else '/' + url}"
            
            self.logger.debug(f"Fetching lyrics from URL: {url}")
            
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            # Log response details
            self.logger.debug(f"Response status code: {response.status_code}")
            self.logger.debug(f"Response content length: {len(response.text)} bytes")
            
            # Parse the HTML with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script tags
            for script in soup.find_all('script'):
                script.extract()
            
            # Check if we actually got a lyrics page
            if 'lyrics' not in url.lower() and not soup.select('[data-lyrics-container="true"]') and not soup.find('div', class_='lyrics'):
                self.logger.warning(f"URL does not appear to be a lyrics page: {url}")
                return None
            
            # Try to find lyrics in different possible containers
            # Method 1: New versions (2020+)
            lyrics_containers = soup.select('[data-lyrics-container="true"]')
            if lyrics_containers:
                self.logger.debug(f"Found {len(lyrics_containers)} lyrics containers with [data-lyrics-container='true']")
                lyrics_text = ""
                for container in lyrics_containers:
                    # Process the lyrics container
                    # Convert <br> tags to newlines
                    for br in container.find_all('br'):
                        br.replace_with('\n')
                    
                    container_text = container.get_text()
                    lyrics_text += container_text + "\n\n"
                    self.logger.debug(f"Container text length: {len(container_text)} chars")
                
                if lyrics_text.strip():
                    cleaned_lyrics = self._clean_lyrics(lyrics_text)
                    self.logger.debug(f"Found lyrics using method 1, length: {len(cleaned_lyrics)}")
                    return cleaned_lyrics
            
            # Method 2: Classic version with class="lyrics"
            lyrics_div = soup.find('div', class_='lyrics')
            if lyrics_div:
                lyrics = lyrics_div.get_text()
                if lyrics.strip():
                    cleaned_lyrics = self._clean_lyrics(lyrics)
                    self.logger.debug(f"Found lyrics using method 2, length: {len(cleaned_lyrics)}")
                    return cleaned_lyrics
            
            # Method 3: Try by ID
            lyrics_div = soup.find(id='lyrics-root')
            if lyrics_div:
                lyrics = lyrics_div.get_text()
                if lyrics.strip():
                    cleaned_lyrics = self._clean_lyrics(lyrics)
                    self.logger.debug(f"Found lyrics using method 3, length: {len(cleaned_lyrics)}")
                    return cleaned_lyrics
            
            # Method 4: Try the 2023-2025 format with Lyrics__Container
            lyrics_div = soup.select('.Lyrics__Container')
            if lyrics_div:
                self.logger.debug(f"Found {len(lyrics_div)} .Lyrics__Container elements")
                lyrics_text = ""
                for div in lyrics_div:
                    # Convert <br> tags to newlines
                    for br in div.find_all('br'):
                        br.replace_with('\n')
                    div_text = div.get_text()
                    lyrics_text += div_text + "\n\n"
                    self.logger.debug(f"Container text length: {len(div_text)} chars")
                
                if lyrics_text.strip():
                    cleaned_lyrics = self._clean_lyrics(lyrics_text)
                    self.logger.debug(f"Found lyrics using method 4, length: {len(cleaned_lyrics)}")
                    return cleaned_lyrics
            
            # Method 5: Try elements with specific content
            # Look for divs with text content that includes common lyric markers
            for div in soup.find_all('div'):
                div_text = div.get_text()
                if '[Verse' in div_text or '[Chorus' in div_text or 'Lyrics' in div.get('class', ''):
                    # Convert <br> tags to newlines
                    for br in div.find_all('br'):
                        br.replace_with('\n')
                    if len(div_text.strip()) > 100:  # Only if it's substantial text
                        cleaned_lyrics = self._clean_lyrics(div_text)
                        self.logger.debug(f"Found lyrics using method 5, length: {len(cleaned_lyrics)}")
                        return cleaned_lyrics
            
            # Method 6: Try all elements with 'lyrics' in their class name
            for element in soup.find_all(class_=lambda c: c and 'lyrics' in c.lower()):
                lyrics = element.get_text()
                if len(lyrics.strip()) > 100:  # Only return if it looks like actual lyrics
                    cleaned_lyrics = self._clean_lyrics(lyrics)
                    self.logger.debug(f"Found lyrics using method 6, length: {len(cleaned_lyrics)}")
                    return cleaned_lyrics
            
            # Method 7: Last resort - try to find a lyrics section by looking at the content and structure
            # Look for elements that contain a significant amount of text with line breaks
            for element in soup.find_all(['div', 'p']):
                if len(element.find_all('br')) > 5:  # If it has several line breaks
                    text = element.get_text()
                    if len(text.strip()) > 200:  # Only if it's substantial text
                        cleaned_lyrics = self._clean_lyrics(text)
                        self.logger.debug(f"Found lyrics using method 7, length: {len(cleaned_lyrics)}")
                        return cleaned_lyrics
            
            # Last resort - get the title and look for containers with that same title text
            page_title = soup.find('title')
            if page_title:
                title_text = page_title.get_text()
                if " – " in title_text:
                    song_title = title_text.split(" – ")[0]
                    for heading in soup.find_all(['h1', 'h2']):
                        if song_title in heading.get_text():
                            # Try to get the next content-rich element
                            next_element = heading.find_next(['div', 'p'])
                            if next_element:
                                text = next_element.get_text()
                                if len(text.strip()) > 200:
                                    cleaned_lyrics = self._clean_lyrics(text)
                                    self.logger.debug(f"Found lyrics using title-based search, length: {len(cleaned_lyrics)}")
                                    return cleaned_lyrics
            
            # Print the entire HTML structure for debugging
            self.logger.debug("HTML structure summary:")
            for tag in soup.find_all(['div', 'section']):
                if 'class' in tag.attrs:
                    self.logger.debug(f"Found tag: {tag.name}, class: {tag['class']}")
            
            self.logger.warning(f"Could not find lyrics in the page: {url}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error scraping lyrics from {url}: {e}")
            self.logger.error(traceback.format_exc())
            return None
    
    def _clean_lyrics(self, lyrics: str) -> str:
        """Clean and format lyrics text.
        
        Args:
            lyrics: Raw lyrics text
            
        Returns:
            str: Cleaned lyrics
        """
        if not lyrics:
            return ""
        
        # Log raw lyrics for debugging
        self.logger.debug(f"Raw lyrics sample: {lyrics[:100]}...")
        
        # Strip whitespace
        lyrics = lyrics.strip()
        
        # Check for unavailable lyrics
        if any(phrase in lyrics.lower() for phrase in [
            "lyrics will be available",
            "not available",
            "cannot find the lyrics",
            "no lyrics found"
        ]):
            return ""
        
        # Remove annotations in square brackets
        lyrics = re.sub(r'\[\d+\]', '', lyrics)
        
        # Remove "[Verse]", "[Chorus]", etc. markers that might disrupt readability
        lyrics = re.sub(r'\[(Verse|Chorus|Bridge|Hook|Intro|Outro|Pre-Chorus|Refrain|Interlude).*?\]', '', lyrics)
        
        # Normalize line endings
        lyrics = re.sub(r'\r\n|\r', '\n', lyrics)
        
        # Remove excessive blank lines (more than 2 in a row)
        lyrics = re.sub(r'\n{3,}', '\n\n', lyrics)
        
        # Log cleaned lyrics for debugging
        cleaned = lyrics.strip()
        self.logger.debug(f"Cleaned lyrics sample: {cleaned[:100]}...")
        self.logger.debug(f"Cleaned lyrics length: {len(cleaned)} characters")
        
        return cleaned