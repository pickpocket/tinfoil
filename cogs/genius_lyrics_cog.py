"""
@file genius_lyrics_cog.py
@brief Cog for fetching lyrics from Genius using direct search.
"""
import logging
import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any, List
import traceback
import re
import urllib.parse

from base_cog import BaseCog
from song import Song
from config import Config


class GeniusLyricsCog(BaseCog):
    """Handle fetching lyrics from Genius using web scraping."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize GeniusLyricsCog.
        
        Args:
            logger: Logger instance
        """
        super().__init__(logger)
        self.base_url = "https://genius.com"
        self.search_url = "https://genius.com/search"
        # Standard user agent to avoid being blocked
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36'
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
            search_url = f"{self.search_url}?q={search_term}"
            
            self.logger.debug(f"Searching Genius with title only: {search_url}")
            
            # Get the search results page
            response = requests.get(search_url, headers=self.headers)
            response.raise_for_status()
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Log a sample of the HTML for debugging
            self.logger.debug(f"Search response length: {len(response.text)} bytes")
            
            # Find song links in search results
            song_links = self._extract_song_links_from_search(soup)
            
            if not song_links:
                self.logger.debug("No song links found in search results")
                return None
            
            # Try the first result
            first_link = song_links[0]['url']
            self.logger.debug(f"Found song link: {first_link}")
            
            # Get the lyrics
            lyrics = self._scrape_lyrics_from_url(first_link)
            return lyrics
            
        except Exception as e:
            self.logger.error(f"Error searching Genius by title: {e}")
            return None
    
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
            search_url = f"{self.search_url}?q={search_term}"
            
            self.logger.debug(f"Searching Genius with artist and title: {search_url}")
            
            # Get the search results page
            response = requests.get(search_url, headers=self.headers)
            response.raise_for_status()
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find song links in search results
            song_links = self._extract_song_links_from_search(soup)
            
            if not song_links:
                return None
            
            # Try the first result
            first_link = song_links[0]['url']
            self.logger.debug(f"Found song link: {first_link}")
            
            # Get the lyrics
            lyrics = self._scrape_lyrics_from_url(first_link)
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
            search_url = f"{self.search_url}?q={search_term}"
            
            self.logger.debug(f"Searching Genius with artist only: {search_url}")
            
            # Get the search results page
            response = requests.get(search_url, headers=self.headers)
            response.raise_for_status()
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find song links in search results
            song_links = self._extract_song_links_from_search(soup)
            
            if not song_links:
                return None
            
            # Try the first result
            first_link = song_links[0]['url']
            self.logger.debug(f"Found song link: {first_link}")
            
            # Get the lyrics
            lyrics = self._scrape_lyrics_from_url(first_link)
            return lyrics
            
        except Exception as e:
            self.logger.error(f"Error searching Genius by artist: {e}")
            return None
    
    def _extract_song_links_from_search(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract song links from a search results page.
        
        Args:
            soup: BeautifulSoup object of the search page
            
        Returns:
            List[Dict[str, str]]: List of song info dictionaries
        """
        results = []
        
        # IMPORTANT: The selectors have been updated to match 2025 Genius search page structure
        # Method 1: Try to find hits in the search results (2024-2025 layout)
        hits = soup.select('div.hit_full')
        if hits:
            self.logger.debug(f"Found {len(hits)} search result hits")
            for hit in hits:
                # Look for song link
                link = hit.select_one('a.mini_card')
                if not link:
                    link = hit.select_one('a')
                
                if link:
                    url = link.get('href')
                    # Try to get title from different possible elements
                    title_elem = hit.select_one('.mini_card-title')
                    if not title_elem:
                        title_elem = hit.select_one('.title') or hit.select_one('.name')
                    
                    # Try to get artist from different possible elements
                    artist_elem = hit.select_one('.mini_card-subtitle')
                    if not artist_elem:
                        artist_elem = hit.select_one('.subtitle') or hit.select_one('.artist')
                    
                    title = title_elem.get_text().strip() if title_elem else ""
                    artist = artist_elem.get_text().strip() if artist_elem else ""
                    
                    if url and (title or url.endswith('-lyrics')):
                        results.append({
                            'url': url,
                            'title': title,
                            'artist': artist
                        })
        
        # Method 2: Current version (2023-2025)
        if not results:
            cards = soup.select('div.mini_card')
            if cards:
                self.logger.debug(f"Found {len(cards)} mini cards")
                for card in cards:
                    link = card.find('a')
                    title_elem = card.select_one('.mini_card-title')
                    artist_elem = card.select_one('.mini_card-subtitle')
                    
                    if link:
                        url = link.get('href')
                        title = title_elem.get_text().strip() if title_elem else ""
                        artist = artist_elem.get_text().strip() if artist_elem else ""
                        
                        if url:
                            results.append({
                                'url': url,
                                'title': title,
                                'artist': artist
                            })
        
        # Method 3: Try looking for any links to lyrics pages
        if not results:
            # Look for any links containing "/lyrics/" or ending with "-lyrics"
            lyric_links = soup.select('a[href*="/lyrics/"], a[href$="-lyrics"]')
            self.logger.debug(f"Found {len(lyric_links)} potential lyric links")
            
            for link in lyric_links:
                url = link.get('href')
                # Make sure the URL is to a song lyrics page
                if url and ('/lyrics/' in url or url.endswith('-lyrics')):
                    # Try to extract title and artist from the URL
                    parts = url.split('/')
                    if len(parts) > 1:
                        filename = parts[-1]
                        # Remove -lyrics suffix if present
                        if filename.endswith('-lyrics'):
                            filename = filename[:-7]
                        # Replace hyphens with spaces
                        title = filename.replace('-', ' ').title()
                    else:
                        title = link.get_text().strip()
                    
                    results.append({
                        'url': url,
                        'title': title or "Unknown Title",
                        'artist': ""
                    })
        
        # Method 4: Alternative selectors for different page versions
        if not results:
            song_rows = soup.select('div.search_results a.search_result_title')
            if song_rows:
                self.logger.debug(f"Found {len(song_rows)} song rows")
                for row in song_rows:
                    url = row.get('href')
                    title = row.get_text().strip()
                    
                    if url and title:
                        results.append({
                            'url': url,
                            'title': title,
                            'artist': ""
                        })
        
        # Method 5: Last resort - find anything that looks like a song link
        if not results:
            # Get all links on the page
            all_links = soup.find_all('a')
            self.logger.debug(f"Found {len(all_links)} total links, scanning for lyrics URLs")
            
            for link in all_links:
                url = link.get('href')
                text = link.get_text().strip()
                
                # Check if the URL contains "/lyrics/" or ends with "-lyrics"
                if url and ('lyrics' in url.lower() or 'song' in url.lower()):
                    results.append({
                        'url': url,
                        'title': text or "Unknown Title",
                        'artist': ""
                    })
        
        # Method 6: Absolute last resort - try to detect any music-related URLs
        if not results:
            all_links = soup.find_all('a', href=True)
            
            for link in all_links:
                url = link.get('href')
                text = link.get_text().strip()
                
                # If it's likely a Genius song URL, add it
                if url and url.startswith(('https://genius.com/', '/')) and not url.startswith(('/search', '/api', '/static')):
                    results.append({
                        'url': url,
                        'title': text or "Unknown Title",
                        'artist': ""
                    })
        
        # Filter results to ensure we're only including song links
        filtered_results = []
        for result in results:
            url = result['url']
            # Make URL absolute if it's relative
            if url.startswith('/'):
                url = f"https://genius.com{url}"
                result['url'] = url
            
            # Verify it's a lyrics URL
            if 'genius.com' in url and not '/search?' in url:
                filtered_results.append(result)
        
        self.logger.debug(f"Found {len(filtered_results)} filtered song links")
        return filtered_results
    
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
            lyrics_container = None
            
            # Method 1: New versions (2020+)
            lyrics_containers = soup.select('[data-lyrics-container="true"]')
            if lyrics_containers:
                lyrics_text = ""
                for container in lyrics_containers:
                    # Process the lyrics container
                    # Convert <br> tags to newlines
                    for br in container.find_all('br'):
                        br.replace_with('\n')
                    
                    lyrics_text += container.get_text() + "\n\n"
                
                if lyrics_text.strip():
                    return self._clean_lyrics(lyrics_text)
            
            # Method 2: Classic version with class="lyrics"
            lyrics_div = soup.find('div', class_='lyrics')
            if lyrics_div:
                lyrics = lyrics_div.get_text()
                if lyrics.strip():
                    return self._clean_lyrics(lyrics)
            
            # Method 3: Try by ID
            lyrics_div = soup.find(id='lyrics-root')
            if lyrics_div:
                lyrics = lyrics_div.get_text()
                if lyrics.strip():
                    return self._clean_lyrics(lyrics)
            
            # Method 4: Try the 2023-2025 format with Lyrics__Container
            lyrics_div = soup.select('.Lyrics__Container')
            if lyrics_div:
                lyrics_text = ""
                for div in lyrics_div:
                    # Convert <br> tags to newlines
                    for br in div.find_all('br'):
                        br.replace_with('\n')
                    lyrics_text += div.get_text() + "\n\n"
                
                if lyrics_text.strip():
                    return self._clean_lyrics(lyrics_text)
            
            # Method 5: Try all elements with 'lyrics' in their class name
            for element in soup.find_all(class_=lambda c: c and 'lyrics' in c.lower()):
                lyrics = element.get_text()
                if len(lyrics.strip()) > 100:  # Only return if it looks like actual lyrics
                    return self._clean_lyrics(lyrics)
            
            # Method 6: Last resort - try to find a lyrics section by looking at the content and structure
            # Look for elements that contain a significant amount of text with line breaks
            for element in soup.find_all(['div', 'p']):
                if len(element.find_all('br')) > 5:  # If it has several line breaks
                    text = element.get_text()
                    if len(text.strip()) > 200:  # Only if it's substantial text
                        return self._clean_lyrics(text)
            
            self.logger.warning(f"Could not find lyrics in the page: {url}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error scraping lyrics from {url}: {e}")
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
        
        return lyrics.strip()