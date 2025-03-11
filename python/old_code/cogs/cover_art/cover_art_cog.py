import requests
from mutagen.flac import FLAC, Picture
import logging
from typing import Optional, Tuple
from pathlib import Path
import io
from PIL import Image

class CoverArtCog:
    """Handle cover art operations."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize CoverArtCog.
        
        Args:
            logger (Optional[logging.Logger]): Logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.max_image_size = (3000, 3000)  # Maximum dimensions for cover art

    def get_cover_art_data(self, release_id: str) -> Optional[bytes]:
        """Fetch cover art from MusicBrainz Cover Art Archive.
        
        Args:
            release_id (str): MusicBrainz release ID
            
        Returns:
            Optional[bytes]: Cover art image data if found
        """
        try:
            url = f"https://coverartarchive.org/release/{release_id}/front"
            self.logger.debug(f"Fetching cover art from URL: {url}")
            
            headers = {'User-Agent': 'tinfoil/1.0'}
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
            image_data (bytes): Original image data
            
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

    def embed_cover_art(self, audio: FLAC, cover_art_data: bytes) -> bool:
        """Embed cover art in FLAC file.
        
        Args:
            audio (FLAC): Mutagen FLAC object
            cover_art_data (bytes): Cover art image data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create picture object
            pic = Picture()
            pic.type = 3  # Front cover
            pic.desc = "Front cover"
            
            # Determine MIME type
            if cover_art_data.startswith(b'\xff\xd8'):
                pic.mime = "image/jpeg"
            elif cover_art_data.startswith(b'\x89PNG'):
                pic.mime = "image/png"
            else:
                pic.mime = "image/jpeg"  # Default to JPEG
                
            # Set image data
            pic.data = cover_art_data
            
            # Remove existing pictures
            audio.clear_pictures()
            
            # Add new picture
            audio.add_picture(pic)
            self.logger.info("Successfully embedded cover art")
            return True
            
        except Exception as e:
            self.logger.error(f"Error embedding cover art: {e}")
            return False

    def extract_cover_art(self, audio: FLAC) -> Optional[bytes]:
        """Extract cover art from FLAC file.
        
        Args:
            audio (FLAC): Mutagen FLAC object
            
        Returns:
            Optional[bytes]: Cover art data if found
        """
        try:
            pictures = audio.pictures
            if pictures:
                # Find front cover
                for pic in pictures:
                    if pic.type == 3:  # Front cover
                        return pic.data
                # If no front cover, use first picture
                return pictures[0].data
            return None
            
        except Exception as e:
            self.logger.error(f"Error extracting cover art: {e}")
            return None

    def save_cover_art(self, cover_art_data: bytes, output_path: Path) -> bool:
        """Save cover art to file.
        
        Args:
            cover_art_data (bytes): Cover art image data
            output_path (Path): Output file path
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(output_path, 'wb') as f:
                f.write(cover_art_data)
            self.logger.info(f"Saved cover art to {output_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving cover art: {e}")
            return False

    def compare_cover_art(self, data1: bytes, data2: bytes) -> bool:
        """Compare two cover art images.
        
        Args:
            data1 (bytes): First image data
            data2 (bytes): Second image data
            
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

    def verify_cover_art(self, file_path: Path) -> Tuple[bool, Optional[str]]:
        """Verify cover art in FLAC file.
        
        Args:
            file_path (Path): Path to FLAC file
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        try:
            audio = FLAC(str(file_path))
            pictures = audio.pictures
            
            if not pictures:
                return False, "No cover art found"
                
            front_covers = [p for p in pictures if p.type == 3]
            if not front_covers:
                return False, "No front cover found"
                
            # Verify image data
            pic = front_covers[0]
            try:
                Image.open(io.BytesIO(pic.data))
                return True, None
            except Exception as e:
                return False, f"Invalid image data: {e}"
                
        except Exception as e:
            return False, f"Error verifying cover art: {e}"