# Transfer Checklist - Files to Move to New Repl

## 📦 Required Files (Transfer ALL of these)

### Migration Scripts (4 files):
- [ ] `init_database.py` - Database schema initialization
- [ ] `migrate_data.py` - Data export/import script
- [ ] `secrets_checklist.py` - Secrets verification helper
- [ ] `database_schema_export.sql` - Database schema definitions

### Data File (1 file - created after export):
- [ ] `data_migration.sql` - Your production data export
  - ⚠️ Create this first by running: `python migrate_data.py export`

### Documentation (3 files):
- [ ] `AI_AGENT_SETUP_INSTRUCTIONS.md` - **Give this to AI agent in new Repl**
- [ ] `NEW_INSTANCE_SETUP.md` - Complete setup guide
- [ ] `QUICK_MIGRATION_GUIDE.md` - Quick reference

### Project Documentation (1 file):
- [ ] `replit.md` - Project overview and preferences

---

## 📋 Transfer Steps

### Step 1: Export Production Data
```bash
python migrate_data.py export
```
This creates `data_migration.sql`

### Step 2: Download These 9 Files
1. `init_database.py`
2. `migrate_data.py`
3. `secrets_checklist.py`
4. `database_schema_export.sql`
5. `data_migration.sql` ← just created
6. `AI_AGENT_SETUP_INSTRUCTIONS.md`
7. `NEW_INSTANCE_SETUP.md`
8. `QUICK_MIGRATION_GUIDE.md`
9. `replit.md`

### Step 3: Upload to New Repl
Upload all 9 files to the root directory of your new Repl

### Step 4: Give Instructions to AI Agent
In the new Repl, tell the AI agent:

```
I need help setting up this application. Please read the 
AI_AGENT_SETUP_INSTRUCTIONS.md file and follow the steps 
to complete the database migration and setup.
```

The AI agent will:
- ✅ Verify prerequisites
- ✅ Check database and secrets
- ✅ Initialize schema
- ✅ Import production data
- ✅ Start workflows
- ✅ Verify everything works

---

## ⚡ Quick Command Summary

### In ORIGINAL Repl (this one):
```bash
python migrate_data.py export     # Export data
python secrets_checklist.py check # Secrets checklist
```

### In NEW Repl (AI agent will run these):
```bash
python secrets_checklist.py verify  # Verify secrets
python init_database.py             # Create schema
python migrate_data.py import       # Import data
./start_all.sh                      # Start app
```

---

## ✅ What Gets Migrated

| Item | Status |
|------|--------|
| All 33 database tables | ✅ Yes |
| Configuration (Key Products, etc.) | ✅ Yes |
| Bundle SKU definitions (54 bundles) | ✅ Yes |
| SKU lot assignments | ✅ Yes |
| Historical shipped orders | ✅ Yes |
| Inventory records | ✅ Yes |
| Production incidents | ✅ Yes |
| Active pending orders | ❌ No (imported fresh) |
| Secrets/API keys | ❌ No (manual transfer) |

---

## 🔐 Secrets to Transfer Manually

Use Replit's Secrets tool (🔒) to add these 5 secrets:

1. `SHIPSTATION_API_KEY`
2. `SHIPSTATION_API_SECRET`
3. `BENCO_FEDEX_ACCOUNT_ID`
4. `ADMIN_EMAILS`
5. `SESSION_SECRET`

**DO NOT transfer:** Database secrets (auto-generated)

---

## ⏱️ Time Estimate

- Export: 1 min
- File transfer: 2 min
- AI agent setup: 10-15 min
- **Total: ~15-20 minutes**

---

## 🎯 Success = Working Dashboard

When done, you should see:
- ✅ Dashboard at https://your-new-repl.replit.app
- ✅ Oracare logo and branding
- ✅ KPI cards with data
- ✅ All 7 workflows running
- ✅ Can log in with Replit Auth
- ✅ Historical shipped orders visible
- ✅ Bundle SKUs configured
