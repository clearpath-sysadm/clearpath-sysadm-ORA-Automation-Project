#!/bin/bash
# Oracare Fulfillment - Startup Script
# Launches all automation workflows and dashboard server

# Don't use set -e as background processes may exit/restart independently

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

echo "Starting unified ShipStation sync (4x daily: 6:00 AM, 12:00 PM, 12:30 PM, 3:00 PM CT)..."
python src/unified_shipstation_sync.py 2>&1 &
UNIFIED_PID=$!

echo "Starting orders cleanup (daily)..."
python src/scheduled_cleanup.py 2>&1 &
CLEANUP_PID=$!

echo "Starting ShipStation units refresh..."
python src/shipstation_units_refresher.py 2>&1 &
UNITS_PID=$!

echo "Starting lot tagger (6:00 AM and 12:00 PM CDT, with startup catch-up)..."
python src/scheduled_lot_tagger.py 2>&1 &
LOT_TAGGER_PID=$!

echo "Starting batch processor (12:00 PM CT on business days)..."
python src/scheduled_batch_processor.py 2>&1 &
BATCH_PID=$!

# Give background processes a moment to start
sleep 1

echo "================================================"
echo "$(date '+%Y-%m-%d %H:%M:%S') - Background automation workflows started"
echo "   - Unified ShipStation Sync: PID $UNIFIED_PID"
echo "   - Cleanup: PID $CLEANUP_PID"
echo "   - Units Refresh: PID $UNITS_PID"
echo "   - Lot Tagger: PID $LOT_TAGGER_PID"
echo "   - Batch Processor: PID $BATCH_PID"
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
kill $UNIFIED_PID $CLEANUP_PID $UNITS_PID $LOT_TAGGER_PID 2>/dev/null
