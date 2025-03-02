# Tinfoil - Audio Fingerprinting and Metadata Management

Tinfoil is a powerful FLAC audio processing application that automatically identifies, tags, and organizes your music library. It uses acoustic fingerprinting to identify tracks, fetches rich metadata from multiple sources, and organizes files into a customizable directory structure.

## Features

- **Acoustic Fingerprinting**: Uses Chromaprint/AcoustID to identify tracks based on audio content
- **Tag-Based Fallback**: Falls back to matching based on existing file tags when fingerprinting fails
- **Rich Metadata**: Fetches detailed metadata from MusicBrainz
- **Cover Art**: Downloads album artwork from the Cover Art Archive
- **Multiple Lyrics Sources**:
  - LRCLIB (synchronized lyrics)
  - NetEase Music (synchronized lyrics from Chinese music service)
  - Genius (text-only lyrics)
- **Customizable File Organization**: Organizes files based on artist, album, year, and track information
- **Modular Architecture**: Easy to extend with new sources and functionality

## Requirements

- Python 3.8+
- AcoustID API key (get one from [acoustid.org](https://acoustid.org/login))
- Chromaprint (`fpcalc` executable) - required for audio fingerprinting
- Optional: Genius API key for using Genius lyrics (set via environment variable)

### Python Dependencies

- `pyacoustid`: For audio fingerprinting
- `musicbrainzngs`: For MusicBrainz API access
- `mutagen`: For audio file metadata handling
- `requests`: For API requests
- `pillow`: For image processing
- `beautifulsoup4`: For HTML parsing (Genius lyrics)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/tinfoil.git
   cd tinfoil
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install Chromaprint (for fpcalc):
   - **Windows**: Download from [acoustid.org/chromaprint](https://acoustid.org/chromaprint)
   - **macOS**: `brew install chromaprint`
   - **Linux**: `sudo apt install libchromaprint-tools`

4. Set up your AcoustID API key:
   ```bash
   export ACOUSTID_API_KEY=your_api_key_here
   ```

## Usage

### Basic Usage

```bash
python tinfoil.py -i /path/to/input -o /path/to/output -k your_api_key_here
```

This will process all FLAC files in the input directory and organize them in the output directory.

### Command-Line Options

```
Main Arguments:
  -i, --input INPUT         Input file or directory path
  -o, --output OUTPUT       Output directory
  -k, --api-key API_KEY     AcoustID API key

Operation Options:
  --force                   Force update even if metadata exists
  --pattern PATTERN         Output filename pattern 
                            (default: {artist}/{year} - {album}/{track:02d} - {title})

Lyrics Options:
  --lyrics-source {combined,genius,lrclib,netease,none}
                            Lyrics source to use (default: combined)

Metadata Options:
  --tag-fallback            Use tag-based matching if AcoustID fails (default: enabled)
  --no-tag-fallback         Disable tag-based matching if AcoustID fails

Debugging Options:
  -v, --verbose             Enable verbose logging
  --debug-musicbrainz       Enable detailed MusicBrainz API debugging
  --validate                Validate setup and exit
  --version                 Show version information and exit
```

### Examples

**Process a single file:**
```bash
python tinfoil.py -i path/to/song.flac -o ~/Music/Organized -k YOUR_API_KEY
```

**Process a directory:**
```bash
python tinfoil.py -i ~/Music/Unsorted -o ~/Music/Organized -k YOUR_API_KEY
```

**Use a specific lyrics source:**
```bash
python tinfoil.py -i ~/Music/Unsorted -o ~/Music/Organized -k YOUR_API_KEY --lyrics-source lrclib
```

**Force metadata update:**
```bash
python tinfoil.py -i ~/Music/Unsorted -o ~/Music/Organized -k YOUR_API_KEY --force
```

**Custom output pattern:**
```bash
python tinfoil.py -i ~/Music/Unsorted -o ~/Music/Organized -k YOUR_API_KEY --pattern "{artist}/{year} - {album}/{disc:01d}.{track:02d} - {title}"
```

## How It Works

Tinfoil processes each audio file through a series of "cogs" (modular components):

1. **AcoustIDCog**: Generates an acoustic fingerprint and searches the AcoustID database
2. **TagBasedMatchCog**: If AcoustID fails, attempts to find matches using existing file tags
3. **MusicBrainzCog**: Fetches detailed metadata from MusicBrainz using the recording ID
4. **CoverArtCog**: Downloads album artwork from the Cover Art Archive
5. **Lyrics Cogs**: Fetches lyrics from various sources (LRCLIB, NetEase, Genius)

After processing, the file is copied to a new location following the specified pattern, with all new metadata embedded.

## Lyrics Sources

Tinfoil can fetch lyrics from multiple sources:

- **Combined** (default): Tries LRCLIB first, then NetEase, then Genius
- **LRCLIB**: A synchronized lyrics database (time-synced lyrics for media players)
- **NetEase**: A Chinese music service with a large collection of synchronized lyrics
- **Genius**: A popular lyrics site with extensive coverage but text-only lyrics
- **None**: Skip lyrics fetching entirely

## Extending Tinfoil

Tinfoil uses a modular architecture with "cogs" that can be easily extended:

1. Create a new Python class that inherits from `BaseCog`
2. Define its `input_tags` and `output_tags` 
3. Implement the `process()` method
4. Add your cog to the processor's cog list

## Troubleshooting

### Common Issues

- **fpcalc not found**: Install Chromaprint and specify the path with `--fpcalc-path`
- **No AcoustID matches**: Try enabling tag-based fallback (enabled by default)
- **Metadata not found**: Verify the track exists in MusicBrainz
- **Errors with special characters**: Use the `-v` flag for verbose logs

## License

MIT License

## Acknowledgments

- [AcoustID](https://acoustid.org/) - For audio fingerprinting
- [MusicBrainz](https://musicbrainz.org/) - For metadata
- [Cover Art Archive](https://coverartarchive.org/) - For album artwork
- [LRCLIB](https://lrclib.net/) - For synchronized lyrics
- [Genius](https://genius.com/) - For lyrics
- [CTAG07](https://github.com/CTAG07) - cog & input and output tag idea