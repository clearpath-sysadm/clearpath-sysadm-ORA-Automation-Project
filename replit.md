# ORA Automation Project

## Overview
This is a Python-based automation system for ORA (Oracare) that handles shipment processing, inventory tracking, and reporting. The project is designed to run as Google Cloud Functions but can also be executed locally.

## Project Architecture
The project consists of several main components:

### Main Entry Points
- `src/weekly_reporter.py` - Generates weekly inventory reports
- `src/daily_shipment_processor.py` - Processes daily shipment data
- `src/shipstation_order_uploader.py` - Uploads orders to ShipStation
- `src/shipstation_reporter.py` - Generates shipment reports
- `src/main_order_import_daily_reporter.py` - Daily import summary reporter

### Key Services
- `src/services/google_sheets/` - Google Sheets API integration
- `src/services/shipstation/` - ShipStation API integration
- `src/services/reporting_logic/` - Business logic for reports and calculations
- `src/services/gcp/` - Google Cloud Platform integrations

### Configuration
- `config/settings.py` - Centralized configuration with environment detection
- Environment variables and secret management for API keys

## Current Setup in Replit
- **Workflow**: `weekly-reporter` running `python src/weekly_reporter.py`
- **Environment**: Python 3.11 with all required dependencies installed
- **Deployment**: Configured for VM deployment (stateful application)

## External Dependencies
This project requires:
- Google Cloud Secret Manager for API keys
- Google Sheets API access
- ShipStation API credentials
- SendGrid for email notifications (optional)

## Recent Changes
- Fixed import issues with notification manager
- Added missing functions to report data loader
- Set up Replit workflow and deployment configuration
- Project successfully imported and configured for Replit environment

## Notes
The application may require actual Google Cloud credentials and API keys to fully function, as it's designed to work with live Google Sheets and external APIs. In the Replit environment, it will run but may hang on API calls without proper authentication.