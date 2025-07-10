import os
from google.cloud import secretmanager

def access_secret_version(project_id, secret_id, version_id):
    """
    Access the payload for the given secret version if it exists.
    """
    try:
        # Create the Secret Manager client.
        client = secretmanager.SecretManagerServiceClient()

        # Build the resource name of the secret version.
        name = client.secret_version_path(project_id, secret_id, version_id)

        # Access the secret version.
        response = client.access_secret_version(request={"name": name})

        # Return the decoded payload.
        # The payload is always a bytes object.
        payload = response.payload.data.decode("UTF-8")
        return payload

    except Exception as e:
        print(f"Error accessing secret '{secret_id}' version '{version_id}' in project '{project_id}': {e}")
        return None

# --- Configuration ---
# IMPORTANT: Replace with your actual Google Cloud Project ID
# You can find this in the Google Cloud Console dashboard.
YOUR_PROJECT_ID = "ora-automation-project" # This should be your GCP Project ID

# IMPORTANT: Replace with the actual Secret ID you want to retrieve.
# This is the name you gave your secret in Secret Manager.
# For testing, you could create a simple secret named 'test-api-key'
# with a dummy value like 'my_dummy_api_key_123'.
YOUR_SECRET_ID = "test-api-key" # e.g., "shipstation-api-key" or "test-api-key"

# IMPORTANT: Use 'latest' to get the most recent active version.
# Or specify a specific version number, e.g., "1", "2", etc.
YOUR_SECRET_VERSION = "latest"

if __name__ == "__main__":
    print("Attempting to retrieve secret...")
    secret_value = access_secret_version(
        YOUR_PROJECT_ID,
        YOUR_SECRET_ID,
        YOUR_SECRET_VERSION
    )

    if secret_value:
        print(f"Successfully retrieved secret '{YOUR_SECRET_ID}'.")
        # For security, DO NOT print the actual secret value in production logs.
        # For this test, we can print a truncated version.
        print(f"Secret value (truncated): {secret_value[:5]}...{secret_value[-5:]}")
    else:
        print(f"Failed to retrieve secret '{YOUR_SECRET_ID}'. See error message above.")