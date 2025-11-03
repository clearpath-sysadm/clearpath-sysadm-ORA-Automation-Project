# Functional Requirements Document (FRD)
## Oracare Fulfillment System

**Document Version:** 1.0.0  
**Last Updated:** November 3, 2025  
**Status:** Production Active  
**Project Phase:** Post-Launch Operations & Enhancement

---

## 1. Introduction

### 1.1 Document Purpose

This Functional Requirements Document (FRD) defines the complete set of functional capabilities of the Oracare Fulfillment System. It serves as the authoritative source for what the system does, how it behaves, and the business rules it enforces.

**Target Audience:**
- Business Analysts
- Product Managers
- Developers
- QA Engineers
- System Administrators
- Business Stakeholders

### 1.2 Project Overview

**System Name:** Oracare Fulfillment System  
**Project Goal:** Replace legacy Google Sheets infrastructure with a production-ready PostgreSQL database system for managing inventory, orders, and fulfillment automation  
**Business Objective:** Zero data loss, real-time visibility, automated workflows with manual oversight

### 1.3 Project Scope

**In Scope:**
- Order management and tracking
- Inventory management with lot-level tracking
- ShipStation integration (bidirectional sync)
- Google Drive XML order import
- Automated fulfillment workflows
- Real-time dashboard and reporting
- Physical inventory controls (EOD/EOW/EOM)
- Duplicate order detection and resolution
- Bundle SKU expansion
- Role-based access control

**Out of Scope:**
- Customer-facing order portal
- Integration with accounting systems
- Supplier management
- Return merchandise authorization (RMA)
- International shipping compliance

### 1.4 Definitions & Glossary

| Term | Definition |
|------|------------|
| **EOD** | End of Day - Daily inventory synchronization process |
| **EOW** | End of Week - Weekly report generation with 52-week averages |
| **EOM** | End of Month - Monthly charge report generation |
| **SKU** | Stock Keeping Unit - Unique product identifier |
| **Lot** | Production batch identifier for inventory tracking |
| **Bundle SKU** | Composite product containing multiple individual SKUs |
| **Manual Order** | Order with number 100000-109999, created directly in ShipStation |
| **Ghost Order** | Order in ShipStation missing item details due to sync timing |
| **ShipStation** | Third-party shipping management platform |
| **FIFO** | First In, First Out - Inventory consumption method |

---

## 2. System Overview

### 2.1 System Context

The Oracare Fulfillment System operates as a centralized hub connecting:
- **Google Drive** (XML order files) → System imports orders
- **System** → **ShipStation** (order upload, status sync)
- **PostgreSQL Database** → Central data store
- **Web Dashboard** → User interface for monitoring and control

### 2.2 User Roles

| Role | Description | Access Level |
|------|-------------|--------------|
| **Admin** | Full system access, can modify data, delete orders, adjust inventory | Full CRUD operations |
| **Viewer** | Read-only access to dashboard and reports | View-only, no modifications |

---

## 3. Functional Requirements

### 3.1 Authentication & Authorization

#### FR-AUTH-001: User Login
**Priority:** High  
**Description:** The system shall authenticate users via Replit OAuth supporting multiple login methods (Google, GitHub, email).

**Acceptance Criteria:**
- User can log in using any supported OAuth provider
- Session persists for 7 days unless explicitly logged out
- Failed login attempts are logged
- Redirect to originally requested page after successful login

**Dependencies:** Replit Auth integration, Flask-Dance library

---

#### FR-AUTH-002: Role-Based Access Control
**Priority:** High  
**Description:** The system shall enforce role-based permissions on all endpoints.

**Acceptance Criteria:**
- Admin users can access all features and modify data
- Viewer users have read-only access
- API returns 403 Forbidden for unauthorized actions
- Role is determined from `user_roles` table in database

**Dependencies:** FR-AUTH-001

---

### 3.2 Order Management

#### FR-ORD-001: XML Order Import
**Priority:** High  
**Description:** The system shall automatically poll Google Drive every 5 minutes for new XML order files and import them into `orders_inbox`.

**Acceptance Criteria:**
- Scan Google Drive folder for `.xml` files
- Parse order details: order number, customer info, line items
- Expand bundle SKUs into component items
- Insert orders into `orders_inbox` with status "pending"
- Move processed XML files to archive folder
- Log import results (success/failure counts)

