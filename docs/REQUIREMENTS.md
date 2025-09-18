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