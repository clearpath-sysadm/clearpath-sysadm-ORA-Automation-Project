# filename: src/utils/notification_manager.py
"""
This module provides a centralized mechanism for sending automated notifications (e.g., emails).
It is designed to use a third-party email API service for reliable delivery from Cloud Functions.
This version integrates with SendGrid.
"""
import logging

# Import central settings and secret manager client
from config import settings
from src.services.gcp.secret_manager import access_secret_version

# Import SendGrid client library components
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To

logger = logging.getLogger(__name__)

def send_email_via_api(recipients: list, subject: str, body: str) -> bool:
    """
    Sends an email using the SendGrid API service.
    Retrieves the SendGrid API key from Secret Manager.

    Args:
        recipients (list): A list of email addresses to send the email to.
        subject (str): The subject line of the email.
        body (str): The plain text body of the email.

    Returns:
        bool: True if the email was successfully sent, False otherwise.
    """
    if not recipients:
        logger.warning({"message": "No recipients specified for email. Skipping email send.", "subject": subject})
        return False

    sendgrid_api_key = access_secret_version(
        settings.YOUR_GCP_PROJECT_ID,
        settings.EMAIL_SERVICE_API_KEY_SECRET_ID,
        credentials_path=settings.SERVICE_ACCOUNT_KEY_PATH # For local testing
    )
    if not sendgrid_api_key:
        logger.critical({"message": "SendGrid API key not found in Secret Manager. Cannot send email.", "secret_id": settings.EMAIL_SERVICE_API_KEY_ID, "subject": subject}) # Corrected: Use EMAIL_SERVICE_API_KEY_SECRET_ID
        return False

    try:
        sg = sendgrid.SendGridAPIClient(sendgrid_api_key)
        
        # Ensure your 'from_email' is a verified sender in your SendGrid account.
        # Replace "no-reply@ora-automation.com" with your actual verified sender email.
        from_email = Email("no-reply@ora-automation.com", "ORA Automation System")
        
        # Convert list of recipient strings to list of SendGrid To objects
        to_emails = [To(email) for email in recipients]
        
        # Create the Mail object
        message = Mail(from_email, to_emails, subject, plain_text_content=body)
        
        # Send the email
        response = sg.send(message)
        
        # Log the SendGrid API response for debugging and monitoring
        logger.info({
            "message": "Email sent via SendGrid API",
            "sendgrid_status_code": response.status_code,
            "sendgrid_headers": dict(response.headers), # Convert headers to dict for logging
            "sendgrid_body": response.body.decode('utf-8') if response.body else None, # Decode body if present
            "recipients": recipients,
            "subject": subject
        })

        # SendGrid typically returns 200 (OK) or 202 (Accepted) for successful requests.
        if response.status_code in [200, 202]:
            logger.info({"message": "Email successfully sent via SendGrid.", "recipients": recipients, "subject": subject})
            return True
        else:
            logger.error({
                "message": "SendGrid API returned an error status.",
                "sendgrid_status_code": response.status_code,
                "sendgrid_body": response.body.decode('utf-8') if response.body else None,
                "recipients": recipients,
                "subject": subject
            })
            return False

    except Exception as e:
        logger.error({
            "message": "An unexpected error occurred while sending email via SendGrid.",
            "error": str(e),
            "recipients": recipients,
            "subject": subject
        }, exc_info=True)
        return False

