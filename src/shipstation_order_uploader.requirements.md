# Requirements for ShipStation Order Uploader Module

## Overview
This module automates the process of fetching X-Cart XML order data, transforming it into ShipStation-compatible payloads, and uploading them to the ShipStation API. It is designed to run both locally and as a Google Cloud Function, with environment-aware configuration and logging.

## Functional Requirements

1. **Order Data Retrieval**
   1.1. Fetch X-Cart order data in XML format from a Google Drive file using a service account.
   1.2. The file ID and credentials must be configurable via environment or settings.


2. **Order Parsing and Transformation**
   2.1. Parse the XML to extract order and item details.
   2.2. Transform extracted data into ShipStation-compatible order payloads.
   2.3. Apply product name mappings from a Google Sheet (ORA_Configuration tab) to order items.


3. **Order Selection and Upload Criteria**

   Orders are uploaded to ShipStation only if they meet all of the following criteria:

   3.1. The order is successfully parsed from the X-Cart XML file.
   3.2. The order number does not already exist in ShipStation (duplicate orders are skipped based on order number).
   3.3. The order contains at least one item with a SKU that is valid for processing.
      3.3.1. If an order contains both valid and invalid SKUs, only the valid SKUs are included in the upload; invalid SKUs are ignored and not sent to ShipStation.

   Orders that do not meet these criteria are not uploaded.

4. **Order Upload**

   4.1. Upload all new, unique, and valid orders to ShipStation using the API.
   4.2. Log the result of each upload attempt, including errors.

5. **Configuration and Secrets Management**

   5.1. Retrieve API keys and service account credentials from Google Secret Manager.
   5.2. Support both local (using a JSON key file) and cloud (using environment variables) execution.

6. **Logging**

   6.1. Log all major actions, errors, and results to a file (locally) or console (cloud).
   6.2. Use DEBUG level logging for diagnostics.

## Non-Functional Requirements
- **Environment Awareness**: Must detect and adapt to local or cloud execution environments.
- **Error Handling**: Must log and gracefully handle missing credentials, file access errors, and API failures.
- **Extensibility**: Should allow for easy updates to mapping logic, credential sources, and endpoints.
- **Security**: Secrets must not be hardcoded; use Secret Manager and environment variables.
1. Environment Awareness: Must detect and adapt to local or cloud execution environments.
2. Error Handling: Must log and gracefully handle missing credentials, file access errors, and API failures.
3. Extensibility: Should allow for easy updates to mapping logic, credential sources, and endpoints.
4. Security: Secrets must not be hardcoded; use Secret Manager and environment variables.

## External Dependencies
1. Google Cloud Secret Manager
2. Google Drive API
3. Google Sheets API
4. ShipStation API
5. Python packages: `dateutil`, `logging`, `os`, `json`, `pathlib`, and any others listed in `requirements.txt`

## Inputs
1. X-Cart XML file (Google Drive)
2. Product name mapping sheet (Google Sheets)
3. API credentials (Secret Manager)

## Outputs
1. ShipStation order uploads (API)
2. Logs (file or console)

## User Stories
1. As an operator, I want to upload only new orders to ShipStation, skipping duplicates.
2. As a developer, I want to configure credentials and file IDs without code changes.
3. As a support engineer, I want detailed logs for troubleshooting failures.

## Assumptions
1. The Google Drive file and Google Sheet are shared with the service account.
2. The required secrets are available in Google Secret Manager.
3. The environment is properly configured for local or cloud execution.

---
*Last updated: 2025-08-18*
