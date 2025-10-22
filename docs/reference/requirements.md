# ORA Automation Project - Requirements Document

## 📋 Project Overview

**Project Name**: ORA (Oracare) Business Automation System  
**Purpose**: Automate inventory management, shipment processing, and business reporting  
**Environment**: Replit Development Environment with Python 3.11  

## 🎯 Primary Requirements

### 1. Cost Constraints
- **Critical**: Lowest possible operational cost
- **Critical**: Minimize ongoing infrastructure expenses
- **Preference**: Use existing Replit environment (no additional hosting costs)
- **Constraint**: Avoid cloud services with monthly fees unless absolutely necessary

### 2. Development Time Constraints  
- **Critical**: Least amount of estimated development time
- **Critical**: Rapid implementation and deployment
- **Preference**: Reuse existing codebase without major refactoring
- **Constraint**: Minimize learning curve for new technologies/frameworks

### 3. Web Dashboard Interface
- **Required**: Professional web-based dashboard for business operations
- **Required**: Real-time or near-real-time data updates (15-30 second refresh acceptable)
- **Required**: Responsive design for desktop and mobile access
- **Required**: Intuitive navigation for non-technical business users

## 📊 Functional Requirements

### Dashboard Features
- **KPI Display**: Today's orders, pending uploads, shipments sent, system status
- **Inventory Management**: Current stock levels, low stock alerts, reorder warnings
- **Automation Status**: Workflow monitoring, last run times, success/failure indicators
- **Business Analytics**: Quick metrics, trends, performance summaries
- **Manual Controls**: Ability to trigger automation workflows on-demand
- **File Processing Status**: XML file access status, last processed file timestamps
- **Real-time Order Monitoring**: Display of XML file polling status and new order detection

### Data Integration
- **Google Sheets**: Primary data source for business operations
- **Google Drive/Docs**: Access to XML files containing order data (X-Cart exports)
- **ShipStation API**: Order management and shipping integration
- **Email Notifications**: Automated reports and alerts via SendGrid
- **Secret Management**: Secure credential storage via Google Cloud Secret Manager
- **Automated Polling**: Check XML file every 5 minutes for new orders

### Product Coverage
- **SKU Management**: Support for 5 key ORA products
  - ORA Clarity Complete Mouthwash (17612)
  - ORA Clarity Rinse Refill (17914)  
  - ORA Essential Kit (17904)
  - ORA Travel Pack (17975)
  - ORA Premium Bundle (18675)

## ⚙️ Technical Requirements

### Backend Architecture
- **Language**: Python 3.11 (existing codebase)
- **Framework**: Minimal approach (static + JSON polling preferred for cost/time)
- **Data Storage**: JSON files for dashboard data (no database required initially)
- **API Design**: Simple REST endpoints if manual triggers needed

### Integration Points
- **Existing Scripts**: 
  - weekly_reporter.py - Weekly inventory reports
  - daily_shipment_processor.py - Daily shipment processing
  - shipstation_order_uploader.py - Order upload automation (requires XML file access)
  - shipstation_reporter.py - Shipment reports
  - main_order_import_daily_reporter.py - Daily import summaries
- **External File Access**:
  - Google Drive API integration for retrieving X-Cart XML order files
  - File parsing capabilities for XML order data processing
  - **Automated XML Monitoring**: Continuous polling service to check XML file every 5 minutes
  - **Order Detection Logic**: Compare file contents to detect new orders since last check

### Development Environment
- **Development Mode**: Continue supporting DEV_MODE bypass system
- **Sample Data**: Use existing fixtures in src/test_data/dev_fixtures/
- **Offline Testing**: Maintain ability to run without external API dependencies

## 🔧 Non-Functional Requirements

### Performance
- **Response Time**: Dashboard loads within 3 seconds
- **Update Frequency**: Data refresh every 15-30 seconds
- **Concurrent Users**: Support 5-10 simultaneous users maximum
- **Availability**: 99% uptime during business hours
- **XML Polling Frequency**: Check for new orders every 5 minutes (300 seconds)
- **Order Processing**: New orders detected and processed within 5-10 minutes

### Security
- **Authentication**: Basic access control (if publicly accessible)
- **API Keys**: Secure handling via existing Secret Manager integration
- **Data Privacy**: No sensitive data exposure in browser/logs

### Scalability
- **Growth**: Handle 50-100 orders per day initially
- **Products**: Support up to 20 SKUs without major changes
- **Reports**: Generate and display reports for up to 1 year of data

