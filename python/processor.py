from pathlib import Path
from typing import List, Optional, Dict, Any, Type
import logging
import shutil
import re

from base_cog import BaseCog
from song import Song

class TinfoilProcessor:
    def __init__(
        self,
        pipeline: List[BaseCog],
        output_pattern: Optional[str] = None,
        logger: Optional[logging.Logger] = None
    ):
        self.logger = logger if logger else logging.getLogger(__name__)
        
        if not pipeline:
            raise ValueError("A cog pipeline must be provided to the processor.")
        
        self.cogs = pipeline
        self.logger.info(f"Processor initialized with {len(self.cogs)} cogs: {[c.__class__.__name__ for c in self.cogs]}")

        self.output_pattern = output_pattern if output_pattern else "{artist}/{year} - {album}/{track:02d} - {title}"
        self.max_filename_length = 250
        self.supported_formats = ['.flac']

    def process_file(self, file_path: Path, output_dir: Path, force_update: bool = False) -> bool:
        if not file_path or not file_path.exists():
            self.logger.error(f"File not found: {file_path}")
            return False
        
        self.logger.info(f"Processing file: {file_path}")
        
        try:
            song = Song(file_path, self.logger)
        except (FileNotFoundError, ValueError) as e:
            self.logger.error(f"Failed to load song {file_path}: {e}")
            return False
        
        for cog in self.cogs:
            cog_name = cog.__class__.__name__
            
            # Check if all output tags for this cog already exist in the metadata
            if not force_update and all(tag in song.all_metadata for tag in cog.output_tags if cog.output_tags):
                self.logger.info(f"Skipping {cog_name} for {file_path}, all output tags already exist.")
                continue
            
            if not cog.can_process(song):
                self.logger.debug(f"{cog_name} cannot process {file_path} due to missing input tags.")
                continue
            
            self.logger.info(f"Executing cog '{cog_name}' for {file_path}")
            try:
                if not cog.process(song):
                    self.logger.warning(f"Cog '{cog_name}' processing failed for {file_path}")
            except Exception as e:
                self.logger.error(f"An exception occurred in cog '{cog_name}' for {file_path}: {e}", exc_info=True)

        output_path = self._generate_output_path(song, output_dir)
        if not output_path:
            self.logger.warning(f"Could not generate output path for {file_path}")
            # Still try to save metadata to the original file if an output path can't be made
            if song.save_overwrite():
                self.logger.info(f"Successfully updated metadata for original file: {file_path}")
                return True
            return False
        
        if not output_path.parent.exists():
            output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # If the destination is the same as the source, just save over it.
        if output_path.resolve() == file_path.resolve():
            self.logger.info(f"Output path is the same as input; saving metadata to {file_path}")
            if song.save_overwrite():
                self.logger.info(f"Successfully processed and saved {file_path}")
                return True
        else:
            # Otherwise, copy to the new location and save metadata there.
            new_song = song.copy_to(output_path)
            if not new_song:
                self.logger.error(f"Could not copy {file_path} to {output_path}")
                return False
            
            new_song.all_metadata = song.all_metadata.copy()
            if new_song.save_overwrite():
                self.logger.info(f"Successfully processed {file_path} to {output_path}")
                return True
        
        self.logger.error(f"Could not save metadata for {file_path}")
        return False
    
    def _generate_output_path(self, song: Song, output_dir: Path) -> Optional[Path]:
        if not song or not hasattr(song, 'all_metadata'):
            return None
        
        metadata = song.all_metadata
        
        # Provide default values for key metadata to prevent errors
        artist = metadata.get('artist', 'Unknown Artist')
        album = metadata.get('album', 'Unknown Album')
        title = metadata.get('title', song.filepath.stem)
        year = metadata.get('date', '0000')
        
        track_str = str(metadata.get('tracknumber', '0'))
        disc_str = str(metadata.get('discnumber', '1'))
        
        # Sanitize track and disc numbers
        track = int(track_str.split('/')[0]) if track_str.split('/')[0].isdigit() else 0
        disc = int(disc_str.split('/')[0]) if disc_str.split('/')[0].isdigit() else 1
        
        # Safely format the output path
        try:
            format_vars = {
                'artist': self._clean_filename(artist),
                'album': self._clean_filename(album),
                'title': self._clean_filename(title),
                'year': year[:4] if isinstance(year, str) and len(year) >= 4 else year,
                'track': track,
                'disc': disc
            }
            rel_path_str = self.output_pattern.format(**format_vars)
        except (KeyError, TypeError) as e:
            self.logger.error(f"Invalid output pattern or missing metadata for formatting: {e}")
            # Fallback to a simple file name in the output directory
            rel_path_str = self._clean_filename(song.filepath.name)

        rel_path = f"{rel_path_str}{song.filepath.suffix}"
        
        output_path = output_dir / rel_path
        
        # Truncate path if it's too long
        if len(str(output_path)) > self.max_filename_length:
            self.logger.warning(f"Generated path is too long, attempting to shorten: {output_path}")
            title_short = (title[:50] + '...') if len(title) > 53 else title
            format_vars['title'] = self._clean_filename(title_short)
            rel_path_str = self.output_pattern.format(**format_vars)
            rel_path = f"{rel_path_str}{song.filepath.suffix}"
            output_path = output_dir / rel_path

        return output_path
    
    def _clean_filename(self, filename: str) -> str:
        if not filename:
            return "Unknown"
        
        # Replace invalid characters with an underscore
        cleaned = re.sub(r'[\\/*?:"<>|]', '_', str(filename))
        # Collapse whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned if cleaned else "Unknown"
    
    def process_directory(self, input_dir: Path, output_dir: Path, force_update: bool = False) -> List[Path]:
        input_dir = Path(input_dir)
        output_dir = Path(output_dir)
        
        if not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)
        
        audio_files = self._get_audio_files(input_dir)
        self.logger.info(f"Found {len(audio_files)} compatible audio files in {input_dir}")
        
        processed_files = []
        for file_path in audio_files:
            if self.process_file(file_path, output_dir, force_update):
                processed_files.append(file_path)
        
        self.logger.info(f"Successfully processed {len(processed_files)} of {len(audio_files)} files")
        return processed_files
    
    def _get_audio_files(self, directory: Path) -> List[Path]:
        audio_files = []
        
        for file_path in directory.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in self.supported_formats:
                audio_files.append(file_path)
        
        return audio_files