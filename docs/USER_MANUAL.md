# ORA Business Automation System - User Manual

**Version:** 1.0  
**Last Updated:** October 2025  
**System URL:** [Your Replit Deployment URL]

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Dashboard Overview](#dashboard-overview)
3. [Orders Inbox](#orders-inbox)
4. [Shipped Orders](#shipped-orders)
5. [Charge Report](#charge-report)
6. [Inventory Management](#inventory-management)
7. [Weekly Reports](#weekly-reports)
8. [Bundle SKUs](#bundle-skus)
9. [SKU-Lot Tracking](#sku-lot-tracking)
10. [Shipping Alerts](#shipping-alerts)
11. [Settings](#settings)
12. [Manual Operations](#manual-operations)
13. [Troubleshooting](#troubleshooting)
14. [FAQ](#faq)
15. [Quick Reference](#quick-reference)

---

## Getting Started

### What is the ORA Automation System?

The ORA Automation System is your complete business operations dashboard. It handles:
- Order processing from XML files
- ShipStation integration
- Inventory tracking
- Shipping management
- Weekly reporting

Everything runs automatically in the background, with this dashboard giving you real-time visibility into your operations.

### Accessing the System

1. Open your web browser (Chrome, Firefox, Safari, or Edge)
2. Navigate to your Replit deployment URL
3. The dashboard loads automatically - no login required (internal system)

### Dashboard Navigation

The left sidebar contains all main sections:

**OPERATIONS** (Main business tools):
- **Dashboard** - Overview and key metrics
- **Orders Inbox** - View and manage orders
- **Inventory Monitor** - Stock levels and alerts
- **Charge Report** - Monthly ShipStation charges

**ADMIN & DATA** (Management tools):
- **Weekly Reports** - Historical inventory reports
- **Shipped Orders** - Order history
- **Bundle SKUs** - Manage product bundles
- **SKU Lot** - Track lot numbers
- **Manual Import** - Upload XML files manually
- **Settings** - System configuration

**Mobile Users**: On phones/tablets, tap the menu icon (≡) to access navigation.

---

## Dashboard Overview

### What You'll See

The dashboard shows 6 key metrics at the top:

1. **Units to Ship** - Total units currently waiting to ship in ShipStation
2. **Pending Uploads** - Orders waiting to be uploaded to ShipStation
3. **Shipments Sent (7 days)** - Orders shipped in the last week
4. **Benco Orders** - Current Benco orders in the system
5. **Hawaiian Orders** - Current Hawaiian orders in the system
6. **System Status** - Health of automated workflows

### Understanding the Metrics

**Units to Ship:**
- Green background = Normal operations
- Shows total units across all pending shipments
- If ≥185 units: Shows "FedEx Pickup Needed" with phone number (651-846-0590)

**Pending Uploads:**
- Orders imported from XML but not yet sent to ShipStation
- Automatic uploads happen every 5 minutes
- If stuck, use "Upload Selected" button in Orders Inbox

**System Status:**
- Green checkmark = All workflows running normally
- Yellow warning = Some issues detected
- Click to see detailed workflow status

### Shipping Violations Alert

A **yellow banner** appears at the top when shipping violations are detected:

**Example:** "3 shipping violations detected - Click to review"

**What are violations?**
These are alerts (not errors) when orders don't match expected shipping rules:
- Hawaiian orders should use FedEx 2Day
- Canadian orders should use FedEx International Ground
- Benco orders should use Benco FedEx carrier account

**How to handle:**
1. Click the banner to see details
2. Review each violation
3. Fix in ShipStation if needed (system won't block shipping)
4. Click "Resolve" once addressed

**Note:** These are informational alerts. Orders still ship even with violations.

### Workflow Status Section

Shows all background automation processes:

- **XML Import Scheduler** - Checks for new orders every 5 minutes
- **ShipStation Upload** - Sends orders to ShipStation every 5 minutes
- **Status Sync** - Updates order statuses hourly
- **Manual Order Sync** - Imports manual ShipStation orders hourly
- **Orders Cleanup** - Deletes old orders daily
- **Weekly Reporter** - Generates inventory reports (manual trigger)
- **Units Refresh** - Updates ShipStation metrics

**Status Indicators:**
- ✅ Green "Running" = Working normally
- ⏸️ Yellow "Stopped" = Needs attention
- ❌ Red "Error" = Critical issue

**Action Required:** If any workflow shows "Stopped" or "Error", contact your system administrator.

### Manual Refresh

The dashboard refreshes automatically every 60 seconds. You can also:
- Click the **🔄 Manual Refresh** button to update immediately

---

## Orders Inbox

**Purpose:** View and manage all incoming orders before they ship.

### Accessing Orders Inbox

Click **Orders Inbox** in the left sidebar.

### Understanding the View

**Status Cards (Top):**
- **Pending Upload** - Orders waiting to go to ShipStation
- **Awaiting Shipment** - Orders uploaded, waiting to ship
- **Failed** - Orders with upload errors

**Filter Options:**

Use the filter button to cycle through views:
1. **Show Pending Only** - Only orders waiting to upload (blue)
2. **Show Awaiting Shipment** - Only orders uploaded to ShipStation (purple)
3. **Show All Orders** - Everything (gray)

**Desktop:** Filter buttons appear in the top right  
**Mobile:** Tap "Actions ▼" dropdown to access filters

### Order Table Columns

| Column | Description |
|--------|-------------|
| **Order #** | Customer order number |
| **Order Date** | When order was created |
| **Company Name** | Customer company |
| **SKU - Lot** | Product SKU and lot number |
| **Quantity** | Number of units |
| **Status** | Current order state |
| **Service** | Shipping service (e.g., "FedEx 2Day") |
| **Carrier Acct** | Carrier account code |
| **ShipStation ID** | ShipStation order number (after upload) |
| **Created At** | When order entered the system |

### Order Statuses

| Status | What It Means | Action Needed |
|--------|---------------|---------------|
| **pending** | Ready to upload | None (auto uploads every 5 min) |
| **uploaded** | In ShipStation, awaiting shipment | None (waiting for shipping) |
| **shipped** | Shipped and completed | None (moved to history) |
| **cancelled** | Cancelled in ShipStation | None (archived) |
| **failed** | Upload error occurred | Click "Retry Failed" |
| **on_hold** | Manually held in ShipStation | Review in ShipStation |
| **synced_manual** | Created manually in ShipStation | None (imported for tracking) |

### Actions You Can Take

**Validate Orders** (purple button):
- Checks all orders for shipping rule compliance
- Displays any violations found
- Does NOT modify or block orders

**Upload Selected** (appears when orders are selected):
1. Check boxes next to orders you want to upload
2. Click **🚀 Upload Selected**
3. Orders send to ShipStation immediately
4. Confirmation appears when complete

**Retry Failed** (appears when failed orders exist):
- Automatically retries all orders with "failed" status
- Useful after fixing configuration issues

**Manual Import** (download icon):
- Opens manual XML import page
- For emergency order uploads outside normal automation

**Sync Manual** (sync icon):
- Triggers immediate sync of manual ShipStation orders
- Normally runs hourly automatically

**Export CSV** (green button):
- Downloads all visible orders as spreadsheet
- Useful for reporting or analysis

### Searching Orders

Use the search box to find orders by:
- Order number
- Company name
- SKU number

**Example:** Type "BENCO" to find all Benco orders

### Common Tasks

**Task: Check if orders are uploading**
1. Go to Orders Inbox
2. Click "Show Pending Only" filter
3. If orders remain pending for >10 minutes, check workflow status on Dashboard

**Task: Upload orders immediately**
1. Select orders using checkboxes
2. Click "🚀 Upload Selected"
3. Wait for confirmation message

**Task: Review shipping violations**
1. Click yellow alert banner on Dashboard
2. Review list of violations
3. Fix in ShipStation if needed
4. Mark as "Resolved"

---

## Shipped Orders

**Purpose:** View historical shipped orders and track fulfillment history.

### Accessing Shipped Orders

Click **Shipped Orders** in the left sidebar (under ADMIN & DATA).

### What You'll See

A complete history of all orders that have been shipped to customers.

**Order Table Columns:**

| Column | Description |
|--------|-------------|
| **Order #** | Customer order number |
| **Ship Date** | When order was shipped |
| **Email** | Customer email address |
| **Company** | Customer company name |
| **SKU** | Product identifier |
| **Quantity** | Number of units shipped |
| **Carrier** | Shipping carrier (e.g., FedEx) |
| **Service** | Shipping service level |
| **Tracking** | Shipment tracking number |
| **ShipStation ID** | ShipStation order reference |

### Searching Orders

Use the search box to find orders by:
- Order number
- Email address
- Ship date (YYYY-MM-DD format)

**Example:** Type "2024-10" to find all October 2024 shipments

### Common Uses

**Task: Verify an order was shipped**
1. Go to Shipped Orders
2. Search by order number or customer email
3. Check ship date and tracking number

**Task: Review monthly shipments**
1. Search by month (e.g., "2024-10")
2. Review order list
3. Total units are calculated automatically

**Task: Find tracking number**
1. Search by order number or customer name
2. Locate the order in the table
3. Copy tracking number from Tracking column

**Note:** Orders appear in Shipped Orders only after they have shipped in ShipStation and the hourly sync has run.

---

## Charge Report

**Purpose:** Review monthly ShipStation shipping charges and costs.

### Accessing Charge Report

Click **Charge Report** in the left sidebar (under OPERATIONS).

### What You'll See

Monthly summary of ShipStation shipping charges.

**Report Sections:**

1. **Monthly Totals**
   - Total shipments for the month
   - Total charges billed by ShipStation
   - Average cost per shipment

2. **Carrier Breakdown**
   - Charges by carrier (FedEx, USPS, etc.)
   - Service level costs
   - Percentage of total

3. **Daily Activity**
   - Shipments per day
   - Daily charge totals
   - Trend analysis

### How to Use

**Task: Review current month charges**
1. Go to Charge Report
2. View monthly total at the top
3. Review carrier breakdown for details

**Task: Compare carrier costs**
1. Scroll to Carrier Breakdown section
2. Compare costs between FedEx, USPS, etc.
3. Identify most cost-effective carriers

**Task: Track daily shipping activity**
1. Scroll to Daily Activity section
2. Review shipments by date
3. Identify peak shipping days

**Note:** Charge data comes directly from ShipStation API and updates daily.

---

## Inventory Management

**Purpose:** Monitor stock levels and track inventory movements.

### Accessing Inventory

Click **Inventory Monitor** in the left sidebar.

### Current Inventory View

Shows real-time stock levels for all products:

| Column | Description |
|--------|-------------|
| **SKU** | Product identifier |
| **Product Name** | Full product description |
| **Current Stock** | Units available now |
| **Low Stock Alert** | Reorder threshold |
| **Status** | Stock health indicator |

**Status Indicators:**
- 🟢 **Healthy** - Stock above low threshold
- 🟡 **Low Stock** - Below reorder point
- 🔴 **Out of Stock** - Zero units available

### Inventory Alerts

The Dashboard shows inventory alerts when:
- Any SKU drops below its low stock threshold
- Critical products are out of stock

**Alert Example:** "Low stock alert: 17612 (2,450 units remaining)"

### Inventory Transactions

Click **Inventory Transactions** in sidebar to see movement history:

**Transaction Types:**
- **shipped** - Units sent to customers (reduces stock)
- **received** - Units received from supplier (increases stock)
- **adjustment** - Manual inventory corrections

**Adding Transactions:**

1. Click **Record Transaction** button
2. Fill in the form:
   - **SKU:** Select product
   - **Transaction Type:** shipped/received/adjustment
   - **Quantity:** Number of units
   - **Date:** Transaction date
   - **Notes:** Optional description
3. Click **Submit**

**When to add transactions:**
- Recording shipments not in ShipStation
- Logging product receipts from suppliers
- Correcting inventory errors

### Understanding Inventory Calculations

**Formula:** `Current Stock = Initial Inventory + Received - Shipped - Adjustments`

- **Initial Inventory** - Baseline from September 19, 2025 (locked, never changes)
- **Received** - All incoming inventory transactions
- **Shipped** - All outgoing shipments (from ShipStation + manual)
- **Adjustments** - Manual corrections

---

## Weekly Reports

**Purpose:** View historical inventory reports with 52-week rolling averages.

### Accessing Weekly Reports

Click **Weekly Reports** in the left sidebar.

### What the Report Shows

The weekly inventory report includes:

1. **Product Information**
   - SKU number
   - Product name
   - Key product status (★ for top sellers)

2. **Inventory Metrics**
   - Current stock levels
   - Low stock thresholds
   - Reorder points

3. **Shipping Data**
   - Units shipped this week
   - 52-week rolling average
   - Trend indicators

4. **Projections**
   - Weeks of inventory remaining
   - Recommended reorder quantities

### When Reports Are Generated

**CRITICAL TIMING:** The weekly report captures a 52-week window and must run AFTER shipping completes for the week.

**Normal Schedule:**
- **Friday** after all shipments sent (typical)

**Holiday Edge Cases:**
- **Friday is holiday** → Run **Thursday** after shipping
- **Thanksgiving week (Thu+Fri closed)** → Run **Wednesday** after shipping  
- **Mid-week holiday** → Run **Friday** after shipping

**You control the timing!** See [Manual Report Generation](#manual-report-generation) below.

### Manual Report Generation

**When to use:**
- Week with holiday schedule
- Need updated report for planning meeting
- After major shipment or receipt

**How to generate:**

1. Go to **Weekly Reports** page
2. Click **Run Report** button (top right)
3. Wait for "Report generated successfully" message
4. Report updates with current data

**Last Updated:** Check the timestamp under the Run Report button to see when the report was last generated.

### Reading the Report

**Weeks Remaining Column:**
- **Green (>8 weeks)** - Healthy inventory
- **Yellow (4-8 weeks)** - Monitor closely
- **Red (<4 weeks)** - Reorder needed

**Rolling Average:**
- Average weekly shipments over past 52 weeks
- Smooths out seasonal variations
- More reliable than simple averages

---

## Bundle SKUs

**Purpose:** Manage product bundles that automatically expand into component items.

### What Are Bundles?

A bundle is a single SKU that contains multiple component products.

**Example:**
- Bundle SKU: 18225 (Retail Pack)
- Contains: 40 units of SKU 17612 (individual toothbrushes)

When you import bundle SKU 18225, the system automatically creates orders for the individual components.

### Accessing Bundle Management

Click **Bundle SKUs** in the left sidebar (under ADMIN & DATA).

### Viewing Bundles

The table shows all configured bundles:

| Column | Description |
|--------|-------------|
| **Bundle SKU** | Parent bundle identifier |
| **Bundle Name** | Description of bundle |
| **# Components** | How many items in bundle |
| **Active** | Whether bundle is enabled |
| **Actions** | Edit or Delete buttons |

### Adding a New Bundle

1. Click **Add Bundle** button (top right)
2. Fill in the form:

   **Bundle Information:**
   - **Bundle SKU:** Unique identifier (e.g., 18225)
   - **Bundle Name:** Description (e.g., "Retail Display Pack")
   - **Active:** Check if bundle is currently in use

   **Components:** (Add one or more)
   - **Component SKU:** Individual product SKU
   - **Quantity:** Units per bundle
   - Click **+ Add Component** for additional items

3. Click **Create Bundle**

**Example - Single Component:**
```
Bundle SKU: 18225
Bundle Name: Retail Display Pack
Components:
  - SKU: 17612, Quantity: 40
```

**Example - Multi-Component:**
```
Bundle SKU: 18615
Bundle Name: Professional Starter Kit
Components:
  - SKU: 17612, Quantity: 10
  - SKU: 17904, Quantity: 5
  - SKU: 18675, Quantity: 2
```

### Editing a Bundle

1. Click **Edit** button for the bundle
2. Modify bundle details or components
3. Add/remove components as needed
4. Click **Update Bundle**

### Deleting a Bundle

1. Click **Delete** button for the bundle
2. Confirm deletion
3. Bundle configuration removed

**Warning:** Deleting a bundle does NOT affect historical orders, but future imports of this SKU will NOT expand automatically.

### How Bundles Work in Orders

**When XML order contains bundle SKU:**

1. **XML Import** detects bundle SKU (e.g., 18225)
2. **Database lookup** finds bundle components
3. **Automatic expansion** creates individual SKU orders
4. **ShipStation upload** sends component SKUs (not bundle)

**Example:**
- XML shows: 1 unit of bundle 18225
- System creates: 40 units of SKU 17612
- ShipStation receives: Order for 40x SKU 17612

**Benefit:** Customers order bundles, but warehouse ships individual products.

---

## SKU-Lot Tracking

**Purpose:** Track specific lot numbers for inventory and compliance.

### What Is SKU-Lot Tracking?

SKU-Lot tracking links product SKUs to specific manufacturing lots.

**Format:** `SKU - Lot` (e.g., "17612 - 250237")

**Why track lots?**
- Traceability for recalls
- Quality control
- Expiration management
- Compliance requirements

### Accessing SKU-Lot Management

Click **SKU Lot** in the left sidebar (under ADMIN & DATA).

### Viewing SKU-Lot Records

The table shows all tracked combinations:

| Column | Description |
|--------|-------------|
| **SKU** | Product identifier |
| **Lot** | Manufacturing lot number |
| **Active** | Whether lot is in current use |
| **Created At** | When record was added |
| **Actions** | Edit or Delete buttons |

### Adding a SKU-Lot Combination

1. Click **Add SKU-Lot** button (top right)
2. Fill in the form:
   - **SKU:** Product identifier (e.g., 17612)
   - **Lot:** Lot number (e.g., 250237)
   - **Active:** Check if currently shipping from this lot
3. Click **Create**

**Duplicate Prevention:** The system prevents duplicate SKU-Lot combinations. If you try to add an existing pair, you'll see an error message.

### Editing a SKU-Lot Record

1. Click **Edit** button for the record
2. Modify SKU, lot number, or active status
3. Click **Update**

**Common use:** Mark old lots as inactive when depleted, add new lots as active.

### Deleting a SKU-Lot Record

1. Click **Delete** button for the record
2. Confirm deletion
3. Record removed from system

**Warning:** Historical orders retain their lot numbers even after deletion.

### How SKU-Lot Works in Orders

**During ShipStation Upload:**

1. **System checks** for active SKU-Lot mapping
2. **If found:** Order uses format "SKU - Lot" (e.g., "17612 - 250237")
3. **If not found:** Order uses plain SKU (e.g., "17612")

**Manual ShipStation Orders:**

When you create orders manually in ShipStation using "SKU - Lot" format:
- **Manual Order Sync** detects the format
- **Automatic parsing** separates SKU and lot
- **Database tracking** preserves lot information

**Example:**
- ShipStation item: "17612 - 250237"
- Database SKU: 17612
- Database Lot: 250237

---

## Shipping Alerts

**Purpose:** Detect and alert on shipping rule violations.

### How Shipping Validation Works

The system monitors all orders and compares actual shipping assignments against business rules.

**This is ALERT-ONLY:** The system does NOT block shipments or modify ShipStation orders. It only notifies you of potential issues.

### Shipping Rules

1. **Hawaiian Orders (HI state)**
   - **Expected:** FedEx 2Day service
   - **Why:** Faster delivery to islands

2. **Canadian Orders (CA/CANADA country)**
   - **Expected:** FedEx International Ground
   - **Why:** Standard international service

3. **Benco Orders (company contains "BENCO")**
   - **Expected:** Benco FedEx carrier account
   - **Why:** Customer-specific billing arrangement

### Viewing Violations

**Dashboard Alert:**
- Yellow banner shows violation count
- Example: "3 shipping violations detected - Click to review"

**Violation Details:**
1. Click the yellow banner
2. Modal window shows violation list
3. Each violation includes:
   - Order number and date
   - Customer company
   - Expected vs. actual shipping
   - Violation reason
   - Resolve button

**Example Violation:**
```
Order: 12345
Company: BENCO Dental Supply
Expected: Benco FedEx Carrier
Actual: Standard FedEx Account
Reason: Benco orders must use Benco carrier account
```

### Resolving Violations

**Option 1: Fix in ShipStation**
1. Open ShipStation
2. Find the order by order number
3. Change carrier/service to match expected
4. Return to ORA dashboard
5. Click **Resolve** button on violation

**Option 2: Accept Exception**
- If the shipping assignment is intentional
- Click **Resolve** to dismiss the alert
- Order ships with current settings

**Resolved violations:**
- Marked as resolved in database
- No longer appear in alert count
- Preserved in history for auditing

### When Violations Are Detected

**Automatic Detection:**
- **Status Sync** (hourly) - Checks uploaded orders
- **Manual Order Sync** (hourly) - Checks manual orders

**Timing:**
- Violations appear within 1 hour of order upload
- Dashboard banner updates automatically
- Alert persists until resolved

---

## Settings

**Purpose:** Configure system parameters and preferences.

### Accessing Settings

Click **Settings** in the left sidebar (under ADMIN & DATA).

### What You Can Configure

The Settings page allows you to view and manage system configuration parameters.

**Configuration Categories:**

1. **Display Preferences**
   - **Dark Mode** - Toggle between light and dark themes
   - Interface preferences
   - Display options

2. **Inventory Configuration**
   - **Low Stock Thresholds** - Set reorder points for each SKU
   - **Initial Inventory** - View baseline values (locked at September 19, 2025)
   - **Key Products** - Mark products for priority tracking

3. **System Parameters**
   - **Pallet Counts** - Configure units per pallet for shipping calculations
   - **FedEx Pickup Threshold** - Set the unit count that triggers pickup alert (default: 185)
   - **Benco Carrier IDs** - Configure Benco-specific carrier account identifiers

4. **Database Information**
   - View system version
   - Database location
   - Last update timestamps

### Using Dark Mode

**To enable dark mode:**
1. Go to Settings
2. Find "Dark Mode" toggle
3. Click to switch between light and dark themes
4. Setting saves automatically

**Benefits:**
- Easier viewing in low-light conditions
- Reduces eye strain
- Personal preference

**Note:** Dark mode preference is saved in your browser and persists across sessions.

### Configuration Best Practices

**Don't Modify Unless Needed:**
- Most settings are configured during initial setup
- Changes to thresholds affect alerts and calculations
- Contact administrator if unsure about changing values

**Low Stock Thresholds:**
- Set based on lead time from suppliers
- Consider weekly average shipments
- Leave safety margin for unexpected demand

**Pallet Configuration:**
- Used for warehouse planning
- Should match actual physical pallet capacity
- Updates affect packing calculations

**Initial Inventory (Read-Only):**
- Locked at September 19, 2025 baseline
- Cannot be modified (database trigger prevents changes)
- All inventory calculations use this as starting point

### When to Contact Administrator

Contact your system administrator before changing:
- Any system parameters you're unfamiliar with
- Benco carrier ID configuration
- Database-related settings

**Note:** Settings changes take effect immediately but may require browser refresh to fully display.

---

## Manual Operations

### Manual XML Import

**When to use:**
- Emergency order upload outside automation
- Testing new XML files
- Reprocessing failed imports

**How to import:**

1. Click **Manual Import** in sidebar (or Orders Inbox "Manual Import" button)
2. Click **Choose File** button
3. Select XML file from your computer
4. Click **Import XML File**
5. Wait for confirmation message

**After import:**
- Orders appear in Orders Inbox with status "pending"
- Automatic upload runs within 5 minutes
- Check Orders Inbox to verify

**File requirements:**
- Must be .xml file extension
- Must match expected XML order format

### Manual ShipStation Sync

**When to use:**
- After creating orders manually in ShipStation
- Want to see manual orders in database immediately
- Hourly sync hasn't run yet

**How to sync:**

1. Go to Orders Inbox
2. Click **Sync Manual** button (purple sync icon)
3. Wait for "Sync completed" message
4. Manual orders appear in table with "synced_manual" status

**What it does:**
- Queries ShipStation for orders not in local database
- Imports order details (SKU, quantity, lot, customer info)
- Updates inventory tracking
- Runs hourly automatically

### Retrying Failed Orders

**When to use:**
- Orders show "failed" status
- After fixing configuration issues
- After ShipStation API issues resolve

**How to retry:**

1. Go to Orders Inbox
2. Click "Show All Orders" to see failed orders
3. Click **Retry Failed** button
4. System attempts to upload all failed orders
5. Check results in confirmation message

**Common failure causes:**
- ShipStation API timeout
- Missing shipping configuration
- Invalid address data
- Network connectivity issues

### Manual Weekly Report

See [Manual Report Generation](#manual-report-generation) in the Weekly Reports section.

**Quick steps:**
1. Go to Weekly Reports page
2. Click **Run Report** button
3. Wait for confirmation
4. Report updates with current data

**IMPORTANT:** Only run after week's shipping is complete.

---

## Troubleshooting

### Orders Not Uploading to ShipStation

**Symptoms:**
- Orders stuck in "pending" status for >10 minutes
- Pending upload count increasing on Dashboard

**Check:**

1. **Dashboard workflow status**
   - Is "ShipStation Upload" showing green "Running"?
   - If stopped/error, contact administrator

2. **ShipStation API connectivity**
   - Check ShipStation website status
   - Verify API credentials in Settings

3. **Order validation errors**
   - Click "Validate" in Orders Inbox
   - Review any error messages
   - Fix invalid addresses or missing data

**Quick fix:**
- Select stuck orders manually
- Click "Upload Selected" to force immediate upload

### Workflow Showing "Stopped" or "Error"

**Symptoms:**
- Red or yellow status on Dashboard workflow
- Automation not running

**Action:**
1. Note which workflow has the issue
2. Contact your system administrator
3. Provide workflow name and error details
4. Do NOT attempt to restart workflows yourself

**Temporary workaround:**
- Use manual operations (Manual Import, Sync Manual, etc.)
- Continue monitoring Dashboard for updates

### Inventory Numbers Don't Match Physical Stock

**Symptoms:**
- Database shows different quantity than warehouse
- Recent shipments not reflected

**Check:**

1. **Recent transactions**
   - Go to Inventory Transactions
   - Verify all shipments recorded
   - Look for missing entries

2. **Manual ShipStation orders**
   - Did you create orders directly in ShipStation?
   - Click "Sync Manual" to import them

3. **Initial inventory baseline**
   - Baseline date is September 19, 2025
   - All calculations start from this date
   - Cannot modify initial inventory

**Fix:**
1. Count physical stock
2. Calculate difference from database
3. Add adjustment transaction:
   - Type: "adjustment"
   - Quantity: Difference (+ or -)
   - Notes: "Physical count correction"

### Shipping Violations Alert Won't Clear

**Symptoms:**
- Yellow banner persists after fixing issues
- Violation count doesn't decrease

**Action:**

1. Click yellow banner to open violation modal
2. For each violation:
   - Verify fix in ShipStation
   - Click **Resolve** button
3. Banner disappears when all resolved

**Note:** Banner updates automatically. If it persists after resolving all violations, manually refresh the page.

### Dashboard Not Updating

**Symptoms:**
- Metrics appear stale
- Recent changes not visible

**Fix:**

1. **Manual refresh** - Click 🔄 Manual Refresh button (top right)
2. **Browser refresh** - Press F5 or Ctrl+R (Cmd+R on Mac)
3. **Clear cache** - Hold Ctrl+Shift+R (Cmd+Shift+R on Mac)

**Note:** Dashboard auto-refreshes every 60 seconds automatically.

### Can't Add Bundle or SKU-Lot (Duplicate Error)

**Symptoms:**
- "This combination already exists" error message
- Create button doesn't work

**Cause:** You're trying to add a duplicate record.

**Fix:**

1. Search existing records for the SKU or bundle
2. If found:
   - Edit existing record instead of creating new
   - Update quantities or status
3. If not found but error persists:
   - Check for typos in SKU numbers
   - Verify exact lot number format

### Mobile Menu Not Appearing

**Symptoms:**
- Can't access navigation on phone/tablet
- Menu button not visible

**Fix:**

1. **Portrait orientation** - Rotate device to portrait mode
2. **Zoom out** - Pinch to zoom out if zoomed in
3. **Scroll to top** - Menu appears at top of page
4. **Browser compatibility** - Try Chrome or Safari

**Known issue:** Some older mobile browsers may not display properly. Use updated browser version.

---

## FAQ

### General Questions

**Q: Do I need to log in?**  
A: No. This is an internal system with no authentication. Access is controlled at the network level.

**Q: Can I access this from home?**  
A: Depends on your Replit deployment settings. Contact your administrator for remote access setup.

**Q: What browsers are supported?**  
A: Chrome, Firefox, Safari, and Edge (latest versions). Mobile browsers on iOS and Android are also supported.

**Q: How often does data refresh?**  
A: The Dashboard auto-refreshes every 30 seconds. You can also manually refresh anytime.

### Orders & Shipping

**Q: How do orders get into the system?**  
A: Automatically from XML files in Google Drive (checked every 5 minutes), or manually via Manual Import page.

**Q: When do orders upload to ShipStation?**  
A: Automatically every 5 minutes. You can also force immediate upload using "Upload Selected" button.

**Q: What happens if ShipStation is down?**  
A: Orders remain in "pending" status and auto-retry every 5 minutes. They'll upload automatically when ShipStation is back online.

**Q: Can I edit orders in the system?**  
A: No. Orders are read-only in ORA. Make changes in ShipStation directly.

**Q: Do shipping violations block orders?**  
A: No! Violations are alerts only. Orders ship normally regardless of alerts.

**Q: How do I ship to multiple addresses on one order?**  
A: Create separate orders in ShipStation. The system imports each as individual order.

### Inventory

**Q: How is inventory calculated?**  
A: `Current Stock = Initial Inventory (Sept 19, 2025) + Received - Shipped - Adjustments`

**Q: Can I change the initial inventory?**  
A: No. The baseline is locked at September 19, 2025 for data integrity.

**Q: Why doesn't my physical count match the system?**  
A: Add an "adjustment" transaction to correct the difference. See [Troubleshooting](#inventory-numbers-dont-match-physical-stock).

**Q: When should I record transactions?**  
A: Shipments from ShipStation are automatic. Manually record: supplier receipts, damaged goods, physical count corrections.

### Reports

**Q: When should I run the weekly report?**  
A: At the END of your business week AFTER all shipping is complete. Normal: Friday. Holiday weeks: See [Weekly Reports](#when-reports-are-generated).

**Q: What's a "52-week rolling average"?**  
A: The average weekly shipments over the past year. More reliable than simple averages because it smooths seasonal variations.

**Q: Can I export reports to Excel?**  
A: Yes! Use the "Export CSV" button on Orders Inbox. Open CSV files in Excel or Google Sheets.

**Q: How far back does historical data go?**  
A: Database contains all data from September 19, 2025 forward. Shipped orders preserved indefinitely.

### Bundles & Lots

**Q: What's the difference between bundles and SKU-Lots?**  
A: **Bundles** expand one SKU into multiple items (e.g., retail pack → individual units). **SKU-Lots** track manufacturing lots for the same SKU.

**Q: Do I need to configure bundles for every product?**  
A: No. Only configure products that are actually sold as bundles. Individual SKUs work without bundle configuration.

**Q: What happens if I delete a bundle?**  
A: Historical orders unchanged. Future imports of that bundle SKU will NOT auto-expand.

**Q: Can one SKU have multiple active lots?**  
A: Yes! You can have multiple active lots for the same SKU. ShipStation upload uses the most recently created active lot.

### System & Automation

**Q: Is the system always running?**  
A: Yes. Deployed on Replit Reserved VM with 24/7 uptime. All workflows run automatically in the background.

**Q: What if I need to make changes?**  
A: Contact your system administrator for configuration changes, workflow adjustments, or technical issues.

**Q: How do I know if automation is working?**  
A: Check Dashboard workflow status. All should show green "Running". Orders should upload within 5-10 minutes of import.

**Q: Can I pause automation?**  
A: Contact your administrator. Generally not recommended as orders will queue up.

**Q: What happens during a power outage?**  
A: Replit Reserved VM has redundancy. System stays online. If your internet is down, you won't be able to access the dashboard.

### Data & Storage

**Q: How much data can the system hold?**  
A: Current SQLite database handles years of data easily. Designed for 50-100 orders/day with room for growth.

**Q: Is my data backed up?**  
A: Replit provides automatic backups. Contact administrator for backup schedule details.

**Q: Can I export all my data?**  
A: Yes. Use Export CSV buttons on each page, or contact administrator for full database export.

**Q: Will old orders be deleted?**  
A: Orders in "orders_inbox" older than 60 days are automatically deleted. Shipped orders in "shipped_orders" are preserved indefinitely for reporting.

---

## Getting Help

### Technical Support

For system issues, errors, or technical questions:

**Contact:** Your system administrator  
**Include:** 
- What you were trying to do
- Error message (screenshot if possible)
- What page you were on
- Time the issue occurred

### Training

Need help using a specific feature? This manual covers all functionality. Use the Table of Contents to jump to relevant sections.

### System Updates

The system is updated periodically to add features and fix bugs. Changes will be communicated by your administrator.

---

## Quick Reference

### Common Tasks Cheat Sheet

| Task | Where to Go | Action |
|------|-------------|--------|
| Check today's orders | Orders Inbox | Click "Show All Orders" |
| Upload orders now | Orders Inbox | Select orders → "Upload Selected" |
| See what's shipping | Dashboard | Check "Units to Ship" metric |
| Check stock levels | Inventory Monitor | Review Current Stock column |
| Generate weekly report | Weekly Reports | Click "Run Report" |
| Add new product bundle | Bundle SKUs | Click "Add Bundle" |
| Track new lot number | SKU Lot | Click "Add SKU-Lot" |
| Import emergency order | Manual Import | Upload XML file |
| Review shipping issues | Dashboard | Click yellow alert banner |
| Record inventory receipt | Inventory Transactions | Click "Record Transaction" |

### Important Phone Numbers

**FedEx Pickup:** 651-846-0590  
(Call when Dashboard shows "FedEx Pickup Needed" - 185+ units)

### System Status Page

Always check the Dashboard workflow status before troubleshooting. Green "Running" = normal operations.

---

**End of User Manual**

*For technical documentation, see: DATABASE_SCHEMA.md, API_INTEGRATION.md, MIGRATION_GUIDE.md*
