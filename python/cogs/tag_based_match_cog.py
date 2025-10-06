"""
@file tag_based_match_cog.py
@brief Cog for finding matches based on existing tags when AcoustID fails.
"""
import logging
import difflib
import musicbrainzngs
from typing import Optional, Dict, Any, List, Tuple

from base_cog import BaseCog
from song import Song


class TagBasedMatchCog(BaseCog):
    """Find MusicBrainz matches based on existing tags when AcoustID fails."""
    
    # Define what tags this cog needs as input - we'll look for any of these
    input_tags = []  # No mandatory tags, we'll use whatever is available
    
    # Define what tags this cog provides as output (same as MusicBrainzCog)
    output_tags = [
        'title', 
        'artist', 
        'album',
        'albumartist',
        'date',
        'tracknumber',
        'discnumber',
        'genre',
        'musicbrainz_recordingid',
        'musicbrainz_albumid',
        'musicbrainz_artistid',
        'musicbrainz_albumartistid'
    ]
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize TagBasedMatchCog.
        
        Args:
            logger: Logger instance
        """
        super().__init__(logger)
        
        # Initialize MusicBrainz API with hardcoded values
        musicbrainzngs.set_useragent(
            "tinfoil",
            "1.0",
            "imsoupp@protonmail.com"
        )
        musicbrainzngs.set_format("json")
    
    def process(self, song: Song) -> bool:
        """Find MusicBrainz match based on existing tags.
        
        This method extracts existing tags from the song and searches MusicBrainz
        for a match, then updates the song metadata with the results.
        
        Args:
            song: The Song object to process
            
        Returns:
            bool: True if processing was successful, False otherwise
        """
        try:
            # Get existing metadata from song
            existing_metadata = self._extract_existing_metadata(song)
            
            # Skip if we don't have enough metadata to search
            if not self._has_minimum_metadata(existing_metadata):
                self.logger.warning(f"Not enough existing metadata to search for {song.filepath}")
                return False
            
            # Search for matching recording
            recording_data = self._search_musicbrainz(existing_metadata)
            
            if not recording_data:
                self.logger.warning(f"No MusicBrainz matches found for {song.filepath}")
                return False
            
            # Process recording data similarly to MusicBrainzCog
            recording_id = recording_data.get('id')
            self.logger.info(f"Found MusicBrainz recording ID: {recording_id}")
            
            # Add recording ID to song metadata
            metadata = {'musicbrainz_recordingid': recording_id}
            self.merge_metadata(song, metadata)
            
            # We successfully found a musicbrainz_recordingid - the MusicBrainzCog can
            # now use this to get full metadata
            self.logger.info(f"Successfully added recording ID for {song.filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error matching based on tags for {song.filepath}: {e}")
            return False
    
    def _extract_existing_metadata(self, song: Song) -> Dict[str, str]:
        """Extract relevant existing metadata from a song.
        
        Args:
            song: The Song object
            
        Returns:
            Dict[str, str]: Existing metadata
        """
        metadata = {}
        
        # Keys to extract from song metadata
        keys = [
            'title', 'artist', 'album', 'albumartist', 
            'date', 'year', 'tracknumber', 'discnumber'
        ]
        
        for key in keys:
            if key in song.all_metadata:
                metadata[key] = song.all_metadata[key]
        
        # If we have a tracknumber in the format "X/Y", extract just the X part
        if 'tracknumber' in metadata and '/' in metadata['tracknumber']:
            metadata['tracknumber'] = metadata['tracknumber'].split('/')[0]
        
        # Extract year from date if we have a date but no year
        if 'date' in metadata and '-' in metadata['date'] and 'year' not in metadata:
            metadata['year'] = metadata['date'].split('-')[0]
        
        return metadata
    
    def _has_minimum_metadata(self, metadata: Dict[str, str]) -> bool:
        """Check if we have enough metadata to search.
        
        Args:
            metadata: Metadata dictionary
            
        Returns:
            bool: True if we have enough metadata, False otherwise
        """
        # Need at least artist and title or album
        return ('artist' in metadata and 
                ('title' in metadata or 'album' in metadata))
    
    def _search_musicbrainz(self, metadata: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Search MusicBrainz for matches based on metadata.
        
        Args:
            metadata: Metadata dictionary
            
        Returns:
            Optional[Dict[str, Any]]: Best matching recording data or None
        """
        try:
            query_parts = []
            
            # Build query based on available metadata
            if 'artist' in metadata:
                query_parts.append(f"artist:{metadata['artist']}")
            
            if 'title' in metadata:
                query_parts.append(f"recording:{metadata['title']}")
            
            if 'album' in metadata:
                query_parts.append(f"release:{metadata['album']}")
            
            if not query_parts:
                return None
            
            # Build query string
            query = ' AND '.join(query_parts)
            self.logger.info(f"Searching MusicBrainz with query: {query}")
            
            # Search recordings in MusicBrainz
            result = musicbrainzngs.search_recordings(query=query, limit=10)
            
            self.logger.debug(f"MusicBrainz search result: {result}")
            
            if not result:
                return None
                
            # The key could be 'recording-list' or 'recordings' depending on the response format
            if 'recording-list' in result:
                recordings = result['recording-list']
            elif 'recordings' in result:
                recordings = result['recordings']
            else:
                self.logger.warning(f"Unexpected MusicBrainz response structure: {list(result.keys())}")
                return None
            
            if not recordings:
                return None
            
            # Check if we found any recordings
            if not recordings:
                self.logger.warning("MusicBrainz returned empty recording list")
                return None
                
            self.logger.debug(f"Found {len(recordings)} potential matches in MusicBrainz")
            
            # Find best match based on similarity
            best_match = self._find_best_match(recordings, metadata)
            
            if best_match:
                self.logger.info(f"Found MusicBrainz match: {best_match.get('id')} - {best_match.get('title')}")
            else:
                self.logger.warning("No recordings passed the similarity threshold")
                
            return best_match
            
        except Exception as e:
            self.logger.error(f"Error searching MusicBrainz: {e}")
            return None
    
    def _find_best_match(
        self, 
        recordings: List[Dict[str, Any]], 
        metadata: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        """Find best matching recording based on similarity to metadata.
        
        Args:
            recordings: List of recording dictionaries
            metadata: Metadata to match against
            
        Returns:
            Optional[Dict[str, Any]]: Best matching recording or None
        """
        best_match = None
        best_score = 0.0
        
        for recording in recordings:
            # Calculate similarity score
            score = self._calculate_similarity_score(recording, metadata)
            
            if score > best_score:
                best_score = score
                best_match = recording
        
        # Only return match if score is high enough
        threshold = 0.5  # Lower threshold to catch more matches
        
        self.logger.debug(f"Best match score: {best_score:.2f} (threshold: {threshold})")
        
        return best_match if best_score >= threshold else None
    
    def _calculate_similarity_score(
        self, 
        recording: Dict[str, Any], 
        metadata: Dict[str, str]
    ) -> float:
        """Calculate similarity score between recording and metadata.
        
        Args:
            recording: Recording dictionary
            metadata: Metadata dictionary
            
        Returns:
            float: Similarity score (0-1)
        """
        score_components = []
        
        # Compare title
        if 'title' in metadata and 'title' in recording:
            title_similarity = difflib.SequenceMatcher(
                None, 
                metadata['title'].lower(), 
                recording['title'].lower()
            ).ratio()
            score_components.append(('title', title_similarity, 0.4))  # 40% weight
            
        # Compare artist
        if 'artist' in metadata and 'artist-credit' in recording:
            artist_name = self._get_artist_name(recording)
            artist_similarity = difflib.SequenceMatcher(
                None, 
                metadata['artist'].lower(), 
                artist_name.lower()
            ).ratio()
            score_components.append(('artist', artist_similarity, 0.4))  # 40% weight
            
        # Compare album if available
        if 'album' in metadata and 'release-list' in recording:
            album_similarity = 0.0
            for release in recording['release-list']:
                if 'title' in release:
                    similarity = difflib.SequenceMatcher(
                        None, 
                        metadata['album'].lower(), 
                        release['title'].lower()
                    ).ratio()
                    album_similarity = max(album_similarity, similarity)
            
            score_components.append(('album', album_similarity, 0.2))  # 20% weight
            
        # Calculate weighted average
        if not score_components:
            return 0.0
            
        total_score = sum(score * weight for _, score, weight in score_components)
        total_weight = sum(weight for _, _, weight in score_components)
        
        return total_score / total_weight if total_weight > 0 else 0.0
    
    def _get_artist_name(self, recording: Dict[str, Any]) -> str:
        """Extract artist name from recording.
        
        Args:
            recording: Recording dictionary
            
        Returns:
            str: Artist name
        """
        if 'artist-credit' not in recording:
            return ''
            
        artist_credit = recording['artist-credit']
        parts = []
        
        for credit in artist_credit:
            if isinstance(credit, dict):
                if 'artist' in credit:
                    parts.append(credit['artist'].get('name', ''))
                    if 'joinphrase' in credit:
                        parts.append(credit['joinphrase'])
            elif isinstance(credit, str):
                parts.append(credit)
                
        return ''.join(parts).strip()