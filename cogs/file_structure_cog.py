import shutil
from pathlib import Path
import logging
from typing import Optional, List
from mutagen.flac import FLAC
from utils.file_utils import sanitize_filename

class FileStructureCog:
    """Handle file system operations and organization."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize FileStructureCog.
        
        Args:
            logger (Optional[logging.Logger]): Logger instance
        """
        self.logger = logger or logging.getLogger(__name__)

    def setup_directory_structure(
        self,
        output_path: Path,
        artist: str,
        album: str,
        year: str
    ) -> Path:
        """Create and return the album directory path.
        
        Args:
            output_path (Path): Base output directory
            artist (str): Artist name
            album (str): Album name
            year (str): Release year
            
        Returns:
            Path: Created album directory path
        """
        artist_dir = output_path / sanitize_filename(artist)
        album_dir = artist_dir / sanitize_filename(f"{album} ({year})")
        
        try:
            album_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Created directory structure: {album_dir}")
            return album_dir
        except Exception as e:
            self.logger.error(f"Error creating directory structure: {e}")
            raise

    def create_file_path(
        self,
        dir_path: Path,
        artist: str,
        album: str,
        track_num: int,
        title: str
    ) -> Path:
        """Generate the complete file path for a track.
        
        Args:
            dir_path (Path): Directory path
            artist (str): Artist name
            album (str): Album name
            track_num (int): Track number
            title (str): Track title
            
        Returns:
            Path: Complete file path
        """
        filename = f"{artist} - {album} - {track_num:02d} - {title}.flac"
        return dir_path / sanitize_filename(filename)

    def copy_file(self, source: Path, destination: Path) -> bool:
        """Copy a file with metadata preservation.
        
        Args:
            source (Path): Source file path
            destination (Path): Destination file path
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            shutil.copy2(source, destination)
            self.logger.info(f"Copied '{source}' to '{destination}'")
            return True
        except Exception as e:
            self.logger.error(f"Error copying file: {e}")
            return False

    def get_flac_files(self, directory: Path) -> List[Path]:
        """Find all FLAC files in a directory recursively.
        
        Args:
            directory (Path): Directory to search
            
        Returns:
            List[Path]: List of FLAC file paths
        """
        try:
            flac_files = list(directory.glob('**/*.flac'))
            self.logger.info(f"Found {len(flac_files)} FLAC files in {directory}")
            return flac_files
        except Exception as e:
            self.logger.error(f"Error scanning for FLAC files: {e}")
            return []

    def update_flac_metadata(
        self,
        file_path: Path,
        metadata: dict,
        cover_art: Optional[bytes] = None,
        lyrics: Optional[str] = None
    ) -> bool:
        """Update FLAC file metadata.
        
        Args:
            file_path (Path): Path to FLAC file
            metadata (dict): Metadata to update
            cover_art (Optional[bytes]): Cover art data
            lyrics (Optional[str]): Lyrics data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            audio = FLAC(str(file_path))
            
            # Clear existing tags
            audio.delete()
            
            # Update basic metadata
            for key, value in metadata.items():
                if value is not None:
                    audio[key] = str(value)
            
            # Save changes
            audio.save()
            self.logger.info(f"Updated metadata for '{file_path}'")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating metadata: {e}")
            return False

    def clean_directory(self, directory: Path) -> bool:
        """Remove empty directories recursively.
        
        Args:
            directory (Path): Directory to clean
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            for path in sorted(directory.glob('**/*'), key=lambda x: len(str(x)), reverse=True):
                if path.is_dir() and not any(path.iterdir()):
                    path.rmdir()
                    self.logger.info(f"Removed empty directory: {path}")
            return True
        except Exception as e:
            self.logger.error(f"Error cleaning directories: {e}")
            return False

    def verify_file_integrity(self, file_path: Path) -> bool:
        """Verify FLAC file integrity.
        
        Args:
            file_path (Path): Path to FLAC file
            
        Returns:
            bool: True if file is valid, False otherwise
        """
        try:
            audio = FLAC(str(file_path))
            if audio.info:
                return True
            return False
        except Exception as e:
            self.logger.error(f"File integrity check failed for '{file_path}': {e}")
            return False