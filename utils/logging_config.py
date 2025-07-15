import logging
import os
import json
from logging.handlers import RotatingFileHandler
from datetime import datetime

class JsonFormatter(logging.Formatter):
    """
    A custom formatter that outputs log records as JSON strings.
    This is crucial for structured logging in Google Cloud Logging.
    """
    def format(self, record):
        # Base log record structure. Google Cloud Logging automatically
        # picks up 'severity', 'message', 'timestamp', and 'logger' fields.
        log_record = {
            "severity": record.levelname,
            "timestamp": datetime.fromtimestamp(record.created).isoformat() + "Z", # ISO 8601 with Z for UTC
            "logger": record.name,
            "message": record.getMessage(), # Get the formatted message
        }

        # If the log message itself is a dictionary, it means the calling code
        # is providing structured data. We merge this into the log_record,
        # and ensure the 'message' field from the dictionary takes precedence
        # if it exists, or keep the default record.getMessage().
        if isinstance(record.msg, dict):
            # Merge the dictionary from record.msg into the log_record
            log_record.update(record.msg)
            # Ensure a 'message' field is always present, taking the one from record.msg if provided
            log_record["message"] = record.msg.get("message", record.getMessage())

        # Add additional standard record attributes if useful for debugging in JSON
        # For example, module, line number, process ID, thread ID
        log_record["module"] = record.module
        log_record["funcName"] = record.funcName
        log_record["lineno"] = record.lineno
        log_record["process"] = record.process
        log_record["thread"] = record.thread

        # If an exception was logged, include its details
        if record.exc_info:
            log_record["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info:
            log_record["stack_info"] = self.formatStack(record.stack_info)

        # CORRECTED: Use json.dumps with indent for pretty-printing locally
        return json.dumps(log_record, indent=2)

def setup_logging(log_file_path=None, log_level=logging.INFO, enable_console_logging=True):
    """
    Sets up a standardized structured logging configuration for the ORA Project.

    This function configures the root logger to:
    1. Output messages to the console (stdout/stderr) as JSON (for Cloud Logging).
    2. Optionally write messages to a rotating file (primarily for local development).

    Args:
        log_file_path (str, optional): The full path to the log file for local storage.
                                       If None, file logging is disabled.
                                       Defaults to None (recommended for cloud deployment).
        log_level (int, optional): The minimum logging level to capture (e.g., logging.INFO,
                                   logging.DEBUG, logging.ERROR). Defaults to logging.INFO.
        enable_console_logging (bool, optional): If True, log messages will also be
                                                 printed to the console (stdout/stderr).
                                                 This is crucial for Google Cloud Functions
                                                 as they ingest logs from stdout/stderr.
                                                 Defaults to True.
    """
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Prevent adding multiple handlers if setup_logging is called multiple times.
    if not logger.handlers:
        # Define the custom JSON formatter
        json_formatter = JsonFormatter()

        # 1. Console Handler (for Cloud Logging ingestion in GCF and local console output)
        if enable_console_logging:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(json_formatter)
            logger.addHandler(console_handler)

        # 2. File Handler (optional, primarily for local development/debugging)
        if log_file_path:
            log_directory = os.path.dirname(log_file_path)
            if log_directory and not os.path.exists(log_directory):
                try:
                    os.makedirs(log_directory)
                except OSError as e:
                    logger.error(f"Could not create log directory {log_directory}: {e}")
                    log_file_path = None

            if log_file_path:
                file_handler = RotatingFileHandler(
                    log_file_path,
                    maxBytes=10 * 1024 * 1024,  # 10 MB
                    backupCount=5
                )
                file_handler.setFormatter(json_formatter)
                logger.addHandler(file_handler)

    logger.debug({"message": "Logging system initialized", "log_level": logging.getLevelName(log_level)})
    if log_file_path:
        logger.debug({"message": "Log file output configured", "path": log_file_path})

# Example usage (for testing this module directly)
if __name__ == '__main__':
    test_log_dir = os.path.join(os.getcwd(), 'test_logs')
    test_log_file = os.path.join(test_log_dir, 'ora_test.log')

    print(f"Setting up logging. Test log file will be at: {test_log_file}")
    setup_logging(log_file_path=test_log_file, log_level=logging.DEBUG, enable_console_logging=True)

    test_logger = logging.getLogger(__name__)

    test_logger.debug({"message": "This is a DEBUG message.", "data_point": 123})
    test_logger.info({"message": "This is an INFO message, showing normal operation.", "event_id": "E001"})
    test_logger.warning({"message": "This is a WARNING message, something might be slightly off.", "issue_code": "W002", "component": "API_Client"})
    test_logger.error({"message": "This is an ERROR message, indicating a significant problem.", "error_code": "ERR_003", "context": "ShipStation_Upload"})
    try:
        1 / 0
    except ZeroDivisionError:
        test_logger.exception({"message": "An exception occurred during division by zero!", "operation": "calculation_error"})

    print("\nLogging setup complete. Check the console and 'test_logs/ora_test.log' for structured JSON output.")
    print("If 'test_logs' didn't exist, it should have been created.")
