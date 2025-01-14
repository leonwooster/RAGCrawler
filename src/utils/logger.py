import logging
from rich.logging import RichHandler
import os

def get_logger(name: str) -> logging.Logger:
    """
    Creates and returns a logger instance with Rich formatting.
    
    Args:
        name (str): The name of the logger, typically __name__
        
    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            RichHandler(rich_tracebacks=True),
            logging.FileHandler(f"logs/crawler.log")
        ]
    )
    
    # Get logger instance
    logger = logging.getLogger(name)
    return logger 