#!/bin/bash
# Oracare Fulfillment - Startup Script
# Launches all automation workflows and dashboard server

set -e

echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting Oracare Fulfillment System..."
echo "================================================"

# Ensure we're in the right directory
cd /home/runner/workspace || cd "$(dirname "$0")"

# Check required environment variables
if [ -z "$DATABASE_URL" ]; then
    echo "WARNING: DATABASE_URL not set, checking individual PG vars..."
    if [ -z "$PGHOST" ] || [ -z "$PGDATABASE" ]; then
        echo "ERROR: Missing required database environment variables"
        echo "Required: DATABASE_URL or (PGHOST, PGDATABASE, PGUSER, PGPASSWORD)"
    fi
fi

echo "Database connection configured: ${PGHOST:-via DATABASE_URL}"

# Start background automation workflows with logging
echo "Starting XML import scheduler (polling every 5 min)..."
python src/scheduled_xml_import.py 2>&1 &
XML_PID=$!

echo "Starting ShipStation upload (polling every 5 min)..."
python src/scheduled_shipstation_upload.py 2>&1 &
UPLOAD_PID=$!

echo "Starting unified ShipStation sync (every 5 min)..."
python src/unified_shipstation_sync.py 2>&1 &
UNIFIED_PID=$!

echo "Starting orders cleanup (daily)..."
python src/scheduled_cleanup.py 2>&1 &
CLEANUP_PID=$!

echo "Starting ShipStation units refresh..."
python src/shipstation_units_refresher.py 2>&1 &
UNITS_PID=$!

echo "Starting duplicate order scanner (every 15 min)..."
python src/scheduled_duplicate_scanner.py 2>&1 &
DUP_PID=$!

echo "Starting lot mismatch scanner (every 15 min)..."
python src/scheduled_lot_mismatch_scanner.py 2>&1 &
LOT_PID=$!

echo "Starting stuck workflow detector (every 15 min)..."
python src/scheduled_stuck_workflow_detector.py 2>&1 &
STUCK_PID=$!

# Give background processes a moment to start
sleep 1

echo "================================================"
echo "$(date '+%Y-%m-%d %H:%M:%S') - Background automation workflows started"
echo "   - XML Import: PID $XML_PID"
echo "   - ShipStation Upload: PID $UPLOAD_PID"
echo "   - Unified ShipStation Sync: PID $UNIFIED_PID"
echo "   - Cleanup: PID $CLEANUP_PID"
echo "   - Units Refresh: PID $UNITS_PID"
echo "   - Duplicate Scanner: PID $DUP_PID"
echo "   - Lot Mismatch Scanner: PID $LOT_PID"
echo "   - Stuck Workflow Detector: PID $STUCK_PID"
echo "   - Weekly Reporter: MANUAL (EOW button)"
echo "================================================"
echo ""
echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting dashboard server on port ${PORT:-5000}..."
echo ""

# Start Flask dashboard (foreground - this keeps the container alive)
# Use PORT env var if set, otherwise default to 5000
export FLASK_PORT=${PORT:-5000}
exec python app.py

# If Flask exits, kill background processes
echo "$(date '+%Y-%m-%d %H:%M:%S') - Dashboard stopped, shutting down background processes..."
kill $XML_PID $UPLOAD_PID $UNIFIED_PID $CLEANUP_PID $UNITS_PID $DUP_PID $LOT_PID $STUCK_PID 2>/dev/null