**Business Rules:**
- BR-ORD-001: Orders already in `orders_inbox` shall not be re-imported
- BR-ORD-002: Invalid XML files shall be logged and skipped, not moved to archive

**Dependencies:** Google Drive integration, Bundle SKU expansion (FR-SKU-004)

---

#### FR-ORD-002: ShipStation Order Upload
**Priority:** High  
**Description:** The system shall upload pending orders from `orders_inbox` to ShipStation every 5 minutes.

**Acceptance Criteria:**
- Select orders with status "pending"
- Map SKU-Lot to ShipStation SKU format
- Create order in ShipStation via API
- Update `orders_inbox.shipstation_order_id` on success
- Mark order status as "uploaded"
- Handle API errors gracefully with retry logic

**Business Rules:**
- BR-ORD-003: Manual orders (100000-109999) shall NEVER be uploaded to ShipStation
- BR-ORD-004: Orders missing required fields shall remain "pending" with error logged
- BR-ORD-005: Duplicate order numbers already in ShipStation shall be flagged, not re-uploaded

**Dependencies:** ShipStation API integration, SKU-Lot mapping (FR-SKU-003)

---

#### FR-ORD-003: Manual Order Sync
**Priority:** High  
**Description:** The system shall sync manual orders (100000-109999) from ShipStation to local database for inventory tracking only.

**Acceptance Criteria:**
- Poll ShipStation every 5 minutes for orders in range 100000-109999
- Insert/update `orders_inbox` with order details
- Do NOT populate `shipstation_order_id` (remains NULL for manual orders)
- Sync to `shipped_orders` and `shipped_items` when status is "shipped"
- Detect conflicts when same order number has different ShipStation IDs

**Business Rules:**
- BR-ORD-006: Manual orders are created in ShipStation by operators, not by automation
- BR-ORD-007: System never uploads manual orders, only imports them for tracking

**Dependencies:** ShipStation API integration

---

#### FR-ORD-004: Order Status Sync
**Priority:** High  
**Description:** The system shall sync order status updates from ShipStation every 5 minutes.

**Acceptance Criteria:**
- Query ShipStation for orders modified since last watermark
- Update `orders_inbox` status (pending → shipped/cancelled/on_hold)
- Update tracking numbers and carrier information
- Record ship_date when order ships
- Sync shipped items to `shipped_items` table

**Business Rules:**
- BR-ORD-008: Order updates require `shipstation_order_id` to be populated
- BR-ORD-009: Status changes are logged with timestamp

**Dependencies:** FR-ORD-002

---

#### FR-ORD-005: Order Lookup & Search
**Priority:** Medium  
**Description:** The system shall allow users to search for orders by order number and view complete details.

**Acceptance Criteria:**
- Search input accepts order numbers
- Display order details: customer, company, items, status, dates
- Show both ShipStation and local database records if available
- Highlight discrepancies between sources
- Provide "Sync from ShipStation" action to refresh data

**Dependencies:** FR-ORD-004

---

#### FR-ORD-006: Order Deletion (Admin Only)
**Priority:** Medium  
**Description:** Admins shall be able to delete duplicate or problematic orders from ShipStation.

**Acceptance Criteria:**
- Delete button available only for Admin role
- Confirmation dialog with order details
- Delete order from ShipStation via API
- Mark local record as deleted (soft delete)
- Log deletion action with user ID and timestamp

**Business Rules:**
- BR-ORD-010: Deletion is permanent and irreversible in ShipStation
- BR-ORD-011: Deleted orders remain in local database with status "deleted"

**Dependencies:** FR-AUTH-002, ShipStation API

---

### 3.3 Inventory Management

#### FR-INV-001: Current Inventory Calculation
**Priority:** High  
**Description:** The system shall calculate current inventory levels using FIFO method based on initial inventory, adjustments, and shipped quantities.

**Acceptance Criteria:**
- Load initial inventory from `configuration_params` (InitialInventory category)
- Apply manual adjustments from `inventory_transactions`
- Subtract shipped quantities from `shipped_items`
- Store results in `inventory_current` table
- Update calculations during EOD/EOW processes

**Business Rules:**
- BR-INV-001: Initial inventory baseline date is September 19, 2025 (protected from modification)
- BR-INV-002: Negative inventory triggers alert but does not block operations

