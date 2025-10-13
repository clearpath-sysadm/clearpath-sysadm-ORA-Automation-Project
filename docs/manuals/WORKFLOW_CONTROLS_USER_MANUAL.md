# Workflow Controls User Manual

## What Are Workflow Controls?

Workflow Controls allow you to turn automation workflows on or off with the flip of a switch. This prevents conflicts between development and production environments, and gives you control during maintenance or testing.

Think of it like a master power switch for each of your automation systems.

---

## Why Use Workflow Controls?

### Problem: Dev/Prod Conflicts
When you have both a development and production system running, they can interfere with each other:
- **Development workflows** might upload orders with incorrect lot numbers (e.g., 250237 instead of 250300)
- **Production workflows** process real customer orders and must use correct, current lot numbers
- Running both simultaneously causes data conflicts and errors

### Solution: Toggle Workflows
With Workflow Controls, you can:
- ✅ **Disable development workflows** to prevent interference with production
- ✅ **Pause specific workflows** during maintenance or troubleshooting
- ✅ **Control automation** without stopping the entire system
- ✅ **Make changes safely** knowing workflows won't run until you're ready

---

## How to Access Workflow Controls

### Option 1: Dashboard Navigation
1. Open your dashboard at `https://your-app.replit.app`
2. Look in the left sidebar for **"Admin & Data"** section
3. Click the **"Admin & Data"** dropdown arrow (▶) to expand it
4. Click **"Workflow Controls"** in the expanded menu

**Note**: The Workflow Controls link is inside the Admin & Data section, so you need to expand that section first to see it.

### Option 2: Direct URL
Go directly to: `https://your-app.replit.app/workflow_controls.html`

---

## Understanding the Dashboard

When you open Workflow Controls, you'll see:

### Warning Banner (Yellow)
> ⚠️ **Important**: Disabling workflows will pause automation. Use this to prevent dev/prod conflicts or during maintenance.

This reminds you that turning off workflows stops automation completely.

### Workflow List
Each workflow has:
- **Name**: What the workflow does
- **Description**: When it runs and what it handles
- **Status**: "Enabled" (green) or "Disabled" (gray)
- **Toggle Switch**: Turn on/off with one click

---

## Available Workflows

### 1. **XML Import**
- **What it does**: Monitors Google Drive for new order XML files every 5 minutes
- **When to disable**: When testing locally or when you don't want orders imported
- **Typical use**: Disable in development, enable in production

### 2. **ShipStation Upload**
- **What it does**: Uploads pending orders to ShipStation every 5 minutes
- **When to disable**: When you need to review orders before uploading, or testing locally
- **⚠️ CRITICAL**: Disable this in dev to prevent uploading with wrong lot numbers

### 3. **Status Sync**
- **What it does**: Checks ShipStation hourly for order status updates (shipped, cancelled)
- **When to disable**: During maintenance or when testing
- **Typical use**: Keep enabled in production to track shipments

### 4. **Manual Order Sync**
- **What it does**: Imports manually-created ShipStation orders hourly
- **When to disable**: When you don't want manual orders imported
- **Typical use**: Enable in production to capture all orders

### 5. **Orders Cleanup**
- **What it does**: Deletes orders older than 60 days from inbox (preserves shipped orders)
- **When to disable**: If you need to keep old orders temporarily
- **Typical use**: Keep enabled to maintain database cleanliness

### 6. **Weekly Reporter**
- **What it does**: Generates weekly inventory reports (runs at startup)
- **When to disable**: Rarely needed; only if reports are causing issues
- **Typical use**: Keep enabled for inventory tracking

---

## How to Use the Toggle Switches

### Enabling a Workflow
1. Find the workflow you want to enable
2. Click the toggle switch (it will turn green)
3. Status changes to "Enabled"
4. **Wait 60 seconds** for the change to take effect

### Disabling a Workflow
1. Find the workflow you want to disable
2. Click the toggle switch (it will turn gray)
3. Status changes to "Disabled"
4. **Wait 60 seconds** for the workflow to stop

### Important Notes
- ⏱️ **Changes take 60 seconds**: Workflows check their status every 45 seconds, so allow up to 60 seconds for changes to apply
- 💾 **Changes persist**: Your settings are saved in the database and survive system restarts
- 🔄 **Works across deployments**: Toggle settings remain active even after redeploying

---

## Common Use Cases

### Use Case 1: Prevent Dev/Prod Conflicts
**Problem**: You're testing changes in development, but don't want to interfere with production.

