#!/bin/bash
# ORA Business Automation - Startup Script
# Launches all automation workflows and dashboard server

echo "🚀 Starting ORA Business Automation System..."
echo "================================================"

# Start background automation workflows
echo "Starting XML import scheduler (polling every 5 min)..."
python src/scheduled_xml_import.py &
XML_PID=$!

echo "Starting ShipStation status sync (hourly)..."
python src/scheduled_status_sync.py &
STATUS_PID=$!

echo "Starting manual order sync (hourly)..."
python src/scheduled_manual_sync.py &
MANUAL_PID=$!

echo "Starting orders cleanup (daily)..."
python src/scheduled_cleanup.py &
CLEANUP_PID=$!

echo "Starting ShipStation units refresh..."
python src/shipstation_units_refresher.py &
UNITS_PID=$!

echo "Starting weekly reporter..."
DEV_MODE=1 python src/weekly_reporter.py &
REPORTER_PID=$!

# Give background processes a moment to start
sleep 2

echo "================================================"
echo "✅ Background automation workflows started"
echo "   - XML Import: PID $XML_PID"
echo "   - Status Sync: PID $STATUS_PID"
echo "   - Manual Orders: PID $MANUAL_PID"
echo "   - Cleanup: PID $CLEANUP_PID"
echo "   - Units Refresh: PID $UNITS_PID"
echo "   - Weekly Reporter: PID $REPORTER_PID"
echo "================================================"
echo ""
echo "🌐 Starting dashboard server on port 5000..."
echo ""

# Start Flask dashboard (foreground - this keeps the container alive)
python app.py

# If Flask exits, kill background processes
echo "⚠️  Dashboard stopped, shutting down background processes..."
kill $XML_PID $STATUS_PID $MANUAL_PID $CLEANUP_PID $UNITS_PID $REPORTER_PID 2>/dev/null