## 🚀 Implementation Preferences

### Recommended Approach (Based on Cost/Time Constraints)
1. **Static Dashboard**: Enhance existing index.html with dynamic data loading
2. **JSON Snapshots**: Modify automation scripts to output dashboard data files
3. **JavaScript Polling**: Update dashboard every 15 seconds via fetch()
4. **Minimal Backend**: Add simple endpoints only if manual triggers required

### Technology Stack
- **Frontend**: HTML/CSS/JavaScript (existing dashboard.html approach)
- **Backend**: Python HTTP server (existing approach) + optional Flask for triggers
- **Data Format**: JSON files served statically
- **Deployment**: Replit environment (port 5000)

## 📈 Success Criteria

### Minimum Viable Product (MVP)
- [ ] Dashboard displays real business data from automation scripts
- [ ] Inventory alerts show current stock levels and warnings
- [ ] Automation status reflects actual workflow execution
- [ ] Updates occur automatically without manual refresh
- [ ] XML file polling service checks for new orders every 5 minutes
- [ ] New orders automatically trigger processing workflow
- [ ] Total implementation time under 10 hours (updated for polling service)
- [ ] Zero additional hosting costs

### Nice-to-Have Features
- [ ] Manual trigger buttons for automation workflows
- [ ] Historical data visualization (charts/graphs)
- [ ] Export functionality for reports
- [ ] Email/SMS notifications for critical alerts
- [ ] Advanced filtering and search capabilities

## 🎯 Business Value

### Primary Benefits
- **Operational Efficiency**: Real-time visibility into business operations
- **Inventory Management**: Prevent stockouts and optimize ordering
- **Automation Monitoring**: Ensure critical workflows are functioning
- **Cost Reduction**: Minimize manual monitoring and intervention

### Key Metrics
- **Time Savings**: Reduce manual reporting by 80%
- **Error Reduction**: Automated alerts prevent inventory issues
- **Visibility**: 100% transparency into automation workflow status
- **Accessibility**: Business team can access data without technical skills

## 🔄 Development Phases

### Phase 1: Core Dashboard (2-4 hours)
- Enhance existing HTML dashboard with dynamic data
- Add JSON output to weekly_reporter.py and other scripts
- Implement JavaScript polling for data updates
- Test with development bypass system

### Phase 2: Real Data Integration (2-3 hours)
- Connect dashboard to actual automation script outputs
- Implement proper error handling and loading states
- Add inventory alert thresholds and status indicators
- Validate with sample business scenarios

### Phase 3: Manual Controls (1-2 hours, optional)
- Add simple API endpoints for workflow triggers
- Implement "Run Now" buttons in dashboard
- Add basic authentication if publicly accessible
- Test manual workflow execution

### Phase 4: XML Polling Service (2-3 hours)
- Implement 5-minute XML file polling mechanism
- Add order detection and change tracking logic
- Integrate with existing shipstation_order_uploader.py workflow
- Add polling status monitoring to dashboard

## 📋 Acceptance Criteria

### Dashboard Functionality
- **Data Accuracy**: Dashboard shows actual data from automation scripts
- **Update Frequency**: New data appears within 30 seconds of generation
- **Error Handling**: Graceful degradation when data unavailable
- **User Experience**: Intuitive navigation and clear visual indicators

### Integration Quality
- **Automation Scripts**: Continue functioning without modification
- **Development Mode**: DEV_MODE bypass system remains operational (including XML file mock data)
- **Performance**: No impact on existing automation workflow execution
- **Reliability**: Dashboard available 99% of time during business hours
- **File Access**: Reliable connection to Google Drive for XML file retrieval

### Cost/Time Targets
- **Development Time**: Complete implementation in under 10 hours (includes XML polling service)
- **Operational Cost**: Zero additional monthly hosting fees
- **Maintenance**: Less than 1 hour per month ongoing support
- **Learning Curve**: Business users productive within 15 minutes
- **Polling Reliability**: 99%+ successful XML file checks during business hours

## 🔧 Technical Constraints

### Must Preserve
- All existing automation script functionality
- Development bypass system for offline testing
- Google Cloud integrations (Sheets, Drive, Secret Manager)
- XML file processing capabilities for order data
- Python-based architecture and dependencies

### Must Avoid
- Major refactoring of existing business logic
- New cloud services with monthly costs
- Complex authentication/user management systems
- Technologies requiring steep learning curves

### Must Deliver
- Professional appearance suitable for business use
- Real-time data visibility for operations team
- Manual control capabilities for ad-hoc workflow execution
- Robust error handling and system status monitoring

