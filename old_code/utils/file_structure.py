"""
@file file_structure.py
@brief File system operations and organization utilities.
"""

import shutil
from pathlib import Path
import logging
from typing import Optional, List
from mutagen.flac import FLAC

from .file_utils import sanitize_filename

def setup_directory_structure(
    output_path: Path,
    artist: str,
    album: str,
    year: str,
    logger: Optional[logging.Logger] = None
) -> Path:
    """
    Create and return the album directory path.

    @param output_path: Base output directory
    @param artist: Artist name
    @param album: Album name
    @param year: Release year
    @param logger: Logger instance
    @return: Created album directory path
    """
    artist_dir = output_path / sanitize_filename(artist)
    album_dir = artist_dir / sanitize_filename(f"{album} ({year})")

    try:
        album_dir.mkdir(parents=True, exist_ok=True)
        if logger:
            logger.info(f"Created directory structure: {album_dir}")
        return album_dir
    except Exception as e:
        if logger:
            logger.error(f"Error creating directory structure: {e}")
        raise

def create_file_path(
    dir_path: Path,
    artist: str,
    album: str,
    track_num: int,
    title: str
) -> Path:
    """
    Generate the complete file path for a track.

    @param dir_path: Directory path
    @param artist: Artist name
    @param album: Album name
    @param track_num: Track number
    @param title: Track title
    @return: Complete file path
    """
    filename = f"{artist} - {album} - {track_num:02d} - {title}.flac"
    return dir_path / sanitize_filename(filename)

def copy_file(
    source: Path,
    destination: Path,
    logger: Optional[logging.Logger] = None
) -> bool:
    """
    Copy a file with metadata preservation.

    @param source: Source file path
    @param destination: Destination file path
    @param logger: Logger instance
    @return: True if successful, False otherwise
    """
    try:
        shutil.copy2(source, destination)
        if logger:
            logger.info(f"Copied '{source}' to '{destination}'")
        return True
    except Exception as e:
        if logger:
            logger.error(f"Error copying file: {e}")
        return False

def get_flac_files(
    directory: Path,
    logger: Optional[logging.Logger] = None
) -> List[Path]:
    """
    Find all FLAC files in a directory recursively.

    @param directory: Directory to search
    @param logger: Logger instance
    @return: List of FLAC file paths
    """
    try:
        flac_files = list(directory.glob('**/*.flac'))
        if logger:
            logger.info(f"Found {len(flac_files)} FLAC files in {directory}")
        return flac_files
    except Exception as e:
        if logger:
            logger.error(f"Error scanning for FLAC files: {e}")
        return []

def update_flac_metadata(
    file_path: Path,
    metadata: dict,
    cover_art: Optional[bytes] = None,
    lyrics: Optional[str] = None,
    logger: Optional[logging.Logger] = None
) -> bool:
    """
    Update FLAC file metadata.

    @param file_path: Path to FLAC file
    @param metadata: Metadata to update
    @param cover_art: Cover art data
    @param lyrics: Lyrics data
    @param logger: Logger instance
    @return: True if successful, False otherwise
    """
    try:
        audio = FLAC(str(file_path))
        # Clear existing tags
        audio.delete()
        # Update basic metadata
        for key, value in metadata.items():
            if value is not None:
                audio[key] = str(value)

        # TODO: if cover_art is provided, attach it here (using mutagen)
        # TODO: if lyrics are provided, attach them

        audio.save()
        if logger:
            logger.info(f"Updated metadata for '{file_path}'")
        return True
    except Exception as e:
        if logger:
            logger.error(f"Error updating metadata: {e}")
        return False

def clean_directory(
    directory: Path,
    logger: Optional[logging.Logger] = None
) -> bool:
    """
    Remove empty directories recursively.

    @param directory: Directory to clean
    @param logger: Logger instance
    @return: True if successful, False otherwise
    """
    try:
        for path in sorted(directory.glob('**/*'), key=lambda x: len(str(x)), reverse=True):
            if path.is_dir() and not any(path.iterdir()):
                path.rmdir()
                if logger:
                    logger.info(f"Removed empty directory: {path}")
        return True
    except Exception as e:
        if logger:
            logger.error(f"Error cleaning directories: {e}")
        return False

def verify_file_integrity(
    file_path: Path,
    logger: Optional[logging.Logger] = None
) -> bool:
    """
    Verify FLAC file integrity.

    @param file_path: Path to FLAC file
    @param logger: Logger instance
    @return: True if file is valid, False otherwise
    """
    try:
        audio = FLAC(str(file_path))
        if audio.info:
            return True
        return False
    except Exception as e:
        if logger:
            logger.error(f"File integrity check failed for '{file_path}': {e}")
        return False