**Dependencies:** FR-PHY-001 (EOD process)

---

#### FR-INV-002: Inventory Adjustments
**Priority:** Medium  
**Description:** Admins shall be able to manually adjust inventory quantities with reason documentation.

**Acceptance Criteria:**
- Adjustment form with SKU, quantity (±), reason, date
- Insert record into `inventory_transactions`
- Recalculate `inventory_current` after adjustment
- Display adjustment history with timestamps and user

**Business Rules:**
- BR-INV-003: All adjustments require written reason (minimum 10 characters)
- BR-INV-004: Adjustments are audit-logged and cannot be deleted

**Dependencies:** FR-AUTH-002 (Admin role)

---

#### FR-INV-003: Low Stock Alerts
**Priority:** Medium  
**Description:** The system shall display alerts when inventory falls below reorder point.

**Acceptance Criteria:**
- Compare `current_quantity` to `reorder_point` for each SKU
- Display yellow warning on dashboard for low stock items
- Show estimated days left based on 52-week rolling average
- Provide "Adjust Inventory" quick action

**Business Rules:**
- BR-INV-005: Reorder point is configurable per SKU in `inventory_current` table
- BR-INV-006: Alert level: Yellow (below reorder point), Red (out of stock)

**Dependencies:** FR-INV-001, FR-REP-002 (52-week average)

---

#### FR-INV-004: Lot-Level Inventory Tracking
**Priority:** High  
**Description:** The system shall track inventory at lot level, auto-calculating quantities per lot using FIFO.

**Acceptance Criteria:**
- Load lot initial quantities from `lot_inventory_current`
- Track shipped quantities per lot from `shipped_items.sku_lot`
- Calculate remaining quantity per lot
- Display lot-level breakdown in Inventory Lot Management page

**Business Rules:**
- BR-INV-007: Lots are consumed in FIFO order (oldest first)
- BR-INV-008: Lot numbers follow format: SKU - LOT (e.g., "17612 - 250300")

**Dependencies:** FR-SKU-003 (SKU-Lot mapping)

---

### 3.4 SKU & Bundle Management

#### FR-SKU-001: SKU Master Data
**Priority:** High  
**Description:** The system shall maintain master data for key SKUs including product names and pallet configurations.

**Acceptance Criteria:**
- Store SKU, product name in `configuration_params` (category: Key Products)
- Store pallet count in `configuration_params` (category: PalletConfig)
- Display product names in all reports and tables
- Provide CRUD interface for SKU master data (Admin only)

**Dependencies:** None

---

#### FR-SKU-002: Bundle SKU Definition
**Priority:** High  
**Description:** Admins shall be able to define bundle SKUs composed of multiple component SKUs.

**Acceptance Criteria:**
- Create bundle with unique SKU identifier
- Add component SKUs with quantities
- Store in `bundle_skus` and `bundle_components` tables
- Display bundle definition in Bundle SKU Management page

**Example:**
- Bundle SKU: STARTER_KIT
- Components: 17612 (qty 2), 17904 (qty 1), 18675 (qty 1)

**Dependencies:** FR-SKU-001

---

#### FR-SKU-003: SKU-Lot Mapping
**Priority:** High  
**Description:** The system shall maintain mappings between SKUs and lot numbers for order fulfillment.

**Acceptance Criteria:**
- Store mappings in `sku_lot` table
- CRUD interface for adding/editing mappings
- Display current lot assignments in SKU Lot Management page
- Use mappings during ShipStation order upload

**Business Rules:**
- BR-SKU-001: Each SKU can have multiple lot mappings
- BR-SKU-002: Lot mappings must be unique per SKU

**Dependencies:** FR-SKU-001

---

#### FR-SKU-004: Bundle Expansion
**Priority:** High  
**Description:** The system shall automatically expand bundle SKUs into component items during XML import.

**Acceptance Criteria:**
- Detect bundle SKU in order line item
- Look up bundle definition in `bundle_components`
- Replace bundle with component SKUs × quantities
- Log expansion action

**Example:**
- Order contains: STARTER_KIT (qty 1)
- Expands to: 17612 (qty 2), 17904 (qty 1), 18675 (qty 1)

**Business Rules:**
- BR-SKU-003: If bundle definition not found, order import fails with error

**Dependencies:** FR-SKU-002, FR-ORD-001

