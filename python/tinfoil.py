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
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Set up logging level
    log_level = logging.DEBUG if verbose else Config.DEFAULT_LOG_LEVEL
    
    # Enable musicbrainzngs debugging if requested
    if verbose:
        import musicbrainzngs
        musicbrainzngs.set_rate_limit(False)
    
    # Configure the file handler
    file_handler = logging.FileHandler(log_dir / 'tinfoil.log', encoding='utf-8')
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter(Config.LOG_FORMAT))
    
    # Configure the console handler with error handling for non-Unicode terminals
    class UnicodeConsoleHandler(logging.StreamHandler):
        def emit(self, record):
            try:
                msg = self.format(record)
                stream = self.stream
                stream.write(msg + self.terminator)
                self.flush()
            except UnicodeEncodeError:
                # Fall back to ASCII representation if the console can't handle Unicode
                fallback_msg = record.getMessage().encode('ascii', 'replace').decode('ascii')
                formatted = self.format(logging.LogRecord(
                    record.name, record.levelno, record.pathname, record.lineno,
                    fallback_msg, record.args, record.exc_info, record.funcName
                ))
                stream = self.stream
                stream.write(formatted + self.terminator)
                self.flush()
            except Exception:
                self.handleError(record)
    
    console_handler = UnicodeConsoleHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(Config.LOG_FORMAT))
    
    # Configure the root logger
    logging.basicConfig(
        level=log_level,
        format=Config.LOG_FORMAT,
        handlers=[console_handler, file_handler]
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
    input_group = parser.add_argument_group('Input/Output')
    input_group.add_argument(
        '-i', '--input',
        help="Input file or directory path"
    )
    
    input_group.add_argument(
        '-o', '--output',
        default=str(Config.get_default_output_dir()),
        help=f"Output directory (default: {Config.get_default_output_dir()})"
    )
    
    # API Keys
    input_group.add_argument(
        '-k', '--api-key',
        default=Config.ACOUSTID_API_KEY,
        help="AcoustID API key (default: from environment variable ACOUSTID_API_KEY)"
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
        choices=['genius', 'lrclib', 'netease', 'none'],
        default='genius',
        help="Lyrics source to use (default: genius)"
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
    metadata_group.add_argument(
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
    
    debug_group.add_argument(
        '--validate',
        action='store_true',
        help="Validate setup and exit"
    )
    
    # REST API options
    api_group = parser.add_argument_group('REST API Options')
    api_group.add_argument(
        '--api',
        action='store_true',
        help="Start the REST API server"
    )
    
    api_group.add_argument(
        '--api-host',
        default='127.0.0.1',
        help="API server host (default: 127.0.0.1)"
    )
    
    api_group.add_argument(
        '--api-port',
        type=int,
        default=8000,
        help="API server port (default: 8000)"
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
        
        # Start API server if requested
        if args.api:
            try:
                import uvicorn
                from api import app
                
                logger.info(f"Starting API server on {args.api_host}:{args.api_port}")
                uvicorn.run(
                    "api:app", 
                    host=args.api_host, 
                    port=args.api_port, 
                    log_level="info" if not args.verbose else "debug"
                )
                return 0
            except ImportError:
                logger.error("Failed to start API server. Make sure FastAPI and Uvicorn are installed:")
                logger.error("pip install fastapi uvicorn python-multipart")
                return 1
        
        # If not starting API server, input is required
        if not args.input:
            logger.error("Input path is required when not in API mode")
            logger.error("Use -i/--input to specify an input file or directory, or use --api to start the API server")
            return 1
        
        # Create processor with the selected lyrics source
        processor = TinfoilProcessor(
            api_key=args.api_key,
            fpcalc_path=args.fpcalc_path,
            output_pattern=args.pattern,
            logger=logger,
            lyrics_source=args.lyrics_source
        )
        
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