## 🔄 ShipStation Integration Requirements

### Bidirectional Sync (CRITICAL)
- **Required**: Sync manual ShipStation orders back to local system
- **Rationale**: Manual orders created in ShipStation impact inventory tracking
- **Requirement**: Maintain continuity between both systems for accurate inventory counts
- **Implementation**: Periodic sync of ShipStation orders to local database to capture manual entries

### Duplicate Prevention (CRITICAL)
- **Required**: Robust duplicate detection to prevent re-uploading orders to ShipStation
- **Implementation Components**:
  1. Query ShipStation by exact order numbers (not date ranges) to eliminate blind spots
  2. Transaction-safe shipped_orders re-check before upload to prevent race conditions
  3. Unique database constraint on shipstation_order_line_items(order_inbox_id, sku)
- **Grade Target**: B or higher from architect review
- **Validation**: All uploaded orders must have verified ShipStation IDs

### Rate Limiting (CRITICAL)
- **Required**: Respect ShipStation API rate limits (40 requests/minute for V1 API)
- **Implementation**:
  1. Detect HTTP 429 (Too Many Requests) responses
  2. Honor Retry-After header from ShipStation
  3. Implement exponential backoff retry strategy (4-10 seconds)
  4. Maximum 5 retry attempts before failure
- **Efficiency**: Use bulk date-range queries with local filtering instead of per-order queries
- **Performance**: Optimize to minimize API calls (e.g., 93 orders should be 1-3 API calls, not 93)

### Data Integrity (CRITICAL)
- **Required**: Orders marked as "uploaded" MUST have verified ShipStation IDs
- **Validation**: shipstation_order_line_items table must contain tracking records for all uploaded orders
- **Enforcement**: Database constraint ensures (order_inbox_id, sku) uniqueness
- **Backfill**: Historical orders without tracking must be validated against ShipStation
- **Status Transitions**: 
  - pending → uploaded (only with ShipStation ID verification)
  - failed → uploaded (only if already shipped and has ShipStation ID)
  - uploaded (requires tracking record in shipstation_order_line_items table)

### Order Status Management
- **Required**: Clear status lifecycle for orders in orders_inbox
- **States**:
  - `pending`: New orders awaiting upload
  - `uploaded`: Successfully uploaded with verified ShipStation ID
  - `failed`: Upload attempted but failed (with failure_reason)
- **Failed Order Handling**:
  - Investigate failure reasons before retry
  - Auto-fix orders that are already shipped but marked as failed
  - Verify against shipped_orders table before reprocessing
- **Tracking Requirements**:
  - All uploaded orders must have entries in shipstation_order_line_items
  - ShipStation ID must be populated (orderId or orderKey)
  - SKU must be tracked for multi-SKU order support

## 📦 Orders Inbox Page - Functional Requirements

### XML Order Import & ShipStation Sync Workflow
All orders imported from XML files must follow this complete sync workflow:

#### 1. ShipStation Existence Check (REQUIRED)
- **Required**: Check if each imported order exists in ShipStation
- **Implementation**: Query ShipStation API by order number to verify existence
- **Purpose**: Prevent duplicate uploads and sync existing orders

#### 2. Existing Order Sync (REQUIRED)
- **Required**: If order exists in ShipStation, sync the unique order ID to app database
- **Unique ID Definition**: Each order+SKU combination has a distinct identifier
  - Example: Order #123 with SKU 17612 has different ID than Order #123 with SKU 17914
- **Database Field**: Store unique ID in `shipstation_order_id` field
- **Status Sync**: Record current ShipStation status in app's `status` field
- **Supported Statuses**:
  - `awaiting_shipment`: Order created and awaiting shipment
  - `cancelled`: Order cancelled in ShipStation
  - `on_hold`: Order placed on hold
  - `shipped`: Order has been shipped

#### 3. Manual Order Sync (REQUIRED)
- **Required**: Sync manually-created ShipStation orders back to app database
- **Detection**: Identify orders created directly in ShipStation (not uploaded from XML)
- **Data Capture**: Import all available fields including:
  - Company name
  - Location/address details
  - Items ordered (SKU, quantity)
  - Order dates and status
- **Purpose**: Maintain data integrity and inventory accuracy for all orders

#### 4. New Order Upload (REQUIRED)
- **Required**: If order doesn't exist in ShipStation, upload it
- **Upload Process**:
  1. Create order in ShipStation via API
  2. Receive unique order ID from ShipStation response
  3. Sync unique ID back to app database `shipstation_order_id` field
  4. Set status to `awaiting_shipment` in app database
