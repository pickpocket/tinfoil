from pathlib import Path
from typing import List, Optional, Dict, Any, Type
import logging
import shutil
import re

from base_cog import BaseCog
from song import Song
from cogs.acoustid_cog import AcoustIDCog
from cogs.musicbrainz_cog import MusicBrainzCog
from cogs.cover_art_cog import CoverArtCog
from cogs.tag_based_match_cog import TagBasedMatchCog

class TinfoilProcessor:
    def __init__(
        self,
        api_key: Optional[str] = None,
        fpcalc_path: Optional[str] = None,
        output_pattern: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
        custom_cogs: Optional[List[BaseCog]] = None
    ):
        self.logger = logger if logger else logging.getLogger(__name__)
        
        self.api_key = api_key
        if not self.api_key:
            raise ValueError("AcoustID API key is required")
        
        self.fpcalc_path = fpcalc_path
        if not self.fpcalc_path:
            self.logger.warning("fpcalc executable not found, fingerprinting may fail")
        
        self.output_pattern = output_pattern if output_pattern else "{artist}/{year} - {album}/{track:02d} - {title}"
        self.max_filename_length = 250
        self.supported_formats = ['.flac']
        
        if custom_cogs:
            self.cogs = custom_cogs
            self.logger.info(f"Using custom cog pipeline with {len(custom_cogs)} cogs")
        else:
            # Default pipeline with essential cogs
            self.acoustid_cog = AcoustIDCog(self.api_key, self.fpcalc_path, self.logger)
            self.tag_based_match_cog = TagBasedMatchCog(self.logger)
            self.musicbrainz_cog = MusicBrainzCog(self.logger)
            self.cover_art_cog = CoverArtCog(self.logger)
            
            self.cogs: List[BaseCog] = [
                self.acoustid_cog,
                self.tag_based_match_cog,
                self.musicbrainz_cog,
                self.cover_art_cog
            ]
            
            self.logger.info(f"Using default cog pipeline with {len(self.cogs)} cogs")
    
    def process_file(self, file_path: Path, output_dir: Path, force_update: bool = False) -> bool:
        if not file_path or not file_path.exists():
            self.logger.error(f"File not found: {file_path}")
            return False
        
        self.logger.info(f"Processing file: {file_path}")
        
        song = Song(file_path, self.logger)
        if not song:
            self.logger.error(f"Failed to load song: {file_path}")
            return False
        
        for cog in self.cogs:
            cog_name = cog.__class__.__name__
            
            if not force_update and all(tag in song.all_metadata for tag in cog.output_tags):
                self.logger.info(f"Skipping {cog_name}, metadata already exists")
                continue
            
            if not cog.can_process(song):
                self.logger.warning(f"{cog_name} cannot process {file_path}, missing required metadata")
                continue
            
            self.logger.info(f"Processing with {cog_name}")
            if not cog.process(song):
                self.logger.warning(f"{cog_name} processing failed for {file_path}")
        
        output_path = self._generate_output_path(song, output_dir)
        if not output_path:
            self.logger.warning(f"Could not generate output path for {file_path}")
            return False
        
        if not output_path.parent.exists():
            output_path.parent.mkdir(parents=True, exist_ok=True)
        
        new_song = song.copy_to(output_path)
        if not new_song:
            self.logger.warning(f"Could not copy {file_path} to {output_path}")
            return False
        
        new_song.all_metadata = song.all_metadata.copy()
        
        if new_song.save_overwrite():
            self.logger.info(f"Successfully processed {file_path} to {output_path}")
            return True
        
        self.logger.warning(f"Could not save metadata to {output_path}")
        return False
    
    def _generate_output_path(self, song: Song, output_dir: Path) -> Optional[Path]:
        if not song or not hasattr(song, 'all_metadata'):
            return None
        
        metadata = song.all_metadata
        
        artist = metadata.get('artist', 'Unknown Artist')
        album = metadata.get('album', 'Unknown Album')
        title = metadata.get('title', 'Unknown Title')
        year = metadata.get('date', 'UnknownYear')
        
        track_str = metadata.get('tracknumber', '1')
        disc_str = metadata.get('discnumber', '1')
        
        if '/' in track_str:
            track_str = track_str.split('/')[0]
        if '/' in disc_str:
            disc_str = disc_str.split('/')[0]
        
        track = 1
        if track_str.isdigit():
            track = int(track_str)
        
        disc = 1
        if disc_str.isdigit():
            disc = int(disc_str)
        
        format_vars = {
            'artist': self._clean_filename(artist),
            'album': self._clean_filename(album),
            'title': self._clean_filename(title),
            'year': year[:4] if len(year) >= 4 else year,
            'track': track,
            'disc': disc
        }
        
        rel_path = self.output_pattern.format(**format_vars)
        rel_path = f"{rel_path}{song.filepath.suffix}"
        
        output_path = output_dir / rel_path
        
        if len(str(output_path)) > self.max_filename_length:
            title_short = title[:20] + "..." if len(title) > 20 else title
            format_vars['title'] = self._clean_filename(title_short)
            rel_path = self.output_pattern.format(**format_vars)
            rel_path = f"{rel_path}{song.filepath.suffix}"
            output_path = output_dir / rel_path
        
        return output_path
    
    def _clean_filename(self, filename: str) -> str:
        if not filename:
            return "Unknown"
        
        cleaned = re.sub(r'[\\/*?:"<>|]', '_', filename)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = cleaned.strip()
        
        if not cleaned:
            cleaned = "Unknown"
        
        return cleaned
    
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
    
    def validate_setup(self) -> Dict[str, bool]:
        validations = {
            'api_key': False,
            'fpcalc': False
        }
        
        if self.api_key:
            validations['api_key'] = self.acoustid_cog.validate_api_key()
        
        if self.fpcalc_path:
            validations['fpcalc'] = Path(self.fpcalc_path).is_file()
        
        return validations