---

### 3.5 Physical Inventory Operations

#### FR-PHY-001: End of Day (EOD)
**Priority:** High  
**Description:** The system shall provide a user-triggered EOD process to sync shipped items and update inventory.

**Acceptance Criteria:**
- User clicks "EOD" button on dashboard
- System fetches all shipped orders from ShipStation since last EOD
- Upsert records to `shipped_orders` and `shipped_items` tables
- Recalculate `inventory_current`
- Display success message with item count

**Business Rules:**
- BR-PHY-001: EOD can be run multiple times per day (idempotent)
- BR-PHY-002: EOD is prerequisite for EOW

**Dependencies:** ShipStation API, FR-INV-001

---

#### FR-PHY-002: End of Week (EOW)
**Priority:** High  
**Description:** The system shall generate weekly inventory report with 52-week rolling averages.

**Acceptance Criteria:**
- User clicks "EOW" button on dashboard
- System runs EOD if not already done today
- Calculate 52-week rolling average per SKU
- Generate weekly report with current qty, avg, days left
- Store results in `inventory_current`
- Display report on dashboard

**Business Rules:**
- BR-PHY-003: EOW calculates weekly averages from `weekly_shipped_history`
- BR-PHY-004: "Days left" = current_qty ÷ (weekly_avg ÷ 7)

**Dependencies:** FR-PHY-001, FR-REP-002

---

#### FR-PHY-003: End of Month (EOM)
**Priority:** Medium  
**Description:** The system shall generate monthly charge report for billing purposes.

**Acceptance Criteria:**
- User clicks "EOM" button on dashboard
- System calculates shipped quantities per SKU for the month
- Apply rates from `configuration_params` (category: Rates)
- Generate charge report with SKU, qty, rate, total
- Display report summary

**Business Rules:**
- BR-PHY-005: EOM runs for previous month only
- BR-PHY-006: Rates are configurable per SKU

**Dependencies:** FR-PHY-001

---

### 3.6 Duplicate Detection & Resolution

#### FR-DUP-001: Duplicate Order Scanning
**Priority:** High  
**Description:** The system shall scan ShipStation every 15 minutes for duplicate order numbers.

**Acceptance Criteria:**
- Query ShipStation for all active orders
- Group by order number, identify duplicates (count > 1)
- Store duplicate sets in `duplicate_order_alerts` table
- Display alert count on dashboard

**Business Rules:**
- BR-DUP-001: Duplicates are order numbers appearing multiple times with different ShipStation IDs

**Dependencies:** ShipStation API

---

#### FR-DUP-002: Manual Duplicate Resolution
**Priority:** High  
**Description:** Users shall be able to view duplicate alerts and delete incorrect orders.

**Acceptance Criteria:**
- Dashboard displays "Duplicate Alerts" badge with count
- Click to open modal showing duplicate order groups
- Display all orders with same order number side-by-side
- Provide "Delete" button for each order (Admin only)
- Real-time UI update when order deleted

**Dependencies:** FR-DUP-001, FR-ORD-006

---

#### FR-DUP-003: Intelligent Auto-Resolution
**Priority:** High  
**Description:** The system shall automatically resolve duplicate alerts when conditions are met.

**Acceptance Criteria:**
- After each scan, evaluate remaining non-deleted records
- Auto-resolve alert if:
  - Duplicates no longer appear in scan, OR
  - All duplicate records are deleted, OR
  - Remaining records no longer constitute duplicates
- Remove resolved alerts from database
- Update dashboard badge count

**Business Rules:**
- BR-DUP-002: Auto-resolution runs after every duplicate scan (every 15 minutes)

**Dependencies:** FR-DUP-001

---

#### FR-DUP-004: Manual Order Conflict Detection
**Priority:** High  
**Description:** The system shall detect when the same order number has different ShipStation IDs (manual order conflicts).

**Acceptance Criteria:**
- Identify order number appearing with multiple distinct ShipStation IDs
- Display as separate alert type in dashboard
- Show all conflicting records with ShipStation IDs
- Provide resolution options

**Business Rules:**
- BR-DUP-003: Conflicts indicate data integrity issue requiring manual review

**Dependencies:** FR-DUP-001, FR-ORD-003

---

### 3.7 Reporting & Analytics

