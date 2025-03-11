"""
A utility script to check the metadata of a FLAC file and print it.
Save this as check_metadata.py and run it with:
python check_metadata.py path_to_flac_file.flac
"""
import sys
from pathlib import Path
from mutagen.flac import FLAC

def check_metadata(file_path):
    try:
        # Load the FLAC file
        audio = FLAC(file_path)
        
        # Get all metadata
        print(f"Metadata for {file_path}:")
        print("-" * 40)
        
        # Count tags and check for lyrics
        tag_count = 0
        has_lyrics = False
        lyrics_length = 0
        
        # Print all tags
        for key, value in sorted(audio.items()):
            tag_count += 1
            tag_value = value[0] if len(value) == 1 else value
            
            # Truncate long values
            if isinstance(tag_value, str) and len(tag_value) > 100:
                print(f"{key}: (length: {len(tag_value)}) {tag_value[:100]}...")
                
                # Check if this is lyrics
                if key.lower() == 'lyrics':
                    has_lyrics = True
                    lyrics_length = len(tag_value)
            else:
                print(f"{key}: {tag_value}")
        
        print("-" * 40)
        print(f"Total tags: {tag_count}")
        print(f"Has LYRICS tag: {has_lyrics}")
        if has_lyrics:
            print(f"Lyrics length: {lyrics_length} characters")
        else:
            # Check for differently named lyrics tags
            for key in audio.keys():
                if 'lyric' in key.lower():
                    print(f"Found potential lyrics tag: {key}")
        
        # Check if the file has pictures
        if audio.pictures:
            print(f"Has cover art: Yes ({len(audio.pictures)} images)")
        else:
            print("Has cover art: No")
            
    except Exception as e:
        print(f"Error reading file: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python check_metadata.py path_to_flac_file.flac")
        sys.exit(1)
        
    file_path = sys.argv[1]
    if not Path(file_path).exists():
        print(f"File not found: {file_path}")
        sys.exit(1)
        
    check_metadata(file_path)