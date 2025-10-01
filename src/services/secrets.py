import os
from typing import Optional

def get_secret(secret_name: str) -> Optional[str]:
    """
    Universal secret getter - Replit first, then GCP fallback.
    
    Args:
        secret_name: The name of the secret to retrieve
        
    Returns:
        The secret value as a string, or None if not found
    """
    # Replit environment?
    if os.getenv('REPL_ID') or os.getenv('REPLIT_ENV'):
        value = os.getenv(secret_name)
        if value:
            return value
    
    # Fallback to GCP Secret Manager
    try:
        from src.services.gcp.secret_manager import access_secret_version
        from config.settings import settings
        return access_secret_version(
            settings.YOUR_GCP_PROJECT_ID,
            secret_name,
            credentials_path=settings.SERVICE_ACCOUNT_KEY_PATH
        )
    except Exception:
        return None
