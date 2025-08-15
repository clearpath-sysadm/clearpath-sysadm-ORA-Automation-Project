
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
    if log_file_path and not IS_CLOUD_ENV:
        # Ensure the log directory exists
        log_directory = os.path.dirname(log_file_path)
        if log_directory and not os.path.exists(log_directory):
            try:
                os.makedirs(log_directory)
            except OSError as e:
                # Log an error if directory creation fails, but don't stop execution
                # Console handler will still work if enabled
                logger.error(f"Could not create log directory {log_directory}: {e}")
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


# Example usage (for testing this module directly)
if __name__ == '__main__':
    # Set up logging to a test file in a 'test_logs' subdirectory
    # Ensure 'test_logs' directory exists or is created by the function
    test_log_dir = os.path.join(os.getcwd(), 'test_logs')
    test_log_file = os.path.join(test_log_dir, 'ora_test.log')

    print(f"Setting up logging. Test log file will be at: {test_log_file}")
    setup_logging(log_file_path=test_log_file, log_level=logging.DEBUG, enable_console_logging=True)

    # Now, use the logger to send some messages
    logger = logging.getLogger(__name__) # Get a logger for this specific module

    logger.debug("This is a DEBUG message.")
    logger.info("This is an INFO message, showing normal operation.")
    logger.warning("This is a WARNING message, something might be slightly off.")
    logger.error("This is an ERROR message, indicating a significant problem.")
    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("An exception occurred during division by zero!")

    print("\nLogging setup complete. Check the console and 'test_logs/ora_test.log' for output.")
    print("If 'test_logs' didn't exist, it should have been created.")
