import acoustid
import requests
import json
from typing import Optional, Tuple, Dict, Any
import logging
from pathlib import Path
from base_cog import BaseCog
from song import Song

class AcoustIDCog(BaseCog):
    output_tags = [
        'musicbrainz_recordingid',
        'acoustid_fingerprint',
        'acoustid_id'
    ]
    
    # Declare the required setting for this cog.
    # 'name' is the internal config key.
    # 'label' is for the UI.
    # 'type': 'password' will tell the UI to treat it like a secret.
    required_settings = [
        {
            'name': 'acoustid_api_key',
            'label': 'AcoustID API Key',
            'type': 'password'
        }
    ]
    
    def __init__(self, api_key: str, fpcalc_path: Optional[str] = None, logger: Optional[logging.Logger] = None):
        super().__init__(logger)
        if not api_key:
            raise ValueError("AcoustID API key is required for AcoustIDCog.")
        self.api_key = api_key
        self.user_agent = "tinfoil/1.0"
        self.acoustid_api_url = "https://api.acoustid.org/v2/lookup"
        
        if fpcalc_path:
            if not Path(fpcalc_path).is_file():
                raise FileNotFoundError(f"fpcalc not found at: {fpcalc_path}")
            acoustid.FPCALC_PATH = fpcalc_path
            self.logger.info(f"Set fpcalc path to: {fpcalc_path}")
    
    def process(self, song: Song) -> bool:
        fingerprint, duration = self.get_fingerprint(str(song.filepath))
        if not fingerprint or not duration:
            self.logger.warning(f"Could not generate fingerprint for {song.filepath}")
            return False
        
        fingerprint_metadata = {
            'acoustid_fingerprint': fingerprint,
            'length': str(int(duration))
        }
        self.merge_metadata(song, fingerprint_metadata)
        
        result = self.lookup_fingerprint(fingerprint, duration)
        if not result:
            self.logger.warning(f"No AcoustID results found for {song.filepath}")
            return False
        
        metadata = {
            'musicbrainz_recordingid': result.get('id', ''),
            'acoustid_id': result.get('acoustid', '')
        }
        
        if 'title' in result:
            metadata['title'] = result['title']
        
        if 'artists' in result:
            artists = [a.get('name', '') for a in result['artists']]
            metadata['artist'] = '; '.join(artists)
        
        self.merge_metadata(song, metadata)
        self.logger.info(f"Successfully processed AcoustID data for {song.filepath}")
        return True
    
    def get_fingerprint(self, file_path: str) -> Tuple[Optional[str], Optional[float]]:
        self.logger.debug(f"Generating AcoustID fingerprint for: {file_path}")
        duration, fingerprint = acoustid.fingerprint_file(file_path)
        self.logger.info(f"Generated fingerprint of length {len(fingerprint)} for file '{file_path}'")
        return fingerprint, duration
    
    def lookup_fingerprint(self, fingerprint: str, duration: float) -> Optional[Dict[str, Any]]:
        params = {
            'client': self.api_key,
            'duration': str(int(duration)),
            'fingerprint': fingerprint,
            'meta': 'recordings releases releasegroups tracks compress',
            'format': 'json'
        }
        
        headers = {'User-Agent': self.user_agent}
        
        self.logger.info(f"Querying AcoustID API with duration: {duration}")
        self.logger.debug(f"AcoustID params: {params}")
        
        response = requests.get(
            self.acoustid_api_url,
            params=params,
            headers=headers,
            timeout=10
        )
        
        self.logger.debug(f"AcoustID response status: {response.status_code}")
        
        data = response.json()
        self.logger.debug("AcoustID raw response:")
        self.logger.debug(json.dumps(data, indent=2))
        
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
    
    def _process_acoustid_results(self, results: list) -> Optional[Dict[str, Any]]:
        for result in results:
            if result.get('recordings'):
                recording = result['recordings'][0]
                recording['score'] = result.get('score', 0)
                recording['acoustid'] = result.get('id')
                
                if 'releasegroups' in result:
                    recording['releasegroups'] = result['releasegroups']
                
                self.logger.info(f"Found matching recording: {recording.get('title', 'Unknown Title')}")
                return recording
        
        self.logger.warning("No recordings found in AcoustID results")
        return None
    
    def validate_api_key(self) -> bool:
        params = {
            'client': self.api_key,
            'format': 'json'
        }
        
        response = requests.get(
            self.acoustid_api_url,
            params=params,
            timeout=5
        )
        
        data = response.json()
        
        if data.get('status') == 'ok':
            self.logger.info("AcoustID API key validated successfully")
            return True
        
        self.logger.warning(f"Invalid AcoustID API key: {data.get('status')}")
        return False

