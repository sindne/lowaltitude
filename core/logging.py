import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Optional

def setup_logger(name: str = 'low_altitude_risk', log_file: Optional[str] = None, level: str = 'INFO') -> logging.Logger:
    logger = logging.getLogger(name)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    logger.setLevel(level)
    return logger

def get_logger(name: str = 'low_altitude_risk') -> logging.Logger:
    return logging.getLogger(name)
