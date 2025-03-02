"""
@file song.py
@brief Class representing a FLAC audio file with its metadata.
"""
import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, Union
import logging

from mutagen.flac import FLAC, Picture


class Song:
    """A class representing a FLAC audio file with its metadata.
    
    This class encapsulates operations on a FLAC file, including reading
    and writing metadata, manipulating cover art, and file operations.
    """
    
    def __init__(self, filepath: Union[str, Path], logger: Optional[logging.Logger] = None):
        """Initialize a Song object.
        
        Args:
            filepath: Path to the FLAC file
            logger: Logger instance
        """
        self.filepath = Path(filepath)
        self.folderpath = self.filepath.parent
        self.filename = self.filepath.name
        self.logger = logger or logging.getLogger(__name__)
        
        # Ensure file exists and is a FLAC file
        if not self.filepath.exists():
            raise FileNotFoundError(f"File not found: {self.filepath}")
        
        if self.filepath.suffix.lower() != '.flac':
            raise ValueError(f"Not a FLAC file: {self.filepath}")
        
        # Load the audio file
        try:
            self.audio = FLAC(str(self.filepath))
            self.logger.debug(f"Loaded FLAC file: {self.filepath}")
        except Exception as e:
            self.logger.error(f"Error loading FLAC file {self.filepath}: {e}")
            raise
        
        # Initialize metadata dictionaries
        self.base_metadata: Dict[str, Any] = {}  # Metadata to be written to the file
        self.all_metadata: Dict[str, Any] = {}   # All available metadata (including computed)
        
        # Load existing metadata
        self._load_existing_metadata()
    
    def _load_existing_metadata(self) -> None:
        """Load existing metadata from the FLAC file."""
        for key, value in self.audio.items():
            # Mutagen returns lists for tag values
            if len(value) == 1:
                self.all_metadata[key] = value[0]
            else:
                self.all_metadata[key] = value
            
            # Also add to base_metadata for preserving existing tags
            self.base_metadata[key] = value
        
        self.logger.debug(f"Loaded {len(self.all_metadata)} metadata tags")
    
    def save_overwrite(self) -> bool:
        """Save metadata to the file, clearing all existing metadata.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Clear all existing tags
            self.audio.clear()
            
            # Add new tags
            for key, value in self.base_metadata.items():
                if isinstance(value, list):
                    self.audio[key] = value
                else:
                    self.audio[key] = [str(value)]
            
            # Save file
            self.audio.save()
            self.logger.info(f"Saved metadata (overwrite) to {self.filepath}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving metadata to {self.filepath}: {e}")
            return False
    
    def save_additive(self) -> bool:
        """Save metadata to the file without clearing existing metadata.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Add or update tags
            for key, value in self.base_metadata.items():
                if isinstance(value, list):
                    self.audio[key] = value
                else:
                    self.audio[key] = [str(value)]
            
            # Save file
            self.audio.save()
            self.logger.info(f"Saved metadata (additive) to {self.filepath}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving metadata to {self.filepath}: {e}")
            return False
    
    def copy_to(self, destination: Union[str, Path]) -> Optional['Song']:
        """Copy the song file to a new location.
        
        Args:
            destination: Destination path
            
        Returns:
            Optional[Song]: New Song object if successful, None otherwise
        """
        dest_path = Path(destination)
        
        # Create parent directories if they don't exist
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Copy the file
            shutil.copy2(self.filepath, dest_path)
            self.logger.info(f"Copied {self.filepath} to {dest_path}")
            
            # Return a new Song object for the copied file
            return Song(dest_path, self.logger)
        except Exception as e:
            self.logger.error(f"Error copying {self.filepath} to {dest_path}: {e}")
            return None
    
    def get_cover_art(self) -> Optional[bytes]:
        """Get cover art data from the FLAC file.
        
        Returns:
            Optional[bytes]: Cover art data if found, None otherwise
        """
        try:
            pictures = self.audio.pictures
            if pictures:
                # Try to find front cover
                for pic in pictures:
                    if pic.type == 3:  # Front cover
                        return pic.data
                
                # If no front cover found, return the first picture
                return pictures[0].data
            
            return None
        except Exception as e:
            self.logger.error(f"Error getting cover art: {e}")
            return None
    
    def set_cover_art(self, image_data: bytes, mime_type: str = "image/jpeg") -> bool:
        """Set cover art for the FLAC file.
        
        Args:
            image_data: Image data as bytes
            mime_type: MIME type of the image
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create a new picture
            pic = Picture()
            pic.type = 3  # Front cover
            pic.mime = mime_type
            pic.desc = "Front cover"
            pic.data = image_data
            
            # Clear existing pictures
            self.audio.clear_pictures()
            
            # Add the new picture
            self.audio.add_picture(pic)
            
            # Save the file
            self.audio.save()
            
            self.logger.info(f"Set cover art for {self.filepath}")
            return True
        except Exception as e:
            self.logger.error(f"Error setting cover art: {e}")
            return False
    
    def __str__(self) -> str:
        """String representation of the Song.
        
        Returns:
            str: String representation
        """
        return f"Song({self.filepath})"