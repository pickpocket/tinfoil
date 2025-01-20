from pathlib import Path
from typing import List
from old_code.config import Config

def sanitize_filename(name: str) -> str:
    """Clean and sanitize a filename to be safe for all filesystems.
    
    Args:
        name (str): Original filename
        
    Returns:
        str: Sanitized filename
    """
    # Remove invalid characters
    invalid_chars = '<>:"/\\|?*'
    name = ''.join(c for c in name if c not in invalid_chars)
    
    # Clean up whitespace and dots
    name = name.strip('. ').replace('\n', '').replace('\r', '')
    
    # Truncate to maximum length
    return name[:Config.MAX_FILENAME_LENGTH]

def ensure_directory(path: Path) -> Path:
    """Create directory if it doesn't exist.
    
    Args:
        path (Path): Directory path to create
        
    Returns:
        Path: Created directory path
    """
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_flac_files(directory: Path) -> List[Path]:
    """Recursively find all FLAC files in a directory.
    
    Args:
        directory (Path): Directory to search
        
    Returns:
        List[Path]: List of FLAC file paths
    """
    return list(directory.glob('**/*.flac'))

def build_file_path(
    output_dir: Path,
    artist: str,
    album: str,
    track_num: int,
    title: str,
    year: str
) -> Path:
    """Build complete file path for a track.
    
    Args:
        output_dir (Path): Base output directory
        artist (str): Artist name
        album (str): Album name
        track_num (int): Track number
        title (str): Track title
        year (str): Release year
        
    Returns:
        Path: Complete file path
    """
    # Create artist and album directories
    artist_dir = ensure_directory(output_dir / sanitize_filename(artist))
    album_dir = ensure_directory(artist_dir / sanitize_filename(f"{album} ({year})"))
    
    # Create filename
    filename = f"{artist} - {album} - {track_num:02d} - {title}.flac"
    return album_dir / sanitize_filename(filename)