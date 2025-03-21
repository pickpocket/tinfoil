"""
@file acoustid_cog.py
@brief Cog for acoustic fingerprinting and AcoustID API interactions.
"""
import acoustid
import requests
import json
from typing import Optional, Tuple, Dict, Any
import logging
from pathlib import Path

from base_cog import BaseCog
from song import Song
from config import Config


class AcoustIDCog(BaseCog):
    """Handle acoustic fingerprinting and AcoustID API interactions."""
    
    # Define what tags this cog provides
    output_tags = [
        'musicbrainz_recordingid',
        'acoustid_fingerprint',
        'acoustid_id'
    ]
    
    def __init__(self, api_key: str, fpcalc_path: Optional[str] = None, logger: Optional[logging.Logger] = None):
        """Initialize AcoustIDCog.
        
        Args:
            api_key: AcoustID API key
            fpcalc_path: Path to fpcalc executable
            logger: Logger instance
        """
        super().__init__(logger)
        self.api_key = api_key
        
        if fpcalc_path:
            if not Path(fpcalc_path).is_file():
                raise FileNotFoundError(f"fpcalc not found at: {fpcalc_path}")
            acoustid.FPCALC_PATH = fpcalc_path
            self.logger.info(f"Set fpcalc path to: {fpcalc_path}")
    
    def process(self, song: Song) -> bool:
        """Process a song using acoustic fingerprinting.
        
        This method generates a fingerprint for the song and looks up metadata
        using the AcoustID API.
        
        Args:
            song: The Song object to process
            
        Returns:
            bool: True if processing was successful, False otherwise
        """
        try:
            # Generate fingerprint
            fingerprint, duration = self.get_fingerprint(str(song.filepath))
            if not fingerprint or not duration:
                self.logger.warning(f"Could not generate fingerprint for {song.filepath}")
                return False
            
            # Store fingerprint in metadata
            fingerprint_metadata = {
                'acoustid_fingerprint': fingerprint,
                'length': str(int(duration))
            }
            self.merge_metadata(song, fingerprint_metadata)
            
            # Look up metadata
            result = self.lookup_fingerprint(fingerprint, duration)
            if not result:
                self.logger.warning(f"No AcoustID results found for {song.filepath}")
                return False
            
            # Extract and store metadata
            metadata = {
                'musicbrainz_recordingid': result.get('id', ''),
                'acoustid_id': result.get('acoustid', '')
            }
            
            # Get additional metadata if available
            if 'title' in result:
                metadata['title'] = result['title']
            
            if 'artists' in result:
                artists = [a.get('name', '') for a in result['artists']]
                metadata['artist'] = '; '.join(artists)
            
            self.merge_metadata(song, metadata)
            self.logger.info(f"Successfully processed AcoustID data for {song.filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing {song.filepath} with AcoustIDCog: {e}")
            return False

    def get_fingerprint(self, file_path: str) -> Tuple[Optional[str], Optional[float]]:
        """Generate an AcoustID fingerprint for a file.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Tuple containing fingerprint and duration or (None, None) on failure
        """
        try:
            self.logger.debug(f"Generating AcoustID fingerprint for: {file_path}")
            duration, fingerprint = acoustid.fingerprint_file(file_path)
            self.logger.info(f"Generated fingerprint of length {len(fingerprint)} for file '{file_path}'")
            return fingerprint, duration
        except Exception as e:
            self.logger.error(f"Error generating fingerprint for '{file_path}': {e}")
            return None, None

    def lookup_fingerprint(self, fingerprint: str, duration: float) -> Optional[Dict[str, Any]]:
        """Look up metadata for a fingerprint using AcoustID API."""
        try:
            params = {
                'client': self.api_key,
                'duration': str(int(duration)),
                'fingerprint': fingerprint,
                'meta': 'recordings releases releasegroups tracks compress',
                'format': 'json'
            }
            
            headers = {'User-Agent': Config.USER_AGENT}
            
            self.logger.info(f"Querying AcoustID API with duration: {duration}")
            self.logger.debug(f"AcoustID params: {params}")
            
            response = requests.get(
                Config.ACOUSTID_API_URL,
                params=params,
                headers=headers,
                timeout=10
            )
            
            self.logger.debug(f"AcoustID response status: {response.status_code}")
            
            try:
                data = response.json()
                self.logger.debug("AcoustID raw response:")
                self.logger.debug(json.dumps(data, indent=2))
            except json.JSONDecodeError:
                self.logger.warning(f"AcoustID received non-JSON response: {response.text[:1000]}")
                return None

            response.raise_for_status()
            
            if data.get('status') != 'ok':
                self.logger.warning(f"AcoustID API returned non-ok status: {data.get('status')}")
                return None
                
            if not data.get('results'):
                self.logger.warning("No results found in AcoustID response")
                return None
                
            result = self._process_acoustid_results(data['results'])
            if result:
                self.logger.debug("Processed AcoustID result:")
                self.logger.debug(json.dumps(result, indent=2))
            return result
            
        except requests.RequestException as e:
            self.logger.error(f"Error during AcoustID API request: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error during fingerprint lookup: {e}")
            return None

    def _process_acoustid_results(self, results: list) -> Optional[Dict[str, Any]]:
        """Process and extract relevant metadata from AcoustID results.
        
        Args:
            results: List of results from AcoustID API
            
        Returns:
            Best matching metadata or None
        """
        try:
            # Look for results with recordings
            for result in results:
                if result.get('recordings'):
                    # Get the first recording (usually best match)
                    recording = result['recordings'][0]
                    
                    # Enhance recording data with additional info
                    recording['score'] = result.get('score', 0)
                    recording['acoustid'] = result.get('id')
                    
                    if 'releasegroups' in result:
                        recording['releasegroups'] = result['releasegroups']
                    
                    self.logger.info(f"Found matching recording: {recording.get('title', 'Unknown Title')}")
                    return recording
                    
            self.logger.warning("No recordings found in AcoustID results")
            return None
            
        except Exception as e:
            self.logger.error(f"Error processing AcoustID results: {e}")
            return None

    def validate_api_key(self) -> bool:
        """Validate the AcoustID API key.
        
        Returns:
            True if API key is valid, False otherwise
        """
        try:
            # Make a minimal API request to check key validity
            params = {
                'client': self.api_key,
                'format': 'json'
            }
            
            response = requests.get(
                Config.ACOUSTID_API_URL,
                params=params,
                timeout=5
            )
            
            data = response.json()
            
            if data.get('status') == 'ok':
                self.logger.info("AcoustID API key validated successfully")
                return True
            else:
                self.logger.warning(f"Invalid AcoustID API key: {data.get('status')}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error validating AcoustID API key: {e}")
            return False