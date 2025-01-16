import argparse
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import logging
from mutagen.flac import FLAC
import difflib

from cogs.acoustid_api import AcoustIDCog
from cogs.metadata import MetadataCog
from cogs.cover_art import CoverArtCog


from utils.logging_utils import setup_logging
from utils.file_structure import *


class FlacParser:
    def __init__(
        self,
        api_key: str,
        fpcalc_path: Optional[str] = None,
        logger: Optional[logging.Logger] = None
    ):

        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize cogs
        #TODO: get fpcalc_path from config.py
        self.acoustid_cog = AcoustIDCog(api_key, fpcalc_path, self.logger)
        self.metadata_cog = MetadataCog(self.logger)
        self.cover_art_cog = CoverArtCog(self.logger)


    def get_existing_metadata(self, file_path: Path) -> Dict[str, str]:
        """Extract existing metadata from FLAC file.
        
        Args:
            file_path (Path): Path to FLAC file
            
        Returns:
            Dict[str, str]: Dictionary of existing metadata
        """
        try:
            audio = FLAC(str(file_path))
            metadata = {
                'title': audio.get('title', [''])[0],
                'artist': audio.get('artist', [''])[0],
                'album': audio.get('album', [''])[0],
            }
            self.logger.debug(f"Existing metadata: {metadata}")
            return metadata
        except Exception as e:
            self.logger.warning(f"Could not read existing metadata: {e}")
            return {}
        
    #TODO: move this to a util functions file
    def calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate string similarity ratio.
        
        Args:
            str1 (str): First string
            str2 (str): Second string
            
        Returns:
            float: Similarity ratio (0-1)
        """
        if not str1 or not str2:
            return 0.0
        return difflib.SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

    #TODO: utils
    def find_best_matching_release(
        self,
        releases: List[Dict[str, Any]],
        existing_metadata: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        """Find release that best matches existing metadata.
        
        Args:
            releases (List[Dict[str, Any]]): List of releases
            existing_metadata (Dict[str, str]): Existing metadata
            
        Returns:
            Optional[Dict[str, Any]]: Best matching release
        """
        best_match = None
        best_score = 0.0
        
        for release in releases:
            # Calculate similarity scores
            title_score = self.calculate_similarity(
                release.get('title', ''),
                existing_metadata.get('album', '')
            )
            
            # Get artist from artist-credit
            artist_name = ''
            if 'artist-credit' in release:
                artist_name = ' '.join(
                    credit.get('name', '') 
                    for credit in release['artist-credit']
                )
            artist_score = self.calculate_similarity(
                artist_name,
                existing_metadata.get('artist', '')
            )
            
            # Combined score (weighted average)
            total_score = (title_score * 0.6) + (artist_score * 0.4)
            
            self.logger.debug(
                f"Release '{release.get('title')}' scores - "
                f"Title: {title_score:.2f}, Artist: {artist_score:.2f}, "
                f"Total: {total_score:.2f}"
            )
            
            if total_score > best_score:
                best_score = total_score
                best_match = release

        return best_match if best_score > 0.5 else None

    #TODO:utils?
    def _prepare_metadata(
        self,
        recording: Dict[str, Any],
        album_release: Dict[str, Any],
        date_release: Dict[str, Any]
    ) -> Dict[str, Any]:
        # Find the English title
        title = None
        
        # First check the release tracks
        if 'mediums' in album_release:
            for medium in album_release.get('mediums', []):
                for track in medium.get('tracks', []):
                    if track.get('title') and all(ord(c) < 128 for c in track['title']):
                        title = track['title']
                        break
                if title:
                    break
        
        # If no English title in tracks, try the album title if it's English
        if not title and album_release.get('title'):
            if all(ord(c) < 128 for c in album_release['title']):
                title = album_release['title']
        
        # Final fallback to the recording title if it's English
        if not title and recording.get('title'):
            if all(ord(c) < 128 for c in recording['title']):
                title = recording['title']
        
        # Last resort: use first title found
        if not title:
            title = (
                recording.get('title') or 
                album_release.get('title') or 
                'Unknown Title'
            )

        # Process artist credits
        artist_parts = []
        for credit in recording.get('artist-credit', []):
            if isinstance(credit, dict):
                # Get artist name (prefer English version)
                artist_name = credit['name']
                if not all(ord(c) < 128 for c in artist_name):
                    artist_name = (
                        credit['artist'].get('sort-name') or 
                        credit.get('artist', {}).get('name') or 
                        artist_name
                    )
                artist_parts.append(artist_name)
                
                # Add joinphrase (", feat. ", etc)
                if 'joinphrase' in credit:
                    artist_parts.append(credit['joinphrase'])
        
        artist_name = ''.join(artist_parts).strip()

        # Get album title (prefer English)
        album_title = album_release.get('title', 'Unknown Album')
        if not all(ord(c) < 128 for c in album_title):
            # Try to find English title in other releases
            for rel in recording.get('releases', []):
                if (rel.get('text-representation', {}).get('language') == 'eng' and 
                    all(ord(c) < 128 for c in rel.get('title', ''))):
                    album_title = rel['title']
                    break

        # Extract year
        year = None
        
        # First try the specific release date
        if 'date' in date_release:
            if isinstance(date_release['date'], str) and date_release['date'].strip():
                year = date_release['date'].split('-')[0]
        
        # Then try release events
        if not year and 'release-events' in date_release:
            events = date_release['release-events']
            if events and isinstance(events, list) and len(events) > 0:
                event_date = events[0].get('date')
                if event_date:
                    if isinstance(event_date, str):
                        year = event_date.split('-')[0]
                    elif isinstance(event_date, dict):
                        year = str(event_date.get('year'))
        
        # Then try first-release-date
        if not year and 'first-release-date' in recording:
            if recording['first-release-date']:
                year = recording['first-release-date'].split('-')[0]
        
        # Fallback
        if not year:
            year = "UnknownYear"

        # Get track number
        track_number = 1
        if 'mediums' in album_release:
            for medium in album_release['mediums']:
                for track in medium.get('tracks', []):
                    if 'recording' in track:
                        if track['recording'].get('id') == recording.get('id'):
                            track_number = track.get('position', 1)
                            break
                    # Direct match
                    elif track.get('id') == recording.get('id'):
                        track_number = track.get('position', 1)
                        break

        self.logger.debug(f"Prepared metadata - Title: {title}, Artist: {artist_name}, Album: {album_title}, Year: {year}")

        return {
            'title': title,
            'artist': artist_name,
            'album': album_title,
            'year': year,
            'track_number': track_number,
            'disc_number': 1,  # Default to 1 if not found
            'musicbrainz_recordingid': recording.get('id', ''),
            'musicbrainz_albumid': album_release.get('id', '')
        }
    
    def process_single_file(
        self,
        input_file: Path,
        output_dir: Path,
        force_update: bool = False
    ) -> bool:
        """Process a single FLAC file."""
        try:
            self.logger.info(f"Processing file: {input_file}")
            
            # Get existing metadata first
            existing_metadata = self.get_existing_metadata(input_file)
            self.logger.info(f"Found existing metadata: {existing_metadata}")
            
            # Generate fingerprint
            fingerprint, duration = self.acoustid_cog.get_fingerprint(str(input_file))
            if not fingerprint or not duration:
                self.logger.warning(f"Could not generate fingerprint for {input_file}")
                return False
                
            # Look up metadata
            recording_data = self.acoustid_cog.lookup_fingerprint(fingerprint, duration)
            if not recording_data:
                self.logger.warning(f"No metadata found for {input_file}")
                return False
                
            # Get detailed MusicBrainz metadata
            mb_recording = self.metadata_cog.get_recording_metadata(recording_data['id'])
            if not mb_recording:
                self.logger.warning(f"No MusicBrainz data found for {input_file}")
                return False
                
            # Get releases and find best match
            releases = mb_recording.get('releases', [])
            if not releases:
                self.logger.warning(f"No releases found for {input_file}")
                return False

            # Find best matching release
            best_match = self.find_best_matching_release(releases, existing_metadata)
            
            if best_match:
                self.logger.info(f"Found best matching release: {best_match.get('title')}")
                album_release = best_match
                date_release = best_match  # Use same release for date
            else:
                # If no good match, fall back to user selection
                self.logger.info("No good automatic match found, falling back to user selection")
                album_release, date_release = self.metadata_cog.pick_album_releases(releases)
                
            if not album_release:
                self.logger.warning(f"No suitable release found for {input_file}")
                return False

            # Extract metadata
            metadata = self._prepare_metadata(mb_recording, album_release, date_release)
            
            # Get cover art
            cover_art = self.cover_art_cog.get_cover_art_data(album_release['id'])
            
            # Create output directory structure
            output_path = setup_directory_structure(
                output_dir,
                metadata['artist'],
                metadata['album'],
                metadata['year']
            )
            
            # Create new file path
            new_file_path = create_file_path(
                output_path,
                metadata['artist'],
                metadata['album'],
                int(metadata['track_number']),
                metadata['title']
            )
            
            # Copy file
            if not copy_file(input_file, new_file_path):
                return False
                
            # Update metadata
            success = update_flac_metadata(
                new_file_path,
                metadata,
                cover_art
            )
            
            if success:
                self.logger.info(f"Successfully processed {input_file}")
            return success
            
        except Exception as e:
            self.logger.error(f"Error processing {input_file}: {e}")
            return False

    def process_directory(
        self,
        input_dir: str,
        output_dir: str,
        force_update: bool = False
    ) -> None:
        """Process all FLAC files in a directory.
        
        Args:
            input_dir (str): Input directory path
            output_dir (str): Output directory path
            force_update (bool): Force metadata update even if exists
        """
        try:
            input_path = Path(input_dir).resolve()
            output_path = Path(output_dir).resolve()
            
            if not input_path.exists():
                raise FileNotFoundError(f"Input directory not found: {input_dir}")
            
            output_path.mkdir(parents=True, exist_ok=True)
            
            flac_files = get_flac_files(input_path)
            self.logger.info(f"Found {len(flac_files)} FLAC files to process")
            
            for flac_file in flac_files:
                if not self.process_single_file(flac_file, output_path, force_update):
                    self.logger.warning(f"Failed to process {flac_file}")
                    
            clean_directory(output_path)
            
        except Exception as e:
            self.logger.error(f"Error processing directory: {e}")
            raise

def main():
    parser = argparse.ArgumentParser(
        description='Fetch FLAC metadata, embed cover art, and organize files.'
    )
    parser.add_argument('-k', '--api-key', required=True, help='AcoustID API key')
    parser.add_argument('-i', '--input-dir', required=True, help='Input directory')
    parser.add_argument('-o', '--output-dir', required=True, help='Output directory')
    parser.add_argument('--force', action='store_true', help='Force metadata update')
    parser.add_argument('--fpcalc-path', help='Path to fpcalc executable')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    logger = setup_logging(verbose=args.verbose)
    
    try:
        tagger = FlacParser(args.api_key, args.fpcalc_path, logger)
        tagger.process_directory(args.input_dir, args.output_dir, args.force)
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()