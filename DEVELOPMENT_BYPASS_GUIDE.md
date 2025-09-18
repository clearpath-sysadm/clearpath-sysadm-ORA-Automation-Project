# ORA Automation - Development Bypass System Guide

## 🔧 Overview

The Development Bypass System allows the ORA Automation Project to run completely offline without any external API dependencies. This enables rapid development, testing, and demonstration of the full business logic using realistic sample data.

## 🎯 Purpose & Benefits

### Why Development Bypasses?
- **Offline Development**: Work without internet or API access
- **Rapid Testing**: Immediate feedback without API rate limits
- **Demo Ready**: Show complete workflows with realistic data
- **Cost Efficient**: No API usage charges during development
- **Predictable Results**: Consistent sample data for testing

### Security Features
- **Auto-Disabled in Cloud**: Bypasses automatically turn off in production
- **Environment Gated**: Only work when `DEV_MODE=1` is explicitly set
- **No Credential Exposure**: Mock credentials never touch real systems
- **Safe Defaults**: Production mode is the default state

## ⚙️ Configuration System

### Master Development Switch
```bash
export DEV_MODE=1  # Enables all development features
```

**Automatic Behavior**:
- `DEV_MODE=1` + Local Environment = Bypasses ENABLED
- `DEV_MODE=1` + Cloud Environment = Bypasses DISABLED (security)
- `DEV_MODE=0` or unset = Bypasses DISABLED

### Individual Service Controls
Each external service can be independently controlled:

```bash
# Google Cloud Secret Manager bypass (enabled by default in dev mode)
export DEV_BYPASS_SECRETS=1

# Google Sheets API bypass (enabled by default in dev mode)  
export DEV_FAKE_SHEETS=1

# ShipStation API bypass (enabled by default in dev mode)
export DEV_FAKE_SHIPSTATION=1

# Email/SendGrid bypass (enabled by default in dev mode)
export DEV_DISABLE_EMAILS=1
```

## 🔐 Secret Manager Bypass

### Location: `src/services/gcp/secret_manager.py`

### Functionality
When `DEV_BYPASS_SECRETS=1`:
- Returns predefined mock credentials
- Logs bypass activity for transparency
- Never attempts to contact Google Cloud Secret Manager

### Mock Credentials Provided
```python
mock_secrets = {
    "google-sheets-service-account-key": "mock-sheets-key-content",
    "shipstation-api-key": "mock-shipstation-key",
    "shipstation-api-secret": "mock-shipstation-secret", 
    "sendgrid-api-key": "mock-sendgrid-key"
}
```

### Usage Example
```python
from src.services.gcp.secret_manager import get_secret

# In DEV_MODE: Returns mock data instantly
# In Production: Retrieves from Google Cloud Secret Manager
api_key = get_secret("shipstation-api-key")
```

## 📊 Google Sheets Bypass

### Location: `src/services/google_sheets/api_client.py`

### Functionality
When `DEV_FAKE_SHEETS=1`:
- Loads data from local JSON fixtures instead of Google Sheets
- Returns data in identical format to live API
- Supports all worksheet names used by the business logic

### Fixture Data Location
```
src/test_data/dev_fixtures/
├── ora_configuration.json         # Business config & product data
├── inventory_transactions.json    # Stock movements
├── shipped_items_data.json       # Order line items  
├── shipped_orders_data.json       # Complete orders
└── ora_weekly_shipped_history.json # Historical shipping data
```

### Fixture Data Contents

**Business Configuration** (`ora_configuration.json`):
- **5 Key Products**: ORA Clarity Complete, Rinse Refill, Essential Kit, Travel Pack, Premium Bundle
- **Business Rates**: Storage ($0.15), Handling ($2.50), Packing ($1.25)
- **Pallet Configurations**: Items per pallet for each product
- **Inventory Levels**: Starting and current quantities
- **Reporting Dates**: Current report periods and date ranges

**Transaction Data**:
- **Inventory Transactions**: Stock adjustments, receipts, and corrections
- **Shipped Items**: Individual line items from fulfilled orders
- **Shipped Orders**: Complete order records with customer data
- **Weekly History**: 60+ rows of historical shipping patterns by product

### Usage Example
```python
from src.services.google_sheets.api_client import get_google_sheet_data

# In DEV_MODE: Loads from local JSON file
# In Production: Retrieves from live Google Sheets
data = get_google_sheet_data(sheet_id, "ORA_Configuration")
```

## 📧 Email Notification Bypass

### Location: `utils/notification_manager.py`

### Functionality
When `DEV_DISABLE_EMAILS=1`:
- Logs email content instead of sending
- Preserves all business logic around notifications
- Shows complete email composition and recipient handling

