import logging
from enum import IntEnum
from functools import wraps
import traceback

LOG_PREFIX = "PeerJS: "

class LogLevel(IntEnum):
    Disabled = 0
    Errors = 1
    Warnings = 2
    All = 3

def setup_logger(name=__name__, log_level=LogLevel.Disabled):
    logger = logging.getLogger(name)
    logger.setLevel(logging.NOTSET)  # We'll use our custom levels

    formatter = logging.Formatter(f'{LOG_PREFIX}%(message)s')
    
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    def set_log_level(level):
        if level == LogLevel.Disabled:
            logger.setLevel(logging.CRITICAL + 1)  # Higher than any standard level
        elif level == LogLevel.Errors:
            logger.setLevel(logging.ERROR)
        elif level == LogLevel.Warnings:
            logger.setLevel(logging.WARNING)
        elif level == LogLevel.All:
            print(f"{LOG_PREFIX} SETUP LOGGER LEVEL ALL")
            logger.setLevel(logging.DEBUG)

    def catch(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Exception in {func.__name__}: {str(e)}\n{traceback.format_exc()}")
                raise
        return wrapper
    
    set_log_level(log_level)
    logger.set_log_level = set_log_level

    logger.catch = catch
    return logger

# Create a default logger instance
logger = setup_logger()

# Usage example:
# logger.debug('API options: %s', options)
# logger.warning('This is a warning')
# logger.error('This is an error')
# 
# To change log level:
# logger.set_log_level(LogLevel.All)