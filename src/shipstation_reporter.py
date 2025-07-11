# shipstation_reporter.py
import logging

logger = logging.getLogger(__name__)

# This is the simplified entry point for the Cloud Function (HTTP trigger)
def shipstation_reporter_http_trigger(request):
    """
    Cloud Function entry point for HTTP trigger.
    Returns a simple success message to pass health check.
    """
    logger.info("Cloud Function received HTTP trigger. Testing extremely basic response.")
    return 'Hello from Basic Cloud Function!', 200

# All other imports, functions (main, run_reporter_logic, etc.),
# and the if __name__ == "__main__": main() block should be commented out or removed.
# Ensure no local file logging setup remains.