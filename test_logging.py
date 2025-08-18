from utils.logging_config import setup_logging
import os

log_dir = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'daily_processor.log')

print(f"[DEBUG] Test log file should be at: {os.path.abspath(log_file)}")
setup_logging(log_file_path=log_file, log_level=10, enable_console_logging=True)

import logging
logger = logging.getLogger(__name__)
logger.info("[TEST] Standalone logger test. This should appear in daily_processor.log and console.")
