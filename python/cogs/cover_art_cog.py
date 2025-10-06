import requests
import logging
from typing import Optional, Tuple
from pathlib import Path
import io
from PIL import Image
from base_cog import BaseCog
from song import Song

class CoverArtCog(BaseCog):
    input_tags = ['musicbrainz_albumid']
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        super().__init__(logger)
        self.max_image_size = (3000, 3000)
        self.user_agent = "tinfoil/1.0"
        self.coverart_api_url = "https://coverartarchive.org"
    
    def process(self, song: Song) -> bool:
        if not self.can_process(song):
            self.logger.warning(f"Missing required metadata for cover art processing")
            return False
        
        release_id = song.all_metadata.get('musicbrainz_albumid')
        
        cover_art_data = self.get_cover_art_data(release_id)
        if not cover_art_data:
            self.logger.warning(f"Could not fetch cover art for release {release_id}")
            return False
        
        mime_type = self._guess_mime_type(cover_art_data)
        if song.set_cover_art(cover_art_data, mime_type):
            self.logger.info(f"Successfully set cover art for {song.filepath}")
            return True
        
        self.logger.warning(f"Failed to set cover art for {song.filepath}")
        return False
    
    def _guess_mime_type(self, image_data: bytes) -> str:
        if image_data.startswith(b'\xff\xd8'):
            return "image/jpeg"
        if image_data.startswith(b'\x89PNG'):
            return "image/png"
        return "image/jpeg"
    
    def get_cover_art_data(self, release_id: str) -> Optional[bytes]:
        url = f"{self.coverart_api_url}/release/{release_id}/front"
        self.logger.debug(f"Fetching cover art from URL: {url}")
        
        headers = {'User-Agent': self.user_agent}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200 and response.content:
            self.logger.info(f"Successfully fetched cover art for release ID '{release_id}'")
            return self._process_image_data(response.content)
        
        self.logger.warning(f"No cover art found for release ID '{release_id}' (Status: {response.status_code})")
        return None
    
    def _process_image_data(self, image_data: bytes) -> bytes:
        with io.BytesIO(image_data) as bio:
            img = Image.open(bio)
            
            if img.size[0] > self.max_image_size[0] or img.size[1] > self.max_image_size[1]:
                img.thumbnail(self.max_image_size, Image.Resampling.LANCZOS)
            
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=90, optimize=True)
            return output.getvalue()
    
    def verify_cover_art(self, song: Song) -> Tuple[bool, Optional[str]]:
        cover_art_data = song.get_cover_art()
        
        if not cover_art_data:
            return False, "No cover art found"
        
        Image.open(io.BytesIO(cover_art_data))
        return True, None
    
    def compare_cover_art(self, data1: bytes, data2: bytes) -> bool:
        img1 = Image.open(io.BytesIO(data1))
        img2 = Image.open(io.BytesIO(data2))
        
        img1 = img1.convert('RGB')
        img2 = img2.convert('RGB')
        
        size = (100, 100)
        img1.thumbnail(size)
        img2.thumbnail(size)
        
        diff = sum(abs(p1 - p2) for p1, p2 in zip(img1.getdata(), img2.getdata()))
        return diff < (size[0] * size[1] * 3 * 0.1)