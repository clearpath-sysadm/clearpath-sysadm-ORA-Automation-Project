# Oracare Fulfillment System - New Instance Setup Guide

This guide walks you through setting up the Oracare Fulfillment System in a new Replit account.

## Prerequisites

- New Replit account (or existing account where you want to deploy)
- Access to production secrets from original instance
- GitHub repository with latest code (optional but recommended)

---

## Step 1: Import Code

### Option A: Import from GitHub (Recommended)
1. In Replit, click **Create Repl**
2. Select **Import from GitHub**
3. Enter your repository URL
4. Click **Import from GitHub**

### Option B: Fork Original Repl
1. Open the original Repl
2. Click the **⋯** menu (top right)
3. Select **Fork**
4. Choose destination account

---

## Step 2: Set Up Database

1. **Create PostgreSQL Database:**
   - Click the **Tools** button in left sidebar
   - Select **PostgreSQL**
   - Click **Create Database**
   - Replit will auto-generate connection credentials

2. **Initialize Database Schema:**
   ```bash
   python init_database.py
   ```
   
   This script will:
   - Create all 33 tables with proper constraints
   - Insert Key Products configuration (5 SKUs)
   - Set up workflow controls (6 workflows)
   - Add sample bundle SKUs
   - Verify installation

---

## Step 3: Configure Secrets

### Required Secrets (copy from original instance):

1. **ShipStation API Credentials:**
   - `SHIPSTATION_API_KEY`
   - `SHIPSTATION_API_SECRET`

2. **Business Configuration:**
   - `BENCO_FEDEX_ACCOUNT_ID`
   - `ADMIN_EMAILS`
   - `SESSION_SECRET`

### How to Add Secrets:
1. Click **Tools** → **Secrets** (or 🔒 icon)
2. Click **+ New Secret**
3. Enter name and value
4. Click **Add Secret**

### Database Secrets (Auto-Generated):
These are created automatically when you create the PostgreSQL database:
- `DATABASE_URL`
- `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`

---

## Step 4: Set Up Integrations

### Google Drive Integration (for XML imports):
```bash
# Use Replit's integration tool
# This will be set up via Replit's OAuth flow
```

---

## Step 5: Configure Active Lot Numbers

After database initialization, you need to set up current lot numbers for each SKU:

```sql
-- Example: Set active lot for SKU 17612
INSERT INTO sku_lot (sku, lot, active, created_at, updated_at)
VALUES ('17612', '250340', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- Repeat for all Key Products: 17612, 17904, 17914, 18675, 18795
```

Or use the **SKU Lot Management** page in the UI after the app starts.

---

## Step 6: Start the Application

### Option A: Using start_all.sh (Production)
```bash
./start_all.sh
```

This starts:
- Dashboard server (port 5000)
- All background automation workflows

### Option B: Dashboard Only (Development)
```bash
python app.py
```

---

## Step 7: Verify Installation

1. **Access Dashboard:**
   - Open the Webview (should show automatically)
   - You should see the Oracare dashboard with KPI cards

2. **Check Workflow Status:**
   - Navigate to **Workflow Controls** page
   - Verify all 6 workflows are enabled

3. **Test Authentication:**
   - Log in with Replit Auth
   - Check your email is recognized (may need to add to ADMIN_EMAILS)

4. **Verify Database:**
   - Go to **Settings** page
   - Check that all tables show correct counts

---

## Step 8: Data Migration (Recommended)

Migrate your production data from the original instance using the automated migration script:

### Step 1: Export Data (in ORIGINAL Repl)
```bash
python migrate_data.py export
```

This creates `data_migration.sql` containing:
- ✅ Configuration settings (Key Products, workflow controls)
- ✅ Bundle SKU definitions and components
- ✅ SKU lot assignments (current active lots)
- ✅ Historical shipped orders and items
- ✅ Inventory records and transactions
- ✅ Incidents, alerts, and monitoring data
- ⏭️ Skips active orders_inbox (will be imported fresh from XML)

### Step 2: Transfer File
Download `data_migration.sql` from original Repl and upload to new Repl.

### Step 3: Import Data (in NEW Repl)
```bash
python migrate_data.py import
```

The script will:
- Show what will be imported
- Ask for confirmation
- Import all data in correct order (respecting foreign keys)
- Verify the import
- Ask for final commit confirmation

**Migration Time:** ~2-5 minutes depending on data volume

---

## Troubleshooting

### Frontend Files Missing After GitHub Import
- Check if HTML files exist: `ls -la *.html`
- Check `.gitignore` - ensure HTML/CSS/JS not excluded
- Manually upload missing files if needed

### Database Connection Errors
- Verify `DATABASE_URL` secret exists
- Check PostgreSQL database is created in Replit
- Try recreating the database

### Workflows Not Starting
- Check business hours (Mon-Fri 6 AM - 6 PM CST)
- Verify secrets are configured
- Check logs for errors: Click workflow name in Replit

### Upload Service Not Working
- Ensure ShipStation API credentials are correct
- Verify lot numbers are assigned (check `sku_lot` table)
- Check `workflow_controls` table - upload should be enabled

---

## Post-Setup Checklist

- [ ] Database initialized (33 tables created)
- [ ] All 5 secrets configured
- [ ] Google Drive integration set up
- [ ] Active lot numbers assigned for all SKUs
- [ ] Dashboard accessible at https://your-repl.replit.app
- [ ] All 6 workflows enabled
- [ ] Test order import from XML
- [ ] Test order upload to ShipStation
- [ ] Admin authentication working

---

## Support

For issues or questions:
1. Check logs in Replit console
2. Review `replit.md` for architecture details
3. Check production logs if issue occurs in production

---

**Initial Setup Time:** ~15-20 minutes
**Database Migration:** +10-30 minutes (if needed)
