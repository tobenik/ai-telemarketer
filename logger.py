import logging
from logging.handlers import RotatingFileHandler

def setup_logger(logger_name, log_file, level=logging.INFO):
    """
    Set up a logger with file rotation
    
    Args:
        logger_name (str): Name of the logger
        log_file (str): Path to the log file
        level (int): Logging level
        
    Returns:
        logger: Configured logger instance
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    
    # Create handler for the log file
    handler = RotatingFileHandler(log_file, maxBytes=10000, backupCount=3)
    
    # Create a formatter and add it to the handler
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    # Add the handler to the logger
    logger.addHandler(handler)
    
    return logger