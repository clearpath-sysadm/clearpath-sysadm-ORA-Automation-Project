# AI Agent Setup Instructions - Oracare Fulfillment System

**IMPORTANT: This is a production application migration. Follow these instructions exactly.**

---

## Project Overview

This is the **Oracare Fulfillment System** - a PostgreSQL-based order management and inventory tracking system that replaces Google Sheets. The system manages:
- Order imports from XML files (Google Drive)
- Automated uploads to ShipStation
- Inventory tracking with lot numbers
- Real-time dashboard and monitoring

**Critical Context:**
- Production system with zero data loss tolerance
- All automation workflows run during business hours only (Mon-Fri 6 AM - 6 PM CST)
- User is fulfillment operations manager (non-technical)
- Primary interface: Dashboard (index.html) - NOT Orders Inbox

---

## Current Situation

The user has:
1. ✅ Imported code from GitHub to this new Repl
2. ✅ Uploaded migration files: `init_database.py`, `migrate_data.py`, `data_migration.sql`
3. ⏳ Needs help completing the setup

---

## Your Task: Complete Database Migration and Setup

### Step 1: Verify Prerequisites

Check these exist:
```bash
ls -la init_database.py migrate_data.py data_migration.sql database_schema_export.sql
```

**Expected:** All 4 files should exist

If any are missing, ask the user to upload them.

---

### Step 2: Check Database Connection

Verify PostgreSQL database is created:
```bash
python -c "import os; print('✅ DATABASE_URL exists' if os.getenv('DATABASE_URL') else '❌ DATABASE_URL missing')"
```

**If missing:** 
- Tell user: "Please create a PostgreSQL database in Replit: Tools → PostgreSQL → Create Database"
- Wait for user to complete this

---

### Step 3: Check Secrets Configuration

Run the secrets verification:
```bash
python secrets_checklist.py verify
```

**If any secrets are missing:**
- Tell user which secrets need to be configured
- Provide the list: SHIPSTATION_API_KEY, SHIPSTATION_API_SECRET, BENCO_FEDEX_ACCOUNT_ID, ADMIN_EMAILS, SESSION_SECRET
- Wait for user to add them via Tools → Secrets

---

### Step 4: Initialize Database Schema

Run the initialization script:
```bash
python init_database.py
```

**Expected output:**
- "✅ Connected successfully"
- "✅ Schema created successfully"
- "✅ Added 5 Key Products"
- "✅ Configured 6 workflow controls"
- "✅ DATABASE INITIALIZATION COMPLETE!"

**If it says "table already exists":**
- This is fine - database was already initialized
- Skip to Step 5

**If errors occur:**
- Read the error message
- Check database connection
- Ask user if they need to create the database

---

### Step 5: Import Production Data

Run the data migration:
```bash
python migrate_data.py import
```

**Expected flow:**
1. Shows what will be imported
2. Asks: "Continue with import? (yes/no)"
   - **Answer: yes**
3. Imports data
4. Shows verification (row counts)
5. Asks: "Commit changes? (yes/no)"
   - **Answer: yes**

**Expected output:**
- "✅ DATA IMPORT COMPLETE!"
- Shows row counts for Configuration, Bundle SKUs, Shipped Orders, etc.

**IMPORTANT - Tables Intentionally Skipped:**
The migration intentionally skips these tables (they will regenerate from workflows):
- `orders_inbox` / `order_items_inbox` - Active orders (imported fresh from XML)
- `shipstation_order_line_items` - References active orders (regenerates from ShipStation sync)
- `shipping_violations` - References active orders (regenerates when violations detected)
- `manual_order_conflicts` - References active orders (regenerates when conflicts occur)

These tables will populate automatically once the XML import and ShipStation sync workflows run.

**If errors occur:**
- Check that `data_migration.sql` file exists and has content
- Check database connection
- Report the specific error to user

---

### Step 6: Verify Installation

Check the database has data:
```sql
SELECT COUNT(*) FROM configuration_params WHERE category = 'Key Products';
```

**Expected:** 5 rows (the 5 Key Product SKUs)

Check bundle SKUs:
```sql
SELECT COUNT(*) FROM bundle_skus WHERE active = 1;
```

