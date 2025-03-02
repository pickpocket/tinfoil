"""
@file musicbrainz_cog.py
@brief Cog for handling MusicBrainz metadata operations.
"""
import musicbrainzngs
from typing import Optional, Dict, Any, List, Tuple
import logging
import json
import difflib
import traceback
import requests

from base_cog import BaseCog
from song import Song
from config import Config


class MusicBrainzCog(BaseCog):
    """Handle MusicBrainz metadata operations."""
    
    # Define what tags this cog needs as input
    input_tags = ['musicbrainz_recordingid']
    
    # Define what tags this cog provides as output
    output_tags = [
        'title', 
        'artist', 
        'album',
        'albumartist',
        'date',
        'tracknumber',
        'discnumber',
        'genre',
        'musicbrainz_albumid',
        'musicbrainz_artistid',
        'musicbrainz_albumartistid'
    ]
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize MusicBrainzCog.
        
        Args:
            logger: Logger instance
        """
        super().__init__(logger)
        
        # Initialize MusicBrainz API
        musicbrainzngs.set_useragent(
            Config.MB_APP_NAME,
            Config.MB_VERSION,
            Config.MB_CONTACT
        )
        musicbrainzngs.set_format("json")
    
    def process(self, song: Song) -> bool:
        """Process metadata for a song.
        
        This method fetches detailed metadata from MusicBrainz using the
        recording ID and updates the song metadata.
        
        Args:
            song: The Song object to process
            
        Returns:
            bool: True if processing was successful, False otherwise
        """
        if not self.can_process(song):
            self.logger.warning(f"Missing required metadata for MusicBrainz processing")
            return False
        
        try:
            # Get MusicBrainz recording ID
            recording_id = song.all_metadata.get('musicbrainz_recordingid')
            
            # Get existing metadata for comparison
            existing_metadata = self._extract_existing_metadata(song)
            
            # OVERRIDE: Make a direct request to the MusicBrainz API to get release information
            # This is more reliable than going through the library's get_recording_by_id
            release_data = self._direct_fetch_release_for_recording(recording_id)
            
            if not release_data or not release_data.get('releases'):
                self.logger.warning(f"No releases found for recording {recording_id}")
                return False
            
            releases = release_data.get('releases', [])
            self.logger.info(f"Found {len(releases)} releases for processing")
            
            # Find best matching release
            best_match = self.find_best_matching_release(releases, existing_metadata)
            
            if best_match:
                self.logger.info(f"Found best matching release: {best_match.get('title')}")
                album_release = best_match
                date_release = best_match  # Use same release for date
            else:
                # If no good match, pick a suitable release
                album_release, date_release = self.pick_best_releases(releases)
                if not album_release:
                    self.logger.warning(f"No suitable release found for recording {recording_id}")
                    return False
            
            # Get release details
            release_id = album_release.get('id')
            detailed_release = self.get_release_metadata(release_id)
            
            # Prepare metadata
            metadata = self._prepare_metadata(
                release_data,  # Use the recording data from our direct fetch
                album_release,
                date_release,
                detailed_release
            )
            
            # Update song metadata
            self.merge_metadata(song, metadata)
            
            self.logger.info(f"Successfully processed MusicBrainz metadata for {song.filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing metadata for {song.filepath}: {e}")
            self.logger.error(traceback.format_exc())
            return False
    
    def _direct_fetch_release_for_recording(self, recording_id: str) -> Dict[str, Any]:
        """Directly fetch release data for a recording using custom request.
        
        This is a more reliable way to get release information for a recording.
        
        Args:
            recording_id: MusicBrainz recording ID
            
        Returns:
            Dict[str, Any]: Recording data with releases
        """
        
        # Set up the headers
        headers = {
            'User-Agent': f"{Config.MB_APP_NAME}/{Config.MB_VERSION} ( {Config.MB_CONTACT} )"
        }
        
        # Set up the URL with proper includes
        url = f"https://musicbrainz.org/ws/2/recording/{recording_id}?fmt=json&inc=releases"
        
        self.logger.debug(f"Making direct request to MusicBrainz API: {url}")
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            self.logger.debug(f"Received direct response with keys: {list(data.keys())}")
            
            if 'releases' in data:
                self.logger.debug(f"Found {len(data['releases'])} releases in response")
            else:
                self.logger.debug("No 'releases' key in response")
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error in direct fetch: {e}")
            self.logger.error(traceback.format_exc())
            return {}
    
    def _extract_existing_metadata(self, song: Song) -> Dict[str, str]:
        """Extract relevant existing metadata from a song.
        
        Args:
            song: The Song object
            
        Returns:
            Dict[str, str]: Existing metadata
        """
        metadata = {}
        
        for key in ['title', 'artist', 'album', 'albumartist']:
            if key in song.all_metadata:
                metadata[key] = song.all_metadata[key]
        
        return metadata
    
    def calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate string similarity ratio.
        
        Args:
            str1: First string
            str2: Second string
            
        Returns:
            float: Similarity ratio (0-1)
        """
        if not str1 or not str2:
            return 0.0
        return difflib.SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

    def find_best_matching_release(
        self,
        releases: List[Dict[str, Any]],
        existing_metadata: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        """Find release that best matches existing metadata.
        
        Args:
            releases: List of releases
            existing_metadata: Existing metadata
            
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
                artist_name = self.get_english_artist(release['artist-credit'])
            
            artist_score = self.calculate_similarity(
                artist_name,
                existing_metadata.get('albumartist', existing_metadata.get('artist', ''))
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

    def get_recording_metadata(self, recording_id: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed recording metadata from MusicBrainz.
        
        Args:
            recording_id: MusicBrainz recording ID
            
        Returns:
            Optional[Dict[str, Any]]: Recording metadata if found
        """
        try:
            includes = ["artists", "releases", "artist-credits"]
            self.logger.info(f"Fetching MusicBrainz recording: {recording_id}")
            
            result = musicbrainzngs.get_recording_by_id(
                recording_id,
                includes=includes
            )
            
            if result:
                self.logger.info("Successfully retrieved recording metadata")
                return result
            else:
                self.logger.warning("No recording data found in response")
                return None
                
        except musicbrainzngs.WebServiceError as e:
            self.logger.error(f"MusicBrainz API error: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error fetching recording metadata: {e}")
            return None

    def get_release_metadata(self, release_id: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed release metadata from MusicBrainz.
        
        Args:
            release_id: MusicBrainz release ID
            
        Returns:
            Optional[Dict[str, Any]]: Release metadata if found
        """
        try:
            includes = ["artists", "recordings", "artist-credits", "labels", "media"]
            self.logger.info(f"Fetching MusicBrainz release: {release_id}")
            
            result = musicbrainzngs.get_release_by_id(
                release_id,
                includes=includes
            )
            
            if 'release' in result:
                return result['release']
            return None
            
        except musicbrainzngs.WebServiceError as e:
            self.logger.error(f"MusicBrainz API error: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error fetching release metadata: {e}")
            return None

    def find_english_release(self, releases: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Look for a release with English text representation.
        
        Args:
            releases: List of release dictionaries
            
        Returns:
            Optional[Dict[str, Any]]: English release if found
        """
        for release in releases:
            if release.get('text-representation', {}).get('language') == 'eng':
                return release
        return None

    def find_official_release(self, releases: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find a release with official status.
        
        Args:
            releases: List of release dictionaries
            
        Returns:
            Optional[Dict[str, Any]]: Official release if found
        """
        for release in releases:
            if release.get('status') == 'Official':
                return release
        return None

    def has_date(self, release: Dict[str, Any]) -> bool:
        """Check if release has date information.
        
        Args:
            release: Release dictionary
            
        Returns:
            bool: True if release has date information
        """
        if 'date' in release and release['date']:
            return True
        
        # Check both formats
        for key in ['release-events', 'release-event-list']:
            if key in release and release[key]:
                for event in release[key]:
                    if 'date' in event and event['date']:
                        return True
        
        return False

    def extract_year_from_release(self, release: Optional[Dict[str, Any]]) -> str:
        """Extract year from release metadata.
        
        Args:
            release: Release dictionary
            
        Returns:
            str: Year or 'UnknownYear' if not found
        """
        if not release:
            return "UnknownYear"

        # Check direct date field
        if 'date' in release and release['date']:
            date_str = release['date']
            if '-' in date_str:
                return date_str.split('-')[0]
            return date_str

        # Check both event list formats
        for key in ['release-events', 'release-event-list']:
            if key in release:
                events = release[key]
                if events and isinstance(events, list):
                    for event in events:
                        if 'date' in event and event['date']:
                            date_str = event['date']
                            if '-' in date_str:
                                return date_str.split('-')[0]
                            return date_str

        return "UnknownYear"

    def get_english_artist(self, artist_credit: List[Any]) -> str:
        """Build artist string from MusicBrainz artist-credit array.
        
        Args:
            artist_credit: Artist credit list from MusicBrainz
            
        Returns:
            str: Combined artist name string
        """
        result = []
        for credit in artist_credit:
            if isinstance(credit, dict):
                if 'artist' in credit:
                    artist = credit['artist']
                    # Prefer sort-name for better organization
                    name = artist.get('sort-name') or artist.get('name', '')
                    result.append(name)
                    if 'joinphrase' in credit:
                        result.append(credit['joinphrase'])
            elif isinstance(credit, str):
                result.append(credit)
        return ''.join(result).strip()

    def pick_best_releases(
        self,
        releases: List[Dict[str, Any]]
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Select appropriate album and date releases from available releases.
        
        Args:
            releases: List of available releases
            
        Returns:
            Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]: Selected album and date releases
        """
        if not releases:
            return None, None
        
        # For album name, prefer English release
        eng_release = self.find_english_release(releases)
        album_release = eng_release or self.find_official_release(releases) or releases[0]
        
        # For date info
        if self.has_date(album_release):
            date_release = album_release
        else:
            date_release = self.find_official_release(releases)
            if not (date_release and self.has_date(date_release)):
                # Find any release with date
                for release in releases:
                    if self.has_date(release):
                        date_release = release
                        break
                else:
                    date_release = album_release
        
        return album_release, date_release

    def get_track_number(
        self,
        release: Dict[str, Any],
        recording_id: str
    ) -> Optional[int]:
        """Get track number from release metadata.
        
        Args:
            release: Release dictionary
            recording_id: MusicBrainz recording ID
            
        Returns:
            Optional[int]: Track number if found
        """
        # Check both formats
        for media_key, track_key in [('media', 'tracks'), ('medium-list', 'track-list')]:
            if media_key in release:
                for medium in release[media_key]:
                    for track in medium.get(track_key, []):
                        # Try two ways to match the recording
                        recording_match = False
                        
                        # Direct recording ID match
                        if track.get('recording', {}).get('id') == recording_id:
                            recording_match = True
                        
                        # Recording ID in 'recording' attribute
                        if track.get('recording-id') == recording_id:
                            recording_match = True
                            
                        if recording_match:
                            try:
                                return int(track.get('position', 0))
                            except (ValueError, TypeError):
                                pass
        
        return None

    def get_disc_number(
        self,
        release: Dict[str, Any],
        recording_id: str
    ) -> Optional[int]:
        """Get disc number from release metadata.
        
        Args:
            release: Release dictionary
            recording_id: MusicBrainz recording ID
            
        Returns:
            Optional[int]: Disc number if found
        """
        # Check both formats
        for media_key, track_key in [('media', 'tracks'), ('medium-list', 'track-list')]:
            if media_key in release:
                for i, medium in enumerate(release[media_key], 1):
                    for track in medium.get(track_key, []):
                        # Try two ways to match the recording
                        recording_match = False
                        
                        # Direct recording ID match
                        if track.get('recording', {}).get('id') == recording_id:
                            recording_match = True
                        
                        # Recording ID in 'recording' attribute
                        if track.get('recording-id') == recording_id:
                            recording_match = True
                            
                        if recording_match:
                            return i
        
        return None
    
    def _prepare_metadata(
        self,
        recording_data: Dict[str, Any],
        album_release: Dict[str, Any],
        date_release: Dict[str, Any],
        detailed_release: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Prepare metadata from MusicBrainz data.
        
        Args:
            recording_data: Recording data
            album_release: Album release data
            date_release: Release data with date information
            detailed_release: Detailed release data (optional)
            
        Returns:
            Dict[str, Any]: Prepared metadata
        """
        metadata = {}
        
        # Basic metadata from recording data
        metadata['title'] = recording_data.get('title', 'Unknown Title')
        
        # Artist
        if 'artist-credit' in recording_data:
            metadata['artist'] = self.get_english_artist(recording_data['artist-credit'])
        
        # Album
        metadata['album'] = album_release.get('title', 'Unknown Album')
        
        # Album artist
        if 'artist-credit' in album_release:
            metadata['albumartist'] = self.get_english_artist(album_release['artist-credit'])
        
        # Date
        if 'date' in date_release and date_release['date']:
            metadata['date'] = date_release['date']
        else:
            metadata['date'] = self.extract_year_from_release(date_release)
        
        # MusicBrainz IDs
        metadata['musicbrainz_recordingid'] = recording_data.get('id', '')
        metadata['musicbrainz_albumid'] = album_release.get('id', '')
        
        # Artist IDs
        if 'artist-credit' in recording_data:
            for credit in recording_data['artist-credit']:
                if isinstance(credit, dict) and 'artist' in credit:
                    metadata['musicbrainz_artistid'] = credit['artist'].get('id', '')
                    break
        
        # Album artist IDs
        if 'artist-credit' in album_release:
            for credit in album_release['artist-credit']:
                if isinstance(credit, dict) and 'artist' in credit:
                    metadata['musicbrainz_albumartistid'] = credit['artist'].get('id', '')
                    break
        
        # Track and disc numbers
        rec_id = recording_data.get('id', '')
        
        # Try to get from detailed release first
        if detailed_release:
            track_num = self.get_track_number(detailed_release, rec_id)
            disc_num = self.get_disc_number(detailed_release, rec_id)
            
            if track_num:
                metadata['tracknumber'] = str(track_num)
            if disc_num:
                metadata['discnumber'] = str(disc_num)
        
        return metadata