- **Validation**: Verify successful upload before marking as complete

### Data Integrity Requirements
- **Bidirectional Sync**: All orders must be synchronized between app database and ShipStation
- **ID Tracking**: Every order in app database with ShipStation interaction must have valid `shipstation_order_id`
- **Status Accuracy**: Order status in app database must reflect current ShipStation status
- **Complete Data**: Manual orders must capture all available ShipStation fields

## 🚨 Shipping Validation Rules (CRITICAL)

### Order-Specific Shipping Requirements
The system MUST validate and enforce shipping requirements based on order characteristics. Violations must trigger prominent alerts visible on ALL pages.

#### 1. Hawaiian Orders (CRITICAL)
- **Requirement**: Orders shipping to Hawaii (state = 'HI') MUST use **FedEx 2Day** shipping service
- **Validation**: Check ship_state = 'HI' against shipping_service field
- **Alert Trigger**: If Hawaiian order detected without FedEx 2Day service
- **Severity**: HIGH - Incorrect shipping to Hawaii may result in delivery failures or excessive costs
- **Service Code**: "fedex_2day" or equivalent ShipStation service identifier

#### 2. Benco Orders (CRITICAL)
- **Requirement**: Orders identified as Benco (ship_company contains "BENCO" or "Benco") MUST use the **Benco FedEx Carrier Account**
- **Context**: **Single ShipStation account** with TWO FedEx carrier account integrations:
  - **Benco FedEx Carrier Account**: For Benco orders only (separate FedEx billing account)
  - **Oracare FedEx Carrier Account**: For all other orders (default, separate FedEx billing account)
- **Validation**: Verify Benco orders use Benco FedEx carrier via ShipStation carrierCode/carrierId field
- **Alert Trigger**: If Benco order detected using Oracare FedEx carrier (or vice versa)
- **Severity**: HIGH - Using wrong carrier causes billing to wrong FedEx account, reconciliation problems, and customer confusion
- **Implementation**: System must capture and store ShipStation carrier identifier (carrierId or carrierCode) for each order to track which FedEx account was used

#### 3. Canadian Orders (CRITICAL)
- **Requirement**: Orders shipping to Canada (ship_country = 'CA' or 'Canada') MUST use **International Ground** shipping service
- **Validation**: Check ship_country in ('CA', 'Canada') against shipping_service field
- **Alert Trigger**: If Canadian order detected with non-International Ground service
- **Severity**: HIGH - Incorrect shipping service may cause customs issues or delivery delays
- **Service Code**: "fedex_international_ground" or equivalent ShipStation service identifier

### Alert System Requirements (CRITICAL)
- **Visibility**: Alerts MUST be prominently displayed via **sticky bar at the very top** of EVERY page
- **Persistence**: Alerts remain visible until violations are resolved
- **Priority**: Shipping validation alerts take precedence over other notifications
- **Design Requirements**:
  - **Sticky positioning**: Fixed bar at absolute top of viewport (above all navigation)
  - High contrast colors (red/orange background for critical violations)
  - Clear, actionable messaging with order numbers and violation details
  - Direct link/button to view problematic orders
  - Count of total violations displayed prominently
  - Dismissible only after resolution (not manually dismissible)
- **Real-time Updates**: Alert system checks for violations on every page load and auto-refresh
- **Multi-page Support**: Shared sticky bar component included in ALL HTML pages (index.html, xml_import.html, bundle_skus.html, sku_lot.html, etc.)
- **User Experience**: Clicking alert bar navigates to Orders Inbox filtered to show only violating orders

### Validation Timing
- **Pre-Upload Validation**: Check shipping rules BEFORE uploading to ShipStation
- **Post-Upload Monitoring**: Continuously monitor uploaded orders for rule compliance
- **Manual Order Sync**: Validate manually-created ShipStation orders against rules
- **Batch Validation**: Provide admin tool to scan all awaiting_shipment orders for violations

### Error Handling
- **Non-Blocking**: Violations **DO NOT** block ShipStation uploads - orders are uploaded even with violations
- **Alert-Based Approach**: System displays prominent sticky alerts for violations but allows operations to proceed
- **Purpose**: Provide visibility and warnings while allowing business operations to continue
- **Audit Trail**: Log all validation checks, violations detected, and when violations are resolved
- **Resolution Tracking**: System automatically clears alerts when violations are fixed in ShipStation