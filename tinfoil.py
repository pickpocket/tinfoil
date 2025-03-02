#!/usr/bin/env python3
"""
@file tinfoil.py
@brief Command-line interface for the Tinfoil application.
"""
import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any

from config import Config
from processor import TinfoilProcessor


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Set up logging.
    
    Args:
        verbose: Enable verbose (debug) logging
        
    Returns:
        logging.Logger: Configured logger
    """
    # Create logs directory if it doesn't exist
    log_dir = Config.get_log_dir()
    
    # Set up logging level
    log_level = logging.DEBUG if verbose else Config.DEFAULT_LOG_LEVEL
    
    # Enable musicbrainzngs debugging if requested
    if verbose:
        import musicbrainzngs
        musicbrainzngs.set_rate_limit(False)
    
    # Configure logging
    logging.basicConfig(
        level=log_level,
        format=Config.LOG_FORMAT,
        handlers=[
            # Console handler
            logging.StreamHandler(),
            # File handler
            logging.FileHandler(log_dir / 'tinfoil.log')
        ]
    )
    
    logger = logging.getLogger('tinfoil')
    logger.info(f"Logging initialized at level {log_level}")
    
    return logger


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description=f"Tinfoil {Config.VERSION} - {Config.DESCRIPTION}"
    )
    
    # Main operation arguments
    parser.add_argument(
        '-i', '--input',
        required=True,
        help="Input file or directory path"
    )
    
    parser.add_argument(
        '-o', '--output',
        default=str(Config.get_default_output_dir()),
        help=f"Output directory (default: {Config.get_default_output_dir()})"
    )
    
    # API Keys
    parser.add_argument(
        '-k', '--api-key',
        default=Config.ACOUSTID_API_KEY,
        help="AcoustID API key (default: from environment variable ACOUSTID_API_KEY)"
    )
    
    parser.add_argument(
        '--genius-key',
        default=Config.GENIUS_API_KEY,
        help="Genius API key (default: from environment variable GENIUS_API_KEY)"
    )
    
    # Operation options
    operation_group = parser.add_argument_group('Operation Options')
    operation_group.add_argument(
        '--force',
        action='store_true',
        help="Force update even if metadata exists"
    )
    
    operation_group.add_argument(
        '--pattern',
        default=Config.DEFAULT_OUTPUT_PATTERN,
        help=f"Output filename pattern (default: {Config.DEFAULT_OUTPUT_PATTERN})"
    )
    
    # Lyrics options
    lyrics_group = parser.add_argument_group('Lyrics Options')
    lyrics_group.add_argument(
        '--lyrics-source',
        choices=['combined', 'genius', 'lrclib', 'netease', 'none'],
        default='combined',
        help="Lyrics source to use (default: combined)"
    )
    
    # Metadata options
    metadata_group = parser.add_argument_group('Metadata Options')
    metadata_group.add_argument(
        '--tag-fallback',
        action='store_true',
        default=True,
        help="Use tag-based matching if AcoustID fails (default: enabled)"
    )
    
    metadata_group.add_argument(
        '--no-tag-fallback',
        action='store_false',
        dest='tag_fallback',
        help="Disable tag-based matching if AcoustID fails"
    )
    
    # Paths
    parser.add_argument(
        '--fpcalc-path',
        default=Config.get_fpcalc_path(),
        help="Path to fpcalc executable (default: auto-detected)"
    )
    
    # Debugging
    debug_group = parser.add_argument_group('Debugging Options')
    debug_group.add_argument(
        '-v', '--verbose',
        action='store_true',
        help="Enable verbose logging"
    )
    
    debug_group.add_argument(
        '--debug-musicbrainz',
        action='store_true',
        help="Enable detailed MusicBrainz API debugging"
    )
    
    parser.add_argument(
        '--validate',
        action='store_true',
        help="Validate setup and exit"
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version=f"Tinfoil {Config.VERSION}"
    )
    
    return parser.parse_args()


def validate_setup(processor: TinfoilProcessor, logger: logging.Logger) -> bool:
    """Validate the setup of the application.
    
    Args:
        processor: TinfoilProcessor instance
        logger: Logger instance
        
    Returns:
        bool: True if setup is valid, False otherwise
    """
    logger.info("Validating setup...")
    
    validations = processor.validate_setup()
    
    # Log validation results
    for key, value in validations.items():
        status = "Valid" if value else "Invalid"
        logger.info(f"{key}: {status}")
    
    # Check overall validity
    is_valid = all(validations.values())
    
    if is_valid:
        logger.info("Setup validation: OK")
    else:
        logger.error("Setup validation: FAILED")
        
        # Provide specific error messages
        if not validations.get('api_key', False):
            logger.error("Invalid or missing AcoustID API key")
            logger.error("Get an API key from https://acoustid.org/login")
            logger.error("Set it with --api-key or environment variable ACOUSTID_API_KEY")
        
        if not validations.get('fpcalc', False):
            logger.error("fpcalc executable not found")
            logger.error("Install Chromaprint and specify path with --fpcalc-path")
    
    return is_valid


def main() -> int:
    """Main function.
    
    Returns:
        int: Exit code
    """
    args = parse_args()
    
    # Set up logging
    logger = setup_logging(args.verbose)
    
    # Enable musicbrainzngs debugging if requested
    if args.debug_musicbrainz:
        import musicbrainzngs
        logging.getLogger('musicbrainzngs').setLevel(logging.DEBUG)
        musicbrainzngs.set_useragent(
            Config.MB_APP_NAME,
            Config.MB_VERSION,
            Config.MB_CONTACT
        )
    
    try:
        # Update config with command line API keys
        Config.ACOUSTID_API_KEY = args.api_key
        Config.GENIUS_API_KEY = args.genius_key
        
        # Create processor
        processor = TinfoilProcessor(
            api_key=args.api_key,
            fpcalc_path=args.fpcalc_path,
            output_pattern=args.pattern,
            logger=logger
        )
        
        # Configure lyrics source
        if args.lyrics_source != 'combined':
            # Remove the default combined lyrics cog
            processor.cogs = [cog for cog in processor.cogs 
                            if cog.__class__.__name__ != 'CombinedLyricsCog']
            
            # Add the selected lyrics cog
            if args.lyrics_source == 'genius':
                processor.cogs.append(processor.genius_lyrics_cog)
            elif args.lyrics_source == 'lrclib':
                processor.cogs.append(processor.lrclib_lyrics_cog)
            elif args.lyrics_source == 'netease':
                processor.cogs.append(processor.netease_lyrics_cog)
            # 'none' means don't add any lyrics cog
        
        # Configure tag-based fallback
        if not args.tag_fallback:
            # Remove the tag-based match cog
            processor.cogs = [cog for cog in processor.cogs 
                             if cog.__class__.__name__ != 'TagBasedMatchCog']
        
        # Validate setup if requested
        if args.validate:
            is_valid = validate_setup(processor, logger)
            return 0 if is_valid else 1
        
        # Process input
        input_path = Path(args.input)
        output_path = Path(args.output)
        
        if not input_path.exists():
            logger.error(f"Input path does not exist: {input_path}")
            return 1
        
        if input_path.is_file():
            # Process single file
            logger.info(f"Processing file: {input_path}")
            success = processor.process_file(input_path, output_path, args.force)
            return 0 if success else 1
        
        elif input_path.is_dir():
            # Process directory
            logger.info(f"Processing directory: {input_path}")
            processed_files = processor.process_directory(input_path, output_path, args.force)
            
            # Return success if at least one file was processed
            return 0 if processed_files else 1
        
        else:
            logger.error(f"Input path is neither a file nor a directory: {input_path}")
            return 1
        
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        return 130  # Standard exit code for SIGINT
    
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())