#### FR-REP-001: Real-Time KPIs
**Priority:** High  
**Description:** The dashboard shall display key performance indicators updated every 30 seconds.

**Acceptance Criteria:**
- Display cards for: Pending Orders, Shipped Today, Inventory Alerts, Workflow Status
- Auto-refresh data every 30 seconds
- Show visual indicators (icons, colors) for status
- Display trend arrows (up/down) where applicable

**Dependencies:** FR-INV-001, FR-ORD-001

---

#### FR-REP-002: 52-Week Rolling Average
**Priority:** High  
**Description:** The system shall calculate 52-week rolling average consumption per SKU.

**Acceptance Criteria:**
- Use `weekly_shipped_history` table (52 weeks of data)
- Calculate average units shipped per week per SKU
- Display in weekly inventory report
- Use for days-left calculations

**Business Rules:**
- BR-REP-001: If <52 weeks of data, use available weeks (minimum 4)

**Dependencies:** FR-PHY-002

---

#### FR-REP-003: Shipping Validation Report
**Priority:** Medium  
**Description:** The system shall display violations of expected carrier/service rules.

**Acceptance Criteria:**
- Compare actual carrier/service from ShipStation to expected rules
- Display violations in dashboard table
- Show: Order number, expected vs actual carrier/service
- Alert-only (no blocking)

**Business Rules:**
- BR-REP-002: Expected rules stored in `configuration_params`

**Dependencies:** FR-ORD-004

---

### 3.8 Workflow Controls

#### FR-WKF-001: Workflow On/Off Toggle
**Priority:** Medium  
**Description:** Admins shall be able to enable/disable automation workflows via dashboard.

**Acceptance Criteria:**
- Display workflow status (running/stopped) on dashboard
- Provide toggle switch for each workflow
- Update `workflows` table enabled status
- Workflows respect enabled flag (skip execution if disabled)

**Workflows:**
- XML Import
- ShipStation Upload
- Unified ShipStation Sync
- Duplicate Scanner
- Lot Mismatch Scanner
- Orders Cleanup

**Dependencies:** FR-AUTH-002

---

#### FR-WKF-002: Workflow Status Monitoring
**Priority:** Medium  
**Description:** The dashboard shall display status and last run time for all workflows.

**Acceptance Criteria:**
- Show workflow name, status, last run timestamp
- Color-code status: Green (running), Yellow (stopped), Red (error)
- Display error message if workflow failed

**Dependencies:** FR-WKF-001

---

### 3.9 Incident Management

#### FR-INC-001: Production Incident Logging
**Priority:** Medium  
**Description:** Users shall be able to log production incidents/bugs with severity and status tracking.

**Acceptance Criteria:**
- Incident form with: title, description, severity, status
- Severities: Critical, High, Medium, Low
- Statuses: Open, In Progress, Resolved, Closed
- Display incident list with filters
- Require resolution notes before closing

**Dependencies:** FR-AUTH-002

---

#### FR-INC-002: Incident History & Search
**Priority:** Low  
**Description:** Users shall be able to search and view incident history.

**Acceptance Criteria:**
- Search by title, description, status, severity
- Display incident details with all updates
- Show timeline of status changes

**Dependencies:** FR-INC-001

---

## 4. Non-Functional Requirements

### 4.1 Performance

- **NFR-PERF-001:** Dashboard KPIs shall load within 2 seconds
- **NFR-PERF-002:** Order search shall return results within 1 second
- **NFR-PERF-003:** System shall support up to 50 concurrent users
- **NFR-PERF-004:** Background workflows shall complete within 60 seconds

### 4.2 Security

- **NFR-SEC-001:** All API endpoints shall require authentication
- **NFR-SEC-002:** Admin actions shall require Admin role
- **NFR-SEC-003:** Passwords shall never be stored in plaintext (OAuth only)
- **NFR-SEC-004:** Database credentials shall be stored in environment secrets
- **NFR-SEC-005:** ShipStation upload shall have dual-layer environment protection

### 4.3 Reliability

- **NFR-REL-001:** System uptime shall be 99.5% excluding scheduled maintenance
- **NFR-REL-002:** Database backups shall occur daily via Replit managed backups
- **NFR-REL-003:** Failed API calls shall retry with exponential backoff (3 attempts)
- **NFR-REL-004:** Data loss tolerance: Zero