### Log Output Example
```
INFO - DEV_BYPASS ACTIVE - Email: Would send to ['user@example.com']
INFO - DEV_BYPASS ACTIVE - Subject: Weekly Inventory Report
INFO - DEV_BYPASS ACTIVE - Content: [Complete email body with data]
```

## 🚢 ShipStation API Bypass

### Location: `src/services/shipstation/api_client.py`

### Functionality
When `DEV_FAKE_SHIPSTATION=1`:
- Returns mock responses for all API endpoints
- Simulates successful order creation and shipment tracking
- Provides realistic response timing and structure

### Mock Response Examples
```python
# Order creation response
{
    "orderId": "mock-order-123",
    "orderNumber": "DEV-ORDER-456", 
    "status": "awaiting_shipment",
    "createDate": "2025-01-15T10:30:00.000"
}

# Shipment tracking response
{
    "shipments": [
        {
            "shipmentId": "mock-shipment-789",
            "trackingNumber": "DEV-TRACK-001",
            "carrierCode": "fedex"
        }
    ]
}
```

## 🔄 Complete Workflow Example

### Running Weekly Reporter in Development Mode
```bash
# Enable development mode
export DEV_MODE=1

# Run the weekly reporter
python src/weekly_reporter.py
```

### Expected Processing Flow
1. **Load Configuration**: 5 products from `ora_configuration.json`
2. **Load History**: 60 rows of weekly shipping data
3. **Load Transactions**: 15 inventory transactions + 13 shipped items
4. **Calculate Inventory**: Real business math with sample data
5. **Calculate Averages**: 12-month rolling averages  
6. **Generate Report**: Complete inventory report with all calculations
7. **Log Results**: Full visibility into data processing

### Sample Log Output
```
INFO - weekly_reporter - Weekly Reporter started. Environment: UNKNOWN
INFO - report_data_loader - Successfully retrieved 5 key SKUs and product names
INFO - weekly_reporter - Step 1 Complete: Found 5 Key SKUs
INFO - google_sheets.api_client - 🔧 DEV BYPASS ACTIVE - Loading fixture for 'Inventory_Transactions'
INFO - weekly_reporter - Step 3 Complete: Fetched 15 inventory transactions and 13 shipped items
INFO - weekly_reporter - Step 5 Complete: Calculated rolling average for 5 SKUs
```

## 🎛️ Advanced Development Features

### Environment Detection
The system automatically detects where it's running:
- **Local Development**: Full bypass capabilities enabled
- **Google Cloud**: Bypasses automatically disabled for security
- **Unknown Environment**: Defaults to production behavior

### Fixture Data Management
- **Realistic Scale**: Sample data matches production data volume and structure
- **Business Logic Testing**: All calculations and workflows process real business scenarios
- **Easy Updates**: JSON format allows easy modification for testing different scenarios

### Debug and Testing
- **Complete Workflows**: End-to-end business process execution
- **Performance Testing**: Measure processing time with realistic data loads  
- **Logic Validation**: Verify calculations and report generation accuracy
- **Integration Testing**: Test all service interactions without external dependencies

## 🚀 Development Best Practices

### Getting Started
1. **Clone Repository**: `git clone [repo-url]`
2. **Install Dependencies**: `pip install -r requirements.txt`
3. **Enable Dev Mode**: `export DEV_MODE=1`
4. **Run Any Script**: Complete workflows work immediately

### Testing Different Scenarios
1. **Modify Fixtures**: Edit JSON files to test edge cases
2. **Change Date Ranges**: Update reporting periods in configuration
3. **Add Products**: Extend fixture data for new business scenarios
4. **Test Error Handling**: Remove fixture files to test error paths

### Transition to Production
1. **Disable Dev Mode**: `unset DEV_MODE` or `export DEV_MODE=0`
2. **Configure Credentials**: Set up Google Cloud service accounts
3. **Test Production APIs**: Verify real API connectivity
4. **Deploy to Cloud**: Use CloudBuild configurations for deployment

## 🔍 Troubleshooting

### Common Issues
- **Bypasses Not Working**: Verify `DEV_MODE=1` is set and environment is detected as local
- **Missing Fixture Data**: Check files exist in `src/test_data/dev_fixtures/`
- **Log Level**: Ensure logging is set to INFO or DEBUG to see bypass messages
- **Import Errors**: Verify Python path includes project root directory

### Verification Commands
```bash
# Check environment variables
echo $DEV_MODE

# Verify fixture files exist
ls -la src/test_data/dev_fixtures/

# Test with debug logging
export LOG_LEVEL=DEBUG
python src/weekly_reporter.py
```

The Development Bypass System provides a complete offline development experience that maintains full business logic fidelity while eliminating external dependencies and associated complexity.