# Tinfoil - Audio Fingerprinting and Metadata Manager

Tinfoil is a powerful application for identifying, tagging, and organizing your FLAC audio files. It uses acoustic fingerprinting to identify tracks, fetches rich metadata from multiple sources, and organizes your music library with a clean, customizable structure.

## Features

- **Acoustic Fingerprinting**: Automatically identifies music using Chromaprint/AcoustID
- **Rich Metadata**: Fetches detailed information from MusicBrainz
- **Cover Art**: Downloads album artwork from Cover Art Archive
- **Lyrics Support**: Multiple sources including Genius, LRCLIB, and NetEase
- **Modular Architecture**: Easily extensible with "cogs" for different functionality
- **Modern UI**: Clean Electron interface with Tailwind CSS

## Prerequisites

To run Tinfoil, you'll need:

1. **Python 3.8+**: For the backend fingerprinting and metadata processing
2. **Node.js and npm**: For the Electron frontend
3. **Chromaprint** (`fpcalc` executable): Required for audio fingerprinting
4. **AcoustID API key**: Get one for free at [acoustid.org](https://acoustid.org/login)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/tinfoil.git
cd tinfoil
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Install Node.js Dependencies

```bash
npm install
```

### 4. Install Chromaprint (for fpcalc)

- **Windows**: Download from [acoustid.org/chromaprint](https://acoustid.org/chromaprint)
- **macOS**: `brew install chromaprint`
- **Linux**: `sudo apt install libchromaprint-tools`

### 5. Configure Your AcoustID API Key

Edit `config.py` and add your API key:

```python
ACOUSTID_API_KEY = 'your_api_key_here'
```

Alternatively, set it as an environment variable:

```bash
export ACOUSTID_API_KEY=your_api_key_here
```

## Running Tinfoil

### Development Mode

To run in development mode with hot-reloading for the frontend:

```bash
# In one terminal window, start the Python API server
python tinfoil.py --api

# In another terminal window, start the Electron app
npm run dev
```

### Production Mode

To build and run the application in production mode:

```bash
# Build the app
npm start
```

## Using the Application

### Main Interface

1. **Select Input Directory**: Click "Browse" next to "Input Directory" to select the folder containing your FLAC files.
2. **Select Output Directory**: Choose where your organized files will be stored.
3. **Configure Processing**: 
   - Use the "Force Update" checkbox to reprocess files even if they already have metadata.
   - Select processing components ("cogs") in the Processing Pipeline section.
4. **Process Files**: Click the "Process Files" button to start processing.

### Processing Pipeline

Tinfoil uses a modular architecture with "cogs" that each handle different aspects of the metadata processing:

1. **AcoustIDCog**: Generates acoustic fingerprints and identifies tracks
2. **TagBasedMatchCog**: Falls back to existing metadata if fingerprinting fails
3. **MusicBrainzCog**: Fetches detailed metadata from MusicBrainz
4. **CoverArtCog**: Downloads album artwork
5. **Various Lyrics Cogs**: Fetch lyrics from different sources

You can select which cogs to use in the Processing Pipeline section of the interface.

### Viewing and Editing Metadata

After processing, you can:

1. Click on any file in the file list to select it
2. Right-click and select "View/Edit Metadata" to open the metadata editor
3. Make any changes and click "Save Changes"

### Dark Mode

Toggle between light and dark modes using the switch in the top-right corner of the application.

## Command-Line Usage

Tinfoil can also be used directly from the command line:

```bash
python tinfoil.py -i /path/to/input -o /path/to/output -k your_api_key_here
```

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
  --lyrics-source {genius,lrclib,netease,none}
                            Lyrics source to use (default: genius)

Metadata Options:
  --tag-fallback            Use tag-based matching if AcoustID fails (default: enabled)
  --no-tag-fallback         Disable tag-based matching if AcoustID fails

Debugging Options:
  -v, --verbose             Enable verbose logging
  --debug-musicbrainz       Enable detailed MusicBrainz API debugging
  --validate                Validate setup and exit
  --version                 Show version information and exit
```

### API Server Mode

To start only the API server (useful for development or third-party integrations):

```bash
python tinfoil.py --api --api-host 127.0.0.1 --api-port 8000
```

## Troubleshooting

### Common Issues

- **"fpcalc not found"**: Make sure Chromaprint is installed and the executable is in your PATH
- **No matches found**: Try enabling tag-based fallback if AcoustID doesn't find matches
- **API connectivity issues**: Check your internet connection and API key
- **Permission errors**: Make sure you have read/write access to the input and output directories

### Logs

Logs are stored in the application directory:
- Windows: `%APPDATA%\Tinfoil\logs\`
- Linux/macOS: `~/.config/tinfoil/logs/`

The application also shows logs in the interface's log panel.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Credits

- AcoustID and Chromaprint for audio fingerprinting
- MusicBrainz for metadata
- Cover Art Archive for album artwork
- Electron and Tailwind CSS for the interface
