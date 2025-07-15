# filename: src/services/google_drive/api_client.py
"""
This module provides functions for interacting with the Google Drive API,
specifically for fetching file content.
"""
import json
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from io import BytesIO
from googleapiclient.http import MediaIoBaseDownload

# Import central settings
from config import settings

# Initialize logger for this module
logger = logging.getLogger(__name__)

def fetch_xml_content_from_drive(file_id: str, service_account_key_json: str) -> str | None:
    """
    Securely retrieves and decodes XML content from a specified Google Drive file ID in-memory.

    Args:
        file_id (str): The Google Drive File ID of the XML file to fetch.
        service_account_key_json (str): The JSON content of the Google Service Account key
                                        as a string, used for authentication.

    Returns:
        str | None: The decoded XML content as a string if successful, None otherwise.
    """
    if not file_id:
        logger.error({"message": "Google Drive File ID is missing.", "function": "fetch_xml_content_from_drive"})
        return None
    if not service_account_key_json:
        logger.critical({"message": "Google Service Account JSON key is missing for Drive access.", "function": "fetch_xml_content_from_drive"})
        return None

    try:
        creds_info = json.loads(service_account_key_json)
        creds = service_account.Credentials.from_service_account_info(creds_info, scopes=settings.SCOPES)
        service = build('drive', 'v3', credentials=creds)
        logger.debug({"message": "Google Drive API service client built successfully.", "function": "fetch_xml_content_from_drive"})

        # First, get file metadata to confirm it's a non-native file and get its actual mimeType
        # This helps in debugging if alt='media' behaves unexpectedly
        file_metadata = service.files().get(fileId=file_id, fields='name,mimeType,size').execute()
        file_name = file_metadata.get('name')
        file_mime_type = file_metadata.get('mimeType')
        file_size = file_metadata.get('size') # Size in bytes

        logger.info({
            "message": "Confirmed file metadata from Google Drive.",
            "file_id": file_id,
            "file_name": file_name,
            "file_mime_type": file_mime_type,
            "file_size_bytes": file_size
        })

        if file_mime_type != 'text/xml':
            logger.warning({
                "message": "File is not of expected text/xml MIME type. Attempting to fetch anyway, but may cause parsing issues.",
                "file_id": file_id,
                "actual_mime_type": file_mime_type
            })
        
        # Request the media content
        request = service.files().get_media(fileId=file_id) # Use get_media() directly for raw content
        
        file_content_stream = BytesIO()
        downloader = MediaIoBaseDownload(file_content_stream, request)
        
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            # CORRECTED: Call the progress method to get its value for logging
            logger.debug({"message": "Downloading chunk from Google Drive", "status_progress": status.progress(), "file_id": file_id})
        
        xml_content_bytes = file_content_stream.getvalue()
        
        logger.info({"message": "File content fetched from Google Drive.", "file_id": file_id, "content_length_bytes": len(xml_content_bytes), "function": "fetch_xml_content_from_drive"})

        if isinstance(xml_content_bytes, bytes):
            if not xml_content_bytes: # Check if content is empty after fetch
                logger.warning({"message": "Fetched XML content is empty.", "file_id": file_id, "function": "fetch_xml_content_from_drive"})
                return None
            
            xml_string = xml_content_bytes.decode('utf-8')
            logger.info({"message": "XML content successfully fetched and decoded from Google Drive.", "file_id": file_id, "function": "fetch_xml_content_from_drive"})
            return xml_string
        else:
            logger.critical({
                "message": "Fetched content is not bytes; expected XML bytes but received unexpected type.",
                "file_id": file_id,
                "received_type": str(type(xml_content_bytes)),
                "received_content_start": str(xml_content_bytes)[:200],
                "function": "fetch_xml_content_from_drive"
            })
            return None

    except HttpError as e:
        logger.error({
            "message": "Google Drive API HTTP error during file fetch.",
            "file_id": file_id,
            "error_code": e.resp.status,
            "error_details": e.content.decode('utf-8') if e.content else "No error details",
            "function": "fetch_xml_content_from_drive"
        }, exc_info=True)
        return None
    except json.JSONDecodeError as e:
        logger.critical({
            "message": "Failed to parse service account JSON key.",
            "error": str(e),
            "function": "fetch_xml_content_from_drive"
        }, exc_info=True)
        return None
    except UnicodeDecodeError as e:
        logger.error({
            "message": "Failed to decode XML content to UTF-8. Content might be corrupted or in a different encoding.",
            "file_id": file_id,
            "error": str(e),
            "function": "fetch_xml_content_from_drive"
        }, exc_info=True)
        return None
    except Exception as e:
        logger.critical({
            "message": "An unexpected error occurred while fetching XML from Google Drive.",
            "file_id": file_id,
            "error": str(e),
            "function": "fetch_xml_content_from_drive"
        }, exc_info=True)
        return None

