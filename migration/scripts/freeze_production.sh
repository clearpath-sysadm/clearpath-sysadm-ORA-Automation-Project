#!/bin/bash
set -e

# SAFETY-ENHANCED PRODUCTION FREEZE
# Properly kills processes, verifies quiescence, validates backup

echo "🔒 FREEZING PRODUCTION FOR MIGRATION (SAFETY-ENHANCED)"
echo "========================================================="

# 1. Disable all workflows in database
echo "⏸️  Step 1: Disabling all workflows in database..."
sqlite3 ora.db "UPDATE workflow_controls SET enabled = 0;"
echo "✅ All workflows disabled in database"

# 2. ACTUALLY KILL running workflow processes
echo ""
echo "💀 Step 2: Killing all running workflow processes..."
pkill -f "python src/unified_shipstation_sync.py" || echo "  (unified-shipstation-sync not running)"
pkill -f "python src/scheduled_xml_import.py" || echo "  (xml-import not running)"
pkill -f "python src/scheduled_shipstation_upload.py" || echo "  (shipstation-upload not running)"
pkill -f "python src/scheduled_cleanup.py" || echo "  (orders-cleanup not running)"
pkill -f "python src/weekly_reporter.py" || echo "  (weekly-reporter not running)"

echo "✅ Kill signals sent to all workflows"

# 3. Wait for processes to die
echo ""
echo "⏳ Step 3: Waiting 10 seconds for processes to terminate..."
sleep 10

# 4. Verify no workflow processes still running
echo ""
echo "🔍 Step 4: Verifying no workflow processes running..."
RUNNING=$(ps aux | grep "python src/" | grep -v grep | wc -l)
if [ "$RUNNING" -gt 0 ]; then
    echo "❌ ERROR: $RUNNING workflow processes still running!"
    ps aux | grep "python src/" | grep -v grep
    echo ""
    echo "Force killing remaining processes..."
    pkill -9 -f "python src/" || true
    sleep 5
    
    # Check again
    RUNNING=$(ps aux | grep "python src/" | grep -v grep | wc -l)
    if [ "$RUNNING" -gt 0 ]; then
        echo "❌ CRITICAL: Cannot kill all processes!"
        exit 1
    fi
fi
echo "✅ No workflow processes running"

# 5. Check pending uploads (informational)
echo ""
echo "📊 Step 5: Checking pending uploads..."
PENDING=$(sqlite3 ora.db "SELECT COUNT(*) FROM orders_inbox WHERE uploaded_to_shipstation = 0;")
echo "  Pending uploads: $PENDING"

if [ "$PENDING" -gt 0 ]; then
    echo "⚠️  WARNING: $PENDING orders pending upload will be migrated as-is"
    read -p "Continue migration anyway? (yes/no): " CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        echo "❌ Migration aborted by user - re-enabling workflows"
        sqlite3 ora.db "UPDATE workflow_controls SET enabled = 1;"
        bash start_all.sh &
        exit 1
    fi
fi

# 6. Verify system is quiescent (no recent writes)
echo ""
echo "🔍 Step 6: Verifying system quiescence (no recent writes)..."
sleep 5  # Wait a bit more

# Check for any writes in last 2 minutes
RECENT_WRITES=$(sqlite3 ora.db "SELECT COUNT(*) FROM shipped_orders WHERE last_updated > datetime('now', '-2 minutes');" || echo "0")
echo "  Recent writes (last 2 min): $RECENT_WRITES"

if [ "$RECENT_WRITES" -gt 5 ]; then
    echo "⚠️  WARNING: Database is still being written to!"
    echo "  This could indicate a process we didn't catch"
    read -p "Continue anyway? (yes/no): " CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        echo "❌ Migration aborted - re-enabling workflows"
        sqlite3 ora.db "UPDATE workflow_controls SET enabled = 1;"
        bash start_all.sh &
        exit 1
    fi
fi
echo "✅ System is quiescent"

# 7. Verify all workflows disabled
echo ""
echo "🔍 Step 7: Final verification - all workflows disabled..."
ENABLED=$(sqlite3 ora.db "SELECT COUNT(*) FROM workflow_controls WHERE enabled = 1;")
if [ "$ENABLED" -ne 0 ]; then
    echo "❌ ERROR: $ENABLED workflows still enabled in database!"
    sqlite3 ora.db "SELECT workflow_name FROM workflow_controls WHERE enabled = 1;"
    exit 1
fi
echo "✅ All workflows confirmed disabled"

# 8. Create canonical backup
echo ""
echo "📦 Step 8: Creating canonical backup..."
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="migration/backups/ora_frozen_${TIMESTAMP}.db"

cp ora.db "$BACKUP_PATH"

# 9. Verify backup integrity
echo ""
echo "🔍 Step 9: Verifying backup integrity..."
INTEGRITY=$(sqlite3 "$BACKUP_PATH" "PRAGMA integrity_check;" || echo "FAILED")
if [ "$INTEGRITY" != "ok" ]; then
    echo "❌ ERROR: Backup integrity check failed!"
    echo "  Result: $INTEGRITY"
    rm "$BACKUP_PATH"
    exit 1
fi
echo "✅ Backup integrity verified: OK"

# 10. Create checksum
echo ""
echo "🔐 Step 10: Creating backup checksum..."
md5sum "$BACKUP_PATH" > "${BACKUP_PATH}.md5"
BACKUP_SIZE=$(ls -lh "$BACKUP_PATH" | awk '{print $5}')
echo "✅ Checksum created"

# 11. Document freeze
echo ""
echo "📝 Step 11: Documenting freeze..."
date > migration/freeze_timestamp.txt
echo $TIMESTAMP > migration/backup_id.txt
sqlite3 "$BACKUP_PATH" "SELECT COUNT(*) FROM shipped_orders;" > migration/backup_row_counts.txt
sqlite3 "$BACKUP_PATH" "SELECT COUNT(*) FROM orders_inbox;" >> migration/backup_row_counts.txt

# 12. Final summary
echo ""
echo "========================================================="
echo "✅ PRODUCTION SAFELY FROZEN"
echo "========================================================="
echo "  Canonical backup: ora_frozen_${TIMESTAMP}.db"
echo "  Backup size: ${BACKUP_SIZE}"
echo "  Integrity: VERIFIED"
echo "  Checksum: CREATED"
echo "  All workflows: DISABLED"
echo "  All processes: STOPPED"
echo "  System state: QUIESCENT"
echo ""
echo "🔒 System is now frozen and safe to migrate"
echo "========================================================="
