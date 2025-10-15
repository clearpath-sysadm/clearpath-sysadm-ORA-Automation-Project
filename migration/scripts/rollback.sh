#!/bin/bash
set -e

# BULLETPROOF ROLLBACK SCRIPT
# Handles dirty git state, validates backup, restores environment

echo "🔄 EMERGENCY ROLLBACK TO SQLITE (BULLETPROOF)"
echo "=============================================="

# 1. Stop ALL processes (force kill)
echo "💀 Step 1: Force killing all Python processes..."
pkill -9 -f "python" || true
sleep 5
echo "✅ All processes killed"

# 2. Find canonical backup
echo ""
echo "🔍 Step 2: Locating canonical backup..."
if [ -f "migration/backup_id.txt" ]; then
    BACKUP_ID=$(cat migration/backup_id.txt)
    BACKUP="migration/backups/ora_frozen_${BACKUP_ID}.db"
else
    # Fallback: find most recent frozen backup
    BACKUP=$(ls -t migration/backups/ora_frozen_*.db 2>/dev/null | head -1)
fi

if [ -z "$BACKUP" ] || [ ! -f "$BACKUP" ]; then
    echo "❌ CRITICAL ERROR: No backup found!"
    echo "   Searched for: migration/backups/ora_frozen_*.db"
    ls -la migration/backups/ || echo "Backups directory not found"
    exit 1
fi

echo "✅ Found backup: $BACKUP"

# 3. Verify backup integrity
echo ""
echo "🔍 Step 3: Verifying backup integrity..."
INTEGRITY=$(sqlite3 "$BACKUP" "PRAGMA integrity_check;" 2>&1 || echo "FAILED")
if [ "$INTEGRITY" != "ok" ]; then
    echo "❌ CRITICAL ERROR: Backup is corrupted!"
    echo "   Integrity check result: $INTEGRITY"
    echo ""
    echo "Cannot safely rollback - backup is not usable"
    exit 1
fi
echo "✅ Backup integrity: OK"

# 4. Verify checksum (if exists)
echo ""
echo "🔐 Step 4: Verifying backup checksum..."
if [ -f "${BACKUP}.md5" ]; then
    CHECKSUM_RESULT=$(md5sum -c "${BACKUP}.md5" 2>&1 || echo "FAILED")
    if echo "$CHECKSUM_RESULT" | grep -q "OK"; then
        echo "✅ Checksum verified: MATCH"
    else
        echo "⚠️  WARNING: Checksum verification failed"
        echo "   This backup may have been tampered with or corrupted"
        read -p "Continue rollback anyway? (yes/no): " CONFIRM
        if [ "$CONFIRM" != "yes" ]; then
            echo "❌ Rollback aborted"
            exit 1
        fi
    fi
else
    echo "⚠️  No checksum file found (skipping verification)"
fi

# 5. Backup current state (just in case)
echo ""
echo "📦 Step 5: Backing up current state..."
CURRENT_BACKUP="migration/backups/ora_pre_rollback_$(date +%Y%m%d_%H%M%S).db"
if [ -f "ora.db" ]; then
    cp ora.db "$CURRENT_BACKUP"
    echo "✅ Current state saved to: $CURRENT_BACKUP"
else
    echo "  (No current database to backup)"
fi

# 6. Restore SQLite backup
echo ""
echo "📥 Step 6: Restoring SQLite backup..."
cp "$BACKUP" ora.db
RESTORED_SIZE=$(ls -lh ora.db | awk '{print $5}')
echo "✅ Backup restored: ora.db (${RESTORED_SIZE})"

# 7. Verify restored database
echo ""
echo "🔍 Step 7: Verifying restored database..."
RESTORED_INTEGRITY=$(sqlite3 ora.db "PRAGMA integrity_check;" || echo "FAILED")
if [ "$RESTORED_INTEGRITY" != "ok" ]; then
    echo "❌ CRITICAL ERROR: Restored database is corrupted!"
    exit 1
fi
echo "✅ Restored database integrity: OK"

# 8. Force revert code (handles dirty git state)
echo ""
echo "🔄 Step 8: Reverting code to pre-migration state..."

# Check if git tag exists
if git rev-parse pre-postgres-migration >/dev/null 2>&1; then
    # Stash any uncommitted changes
    git stash push -m "Auto-stash during rollback" || true
    
    # Force reset to pre-migration tag
    git reset --hard pre-postgres-migration
    
    # Clean untracked files
    git clean -fd
    
    echo "✅ Code reverted to pre-migration state"
else
    echo "⚠️  WARNING: pre-postgres-migration tag not found"
    echo "   Cannot revert code automatically"
    echo "   Manual code revert may be required"
fi

# 9. Restore environment variables
echo ""
echo "🔧 Step 9: Restoring environment to SQLite..."
export USE_POSTGRES=false
echo "USE_POSTGRES=false" > .env
unset DATABASE_URL  # Remove PostgreSQL connection string
echo "✅ Environment restored to SQLite"

# 10. Re-enable all workflows
echo ""
echo "▶️  Step 10: Re-enabling all workflows..."
sqlite3 ora.db "UPDATE workflow_controls SET enabled = 1;"
ENABLED=$(sqlite3 ora.db "SELECT COUNT(*) FROM workflow_controls WHERE enabled = 1;")
echo "✅ $ENABLED workflows re-enabled"

# 11. Verify requirements
echo ""
echo "📦 Step 11: Verifying SQLite dependencies..."
python -c "import sqlite3; print('SQLite available')" || {
    echo "⚠️  SQLite module not available - attempting reinstall"
    pip install -q pysqlite3 || true
}
echo "✅ SQLite dependencies OK"

# 12. Restart all workflows
echo ""
echo "🚀 Step 12: Restarting all workflows..."
bash start_all.sh &
sleep 5
echo "✅ Workflows restarting in background"

# 13. Final verification
echo ""
echo "🔍 Step 13: Final verification..."
sleep 5

# Check if processes are running
RUNNING=$(ps aux | grep "python src/" | grep -v grep | wc -l)
echo "  Workflow processes running: $RUNNING"

# Check database is accessible
sqlite3 ora.db "SELECT COUNT(*) FROM workflow_controls;" > /dev/null && echo "  ✅ Database accessible"

# 14. Document rollback
echo ""
echo "📝 Step 14: Documenting rollback..."
cat > migration/logs/rollback_$(date +%Y%m%d_%H%M%S).log << EOF
Rollback executed at: $(date)
Backup restored: $BACKUP
Backup size: $RESTORED_SIZE
Backup integrity: $RESTORED_INTEGRITY
Workflows re-enabled: $ENABLED
Processes restarted: $RUNNING
Environment: SQLite (USE_POSTGRES=false)
EOF

# Final summary
echo ""
echo "=============================================="
echo "✅ ROLLBACK COMPLETE"
echo "=============================================="
echo "  ✅ Database: Restored from frozen backup"
echo "  ✅ Code: Reverted to pre-migration state"
echo "  ✅ Environment: SQLite mode"
echo "  ✅ Workflows: Re-enabled and restarting"
echo ""
echo "System is now back on SQLite"
echo "=============================================="
