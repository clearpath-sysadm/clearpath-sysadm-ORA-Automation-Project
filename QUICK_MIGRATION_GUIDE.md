# Quick Migration Guide - Oracare to New Repl

## 🚀 Complete Setup in 3 Steps

### Step 1️⃣: In ORIGINAL Repl (This One)

```bash
# Export production data
python migrate_data.py export
```

**Downloads needed:**
- ✅ `data_migration.sql` (just created)
- ✅ `init_database.py` (already exists)
- ✅ `database_schema_export.sql` (already exists)

---

### Step 2️⃣: In NEW Repl

**A. Import code from GitHub**
- Create new Repl → Import from GitHub → Your repo URL

**B. Create PostgreSQL database**
- Tools → PostgreSQL → Create Database

**C. Add 5 secrets** (copy from original):
```
SHIPSTATION_API_KEY
SHIPSTATION_API_SECRET
BENCO_FEDEX_ACCOUNT_ID
ADMIN_EMAILS
SESSION_SECRET
```

**D. Upload these 3 files:**
- `init_database.py`
- `database_schema_export.sql`
- `migrate_data.py`
- `data_migration.sql`

---

### Step 3️⃣: Run Setup (in NEW Repl)

```bash
# 1. Initialize empty database schema
python init_database.py

# 2. Import production data
python migrate_data.py import

# 3. Start the application
./start_all.sh
```

---

## ✅ What Gets Migrated

| Data Type | Migrated? | Notes |
|-----------|-----------|-------|
| Configuration settings | ✅ Yes | Key Products, workflow controls |
| Bundle SKUs | ✅ Yes | All definitions + components |
| SKU lot assignments | ✅ Yes | Current active lots |
| Historical shipments | ✅ Yes | All shipped_orders + shipped_items |
| Inventory records | ✅ Yes | Current inventory + transactions |
| Incidents & alerts | ✅ Yes | Production incidents, violations |
| Active orders | ❌ No | Will import fresh from XML |
| Database credentials | ❌ No | Auto-generated in new Repl |

---

## ⏱️ Time Estimate

- Export data: ~1 minute
- File transfer: ~2 minutes
- Import + verify: ~3 minutes
- **Total: ~15-20 minutes** (including secret setup)

---

## 🆘 Troubleshooting

**"Table already exists" error during init:**
- Database already initialized - skip to migration step

**"data_migration.sql not found" error:**
- Make sure file is uploaded to new Repl root directory

**Import shows 0 rows:**
- Check you're running in the correct Repl (new one, not original)
- Verify database was initialized with `init_database.py` first

**Workflows won't start:**
- Check business hours (Mon-Fri 6 AM - 6 PM CST)
- Verify all 5 secrets are configured
- Check workflow logs for errors

---

## 📋 Post-Migration Checklist

- [ ] Dashboard loads at https://your-new-repl.replit.app
- [ ] Configuration → Key Products shows 5 SKUs
- [ ] Bundle SKUs page shows your bundles
- [ ] SKU Lot page shows active lot assignments
- [ ] Shipped Orders shows historical data
- [ ] All 7 workflows running (during business hours)
- [ ] Test login with Replit Auth
- [ ] Test XML import (upload sample file)

---

## 🎯 Success Criteria

When migration is complete, you should see:
- ✅ ~33 database tables created
- ✅ 5 Key Products configured
- ✅ Historical shipped orders preserved
- ✅ Bundle SKUs working
- ✅ Current lot assignments active
- ✅ All automation workflows enabled

**Ready to go live!** 🚀
