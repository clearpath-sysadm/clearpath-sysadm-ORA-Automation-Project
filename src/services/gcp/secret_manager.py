# Standard library imports
import logging
import os

# Third-party imports
# This script now requires 'google-cloud-secret-manager' and 'google-auth' to be installed.
from google.cloud import secretmanager
from google.oauth2 import service_account
from google.auth.exceptions import DefaultCredentialsError

logger = logging.getLogger(__name__)

def access_secret_version(project_id: str, secret_id: str, version_id: str = "latest", credentials_path: str = None) -> str | None:
    """
    Accesses a secret version from Google Cloud Secret Manager.

    This function requires the necessary GCP libraries to be installed and proper
    authentication (either a service account file or Application Default Credentials)
    to be configured in the execution environment.

    Args:
        project_id (str): Your Google Cloud project ID.
        secret_id (str): The ID of the secret to access.
        version_id (str): The version of the secret to access (default is "latest").
        credentials_path (str): The path to the GCP service account JSON file.

    Returns:
        str | None: The secret payload as a string, or None if an error occurs.
    """
    try:
        logger.debug(f"Attempting to access secret '{secret_id}' in project '{project_id}'.")

        # Create credentials from the service account file if path is valid
        if credentials_path and os.path.exists(credentials_path):
            credentials = service_account.Credentials.from_service_account_file(credentials_path)
            client = secretmanager.SecretManagerServiceClient(credentials=credentials)
            logger.debug("Using service account file for authentication.")
        else:
            # Fallback to default credentials if no path is provided
            logger.debug("No valid credentials_path provided. Attempting to use Application Default Credentials.")
            client = secretmanager.SecretManagerServiceClient()

        # Build the resource name of the secret version
        name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"

        # Access the secret version
        response = client.access_secret_version(request={"name": name})

        # Decode the payload
        payload = response.payload.data.decode("UTF-8")
        logger.info(f"Successfully accessed secret '{secret_id}'.")
        return payload

    except DefaultCredentialsError:
        logger.critical(
            "GCP Default Credentials not found. "
            "Ensure you are authenticated (e.g., 'gcloud auth application-default login') "
            "or provide a valid service account file via 'credentials_path'."
        )
        return None
    except Exception as e:
        logger.critical(f"An unexpected error occurred while accessing secret '{secret_id}': {e}", exc_info=True)
        return None
