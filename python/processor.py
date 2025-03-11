"""
@file processor.py
@brief Main processor class for the Tinfoil application.
"""
import os
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any, Type
import shutil
import re

from base_cog import BaseCog
from song import Song
from config import Config
from cogs.acoustid_cog import AcoustIDCog
from cogs.musicbrainz_cog import MusicBrainzCog
from cogs.cover_art_cog import CoverArtCog
from cogs.genius_lyrics_cog import GeniusLyricsCog
from cogs.lrclib_lyrics_cog import LrclibLyricsCog
from cogs.netease_lyrics_cog import NeteaseLyricsCog
from cogs.tag_based_match_cog import TagBasedMatchCog


class TinfoilProcessor:
    """Main processor class for the Tinfoil application."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        fpcalc_path: Optional[str] = None,
        output_pattern: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
        custom_cogs: Optional[List[BaseCog]] = None,  # New parameter for custom cogs
        lyrics_source: str = "genius"  # Default lyrics source
    ):
        """Initialize TinfoilProcessor.
        
        Args:
            api_key: AcoustID API key
            fpcalc_path: Path to fpcalc executable
            output_pattern: Pattern for output filenames
            logger: Logger instance
            custom_cogs: Custom list of cogs to use instead of the default pipeline
            lyrics_source: Which lyrics source to use ('genius', 'lrclib', 'netease', or 'none')
        """
        self.logger = logger or logging.getLogger(__name__)
        
        # Use provided API key or get from config
        self.api_key = api_key or Config.ACOUSTID_API_KEY
        if not self.api_key:
            raise ValueError("AcoustID API key is required")
        
        # Use provided fpcalc path or get from config
        self.fpcalc_path = fpcalc_path or Config.get_fpcalc_path()
        if not self.fpcalc_path:
            self.logger.warning("fpcalc executable not found, fingerprinting may fail")
        
        # Use provided output pattern or get from config
        self.output_pattern = output_pattern or Config.DEFAULT_OUTPUT_PATTERN
        
        # If custom cogs are provided, use them
        if custom_cogs:
            self.cogs = custom_cogs
            self.logger.info(f"Using custom cog pipeline with {len(custom_cogs)} cogs")
        else:
            # Initialize standard cogs
            self.acoustid_cog = AcoustIDCog(self.api_key, self.fpcalc_path, self.logger)
            self.tag_based_match_cog = TagBasedMatchCog(self.logger)
            self.musicbrainz_cog = MusicBrainzCog(self.logger)
            self.cover_art_cog = CoverArtCog(self.logger)
            
            # Initialize individual lyrics cogs
            self.genius_lyrics_cog = GeniusLyricsCog(self.logger)
            self.lrclib_lyrics_cog = LrclibLyricsCog(self.logger)
            self.netease_lyrics_cog = NeteaseLyricsCog(self.logger)
            
            # List of cogs in processing order (default without lyrics)
            self.cogs: List[BaseCog] = [
                self.acoustid_cog,
                self.tag_based_match_cog,  # Try tag-based matching if AcoustID fails
                self.musicbrainz_cog,
                self.cover_art_cog
            ]
            
            # Add the selected lyrics cog
            if lyrics_source == "genius":
                self.cogs.append(self.genius_lyrics_cog)
                self.logger.info("Using Genius for lyrics")
            elif lyrics_source == "lrclib":
                self.cogs.append(self.lrclib_lyrics_cog)
                self.logger.info("Using LRCLIB for lyrics")
            elif lyrics_source == "netease":
                self.cogs.append(self.netease_lyrics_cog)
                self.logger.info("Using NetEase for lyrics")
            elif lyrics_source == "none":
                self.logger.info("Lyrics fetching disabled")
            else:
                self.logger.warning(f"Unknown lyrics source '{lyrics_source}', defaulting to Genius")
                self.cogs.append(self.genius_lyrics_cog)
    
    def process_file(self, file_path: Path, output_dir: Path, force_update: bool = False) -> bool:
        """Process a single audio file.
        
        Args:
            file_path: Path to the audio file
            output_dir: Output directory
            force_update: Force update even if metadata exists
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.logger.info(f"Processing file: {file_path}")
            
            # Create Song object
            song = Song(file_path, self.logger)
            
            # Process the song with each cog
            for cog in self.cogs:
                cog_name = cog.__class__.__name__
                
                # Skip if we already have needed metadata and not forcing update
                if not force_update and all(tag in song.all_metadata for tag in cog.output_tags):
                    self.logger.info(f"Skipping {cog_name}, metadata already exists")
                    continue
                
                # Check if cog can process the song
                if not cog.can_process(song):
                    self.logger.warning(f"{cog_name} cannot process {file_path}, missing required metadata")
                    # Continue with next cog, some might not need input tags
                    continue
                
                # Process with cog
                self.logger.info(f"Processing with {cog_name}")
                if not cog.process(song):
                    self.logger.warning(f"{cog_name} processing failed for {file_path}")
                    # Continue with next cog anyway
            
            # Generate output path
            output_path = self._generate_output_path(song, output_dir)
            if not output_path:
                self.logger.warning(f"Could not generate output path for {file_path}")
                return False
            
            # Create output directory if it doesn't exist
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file to output location
            new_song = song.copy_to(output_path)
            if not new_song:
                self.logger.warning(f"Could not copy {file_path} to {output_path}")
                return False
            
            # Propagate metadata (including lyrics) from original song to the copied song
            new_song.all_metadata = song.all_metadata.copy()
            
            # Save metadata to new file
            if new_song.save_overwrite():
                self.logger.info(f"Successfully processed {file_path} to {output_path}")
                return True
            else:
                self.logger.warning(f"Could not save metadata to {output_path}")
                return False
            
        except Exception as e:
            self.logger.error(f"Error processing {file_path}: {e}")
            return False

    
    def _generate_output_path(self, song: Song, output_dir: Path) -> Optional[Path]:
        """Generate output path for a processed song.
        
        Args:
            song: The Song object
            output_dir: Base output directory
            
        Returns:
            Optional[Path]: Output path or None if it cannot be generated
        """
        try:
            # Get metadata for filename generation
            metadata = song.all_metadata
            
            # Required fields
            artist = metadata.get('artist', 'Unknown Artist')
            album = metadata.get('album', 'Unknown Album')
            title = metadata.get('title', 'Unknown Title')
            year = metadata.get('date', 'UnknownYear')
            
            # Optional fields with defaults
            # Handle track/disc numbers that may be in the format '1/1'
            track_str = metadata.get('tracknumber', '1')
            disc_str = metadata.get('discnumber', '1')
            
            # Extract just the first number if in format like '1/10'
            if '/' in track_str:
                track_str = track_str.split('/')[0]
            if '/' in disc_str:
                disc_str = disc_str.split('/')[0]
                
            try:
                track = int(track_str)
            except ValueError:
                track = 1
                
            try:
                disc = int(disc_str)
            except ValueError:
                disc = 1
            
            # Format variables for pattern
            format_vars = {
                'artist': self._clean_filename(artist),
                'album': self._clean_filename(album),
                'title': self._clean_filename(title),
                'year': year[:4] if len(year) >= 4 else year,  # Extract year from date
                'track': track,
                'disc': disc
            }
            
            # Generate relative path
            rel_path = self.output_pattern.format(**format_vars)
            
            # Add extension
            rel_path = f"{rel_path}{song.filepath.suffix}"
            
            # Join with output directory
            output_path = output_dir / rel_path
            
            # Ensure path is not too long
            if len(str(output_path)) > Config.MAX_FILENAME_LENGTH:
                # Truncate title if path is too long
                title_short = title[:20] + "..." if len(title) > 20 else title
                format_vars['title'] = self._clean_filename(title_short)
                rel_path = self.output_pattern.format(**format_vars)
                rel_path = f"{rel_path}{song.filepath.suffix}"
                output_path = output_dir / rel_path
            
            return output_path
            
        except Exception as e:
            self.logger.error(f"Error generating output path: {e}")
            return None
    
    def _clean_filename(self, filename: str) -> str:
        """Clean a string for use in filenames.
        
        Args:
            filename: String to clean
            
        Returns:
            str: Cleaned string
        """
        # Replace illegal characters
        cleaned = re.sub(r'[\\/*?:"<>|]', '_', filename)
        
        # Replace multiple spaces with a single space
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Trim spaces
        cleaned = cleaned.strip()
        
        # Ensure not empty
        if not cleaned:
            cleaned = "Unknown"
        
        return cleaned
    
    def process_directory(self, input_dir: Path, output_dir: Path, force_update: bool = False) -> List[Path]:
        """Process all compatible audio files in a directory.
        
        Args:
            input_dir: Input directory
            output_dir: Output directory
            force_update: Force update even if metadata exists
            
        Returns:
            List[Path]: List of successfully processed files
        """
        input_dir = Path(input_dir)
        output_dir = Path(output_dir)
        
        # Create output directory if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Find all compatible audio files
        audio_files = self._get_audio_files(input_dir)
        self.logger.info(f"Found {len(audio_files)} compatible audio files in {input_dir}")
        
        # Process each file
        processed_files = []
        for file_path in audio_files:
            if self.process_file(file_path, output_dir, force_update):
                processed_files.append(file_path)
        
        self.logger.info(f"Successfully processed {len(processed_files)} of {len(audio_files)} files")
        return processed_files
    
    def _get_audio_files(self, directory: Path) -> List[Path]:
        """Get all compatible audio files in a directory.
        
        Args:
            directory: Directory to search
            
        Returns:
            List[Path]: List of audio file paths
        """
        audio_files = []
        
        for file_path in directory.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in Config.SUPPORTED_AUDIO_FORMATS:
                audio_files.append(file_path)
        
        return audio_files
    
    def validate_setup(self) -> Dict[str, bool]:
        """Validate the setup of the processor.
        
        Returns:
            Dict[str, bool]: Dictionary of validation results
        """
        validations = {
            'api_key': False,
            'fpcalc': False
        }
        
        # Validate API key
        if self.api_key:
            validations['api_key'] = self.acoustid_cog.validate_api_key()
        
        # Validate fpcalc
        if self.fpcalc_path:
            validations['fpcalc'] = Path(self.fpcalc_path).is_file()
        
        return validations