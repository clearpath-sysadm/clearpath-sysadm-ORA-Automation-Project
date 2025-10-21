#!/bin/bash
# ORA Business Automation - Startup Script
# Launches all automation workflows and dashboard server

echo "🚀 Starting ORA Business Automation System..."
echo "================================================"

# Start background automation workflows
echo "Starting XML import scheduler (polling every 5 min)..."
python src/scheduled_xml_import.py &
XML_PID=$!

echo "Starting ShipStation upload (polling every 5 min)..."
python src/scheduled_shipstation_upload.py &
UPLOAD_PID=$!

echo "Starting unified ShipStation sync (every 5 min)..."
python src/unified_shipstation_sync.py &
UNIFIED_PID=$!

echo "Starting orders cleanup (daily)..."
python src/scheduled_cleanup.py &
CLEANUP_PID=$!

echo "Starting ShipStation units refresh..."
python src/shipstation_units_refresher.py &
UNITS_PID=$!

echo "Starting duplicate order scanner (every 15 min)..."
python src/scheduled_duplicate_scanner.py &
DUP_PID=$!

echo "Starting lot mismatch scanner (every 15 min)..."
python src/scheduled_lot_mismatch_scanner.py &
LOT_PID=$!

# Weekly reporter is now manual (triggered by EOW button)
# echo "Starting weekly reporter..."
# DEV_MODE=1 python src/weekly_reporter.py &
# REPORTER_PID=$!

# Give background processes a moment to start
sleep 2

echo "================================================"
echo "✅ Background automation workflows started"
echo "   - XML Import: PID $XML_PID"
echo "   - ShipStation Upload: PID $UPLOAD_PID"
echo "   - Unified ShipStation Sync: PID $UNIFIED_PID"
echo "   - Cleanup: PID $CLEANUP_PID"
echo "   - Units Refresh: PID $UNITS_PID"
echo "   - Duplicate Scanner: PID $DUP_PID"
echo "   - Lot Mismatch Scanner: PID $LOT_PID"
echo "   - Weekly Reporter: MANUAL (EOW button)"
echo "================================================"
echo ""
echo "🌐 Starting dashboard server on port 5000..."
echo ""

# Start Flask dashboard (foreground - this keeps the container alive)
python app.py

# If Flask exits, kill background processes
echo "⚠️  Dashboard stopped, shutting down background processes..."
kill $XML_PID $UPLOAD_PID $UNIFIED_PID $CLEANUP_PID $UNITS_PID $DUP_PID $LOT_PID 2>/dev/null
