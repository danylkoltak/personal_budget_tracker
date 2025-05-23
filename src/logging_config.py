import logging

def setup_logging():
    """Configures logging for the application."""
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(filename)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("/tmp/app.log"),  # Log to a file
            logging.StreamHandler()  # Log to console
        ],
    )
    return logging.getLogger(__name__)

logger = setup_logging()