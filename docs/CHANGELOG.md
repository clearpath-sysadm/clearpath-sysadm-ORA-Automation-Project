# Changelog

All notable changes to the Oracare Fulfillment System will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- **Permanent Duplicate Order Exclusion System** - Two-tier resolution system for duplicate alerts
  - "Mark Resolved" (green button): Temporarily dismisses alert without permanent exclusion
  - "Permanently Exclude" (red button): Forever excludes order+SKU from duplicate detection
  - New `excluded_duplicate_orders` database table with UNIQUE constraint on (order_number, base_sku)
  - Duplicate scanner checks exclusion table before creating alerts
  - Strong confirmation dialog warns users of irreversible permanent exclusion
  - Use case: Orders predating local database (e.g., #674715 from before Sept 19, 2025)
  - Admin-only access for both resolution and exclusion actions
  - API endpoints: PUT `/api/duplicate_alerts/{id}/resolve` and PUT `/api/duplicate_alerts/{id}/exclude`
- **Inventory Transactions Clipboard Export** - Added formatted clipboard copy functionality to Inventory Monitor
  - "📋 Copy to Clipboard" button exports filtered transactions in dual format (HTML table + plain text)
  - HTML format pastes as formatted table in email clients, Word, Google Docs
  - Plain text fallback works in Notepad, Slack, chat applications
  - Format matches weekly inventory report style for consistency
  - Copies only filtered data (by date range, SKU, or transaction type)
  - Summary includes total transaction count and "Receive" transaction count for billing reports
- **PDF Export for Charge Report** - Added jsPDF and autoTable libraries to enable PDF export functionality
  - Added CDN links for jsPDF 2.5.1 and jsPDF-autoTable 3.5.31
  - PDF export button now functional with color-coded columns (purple for quantities, green for charges)
  - Filename format: "Charge Report Oct 2025.pdf" (month abbreviation + year)

### Removed
- **"Mark Resolved" Button Removed from Duplicate Alerts** - Simplified duplicate resolution workflow
  - Removed green "Mark Resolved" button due to bug and lack of value
  - Root cause: Button only marked alert as resolved in current session; alert reappeared after scanner ran (15 min)
  - Database bug: API set `notes` field, but scanner checked `resolution_notes` field (column mismatch)
  - Rationale: If duplicates still exist in ShipStation, temporary dismissal doesn't solve the problem
  - Users must now either "Permanently Exclude" the alert OR delete the duplicate order from ShipStation
  - Removed API endpoint: `PUT /api/duplicate_alerts/{id}/resolve`
  - Removed 30-day suppression logic from duplicate scanner
  - Simplified user experience with clear action choices

### Changed
- **FRD Documentation Updated to v1.2.0** - Removed temporary resolution feature, documented permanent exclusion only
  - Removed FR-DUP-005: Temporary Duplicate Alert Resolution (deprecated feature)
  - Renumbered FR-DUP-006 → FR-DUP-005: Permanent Duplicate Alert Exclusion
  - Updated FR-DUP-002: Single "Permanently Exclude" button only
  - Updated FR-DUP-003: Auto-resolution no longer checks for manually-resolved alerts
  - Renumbered business rules BR-DUP-008 through BR-DUP-016 (was BR-DUP-012 through BR-DUP-021)
  - Simplified workflow: Delete duplicates OR permanently exclude them

### Fixed
- **CRITICAL: EOM Endpoint Fixed** - Applied same fixes as charge report to ensure consistency
  - Changed baseline from InitialInventory/EOD_Prior_Week to Inventory/EomPreviousMonth (matches charge report)
  - Added "Adjust Up" and "Adjust Down" transaction handling (was only processing Receive and Repack)
  - EOM button now calculates space rental correctly using end-of-previous-month baseline
  - Both charge report and EOM now use identical calculation logic
- **CRITICAL: 7-Pallet Charge Report Discrepancy Resolved** - Fixed major inventory calculation error
  - **Root Cause:** Sept 30 baseline stored in database did not match actual inventory
    - SKU 17612 was off by +1,167 units, other SKUs had errors ranging from -1,244 to +390 units
    - Charge report also ignored "Adjust Up" and "Adjust Down" transactions (physical count corrections)
  - **Impact:** October charge report showed incorrect inventory levels and space rental charges
    - Before fix: Discrepancy of 7-10 pallets between charge report and weekly inventory
  - **Solution:** 
    - Recalculated Sept 30 baseline by working backwards from correct Oct 31 inventory (weekly inventory as source of truth)
    - Updated `configuration_params` with correct baseline: 326, 449, 1368, 714, 7704 (was: 1493, 59, 127, 738, 7799)
    - Added "Adjust Up" and "Adjust Down" transaction handling to charge report calculation (app.py lines 933-940)
  - **Result:** Both reports now show identical Oct 31 inventory: 11,276 units = 72.28 pallets = $32.53 space rental
  - See `docs/RCA_7_Pallet_Discrepancy_Nov_3_2025.md` for complete root cause analysis
- **Charge Report Date Display Bug** - Fixed timezone issue causing dates to shift back by 1 day
  - Root cause: JavaScript `new Date(dateStr)` parsed dates as UTC, then converted to local timezone
  - Impact: October report showed Sept 30-Oct 30 instead of Oct 1-Oct 31 (dates shifted back 1 day)
  - Solution: Parse date components in local timezone to avoid UTC conversion
  - Changed `formatChargeReportDate()` in charge_report.html to split date string and construct Date object locally
- **EOM Button Error** - Fixed crash when calculating monthly charge report
  - Root cause: SQL `SUM()` returns NULL when no rows match, causing `None * float` TypeError
  - Impact: EOM button failed with "unsupported operand type(s) for +: 'NoneType' and 'float'"
  - Solution: Added NULL handling with `or 0` for SQL aggregate results in `/api/reports/eom`
  - Also fixed incorrect column references (`carrier`/`service` → `shipping_carrier_code`/`shipping_service_code`)
  - Changed EOM purpose from carrier/service breakdown to order/package/space rental calculation

### Planned
- Customer-facing order tracking portal
- Barcode scanning for inventory adjustments
- Mobile app for warehouse operations
- QuickBooks integration for accounting sync

---

## [1.4.0] - 2025-11-03

### Added
- **Order Management Sync from ShipStation:** Added "🔄 Sync from SS" feature in two locations:
  - Manual Order Conflicts modal for syncing conflicting orders
  - Order Management table Actions column for refreshing local data with ShipStation as source of truth
- Comprehensive industry-standard documentation:
  - `docs/UI_SPECIFICATIONS.md` - Complete design system, component library, and UI standards
  - `docs/FUNCTIONAL_REQUIREMENTS.md` - Full FRD with business rules and acceptance criteria
  - `docs/CHANGELOG.md` - Version history following Keep a Changelog format
- Documentation maintenance guidelines in `replit.md`

### Fixed
- **Critical Bug:** Weekly inventory report product names now display correctly
  - Root cause: Query was selecting wrong column (`value` instead of `parameter_name`)
  - Fixed in `src/weekly_reporter.py` line 54
  - Product names now properly show: "PT Kit", "Travel Kit", "PPR Kit", "Ortho Protect", "OraPro Paste Peppermint"
- **Display Bug:** Order items in Order Management table no longer show duplicate SKU numbers
  - Fixed `sku_lot` display to use lot value directly (already contains "SKU - LOT" format)
  - Changed from concatenating `sku + sku_lot` to using `sku_lot` directly
- **Database Schema:** Sync from ShipStation endpoint now correctly maps columns:
  - `orders_inbox`: Uses `shipping_carrier_code` and `shipping_service_code` (not `carrier_code`/`service_code`)
  - `shipped_orders`: Correctly populates only 3 columns (ship_date, order_number, shipstation_order_id)
  - `shipped_items`: Properly tracks individual SKUs with lot information
- **NULL Constraint Violation:** Added `ship_date` fallback to `order_date` when shipment data unavailable
  - Prevents database errors for recently shipped orders without shipment records

### Changed
- Enhanced Order Management tool with real-time sync capability from ShipStation API
- Improved transaction handling in sync operations with explicit commit/rollback
- Updated Order Management UI to show cleaner item display without SKU duplication

---

## [1.3.0] - 2025-10-31

### Added
- **Manual Order Conflicts Detection:** System now identifies when the same order number appears with different ShipStation IDs
  - Separate alert type in duplicate detection system
  - Displays all conflicting records with ShipStation IDs in modal
  - Provides sync and resolution options
- **Duplicate Order Auto-Resolution Enhancements:** Intelligent evaluation of remaining records after deletions
  - Auto-resolves when duplicates no longer appear in scans
  - Auto-resolves when all duplicate records are deleted
  - Auto-resolves when remaining records no longer constitute duplicates
- **Real-Time Modal Updates:** Dashboard modals update asynchronously without page refresh
  - Deleted orders show red "🗑️ DELETED" badges
  - Actions disabled for deleted orders
  - Smooth animations for state changes

### Changed
- Duplicate scanner now runs auto-resolution logic every 15 minutes during scan cycle
- Enhanced error handling in duplicate detection modal with automatic refresh on errors

---

## [1.2.0] - 2025-10-30

### Added
- **Order Management Admin Tool:** New comprehensive interface at `order-management.html`
  - Order lookup by order number with detailed display
  - Shows customer, company, items, status, and dates
  - Side-by-side comparison of ShipStation and local database records
  - Safe deletion with confirmation dialogs
  - Warnings for duplicate order numbers
  - Admin authentication required for all operations
  - Full operation logging
- **Order Update Safety Measures:** All order updates blocked until `shipstation_order_id` is synced
  - Prevents data integrity issues with XML-imported orders
  - Ensures orders uploaded to ShipStation before tracking updates applied

### Security
- Order deletion requires admin role verification
- All operations logged with user ID and timestamp

---

## [1.1.0] - 2025-10-25

### Added
- **Duplicate Order Detection System:** Automated monitoring for duplicate order numbers in ShipStation
  - Scans every 15 minutes for orders with same order number but different ShipStation IDs
  - Dashboard displays alert badge with duplicate count
  - Modal interface for viewing and managing duplicates
  - Manual resolution: admins can delete incorrect duplicate orders
  - Intelligent auto-resolution: alerts automatically resolve when conditions met
- **Ghost Order Backfill System:** Repairs orders missing item details due to sync timing issues
  - Automatically detects orders in ShipStation without items
  - Backfills item data from `orders_inbox` table
  - Runs during unified ShipStation sync process

### Changed
- Enhanced duplicate detection to differentiate between true duplicates and manual order conflicts
- Improved modal UI with real-time updates and smooth animations

---

## [1.0.0] - 2025-10-15

### Added
- **Core System Launch:** Production deployment of Oracare Fulfillment System replacing Google Sheets
- **PostgreSQL Database:** Complete schema with 15+ tables for orders, inventory, workflows
  - STRICT tables with proper constraints
  - Foreign keys for data integrity
  - Transaction handling with SAVEPOINT pattern
- **Replit Authentication:** Role-based access control (Admin/Viewer)
  - OAuth integration supporting Google, GitHub, email
  - Dual database architecture (psycopg2 + SQLAlchemy)
  - Centralized API authentication middleware protecting ~80 endpoints
- **Order Processing Workflows:**
  - XML import from Google Drive every 5 minutes
  - Automatic bundle SKU expansion
  - ShipStation upload service (every 5 minutes)
  - Unified ShipStation sync (status + manual orders)
  - Order cleanup service (60-day retention)
- **Inventory Management:**
  - FIFO inventory tracking at lot level
  - Real-time current inventory calculations
  - 52-week rolling average consumption
  - Low stock alerts with reorder points
  - Manual inventory adjustments with audit trail
- **Physical Inventory Controls:**
  - EOD (End of Day): Daily shipment sync
  - EOW (End of Week): Weekly report with 52-week averages
  - EOM (End of Month): Monthly charge report generation
- **Dashboard & Reporting:**
  - Real-time KPIs with 30-second auto-refresh
  - Workflow status monitoring
  - Inventory risk table with days-left calculations
  - Shipping validation alerts
  - Production incident tracker
- **Premium UI/UX:**
  - Enterprise-grade dashboard with Oracare branding
  - Responsive design (mobile/tablet/desktop)
  - Light/dark mode with navy glass sidebar
  - IBM Plex Sans + Source Serif 4 typography
  - Skeleton loaders and smooth animations
  - WCAG 2.1 Level AA accessibility compliance
- **Bundle & SKU Management:**
  - Database-driven bundle SKU definitions
  - CRUD interfaces for bundle components
  - SKU-Lot mapping for order fulfillment
  - Lot inventory auto-calculations
- **Workflow Controls:**
  - Programmatic on/off toggles for all automation
  - Real-time status display
  - Error logging and monitoring

### Security
- Dual-layer environment protection for ShipStation uploads
- API credentials in environment secrets
- Replit-managed database backups with rollback support
- Role-based endpoint protection

### Business Rules Implemented
- Manual orders (100000-109999) NEVER uploaded by system
- Initial inventory baseline (Sept 19, 2025) protected from modification
- FIFO lot consumption for inventory tracking
- Order update safety requiring shipstation_order_id sync
- Idempotent operations using UPSERT patterns

### External Integrations
- **ShipStation API:** Order upload, status sync, manual order import
- **Google Drive:** XML file polling and import
- **SendGrid:** Email notifications (optional)
- **Google Cloud Secret Manager:** Production credential management

---

## [0.9.0] - 2025-09-19 (Beta)

### Added
- Initial beta deployment with core database schema
- Basic order import from XML files
- Manual ShipStation upload workflow
- Simple inventory tracking without lot-level detail
- Prototype dashboard with basic KPIs

### Changed
- Database schema refinements based on beta testing
- ShipStation API integration improvements

### Fixed
- XML parsing errors for malformed order files
- Database connection pooling issues

---

## [0.5.0] - 2025-09-01 (Alpha)

### Added
- Proof of concept: PostgreSQL database replacing Google Sheets
- Basic authentication (email/password only)
- Minimal order management interface
- SQLite-based development environment

### Deprecated
- SQLite database (migrated to PostgreSQL in 0.9.0)

---

## Version Numbering

This project uses [Semantic Versioning](https://semver.org/):
- **MAJOR** version (1.x.x): Incompatible API/database schema changes
- **MINOR** version (x.1.x): New features, backward-compatible
- **PATCH** version (x.x.1): Bug fixes, backward-compatible

---

## Maintenance Guidelines

### When to Update This Changelog

**Always update when:**
- Adding new features or functionality
- Fixing bugs or errors
- Changing existing behavior
- Deprecating features
- Removing features
- Improving security
- Making breaking changes

**Update before:**
- Merging pull requests
- Deploying to production
- Creating release tags

### How to Write Entries

1. **Add to [Unreleased] section first**
2. **Use standard categories:**
   - `Added` for new features
   - `Changed` for changes in existing functionality
   - `Deprecated` for soon-to-be removed features
   - `Removed` for now removed features
   - `Fixed` for bug fixes
   - `Security` for vulnerability patches
3. **Write clear, user-focused descriptions:**
   - ✅ Good: "Fixed weekly inventory report product names displaying as blank"
   - ❌ Bad: "Updated query in weekly_reporter.py line 54"
4. **Link to issues/PRs when applicable**
5. **On release, rename [Unreleased] to version number + date**
6. **Create new empty [Unreleased] section**

### Format Rules

- **Date format:** YYYY-MM-DD (ISO 8601)
- **Newest entries first** (reverse chronological)
- **Bullet points** for all entries
- **Bold** for feature names or emphasis
- **Code blocks** for technical details when necessary

---

## Links

- [Project Documentation](./README.md)
- [UI Specifications](./UI_SPECIFICATIONS.md)
- [Functional Requirements](./FUNCTIONAL_REQUIREMENTS.md)
- [Database Schema](./reference/database-schema.md)
- [User Manual](./guides/user-manual.md)

---

**Maintained by:** Oracare Development Team  
**Review Frequency:** Before each release  
**Format Standard:** [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/)
