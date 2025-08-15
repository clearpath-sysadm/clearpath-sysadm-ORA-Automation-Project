# --- Cloud Function HTTP Entry Point ---
def daily_shipment_processor_http_trigger(request):
    """
    Cloud Function entry point for HTTP trigger.
    Triggers the daily shipment processor logic.
    """
    logger.info("Cloud Function received HTTP trigger. Starting daily shipment processor logic.")
    try:
        result, status = run_daily_shipment_pull(request)
        logger.info("Cloud Function execution completed successfully.")
        return result, status
    except Exception as e:
        logger.critical(f"Cloud Function execution failed: {e}", exc_info=True)
        return f"Daily Shipment Processor script failed: {e}", 500
