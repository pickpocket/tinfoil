import musicbrainzngs
from typing import Optional, Dict, Any, List, Tuple
import logging
import json
import difflib
import traceback
import requests
from base_cog import BaseCog
from song import Song

class MusicBrainzCog(BaseCog):
    input_tags = ['musicbrainz_recordingid']
    
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
        super().__init__(logger)
        
        musicbrainzngs.set_useragent(
            "tinfoil",
            "1.0",
            "imsoupp@protonmail.com"
        )
        musicbrainzngs.set_format("json")
    
    def process(self, song: Song) -> bool:
        if not self.can_process(song):
            self.logger.warning(f"Missing required metadata for MusicBrainz processing")
            return False
        
        recording_id = song.all_metadata.get('musicbrainz_recordingid')
        existing_metadata = self._extract_existing_metadata(song)
        
        release_data = self._direct_fetch_release_for_recording(recording_id)
        
        if not release_data or not release_data.get('releases'):
            self.logger.warning(f"No releases found for recording {recording_id}")
            return False
        
        releases = release_data.get('releases', [])
        self.logger.info(f"Found {len(releases)} releases for processing")
        
        best_match = self.find_best_matching_release(releases, existing_metadata)
        
        if best_match:
            self.logger.info(f"Found best matching release: {best_match.get('title')}")
            album_release = best_match
            date_release = best_match
        else:
            album_release, date_release = self.pick_best_releases(releases)
            if not album_release:
                self.logger.warning(f"No suitable release found for recording {recording_id}")
                return False
        
        release_id = album_release.get('id')
        detailed_release = self.get_release_metadata(release_id)
        
        metadata = self._prepare_metadata(
            release_data,
            album_release,
            date_release,
            detailed_release
        )
        
        self.merge_metadata(song, metadata)
        
        self.logger.info(f"Successfully processed MusicBrainz metadata for {song.filepath}")
        return True
    
    def _direct_fetch_release_for_recording(self, recording_id: str) -> Dict[str, Any]:
        headers = {
            'User-Agent': "tinfoil/1.0 ( imsoupp@protonmail.com )"
        }
        
        url = f"https://musicbrainz.org/ws/2/recording/{recording_id}?fmt=json&inc=releases"
        
        self.logger.debug(f"Making direct request to MusicBrainz API: {url}")
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        self.logger.debug(f"Received direct response with keys: {list(data.keys())}")
        
        if 'releases' in data:
            self.logger.debug(f"Found {len(data['releases'])} releases in response")
        else:
            self.logger.debug("No 'releases' key in response")
        
        return data
    
    def _extract_existing_metadata(self, song: Song) -> Dict[str, str]:
        metadata = {}
        
        for key in ['title', 'artist', 'album', 'albumartist']:
            if key in song.all_metadata:
                metadata[key] = song.all_metadata[key]
        
        return metadata
    
    def calculate_similarity(self, str1: str, str2: str) -> float:
        if not str1 or not str2:
            return 0.0
        return difflib.SequenceMatcher(None, str1.lower(), str2.lower()).ratio()
    
    def find_best_matching_release(
        self,
        releases: List[Dict[str, Any]],
        existing_metadata: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        best_match = None
        best_score = 0.0
        
        for release in releases:
            title_score = self.calculate_similarity(
                release.get('title', ''),
                existing_metadata.get('album', '')
            )
            
            artist_name = ''
            if 'artist-credit' in release:
                artist_name = self.get_english_artist(release['artist-credit'])
            
            artist_score = self.calculate_similarity(
                artist_name,
                existing_metadata.get('albumartist', existing_metadata.get('artist', ''))
            )
            
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
        includes = ["artists", "releases", "artist-credits"]
        self.logger.info(f"Fetching MusicBrainz recording: {recording_id}")
        
        result = musicbrainzngs.get_recording_by_id(
            recording_id,
            includes=includes
        )
        
        if result:
            self.logger.info("Successfully retrieved recording metadata")
            return result
        
        self.logger.warning("No recording data found in response")
        return None
    
    def get_release_metadata(self, release_id: str) -> Optional[Dict[str, Any]]:
        includes = ["artists", "recordings", "artist-credits", "labels", "media"]
        self.logger.info(f"Fetching MusicBrainz release: {release_id}")
        
        result = musicbrainzngs.get_release_by_id(
            release_id,
            includes=includes
        )
        
        if 'release' in result:
            return result['release']
        return None
    
    def find_english_release(self, releases: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        for release in releases:
            if release.get('text-representation', {}).get('language') == 'eng':
                return release
        return None
    
    def find_official_release(self, releases: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        for release in releases:
            if release.get('status') == 'Official':
                return release
        return None
    
    def has_date(self, release: Dict[str, Any]) -> bool:
        if 'date' in release and release['date']:
            return True
        
        for key in ['release-events', 'release-event-list']:
            if key in release and release[key]:
                for event in release[key]:
                    if 'date' in event and event['date']:
                        return True
        
        return False
    
    def extract_year_from_release(self, release: Optional[Dict[str, Any]]) -> str:
        if not release:
            return "UnknownYear"
        
        if 'date' in release and release['date']:
            date_str = release['date']
            if '-' in date_str:
                return date_str.split('-')[0]
            return date_str
        
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
        result = []
        for credit in artist_credit:
            if isinstance(credit, dict):
                if 'artist' in credit:
                    artist = credit['artist']
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
        if not releases:
            return None, None
        
        eng_release = self.find_english_release(releases)
        album_release = eng_release or self.find_official_release(releases) or releases[0]
        
        if self.has_date(album_release):
            date_release = album_release
        else:
            date_release = self.find_official_release(releases)
            if not (date_release and self.has_date(date_release)):
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
        for media_key, track_key in [('media', 'tracks'), ('medium-list', 'track-list')]:
            if media_key in release:
                for medium in release[media_key]:
                    for track in medium.get(track_key, []):
                        recording_match = False
                        
                        if track.get('recording', {}).get('id') == recording_id:
                            recording_match = True
                        
                        if track.get('recording-id') == recording_id:
                            recording_match = True
                        
                        if recording_match:
                            position = track.get('position', 0)
                            if isinstance(position, (int, str)) and str(position).isdigit():
                                return int(position)
        
        return None
    
    def get_disc_number(
        self,
        release: Dict[str, Any],
        recording_id: str
    ) -> Optional[int]:
        for media_key, track_key in [('media', 'tracks'), ('medium-list', 'track-list')]:
            if media_key in release:
                for i, medium in enumerate(release[media_key], 1):
                    for track in medium.get(track_key, []):
                        recording_match = False
                        
                        if track.get('recording', {}).get('id') == recording_id:
                            recording_match = True
                        
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
        metadata = {}
        
        metadata['title'] = recording_data.get('title', 'Unknown Title')
        
        if 'artist-credit' in recording_data:
            metadata['artist'] = self.get_english_artist(recording_data['artist-credit'])
        
        metadata['album'] = album_release.get('title', 'Unknown Album')
        
        if 'artist-credit' in album_release:
            metadata['albumartist'] = self.get_english_artist(album_release['artist-credit'])
        
        if 'date' in date_release and date_release['date']:
            metadata['date'] = date_release['date']
        else:
            metadata['date'] = self.extract_year_from_release(date_release)
        
        metadata['musicbrainz_recordingid'] = recording_data.get('id', '')
        metadata['musicbrainz_albumid'] = album_release.get('id', '')
        
        if 'artist-credit' in recording_data:
            for credit in recording_data['artist-credit']:
                if isinstance(credit, dict) and 'artist' in credit:
                    metadata['musicbrainz_artistid'] = credit['artist'].get('id', '')
                    break
        
        if 'artist-credit' in album_release:
            for credit in album_release['artist-credit']:
                if isinstance(credit, dict) and 'artist' in credit:
                    metadata['musicbrainz_albumartistid'] = credit['artist'].get('id', '')
                    break
        
        rec_id = recording_data.get('id', '')
        
        if detailed_release:
            track_num = self.get_track_number(detailed_release, rec_id)
            disc_num = self.get_disc_number(detailed_release, rec_id)
            
            if track_num:
                metadata['tracknumber'] = str(track_num)
            if disc_num:
                metadata['discnumber'] = str(disc_num)
        
        return metadata