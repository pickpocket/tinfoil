"""
@file cover_art_cog.py
@brief Cog for handling cover art operations.
"""
import requests
import logging
from typing import Optional, Tuple
from pathlib import Path
import io
from PIL import Image

from base_cog import BaseCog
from song import Song
from config import Config


class CoverArtCog(BaseCog):
    """Handle cover art operations."""
    
    # Define what tags this cog needs as input
    input_tags = ['musicbrainz_albumid']
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize CoverArtCog.
        
        Args:
            logger: Logger instance
        """
        super().__init__(logger)
        self.max_image_size = (3000, 3000)  # Maximum dimensions for cover art
    
    def process(self, song: Song) -> bool:
        """Process cover art for a song.
        
        This method fetches cover art using the MusicBrainz release ID
        and embeds it in the song file.
        
        Args:
            song: The Song object to process
            
        Returns:
            bool: True if processing was successful, False otherwise
        """
        if not self.can_process(song):
            self.logger.warning(f"Missing required metadata for cover art processing")
            return False
        
        try:
            # Get MusicBrainz release ID
            release_id = song.all_metadata.get('musicbrainz_albumid')
            
            # Fetch cover art
            cover_art_data = self.get_cover_art_data(release_id)
            if not cover_art_data:
                self.logger.warning(f"Could not fetch cover art for release {release_id}")
                return False
            
            # Set cover art
            mime_type = self._guess_mime_type(cover_art_data)
            if song.set_cover_art(cover_art_data, mime_type):
                self.logger.info(f"Successfully set cover art for {song.filepath}")
                return True
            else:
                self.logger.warning(f"Failed to set cover art for {song.filepath}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error processing cover art for {song.filepath}: {e}")
            return False
    
    def _guess_mime_type(self, image_data: bytes) -> str:
        """Guess the MIME type of image data.
        
        Args:
            image_data: Image data as bytes
            
        Returns:
            str: MIME type
        """
        if image_data.startswith(b'\xff\xd8'):
            return "image/jpeg"
        elif image_data.startswith(b'\x89PNG'):
            return "image/png"
        else:
            return "image/jpeg"  # Default to JPEG

    def get_cover_art_data(self, release_id: str) -> Optional[bytes]:
        """Fetch cover art from MusicBrainz Cover Art Archive.
        
        Args:
            release_id: MusicBrainz release ID
            
        Returns:
            Optional[bytes]: Cover art image data if found
        """
        try:
            url = f"{Config.COVERART_API_URL}/release/{release_id}/front"
            self.logger.debug(f"Fetching cover art from URL: {url}")
            
            headers = {'User-Agent': Config.USER_AGENT}
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200 and response.content:
                self.logger.info(f"Successfully fetched cover art for release ID '{release_id}'")
                return self._process_image_data(response.content)
            else:
                self.logger.warning(f"No cover art found for release ID '{release_id}' (Status: {response.status_code})")
                return None
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching cover art: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error fetching cover art: {e}")
            return None

    def _process_image_data(self, image_data: bytes) -> bytes:
        """Process and optimize image data.
        
        Args:
            image_data: Original image data
            
        Returns:
            bytes: Processed image data
        """
        try:
            # Open image with PIL
            with io.BytesIO(image_data) as bio:
                img = Image.open(bio)
                
                # Check if resizing is needed
                if img.size[0] > self.max_image_size[0] or img.size[1] > self.max_image_size[1]:
                    img.thumbnail(self.max_image_size, Image.Resampling.LANCZOS)
                    
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                
                # Save optimized image
                output = io.BytesIO()
                img.save(output, format='JPEG', quality=90, optimize=True)
                return output.getvalue()
                
        except Exception as e:
            self.logger.warning(f"Error processing image, using original: {e}")
            return image_data

    def verify_cover_art(self, song: Song) -> Tuple[bool, Optional[str]]:
        """Verify cover art in a song file.
        
        Args:
            song: The Song object to verify
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        try:
            # Get cover art data
            cover_art_data = song.get_cover_art()
            
            if not cover_art_data:
                return False, "No cover art found"
            
            # Verify image data
            try:
                Image.open(io.BytesIO(cover_art_data))
                return True, None
            except Exception as e:
                return False, f"Invalid image data: {e}"
                
        except Exception as e:
            return False, f"Error verifying cover art: {e}"

    def compare_cover_art(self, data1: bytes, data2: bytes) -> bool:
        """Compare two cover art images.
        
        Args:
            data1: First image data
            data2: Second image data
            
        Returns:
            bool: True if images are similar
        """
        try:
            img1 = Image.open(io.BytesIO(data1))
            img2 = Image.open(io.BytesIO(data2))
            
            # Convert to same format and size for comparison
            img1 = img1.convert('RGB')
            img2 = img2.convert('RGB')
            
            # Resize to thumbnail for quick comparison
            size = (100, 100)
            img1.thumbnail(size)
            img2.thumbnail(size)
            
            # Calculate difference
            diff = sum(abs(p1 - p2) for p1, p2 in zip(img1.getdata(), img2.getdata()))
            return diff < (size[0] * size[1] * 3 * 0.1)  # Less than 10% difference
            
        except Exception as e:
            self.logger.error(f"Error comparing cover art: {e}")
            return False