### 4.4 Scalability

- **NFR-SCAL-001:** System shall handle up to 10,000 orders per month
- **NFR-SCAL-002:** Inventory calculations shall complete for 100+ SKUs
- **NFR-SCAL-003:** Database shall support 1M+ shipped items records

### 4.5 Usability

- **NFR-USE-001:** Dashboard shall be responsive (mobile, tablet, desktop)
- **NFR-USE-002:** System shall provide visual feedback for all user actions
- **NFR-USE-003:** Error messages shall be clear and actionable
- **NFR-USE-004:** UI shall comply with WCAG 2.1 Level AA

### 4.6 Maintainability

- **NFR-MAIN-001:** Code shall follow Python PEP 8 style guide
- **NFR-MAIN-002:** Database schema changes shall use migration tools (Drizzle/Alembic)
- **NFR-MAIN-003:** All workflows shall log execution status and errors
- **NFR-MAIN-004:** Configuration parameters shall be database-driven (not hard-coded)

---

## 5. Business Rules Summary

| ID | Rule | Impact |
|----|------|--------|
| BR-ORD-001 | Orders already in orders_inbox shall not be re-imported | Prevents duplicates |
| BR-ORD-003 | Manual orders (100000-109999) never uploaded to ShipStation | Critical business rule |
| BR-ORD-008 | Order updates require shipstation_order_id | Data integrity |
| BR-INV-001 | Initial inventory baseline date is Sept 19, 2025 (protected) | Historical accuracy |
| BR-INV-007 | Lots consumed in FIFO order | Inventory method |
| BR-SKU-003 | Bundle expansion fails if definition not found | Data quality |
| BR-PHY-002 | EOD is prerequisite for EOW | Process dependency |
| BR-DUP-001 | Duplicates = same order number, different ShipStation IDs | Definition |

---

## 6. Assumptions & Constraints

### Assumptions
- ShipStation API remains stable and backward-compatible
- Google Drive integration has reliable uptime
- Users have modern browsers (Chrome, Firefox, Safari, Edge)
- Network connectivity is reliable

### Constraints
- Database: PostgreSQL (Replit managed)
- Deployment: Replit VM (always-on)
- Authentication: Replit Auth only (no custom auth)
- ShipStation rate limits: 40 requests/minute

---

## 7. Dependencies & Integrations

| System | Purpose | API/Protocol | Frequency |
|--------|---------|--------------|-----------|
| ShipStation API | Order upload, status sync | REST API | Every 5 min |
| Google Drive | XML order import | Google Drive API | Every 5 min |
| SendGrid | Email notifications (optional) | SMTP/API | As needed |
| Replit Auth | User authentication | OAuth 2.0 | Per session |

---

## 8. Acceptance Criteria

The system shall be considered complete when:
1. All High priority functional requirements are implemented and tested
2. Non-functional requirements for performance and security are validated
3. User acceptance testing (UAT) passes for all workflows
4. Documentation is complete (this FRD, UI specs, user manual)
5. Admin and Viewer roles can successfully use all authorized features
6. Zero data loss verified through end-to-end testing

---

## 9. Future Enhancements (Out of Current Scope)

- Customer-facing order tracking portal
- Barcode scanning for inventory adjustments
- Automated reorder suggestions
- Integration with QuickBooks/accounting
- Mobile app for warehouse operations
- Multi-warehouse support
- Advanced analytics dashboards

---

## 10. Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0.0 | 2025-11-03 | Initial FRD based on implemented system | System |

---

## 11. Approval Sign-Off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Business Owner | | | |
| Product Manager | | | |
| Technical Lead | | | |
| QA Lead | | | |

---

## Appendix A: Requirements Traceability Matrix

| Req ID | Feature | Priority | Status | Test Case |
|--------|---------|----------|--------|-----------|
| FR-AUTH-001 | User Login | High | Complete | TC-AUTH-001 |
| FR-AUTH-002 | RBAC | High | Complete | TC-AUTH-002 |
| FR-ORD-001 | XML Import | High | Complete | TC-ORD-001 |
| FR-ORD-002 | SS Upload | High | Complete | TC-ORD-002 |
| ... | ... | ... | ... | ... |

---

**Document Maintenance:** This FRD should be updated whenever new features are added, business rules change, or system behavior is modified. Review quarterly or after major releases.
