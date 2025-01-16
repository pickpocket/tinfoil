import acoustid
import requests
import json
from typing import Optional, Tuple, Dict, Any
import logging
from pathlib import Path
from config import Config

class AcoustIDCog:
    """Handle acoustic fingerprinting and AcoustID API interactions."""
    
    def __init__(self, api_key: str, fpcalc_path: Optional[str] = None, logger: Optional[logging.Logger] = None):
        """Initialize AcoustIDCog.
        
        Args:
            api_key (str): AcoustID API key
            fpcalc_path (Optional[str]): Path to fpcalc executable
            logger (Optional[logging.Logger]): Logger instance
        """
        self.api_key = api_key
        self.logger = logger or logging.getLogger(__name__)
        
        if fpcalc_path:
            if not Path(fpcalc_path).is_file():
                raise FileNotFoundError(f"fpcalc not found at: {fpcalc_path}")
            acoustid.FPCALC_PATH = fpcalc_path
            self.logger.info(f"Set fpcalc path to: {fpcalc_path}")

    def get_fingerprint(self, file_path: str) -> Tuple[Optional[str], Optional[float]]:
        """Generate an AcoustID fingerprint for a file.
        
        Args:
            file_path (str): Path to audio file
            
        Returns:
            Tuple[Optional[str], Optional[float]]: (fingerprint, duration) or (None, None) on failure
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
            
            headers = {'User-Agent': 'tinfoil/1.0'}
            
            self.logger.info(f"Querying AcoustID API with duration: {duration}")
            self.logger.debug(f"AcoustID params: {params}")
            
            response = requests.get(
                'https://api.acoustid.org/v2/lookup',
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
            results (list): List of results from AcoustID API
            
        Returns:
            Optional[Dict[str, Any]]: Best matching metadata or None
        """
        try:
            # Look for results with recordings
            for result in results:
                if result.get('recordings'):
                    # Get the first recording (usually best match)
                    recording = result['recordings'][0]
                    
                    # Enhance recording data with additional info
                    recording['score'] = result.get('score', 0)
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
            bool: True if API key is valid, False otherwise
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