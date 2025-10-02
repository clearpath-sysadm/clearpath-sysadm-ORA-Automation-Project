import logging
import requests
import json
import os
import sys

# Try relative import first, which is the correct way when this module is part of a package.
try:
    from .logging_config import setup_logging
except ImportError:
    # If a relative import fails (this typically happens when the script is run directly
    # and Python doesn't recognize it as part of a package), we adjust sys.path
    # to allow an absolute import based on the project structure.
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    # Now, attempt the import using the absolute path relative to the project root.
    from utils.logging_config import setup_logging

# --- Setup Logging for this module (for standalone testing and general use) ---
# This block handles the logger instance for this specific module.
# The 'setup_logging' function (which configures the root logger) should ideally
# be called once at the main entry point of your application.
# However, for demonstration and direct execution of this 'api_utils.py',
# we ensure that the logging system is configured if it hasn't been already.
_log_dir = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')), 'logs')
_log_file = os.path.join(_log_dir, 'app.log')

# Check if logging is already configured. If not, configure it.
# This prevents re-adding handlers if setup_logging is called multiple times by different modules
# or if the main application already configured it.
if not logging.getLogger().handlers:
    setup_logging(log_file_path=_log_file, log_level=logging.DEBUG, enable_console_logging=True)

logger = logging.getLogger(__name__) # Get a logger instance for this module

# --- Retry Strategy Configuration ---
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    retry_if_exception
)
import time

def is_retryable_error(exception):
    """Check if exception is retryable (including 429 rate limit)"""
    if isinstance(exception, requests.exceptions.HTTPError):
        return exception.response.status_code == 429
    return isinstance(exception, (
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.TooManyRedirects,
        requests.exceptions.RequestException
    ))

RETRY_STRATEGY = retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception(is_retryable_error),
    reraise=True
)

@RETRY_STRATEGY
def make_api_request(url: str, method: str = 'GET', data: dict = None, headers: dict = None, params: dict = None, timeout: int = 30):
    """
    Makes an API request with built-in retry logic and logging.

    Args:
        url (str): The URL for the API endpoint.
        method (str): The HTTP method ('GET', 'POST', 'PUT', 'DELETE'). Defaults to 'GET'.
        data (dict): Dictionary of data to send in the request body (for POST/PUT). Defaults to None.
        headers (dict): Dictionary of HTTP headers to send. Defaults to None.
        params (dict): Dictionary of URL query parameters. Defaults to None.
        timeout (int): Timeout for the request in seconds. Defaults to 30.

    Returns:
        requests.Response: The response object from the API call.

    Raises:
        requests.exceptions.RequestException: If the request fails after all retries,
                                              or for non-retryable HTTP errors.
        json.JSONDecodeError: If response content is not valid JSON and `json()` is called.
    """
    logger.info(f"Attempting {method} request to: {url}")
    if data:
        # In a real scenario, be careful about logging sensitive data (e.g., passwords, API keys)
        logger.debug(f"Request data: {data}")

    try:
        if method.upper() == 'GET':
            response = requests.get(url, headers=headers, params=params, timeout=timeout)
        elif method.upper() == 'POST':
            response = requests.post(url, json=data, headers=headers, params=params, timeout=timeout)
        elif method.upper() == 'PUT':
            response = requests.put(url, json=data, headers=headers, params=params, timeout=timeout)
        elif method.upper() == 'DELETE':
            response = requests.delete(url, headers=headers, params=params, timeout=timeout)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        # Raise an HTTPError for bad responses (4xx or 5xx)
        # This allows tenacity to retry on certain status codes if configured,
        # otherwise it will immediately fail and be caught by the outer try-except.
        response.raise_for_status()

        logger.info(f"Successfully received response from {url} with status code: {response.status_code}")
        return response

    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code
        
        if status_code == 429:
            retry_after = e.response.headers.get('Retry-After', '60')
            try:
                wait_seconds = int(retry_after)
            except ValueError:
                wait_seconds = 60
            
            logger.warning(f"Rate limit (429) hit for {url}. Retry-After: {wait_seconds}s. Will retry with exponential backoff.")
        else:
            logger.error(f"HTTP Error {status_code} for {url}: {e.response.text}")
        
        raise

    except requests.exceptions.RequestException as e:
        # Catch broader requests exceptions (connection errors, timeouts, etc.)
        logger.error(f"Request failed for {url} due to network/request issue: {e}")
        raise # Re-raise for tenacity or the caller to handle

    except Exception as e:
        # Catch any other unexpected errors during the request process
        logger.critical(f"An unexpected error occurred during API request to {url}: {e}", exc_info=True)
        raise # Re-raise unknown exceptions

# --- Example Usage (for testing this module directly) ---
if __name__ == '__main__':
    # This example requires a valid URL to test against.
    TEST_API_URL_SUCCESS = "https://jsonplaceholder.typicode.com/todos/1"
    TEST_API_URL_FAIL_404 = "https://jsonplaceholder.typicode.com/nonexistent-endpoint"
    POST_API_URL = "https://jsonplaceholder.typicode.com/posts"

    print(f"Testing API utilities. Logs will be written to: {_log_file}")

    # Test Case 1: Successful GET request
    print("\n--- Test Case 1: Successful GET Request ---")
    try:
        response = make_api_request(TEST_API_URL_SUCCESS, method='GET')
        print(f"Success! Response JSON: {json.dumps(response.json(), indent=2)}")
    except requests.exceptions.RequestException as e:
        print(f"Test Case 1 Failed: {type(e).__name__}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred in Test Case 1: {type(e).__name__}: {e}")

    # Test Case 2: Failed GET request (e.g., 404 Not Found)
    print("\n--- Test Case 2: Failed GET Request (404) ---")
    try:
        response = make_api_request(TEST_API_URL_FAIL_404, method='GET')
        print(f"Unexpected Success for 404! Response: {response.status_code}")
    except requests.exceptions.HTTPError as e:
        print(f"Test Case 2 Expected Failure (HTTP Error): {e.response.status_code} - {e.response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Test Case 2 Unexpected Request Failure: {type(e).__name__}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred in Test Case 2: {type(e).__name__}: {e}")

    # Test Case 3: Simulate a POST request with data
    print("\n--- Test Case 3: Simulate POST Request ---")
    post_data = {"title": "foo", "body": "bar", "userId": 1}
    try:
        response = make_api_request(POST_API_URL, method='POST', data=post_data,
                                     headers={"Content-Type": "application/json"})
        print(f"POST Success! Response JSON: {json.dumps(response.json(), indent=2)}")
    except requests.exceptions.RequestException as e:
        print(f"Test Case 3 Failed: {type(e).__name__}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred in Test Case 3: {type(e).__name__}: {e}")

    print("\nAPI utility testing complete. Check the console and 'logs/app.log' for detailed output.")