**Expected:** 50+ rows

Check workflows:
```sql
SELECT COUNT(*) FROM workflow_controls;
```

**Expected:** 6 rows

---

### Step 7: Start the Application

Start all workflows:
```bash
./start_all.sh
```

**Expected:**
- Dashboard server starts on port 5000
- All 7 background workflows start
- No immediate errors in logs

**Verify the dashboard loads:**
- Use the screenshot tool to capture the homepage
- Should show Oracare logo, KPI cards, workflow status

---

### Step 8: Final Verification

Run the final secrets check:
```bash
python secrets_checklist.py verify
```

**Expected:** "✅ SUCCESS! All secrets configured correctly"

Check that the user can access the dashboard at the Replit webview URL.

---

## Success Criteria

When complete, verify:
- ✅ Database has 33 tables
- ✅ Configuration shows 5 Key Products
- ✅ Bundle SKUs table has 50+ bundles
- ✅ Historical shipped orders preserved
- ✅ All 7 workflows running
- ✅ Dashboard loads with Oracare branding
- ✅ All secrets configured

---

## Common Issues and Solutions

### Issue: "data_migration.sql not found"
**Solution:** Ask user to upload the file from original Repl

### Issue: "DATABASE_URL not found"
**Solution:** User needs to create PostgreSQL database: Tools → PostgreSQL → Create Database

### Issue: "Secret X is missing"
**Solution:** User needs to add it: Tools → Secrets → + New Secret

### Issue: Workflows show errors in logs
**Solution:** 
1. Check it's business hours (Mon-Fri 6 AM - 6 PM CST)
2. Verify all secrets are configured
3. Read the specific error from logs
4. Most common: Missing ShipStation API credentials

### Issue: Dashboard shows 404 or won't load
**Solution:**
1. Check dashboard-server workflow is running
2. Restart workflow if needed
3. Check for errors in dashboard-server logs

---

## Important Technical Details

**Database Structure:**
- PostgreSQL with strict constraints
- Foreign keys enforced
- Money stored as INTEGER (cents)
- All timestamps in UTC

**Business Rules:**
- 12 noon CST cutoff for daily orders
- Unit counts (not order counts) drive all metrics
- ShipStation is the fulfillment execution platform
- This system is for monitoring and inventory management

**Workflow Schedule:**
- All automation runs Mon-Fri 6 AM - 6 PM CST only
- 64% database compute reduction vs 24/7 operation
- No business impact from limited hours

**User Context:**
- Fulfillment operations manager
- Non-technical user
- Values: Production-ready, minimal dev time, zero data loss
- Default view: Dashboard (not Orders Inbox)

---

## After Setup is Complete

Tell the user:
1. ✅ Migration complete - new instance is ready
2. 🔍 Show them the dashboard (use screenshot tool)
3. 📋 Remind them to test:
   - Login with Replit Auth
   - Check workflow controls page
   - Verify shipped orders show historical data
4. 🚀 Confirm they can start using the new instance

---

## File Cleanup (After Successful Setup)

Once everything works, you can optionally clean up migration files:
- `data_migration.sql` (large file, no longer needed)
- `secrets_checklist_*.txt` files

**Keep these files:**
- `init_database.py` (useful for future fresh installs)
- `migrate_data.py` (useful for future migrations)
- `NEW_INSTANCE_SETUP.md` (documentation)

---

## Questions to Ask User

If anything is unclear:
- "Have you created the PostgreSQL database in Replit?"
- "Have you added all 5 secrets (SHIPSTATION_API_KEY, etc.)?"
- "Did you upload the data_migration.sql file from the original Repl?"

---

## Final Notes

**DO:**
- Follow these steps in order
- Verify each step before proceeding
- Use the provided scripts (don't write new ones)
- Check logs if errors occur
- Ask user for clarification if stuck

**DON'T:**
- Skip the secrets verification
- Assume database is created (check first)
- Modify the migration scripts
- Create new migration approaches
- Proceed if prerequisites aren't met

---

**Time Estimate:** 10-15 minutes (if all files are ready)

**User's Goal:** Working production instance of their order management system in new Repl account
