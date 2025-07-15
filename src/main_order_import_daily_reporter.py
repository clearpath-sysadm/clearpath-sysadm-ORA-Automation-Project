# filename: src/main_order_import_daily_reporter.py
"""
This script serves as a daily reporter for the ShipStation Order Uploader.
It queries Google Cloud Logging for order import statistics (successful, skipped, errors)
from the previous 24 hours and sends a summary email.
"""
import os
import sys
import logging
import datetime

# Add the project root to the Python path to enable imports from utils and config
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Core utility imports
from utils.logging_config import setup_logging
from config import settings
# NEW: Import the notification manager for sending emails
from src.utils.notification_manager import send_email_via_api

# Google Cloud Logging client library
from google.cloud import logging_v2

# --- Setup Logging for this script ---
_log_file_path = None # Default to no file logging for cloud deployment
if not logging.getLogger().handlers:
    setup_logging(log_file_path=_log_file_path, log_level=logging.INFO, enable_console_logging=True)
logger = logging.getLogger(__name__)

def query_cloud_logging_for_metrics(project_id: str, start_time: datetime.datetime, end_time: datetime.datetime) -> dict:
    """
    Queries Google Cloud Logging for order import statistics from the main_shipstation_order_uploader.py.

    Args:
        project_id (str): Your Google Cloud Project ID.
        start_time (datetime.datetime): The start of the time window for the query (UTC).
        end_time (datetime.datetime): The end of the time window for the query (UTC).

    Returns:
        dict: A dictionary containing counts for processed, successful, skipped, and error orders.
    """
    client = logging_v2.Client(project=project_id)
    
    # Define the base filter for logs from the order uploader script
    # This should match the deployed Cloud Function name for the order uploader.
    uploader_function_name = "shipstation_order_uploader" # Corrected: Matches the actual file name for deployment
    base_filter = f'resource.type="cloud_function" AND resource.labels.function_name="{uploader_function_name}"'
    
    # Convert datetime objects to ISO 8601 strings for the filter
    start_time_iso = start_time.isoformat(timespec='seconds') + 'Z'
    end_time_iso = end_time.isoformat(timespec='seconds') + 'Z'
    time_filter = f'timestamp >= "{start_time_iso}" AND timestamp < "{end_time_iso}"'

    # Initialize counts
    metrics = {
        "total_processed": 0,
        "successful_imports": 0,
        "skipped_duplicates": 0,
        "errors": 0,
        "warnings": 0,
        "critical_failures": 0,
        "log_query_errors": []
    }

    logger.info({"message": "Starting Cloud Logging query for order import metrics",
                 "start_time": start_time_iso, "end_time": end_time_iso, "target_function": uploader_function_name})

    try:
        # Query for total orders processed (e.g., "Orders prepared for upload")
        # We assume the 'count' field in the structured log gives the number of orders prepared.
        total_processed_filter = f'{base_filter} AND {time_filter} AND jsonPayload.message="Orders prepared for upload"'
        for entry in client.list_entries(filter_=total_processed_filter):
            # Sum up the 'count' field from each relevant log entry
            metrics["total_processed"] += entry.json_payload.get("count", 0)

        # Query for successful imports (e.g., "ShipStation single order upload result" with success: True)
        successful_imports_filter = f'{base_filter} AND {time_filter} AND jsonPayload.message="ShipStation single order upload result" AND jsonPayload.success=true'
        for entry in client.list_entries(filter_=successful_imports_filter):
            metrics["successful_imports"] += 1

        # Query for skipped duplicates (e.g., "Skipping duplicate order")
        skipped_duplicates_filter = f'{base_filter} AND {time_filter} AND jsonPayload.message="Skipping duplicate order"'
        for entry in client.list_entries(filter_=skipped_duplicates_filter):
            metrics["skipped_duplicates"] += 1

        # Query for errors (severity ERROR or higher) and warnings
        errors_warnings_filter = f'{base_filter} AND {time_filter} AND severity>="WARNING"'
        for entry in client.list_entries(filter_=errors_warnings_filter):
            if entry.severity == 'ERROR' or entry.severity == 'CRITICAL':
                metrics["errors"] += 1
            if entry.severity == 'CRITICAL':
                metrics["critical_failures"] += 1
            if entry.severity == 'WARNING':
                metrics["warnings"] += 1

        logger.info({"message": "Cloud Logging query completed", "metrics": metrics})

    except Exception as e:
        logger.error({"message": "Error querying Cloud Logging", "error": str(e)}, exc_info=True)
        metrics["log_query_errors"].append(str(e))

    return metrics

def send_summary_email(recipients: list, subject: str, body: str):
    """
    Sends an email summary using the dedicated notification manager.
    """
    # Delegate to the notification_manager module
    return send_email_via_api(recipients, subject, body)

def generate_daily_summary_report():
    """
    Main function to generate and send the daily order import summary.
    """
    logger.info({"message": "Starting daily order import summary report generation."})

    # Define the 24-hour window for the report (UTC)
    end_time = datetime.datetime.now(datetime.timezone.utc)
    start_time = end_time - datetime.timedelta(days=1)

    # Query Cloud Logging for metrics
    metrics = query_cloud_logging_for_metrics(settings.YOUR_GCP_PROJECT_ID, start_time, end_time)

    # Compose the email body
    # Using the start_time for the report date to ensure consistency
    report_date = start_time.strftime('%Y-%m-%d')
    subject = f"Daily ShipStation Order Import Summary - {report_date}"
    
    body = f"""
Dear Team,

Here is the daily summary for ShipStation order imports from {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')} to {end_time.strftime('%Y-%m-%d %H:%M:%S UTC')}:

Total Orders Prepared for Upload: {metrics['total_processed']}
Orders Successfully Imported to ShipStation: {metrics['successful_imports']}
Orders Skipped (Duplicates): {metrics['skipped_duplicates']}

Summary of Issues:
Errors Encountered: {metrics['errors']}
Warnings Encountered: {metrics['warnings']}
Critical Failures: {metrics['critical_failures']}
{f"Cloud Logging Query Errors: {'; '.join(metrics['log_query_errors'])}" if metrics['log_query_errors'] else ""}

This report provides a high-level overview. For detailed logs and troubleshooting, please refer to Google Cloud Logging.

Best regards,
ORA Automation System
"""

    # --- Comment out the following lines to disable email sending ---
    # send_success = send_summary_email(settings.DAILY_SUMMARY_RECIPIENTS, subject, body)

    # if send_success:
    #     logger.info({"message": "Daily summary report email sent successfully.", "recipients": settings.DAILY_SUMMARY_RECIPIENTS})
    # else:
    #     logger.error({"message": "Failed to send daily summary report email.", "recipients": settings.DAILY_SUMMARY_RECIPIENTS})
    # --- End of email sending block ---

    logger.info({"message": "Daily order import summary report generation finished."})


# --- Cloud Function Entry Point ---
# This function name should be your --entry-point when deploying to Google Cloud Functions.
def order_import_daily_reporter_http_trigger(request):
    """
    Google Cloud Function entry point for HTTP trigger.
    Triggers the daily order import summary report generation.
    """
    logger.info({"message": "Cloud Function received HTTP trigger for daily reporter.", "trigger_type": "HTTP"})
    try:
        generate_daily_summary_report()
        logger.info({"message": "Cloud Function execution completed successfully for daily reporter."})
        return 'Daily ShipStation Order Import Reporter script executed successfully!', 200
    except Exception as e:
        logger.critical({"message": "Cloud Function execution failed", "error": str(e)}, exc_info=True)
        return f"Daily ShipStation Order Import Reporter script failed: {e}", 500