**Solution**:
1. Open Workflow Controls in your **development environment**
2. Disable all workflows (especially ShipStation Upload)
3. Test your changes safely
4. Re-enable when ready to deploy

**SQL Alternative** (for advanced users):
```sql
-- Disable all workflows at once
UPDATE workflow_controls SET enabled = FALSE WHERE 1=1;
```

### Use Case 2: Pause During Maintenance
**Problem**: You need to update lot numbers in the sku_lot table without workflows uploading old data.

**Solution**:
1. Open Workflow Controls
2. Disable "ShipStation Upload" temporarily
3. Update your lot numbers in SKU Lot Management
4. Re-enable "ShipStation Upload" when ready

### Use Case 3: Review Orders Before Upload
**Problem**: You want to manually review orders before they're uploaded to ShipStation.

**Solution**:
1. Disable "ShipStation Upload"
2. Let "XML Import" continue bringing in orders
3. Review orders in the Orders Inbox
4. When satisfied, enable "ShipStation Upload" to process them

### Use Case 4: Stop New Orders Temporarily
**Problem**: You're at capacity and need to pause new order processing.

**Solution**:
1. Disable "XML Import" to stop new orders from coming in
2. Keep other workflows running to process existing orders
3. Re-enable "XML Import" when ready to accept new orders

---

## Safety & Best Practices

### ✅ Safe to Disable
- **During development/testing**: Disable all workflows in dev environments
- **During maintenance**: Disable specific workflows you're working on
- **When reviewing data**: Disable uploads while checking data quality
- **When changing lot numbers**: Disable ShipStation Upload while updating SKU-Lot mappings

### ⚠️ Use Caution
- **In production**: Only disable workflows when necessary
- **During business hours**: Disabling workflows stops automation completely
- **Customer orders**: Disabling XML Import or ShipStation Upload delays order processing

### ❌ Don't Disable Unless Needed
- **Weekly Reporter**: Only disable if reports are causing problems
- **Status Sync**: Disabling means you won't see shipment updates
- **Orders Cleanup**: Disabling allows old orders to accumulate

---

## Troubleshooting

### Toggle Doesn't Change Status
- **Wait 60 seconds**: Changes aren't instant
- **Refresh the page**: Click the browser refresh button
- **Check database**: Verify workflow_controls table has the correct values

### Workflow Still Running After Disable
- **Wait longer**: Can take up to 60 seconds to stop
- **Check logs**: Look in workflow logs to confirm it stopped
- **Restart system**: In rare cases, restart all workflows

### Can't Access Dashboard
- **Check URL**: Make sure you're using `/workflow_controls.html`
- **Server running**: Verify the dashboard server is running
- **Browser cache**: Clear cache and try again

---

## Technical Details (Optional)

### How It Works
1. **Database Storage**: Enable/disable states stored in `workflow_controls` table
2. **Cache Layer**: Workflows check status every 45 seconds (±10 seconds jitter)
3. **Fail-Open**: If database check fails, workflows default to enabled (safe mode)
4. **API Endpoints**: 
   - `GET /api/workflow_controls` - View all workflow states
   - `PUT /api/workflow_controls/:name` - Toggle specific workflow

### Database Schema
```sql
CREATE TABLE workflow_controls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_name TEXT UNIQUE NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by TEXT DEFAULT 'system'
);
```

### Cache Behavior
- **TTL**: 45 seconds (with ±10 second jitter to prevent thundering herd)
- **Update Window**: Changes take effect within 60 seconds
- **Error Handling**: If cache lookup fails, workflows continue running (fail-open)

---

## Quick Reference

| Workflow | Runs | Safe to Disable in Dev? |
|----------|------|------------------------|
| XML Import | Every 5 min | ✅ Yes |
| ShipStation Upload | Every 5 min | ✅ Yes (CRITICAL) |
| Status Sync | Hourly | ✅ Yes |
| Manual Order Sync | Hourly | ✅ Yes |
| Orders Cleanup | Daily | ✅ Yes |
| Weekly Reporter | At startup | ⚠️ Usually keep enabled |

---

## Getting Help

If you encounter issues:
1. Check this manual first
2. Review workflow logs in `/tmp/logs/`
3. Verify database state in workflow_controls table
4. Contact system administrator

---

**Last Updated**: October 13, 2025  
**Version**: 1.0  
**Feature Status**: Production Ready ✅
