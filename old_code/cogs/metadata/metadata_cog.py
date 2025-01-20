import musicbrainzngs
from typing import Optional, Dict, Any, List, Tuple
import logging
from old_code.config import Config
import json

class MetadataCog:
    """Handle MusicBrainz metadata operations."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize MetadataCog.
        
        Args:
            logger (Optional[logging.Logger]): Logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        
        musicbrainzngs.set_useragent(
            Config.MB_APP_NAME,
            Config.MB_VERSION,
            Config.MB_CONTACT
        )
        musicbrainzngs.set_format("json")

    def get_recording_metadata(self, recording_id: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed recording metadata from MusicBrainz."""
        try:
            includes = ["artists", "releases", "artist-credits"]
            self.logger.info(f"Fetching MusicBrainz recording: {recording_id}")
            self.logger.debug(f"Using includes: {includes}")

            result = musicbrainzngs.get_recording_by_id(
                recording_id,
                includes=includes
            )

            self.logger.debug("MusicBrainz raw response:")
            self.logger.debug(json.dumps(result, indent=2))

            if result:  # Check if the result is not empty
                self.logger.info("Successfully retrieved recording metadata")
                return result  # Return the top-level result
            else:
                self.logger.warning("No recording data found in response")
                return None

        except musicbrainzngs.WebServiceError as e:
            self.logger.error(f"MusicBrainz API error: {e}")
            self.logger.error(f"Error details: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Error fetching recording metadata: {e}")
            return None

    def get_release_metadata(self, release_id: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed release metadata from MusicBrainz.
        
        Args:
            release_id (str): MusicBrainz release ID
            
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
            releases (List[Dict[str, Any]]): List of release dictionaries
            
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
            releases (List[Dict[str, Any]]): List of release dictionaries
            
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
            release (Dict[str, Any]): Release dictionary
            
        Returns:
            bool: True if release has date information
        """
        if 'date' in release:
            return True
        if 'release-event-list' in release and release['release-event-list']:
            return True
        if 'release-events' in release and release['release-events']:
            return True
        return False

    def extract_year_from_release(self, release: Optional[Dict[str, Any]]) -> str:
        """Extract year from release metadata.
        
        Args:
            release (Optional[Dict[str, Any]]): Release dictionary
            
        Returns:
            str: Year or 'UnknownYear' if not found
        """
        if not release:
            return "UnknownYear"

        # Check direct date field
        date_val = release.get('date')
        if isinstance(date_val, dict):
            return str(date_val.get('year', 'UnknownYear'))
        elif isinstance(date_val, str):
            if '-' in date_val:
                return date_val.split('-')[0]
            return date_val

        # Check release events
        for events_key in ['release-event-list', 'release-events']:
            events = release.get(events_key, [])
            if events and isinstance(events, list):
                for event in events:
                    event_date = event.get('date')
                    if isinstance(event_date, dict):
                        return str(event_date.get('year', 'UnknownYear'))
                    elif isinstance(event_date, str):
                        if '-' in event_date:
                            return event_date.split('-')[0]
                        return event_date

        return "UnknownYear"

    def get_english_track_name(
        self,
        releases: List[Dict[str, Any]],
        recording_id: str,
        default_title: str
    ) -> str:
        """Get English track name from releases.
        
        Args:
            releases (List[Dict[str, Any]]): List of release dictionaries
            recording_id (str): MusicBrainz recording ID
            default_title (str): Default title if English not found
            
        Returns:
            str: English track name or default title
        """
        for release in releases:
            if release.get('text-representation', {}).get('language') == 'eng':
                # Check medium list
                for medium in release.get('media', []):
                    for track in medium.get('track-list', []):
                        if track.get('recording', {}).get('id') == recording_id:
                            return track.get('title', default_title)
                
                # Check recording list
                for track in release.get('recording-list', []):
                    if track.get('id') == recording_id:
                        return track.get('title', default_title)

        return default_title

    def get_english_artist(self, artist_credit: List[Any]) -> str:
        """Build artist string from MusicBrainz artist-credit array.
        
        Args:
            artist_credit (List[Any]): Artist credit list from MusicBrainz
            
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

    def pick_album_releases(
        self,
        releases: List[Dict[str, Any]]
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Select appropriate album and date releases from available releases.
        
        Args:
            releases (List[Dict[str, Any]]): List of available releases
            
        Returns:
            Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]: Selected album and date releases
        """
        if not releases:
            return None, None

        # Group releases by release group
        release_groups = {}
        for release in releases:
            if 'release-group' in release:
                group_id = release['release-group'].get('id', release.get('id', 'unknown'))
                group_title = release['release-group'].get('title') or release.get('title', 'Unknown Album')
                group_type = release['release-group'].get('type') or release.get('status', 'Unknown Type')
            else:
                group_id = release.get('id', 'unknown')
                group_title = release.get('title', 'Unknown Album')
                group_type = release.get('status', 'Unknown Type')

            if group_id not in release_groups:
                release_groups[group_id] = {
                    'title': group_title,
                    'releases': [],
                    'type': group_type
                }
            release_groups[group_id]['releases'].append(release)

        # Present options to user
        print("\nAvailable albums containing this track:")
        print("-" * 50)

        options = []
        for i, (_, group_info) in enumerate(release_groups.items(), 1):
            release = group_info['releases'][0]
            year = self.extract_year_from_release(release)
            print(f"{i}. {group_info['title']} ({year}) - {group_type}")

            # Show additional release info
            for rel in group_info['releases']:
                status = rel.get('status', 'unknown status')
                language = rel.get('text-representation', {}).get('language', 'unknown language')
                print(f"   - {status} release ({language})")

            options.append(group_info['releases'])

        while True:
            try:
                choice = input("\nSelect album number (or 'q' to skip): ").strip()
                if choice.lower() == 'q':
                    return None, None

                idx = int(choice) - 1
                if 0 <= idx < len(options):
                    chosen_releases = options[idx]
                    return self.pick_album_releases_specific(chosen_releases)
                else:
                    print("Invalid choice. Please try again.")
            except ValueError:
                print("Please enter a valid number or 'q'")

    def pick_album_releases_specific(
        self,
        releases: List[Dict[str, Any]]
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Select specific album and date releases from a release group.
        
        Args:
            releases (List[Dict[str, Any]]): Releases within a selected release group
            
        Returns:
            Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]: Selected album and date releases
        """
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
            release (Dict[str, Any]): Release dictionary
            recording_id (str): MusicBrainz recording ID
            
        Returns:
            Optional[int]: Track number if found
        """
        if 'media' in release:
            for medium in release['media']:
                for track in medium.get('track-list', []):
                    if track.get('recording', {}).get('id') == recording_id:
                        return track.get('position')
        return None

    def get_disc_number(
        self,
        release: Dict[str, Any],
        recording_id: str
    ) -> Optional[int]:
        """Get disc number from release metadata.
        
        Args:
            release (Dict[str, Any]): Release dictionary
            recording_id (str): MusicBrainz recording ID
            
        Returns:
            Optional[int]: Disc number if found
        """
        if 'media' in release:
            for i, medium in enumerate(release['media'], 1):
                for track in medium.get('track-list', []):
                    if track.get('recording', {}).get('id') == recording_id:
                        return i
        return None