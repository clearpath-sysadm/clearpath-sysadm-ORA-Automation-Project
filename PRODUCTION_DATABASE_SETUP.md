# Production Database Setup Guide

## Overview
Your app is now configured to automatically use separate databases for development and production environments. This prevents your testing activities from affecting live production data.

## How It Works

### Environment Detection
The app automatically detects the environment using the `REPLIT_DEPLOYMENT` environment variable:

- **Development (Workspace)**: `REPLIT_DEPLOYMENT` is not set
  - Uses `DATABASE_URL` → Your development database
  - Safe for testing and debugging

- **Production (Deployed App)**: `REPLIT_DEPLOYMENT=1`
  - Uses `PRODUCTION_DATABASE_URL` (if set) or falls back to `DATABASE_URL`
  - Your live, customer-facing data

### Database Connection Logic
```
IF deployed (REPLIT_DEPLOYMENT=1):
    Use PRODUCTION_DATABASE_URL
    ↓ (if not set, fall back to)
    Use DATABASE_URL
ELSE (workspace):
    Use DATABASE_URL (dev database)
```

---

## Setup Steps

### Step 1: Create Production Database

1. **Through Replit UI**:
   - Open the **Database tool** in the left sidebar
   - Look for "Create Production Database" or similar option
   - Replit will provision a separate PostgreSQL database for production

2. **Get Production Database Credentials**:
   - Once created, Replit provides connection details
   - Copy the production database URL

### Step 2: Set Production Database URL

Add the production database URL as a **secret**:

1. Open the **Secrets tool** (🔒 icon in left sidebar)
2. Add a new secret:
   - **Key**: `PRODUCTION_DATABASE_URL`
   - **Value**: Your production database connection string
     ```
     postgresql://username:password@host:5432/database_name
     ```

### Step 3: Apply Schema to Production Database

Use the exported schema file (`database_schema_export.sql`) to set up your production database:

**Option A: Through Replit Database Tool**
1. Open the Database tool
2. Switch to your **production database**
3. Open SQL runner
4. Copy contents of `database_schema_export.sql`
5. Execute the SQL

**Option B: Using Command Line** (in production environment)
```bash
# When deployed, this will target production database
psql $PRODUCTION_DATABASE_URL < database_schema_export.sql
```

### Step 4: Verify Setup

**In Development (Workspace)**:
```bash
# Check which database is being used
python -c "from src.services.database.pg_utils import DATABASE_URL; print(f'Dev DB: {DATABASE_URL[:30]}...')"
```

**In Production (After Deployment)**:
```bash
# The deployed app will automatically use PRODUCTION_DATABASE_URL
# Check logs to confirm connection
```

---

## Migration Checklist

- [ ] Create production database through Replit Database tool
- [ ] Add `PRODUCTION_DATABASE_URL` secret with production database URL
- [ ] Apply schema to production database (use `database_schema_export.sql`)
- [ ] Test development workflows (should use dev database)
- [ ] Deploy app and verify it connects to production database
- [ ] Migrate critical data from dev to production (if needed)

---

## Current Status

✅ **Development Database**: Already configured and working
✅ **Environment Detection**: Configured in `db_adapter.py` and `pg_utils.py`
✅ **Schema Export**: Available in `database_schema_export.sql` (34KB, 1350 lines)

⏳ **Pending**: 
- Create production database
- Set `PRODUCTION_DATABASE_URL` secret
- Apply schema to production
- Deploy app

---

## Testing Database Separation

**Test 1: Development Environment**
```bash
# In workspace, should use DATABASE_URL
python -c "import os; print('REPLIT_DEPLOYMENT:', os.getenv('REPLIT_DEPLOYMENT', 'Not set'))"
# Output: REPLIT_DEPLOYMENT: Not set
```

**Test 2: Production Environment**
```bash
# When deployed, should have REPLIT_DEPLOYMENT=1
# App will automatically use PRODUCTION_DATABASE_URL
```

---

## Important Notes

1. **Data Isolation**: Dev and prod databases are completely separate
2. **Automatic Switching**: No code changes needed - the app detects environment automatically
3. **Fallback Safety**: If `PRODUCTION_DATABASE_URL` is not set, production will use `DATABASE_URL` (warn before deploying!)
4. **Schema Sync**: Keep `database_schema_export.sql` updated whenever you change the database structure

---

## Troubleshooting

**Issue**: Production app still uses dev database
- **Solution**: Verify `PRODUCTION_DATABASE_URL` secret is set correctly

**Issue**: Schema import fails
- **Solution**: Check PostgreSQL version compatibility (export is from PostgreSQL 16.9)

**Issue**: Connection errors in production
- **Solution**: Verify production database URL format and credentials

---

## Next Steps

1. **Create production database** (use Replit Database tool)
2. **Set the secret** `PRODUCTION_DATABASE_URL` with your production database URL
3. **Run the schema import** to create tables in production database
4. **Deploy your app** - it will automatically connect to production database
5. **Monitor logs** to confirm proper database connection

Once complete, you'll have:
- ✅ Safe development environment (test freely without affecting production)
- ✅ Isolated production environment (real customer data protected)
- ✅ Automatic environment detection (zero code changes needed)
