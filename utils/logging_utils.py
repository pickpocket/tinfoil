import logging
from typing import Optional
from config import Config

def setup_logging(verbose: bool = False, log_file: Optional[str] = None) -> logging.Logger:
    """Configure logging settings with optional file output.
    
    Args:
        verbose (bool): If True, sets logging level to DEBUG
        log_file (Optional[str]): Path to log file if file logging is desired
        
    Returns:
        logging.Logger: Configured logger instance
    """
    level = logging.DEBUG if verbose else logging.INFO
    
    # Create formatter
    formatter = logging.Formatter(Config.LOG_FORMAT)
    
    # Configure handlers
    handlers = [logging.StreamHandler()]
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    
    # Setup basic configuration
    logging.basicConfig(
        level=level,
        format=Config.LOG_FORMAT,
        handlers=handlers
    )
    
    logger = logging.getLogger(__name__)
    logger.debug("Logging setup complete")
    return logger