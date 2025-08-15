
import logging
import os
from logging.handlers import RotatingFileHandler
# Environment detection for logging behavior
from config.settings import IS_CLOUD_ENV, IS_LOCAL_ENV

def setup_logging(log_file_path=None, log_level=logging.INFO, enable_console_logging=True):
    """
    Sets up a standardized logging configuration for the ORA Project.

    This function configures the root logger to:
    1. Output messages to the console (optional).
    2. Write messages to a rotating file.

    Args:
        log_file_path (str, optional): The full path to the log file.
                                       If None, logs will only go to the console (if enabled).
                                       Defaults to None.
        log_level (int, optional): The minimum logging level to capture (e.g., logging.INFO,
                                   logging.DEBUG, logging.ERROR). Defaults to logging.INFO.
        enable_console_logging (bool, optional): If True, log messages will also be
                                                 printed to the console. Defaults to True.
    """


    # Create logger
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Remove all existing handlers to avoid duplicate logs or missing output
    while logger.handlers:
        logger.handlers.pop()

    # Define a consistent log format
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 1. Console Handler (always enabled in cloud, optional locally)
    if IS_CLOUD_ENV or enable_console_logging:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.DEBUG if IS_LOCAL_ENV else logging.INFO)
        logger.addHandler(console_handler)

    # 2. File Handler (only if log_file_path is provided and not in cloud)
    if log_file_path is None:
        # Set default log_dir and log_file_path if not provided
        log_dir = "/tmp/logs" if IS_CLOUD_ENV else "logs"
        log_file_path = os.path.join(log_dir, "app.log")
    else:
        log_dir = os.path.dirname(log_file_path)

    if not IS_CLOUD_ENV:
        # Ensure the log directory exists
        if log_dir and not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir)
            except OSError as e:
                logger.error(f"Could not create log directory {log_dir}: {e}")
                log_file_path = None # Disable file logging if directory cannot be created

        if log_file_path:
            # Rotating file handler:
            # maxBytes: 10 MB per file
            # backupCount: keep 5 backup log files (app.log.1, app.log.2, etc.)
            file_handler = RotatingFileHandler(
                log_file_path,
                maxBytes=10 * 1024 * 1024,  # 10 MB
                backupCount=5
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

    # Log a message to confirm setup (at DEBUG level, so it's not always visible)
    logger.debug(f"Logging system initialized with level: {logging.getLevelName(log_level)}")
    logger.info(f"Logging environment: {'CLOUD' if IS_CLOUD_ENV else 'LOCAL' if IS_LOCAL_ENV else 'UNKNOWN'}")
    if log_file_path:
        logger.debug(f"Log file output to: {log_file_path}")
    # ...existing code...
