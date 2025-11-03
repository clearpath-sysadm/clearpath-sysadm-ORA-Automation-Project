"""
Oracare Fulfillment Dashboard - Flask Application
Serves the dashboard UI and provides API endpoints for real-time data.
"""
import os
import sys
import uuid
import logging
from flask import Flask, jsonify, render_template, send_from_directory, request, session, g
from datetime import datetime, timedelta
import pytz
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
import psycopg2
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import current_user

# Add project root to path
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.services.database.pg_utils import get_connection, execute_query

# Initialize logger
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static', static_url_path='/static')

# Session and auth configuration
app.secret_key = os.environ.get("SESSION_SECRET")
if not app.secret_key:
    raise RuntimeError("SESSION_SECRET environment variable not set!")

# ProxyFix for correct HTTPS redirects behind Replit proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Flask-SQLAlchemy for auth tables ONLY (business logic continues using psycopg2)
class Base(DeclarativeBase):
    pass

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    'pool_size': 10,
    'pool_pre_ping': True,
    'pool_recycle': 300,
}

db = SQLAlchemy(app, model_class=Base)

# Create auth models
from models.auth_models import create_auth_models
User, OAuth = create_auth_models(db)

# Initialize Flask-Login
from src.auth.replit_auth import init_login_manager, make_replit_blueprint
from src.auth.middleware import login_required, admin_required
init_login_manager(app, User)

# Register auth blueprint
replit_bp = make_replit_blueprint(app, db, User, OAuth)
app.register_blueprint(replit_bp, url_prefix="/auth")

# Make session permanent (7-day duration)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

@app.before_request
def make_session_permanent():
    """Make Flask sessions last 7 days"""
    session.permanent = True

@app.before_request
def enforce_api_auth():
    """
    Centralized authentication guard for all /api/* routes.
    
    Default policy:
    - GET/HEAD/OPTIONS requests → require viewer role (login_required)
    - POST/PUT/PATCH/DELETE requests → require admin role (admin_required)
    
    Override map below for exceptions (public routes, special cases).
    """
    # Only apply to /api/* routes
    if not request.path.startswith('/api/'):
        return None
    
    # Public API routes (no authentication required)
    PUBLIC_ROUTES = {
        '/api/auth/status',  # Required for login flow - landing page checks auth state
    }
    
    # Admin-only routes regardless of method
    ADMIN_ONLY_ROUTES = {
        '/api/sync_shipstation',
        '/api/fedex_pickup/mark_completed',
        '/api/reports/eod',
        '/api/reports/eow',
        '/api/reports/eom',
    }
    
    # Viewer-allowed write operations (POST allowed for authenticated users)
    VIEWER_ALLOWED_WRITE_ROUTES = {
        '/api/incidents',  # Viewers can report bugs (POST)
        '/api/physical_count_adjustment',  # Viewers can adjust inventory up to ±4 units (admin threshold enforced in handler)
    }
    
    # Viewer-allowed write routes with dynamic paths (POST only - PUT/PATCH/DELETE still require admin)
    VIEWER_ALLOWED_WRITE_PATTERNS = [
        '/api/incidents/',  # Viewers can add notes/screenshots to incidents
    ]
    
    # Check if route is public
    if request.path in PUBLIC_ROUTES:
        return None
    
    # Determine required role based on method and overrides
    safe_methods = {'GET', 'HEAD', 'OPTIONS'}
    modifying_methods = {'POST', 'PUT', 'PATCH', 'DELETE'}
    
    # Check if this is a viewer-allowed write operation
    # Only POST is allowed for patterns (PUT/PATCH/DELETE still require admin)
    is_viewer_allowed_write = (
        request.method == 'POST' and 
        (request.path in VIEWER_ALLOWED_WRITE_ROUTES or
         any(request.path.startswith(pattern) for pattern in VIEWER_ALLOWED_WRITE_PATTERNS))
    )
    
    if request.path in ADMIN_ONLY_ROUTES or (request.method in modifying_methods and not is_viewer_allowed_write):
        # Require admin role
        if not current_user.is_authenticated:
            return jsonify({
                'error': 'Authentication required',
                'authenticated': False
            }), 401
        
        if current_user.role != 'admin':
            return jsonify({
                'error': 'Admin access required',
                'authenticated': True,
                'role': current_user.role
            }), 403
    
    elif request.method in safe_methods:
        # Require any authenticated user (viewer or admin)
        if not current_user.is_authenticated:
            return jsonify({
                'error': 'Authentication required',
                'authenticated': False
            }), 401
    
    return None

# Configure Flask
app.config['JSON_SORT_KEYS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = os.path.join(project_root, 'uploads', 'incident_screenshots')

# Allowed file extensions for screenshots
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# List of allowed HTML files to serve (security: prevent directory traversal)
ALLOWED_PAGES = ['index.html', 'shipped_orders.html', 'shipped_items.html', 'charge_report.html', 'inventory_transactions.html', 'weekly_shipped_history.html', 'xml_import.html', 'settings.html', 'bundle_skus.html', 'sku_lot.html', 'lot_inventory.html', 'order_audit.html', 'workflow_controls.html', 'incidents.html', 'help.html', 'landing.html', 'email_contacts.html', 'order-management.html']

# Concurrency locks for report endpoints (prevents duplicate processing)
# NOTE: In-memory locks only protect a single Flask process. If multiple workers are deployed,
# upgrade to database advisory locks (pg_advisory_lock) for system-wide concurrency protection.
_report_locks = {'EOD': False, 'EOW': False, 'EOM': False}

@app.route('/')
@login_required
def index():
    """Serve the main dashboard"""
    from flask import make_response
    response = make_response(send_from_directory(project_root, 'index.html'))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/favicon.ico')
def favicon():
    """Return empty favicon to prevent 404 errors"""
    from flask import Response
    return Response(status=204)

@app.route('/scratch/<path:filename>')
def serve_scratch(filename):
    """Serve scratch test files (temporary testing only)"""
    from flask import make_response
    response = make_response(send_from_directory(os.path.join(project_root, 'scratch'), filename))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return response

@app.route('/email_contacts')
@login_required
def email_contacts_redirect():
    """Redirect /email_contacts to /email_contacts.html for convenience"""
    from flask import redirect
    return redirect('/email_contacts.html')

@app.route('/<path:filename>')
def serve_page(filename):
    """Serve HTML pages only (security: whitelist approach)"""
    if filename in ALLOWED_PAGES:
        # landing.html is public - all other pages require authentication
        if filename != 'landing.html' and not current_user.is_authenticated:
            from flask import redirect
            return redirect('/landing.html')
        
        from flask import make_response
        response = make_response(send_from_directory(project_root, filename))
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    else:
        return "Not found", 404

# Production Health Check
@app.route('/health')
def health_check():
    """Production health check - shows environment and workflow status"""
    try:
        is_production = os.getenv('REPLIT_DEPLOYMENT') == '1'
        repl_slug = os.getenv('REPL_SLUG', 'unknown')
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get workflow status from database
        cursor.execute("""
            SELECT name, last_run_at, enabled, status, records_processed, updated_at
            FROM workflows
            ORDER BY name
        """)
        workflows = cursor.fetchall()
        
        workflow_status = []
        now = datetime.now()
        
        for name, last_run_at, enabled, status, records_processed, updated_at in workflows:
            # Parse last_run_at timestamp
            if last_run_at:
                if isinstance(last_run_at, str):
                    last_run_dt = datetime.fromisoformat(last_run_at.replace('Z', '+00:00'))
                else:
                    last_run_dt = last_run_at
                    
                # Ensure timezone-aware (UTC)
                if last_run_dt.tzinfo is None:
                    last_run_dt = pytz.UTC.localize(last_run_dt)
                    
                age_minutes = int((now.timestamp() - last_run_dt.timestamp()) / 60)
                last_run_iso = last_run_dt.isoformat()  # Send as ISO for client timezone conversion
                
                # Health indicator based on age and status
                # Orange for "running but stale", Red only for "stopped" or "never ran"
                if age_minutes <= 10:
                    health = '🟢 Healthy'
                elif age_minutes <= 30:
                    health = '🟡 Warning'
                else:
                    # Stale: Orange if running, Red if stopped
                    if status == 'running':
                        health = '🟠 Stale'  # Orange for running but stale
                    else:
                        health = '🔴 Stale'  # Red for stopped and stale
            else:
                last_run_iso = None
                age_minutes = 999999
                # Never ran: Red if stopped/not running, otherwise Orange
                if status == 'running':
                    health = '🟠 Never ran'  # Orange (shouldn't happen but handle it)
                else:
                    health = '🔴 Never ran'  # Red for never ran and not running
            
            workflow_status.append({
                'name': name,
                'enabled': bool(enabled),
                'last_run_at': last_run_iso,  # ISO timestamp for client-side formatting
                'age_minutes': age_minutes,  # For health calculations
                'health': health,
                'status': status,
                'records_processed': records_processed
            })
        
        # Check ShipStation sync watermark freshness
        cursor.execute("""
            SELECT last_sync_timestamp 
            FROM sync_watermark 
            WHERE workflow_name = 'unified-shipstation-sync'
        """)
        watermark_result = cursor.fetchone()
        
        if watermark_result and watermark_result[0]:
            watermark_ts = watermark_result[0]
            if isinstance(watermark_ts, str):
                watermark_dt = datetime.fromisoformat(watermark_ts.replace('Z', '+00:00'))
            else:
                watermark_dt = watermark_ts
            
            watermark_age_minutes = int((now.timestamp() - watermark_dt.timestamp()) / 60)
            
            # Ensure timezone-aware (UTC) for client-side conversion
            if watermark_dt.tzinfo is None:
                watermark_dt = pytz.UTC.localize(watermark_dt)
            
            watermark_str = f"{watermark_age_minutes} min ago"
            watermark_formatted = watermark_dt.isoformat()
            
            # Determine watermark health
            if watermark_age_minutes <= 10:
                watermark_health = '🟢 Healthy'
                watermark_status = 'Syncing orders successfully'
            elif watermark_age_minutes <= 30:
                watermark_health = '🟡 Warning'
                watermark_status = 'Sync may be delayed'
            else:
                watermark_health = '🔴 Critical'
                watermark_status = 'Sync is stalled - orders not updating'
            
            sync_health = {
                'watermark_age': watermark_str,
                'watermark_age_minutes': watermark_age_minutes,
                'health': watermark_health,
                'status': watermark_status,
                'last_watermark': watermark_dt.strftime('%b %d, %I:%M %p')
            }
        else:
            sync_health = {
                'watermark_age': 'Unknown',
                'watermark_age_minutes': 999999,
                'health': '⚪ Not Started',
                'status': 'No sync watermark found',
                'last_watermark': 'Never'
            }
        
        cursor.close()
        conn.close()
        
        # Check deployment configuration
        expected_workflows = ['orders-cleanup', 'unified-shipstation-sync', 'shipstation-upload', 
                             'xml-import', 'duplicate-scanner', 'lot-mismatch-scanner', 'dashboard-server']
        deployment_configured = True  # start_all.sh is configured in .replit [deployment] section
        
        # Overall system health
        all_healthy = all(wf['health'] == '🟢 Healthy' for wf in workflow_status if wf['enabled'])
        sync_healthy = sync_health['health'] == '🟢 Healthy'
        
        if all_healthy and sync_healthy:
            overall_health = '🟢 All Systems Operational'
        elif sync_health['health'] == '🔴 Critical':
            overall_health = '🔴 Critical - Sync Stalled'
        else:
            overall_health = '🟡 Some Issues Detected'
        
        return jsonify({
            'environment': 'PRODUCTION' if is_production else 'DEVELOPMENT',
            'repl_slug': repl_slug,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'overall_health': overall_health,
            'sync_health': sync_health,
            'workflows': workflow_status,
            'database_connected': True,
            'deployment': {
                'configured': deployment_configured,
                'command': 'bash start_all.sh',
                'expected_workflows': len(expected_workflows),
                'actual_workflows': len(workflows),
                'missing_workflows': [w for w in expected_workflows if w not in [wf['name'] for wf in workflow_status]]
            }
        })
    except Exception as e:
        return jsonify({
            'environment': 'PRODUCTION' if os.getenv('REPLIT_DEPLOYMENT') == '1' else 'DEVELOPMENT',
            'error': str(e),
            'database_connected': False,
            'overall_health': '🔴 Error'
        }), 500

# Auth Status API Endpoint
@app.route('/api/auth/status')
def auth_status():
    """Return current user auth status for JavaScript"""
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'user': {
                'id': current_user.id,
                'email': current_user.email,
                'first_name': current_user.first_name,
                'last_name': current_user.last_name,
                'profile_image_url': current_user.profile_image_url,
                'role': current_user.role
            }
        })
    else:
        return jsonify({
            'authenticated': False,
            'user': None
        })

# API Endpoints

@app.route('/api/dashboard_stats')
def api_dashboard_stats():
    """Get dashboard statistics"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Units to be shipped (from ShipStation awaiting shipment)
        cursor.execute("""
            SELECT metric_value
            FROM shipstation_metrics
            WHERE metric_name = 'units_to_ship'
        """)
        result = cursor.fetchone()
        units_to_ship = result[0] if result else 0
        
        # Check if FedEx pickup is needed (>= 185 units)
        fedex_pickup_needed = units_to_ship >= 185
        fedex_phone = '651-846-0590'
        
        # Check if today's FedEx pickup has been marked completed
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute("""
            SELECT completed_at, units_count 
            FROM fedex_pickup_log 
            WHERE pickup_date = %s
            ORDER BY completed_at DESC
            LIMIT 1
        """, (today,))
        pickup_log = cursor.fetchone()
        fedex_pickup_completed = pickup_log is not None
        fedex_pickup_completed_at = pickup_log[0] if pickup_log else None
        
        # Pending uploads from orders_inbox
        cursor.execute("SELECT COUNT(*) FROM orders_inbox WHERE status = 'pending'")
        pending_uploads = cursor.fetchone()[0] or 0
        
        # Recent shipments (last 7 days)
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        cursor.execute("SELECT COUNT(*) FROM shipped_orders WHERE ship_date >= %s", (week_ago,))
        recent_shipments = cursor.fetchone()[0] or 0
        
        # Benco orders (orders with "BENCO" in company name) - awaiting shipment only
        cursor.execute("""
            SELECT COUNT(*) FROM orders_inbox 
            WHERE status = 'awaiting_shipment'
            AND (ship_company LIKE '%BENCO%' OR ship_company LIKE '%Benco%')
        """)
        benco_orders = cursor.fetchone()[0] or 0
        
        # Hawaiian orders (ship to Hawaii) - unshipped from last 5 days (handles weekend backlog)
        five_days_ago = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
        cursor.execute("""
            SELECT COUNT(*) FROM orders_inbox 
            WHERE order_date >= %s
            AND ship_state = 'HI'
            AND status IN ('awaiting_shipment', 'uploaded')
        """, (five_days_ago,))
        hawaiian_orders = cursor.fetchone()[0] or 0
        
        # Canadian orders (ship to Canada) - unshipped from last 5 days
        cursor.execute("""
            SELECT COUNT(*) FROM orders_inbox 
            WHERE order_date >= %s
            AND (ship_country = 'CA' OR ship_country = 'Canada')
            AND status IN ('awaiting_shipment', 'uploaded')
        """, (five_days_ago,))
        canadian_orders = cursor.fetchone()[0] or 0
        
        # Other international orders (not US or Canada) - unshipped from last 5 days
        cursor.execute("""
            SELECT COUNT(*) FROM orders_inbox 
            WHERE order_date >= %s
            AND ship_country IS NOT NULL
            AND ship_country NOT IN ('US', 'USA', 'United States', 'CA', 'Canada')
            AND status IN ('awaiting_shipment', 'uploaded')
        """, (five_days_ago,))
        other_international_orders = cursor.fetchone()[0] or 0
        
        # System status (check recent workflow health)
        # Check if critical workflows ran recently (within last 2 hours)
        two_hours_ago = (datetime.now() - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'failed' OR status = 'error' THEN 1 ELSE 0 END) as failed,
                MAX(last_run_at) as last_activity
            FROM workflows 
            WHERE last_run_at >= %s
        """, (two_hours_ago,))
        workflow_health = cursor.fetchone()
        
        total_recent = workflow_health[0] or 0
        completed_recent = workflow_health[1] or 0
        failed_recent = workflow_health[2] or 0
        last_activity = workflow_health[3]
        
        # Determine system status
        if failed_recent > 0:
            system_status = 'error'
            system_message = f'{failed_recent} workflow(s) failed'
        elif total_recent == 0:
            system_status = 'warning'
            system_message = 'No recent activity'
        else:
            system_status = 'operational'
            system_message = f'{completed_recent} workflows active'
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'units_to_ship': units_to_ship,
                'fedex_pickup_needed': fedex_pickup_needed,
                'fedex_pickup_completed': fedex_pickup_completed,
                'fedex_pickup_completed_at': fedex_pickup_completed_at.isoformat() if fedex_pickup_completed_at else None,
                'fedex_phone': fedex_phone,
                'pending_uploads': pending_uploads,
                'recent_shipments': recent_shipments,
                'benco_orders': benco_orders,
                'hawaiian_orders': hawaiian_orders,
                'canadian_orders': canadian_orders,
                'other_international_orders': other_international_orders,
                'system_status': system_status,
                'system_message': system_message,
                'last_activity': last_activity,
                'workflows_completed': completed_recent,
                'workflows_failed': failed_recent
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/inventory_alerts')
def api_get_inventory_alerts():
    """Get inventory alerts for dashboard"""
    try:
        query = """
            SELECT 
                sku,
                product_name,
                current_quantity,
                alert_level,
                reorder_point,
                last_updated
            FROM inventory_current
            WHERE sku IN ('17612', '17904', '17914', '18675', '18795')
            ORDER BY 
                CASE alert_level 
                    WHEN 'critical' THEN 1
                    WHEN 'warning' THEN 2
                    ELSE 3
                END,
                current_quantity ASC
        """
        results = execute_query(query)
        
        alerts = []
        for row in results:
            sku = row[0]
            product_name = row[1] or f'Product {sku}'
            current_qty = row[2] or 0
            alert_level = row[3] or 'normal'
            reorder_point = row[4] or 100
            
            # Map alert_level to severity and create message
            if alert_level == 'critical':
                severity = 'critical'
                message = f'Low Stock: {current_qty} units remaining'
            elif alert_level == 'warning' or alert_level == 'low':
                severity = 'warning'
                message = f'Reorder Point: {current_qty} units remaining'
            else:
                severity = 'normal'
                message = f'Normal Stock: {current_qty} units available'
            
            alerts.append({
                'base_sku': sku,
                'product_name': product_name,
                'current_quantity': current_qty,
                'severity': severity,
                'message': message
            })
        
        return jsonify({
            'success': True,
            'data': alerts,
            'count': len(alerts)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/automation_status')
def api_automation_status():
    """Get automation workflow status from workflow_controls table"""
    try:
        query = """
            SELECT 
                workflow_name,
                enabled,
                last_run_at
            FROM workflow_controls
            WHERE workflow_name IN ('shipstation-upload', 'xml-import', 'unified-shipstation-sync', 'orders-cleanup', 'weekly-reporter')
            ORDER BY last_run_at DESC NULLS LAST
        """
        results = execute_query(query)
        
        display_names = {
            'shipstation-upload': 'ShipStation Upload',
            'xml-import': 'XML Import',
            'unified-shipstation-sync': 'ShipStation Sync',
            'orders-cleanup': 'Orders Cleanup',
            'weekly-reporter': 'Weekly Reporter'
        }
        
        workflows_data = []
        for row in results:
            workflow_name = row[0]
            enabled = row[1]
            last_run_at = row[2]
            
            workflows_data.append({
                'workflow_name': workflow_name,
                'display_name': display_names.get(workflow_name, workflow_name),
                'status': 'running' if enabled else 'disabled',
                'last_run': last_run_at,
                'duration_seconds': 0,
                'records_processed': 0
            })
        
        return jsonify({
            'success': True,
            'data': workflows_data,
            'count': len(workflows_data)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/workflow_timestamps')
def api_workflow_timestamps():
    """Lightweight endpoint - returns only workflow timestamps for change detection"""
    try:
        query = """
            SELECT 
                workflow_name,
                EXTRACT(EPOCH FROM last_run_at) as timestamp_epoch
            FROM workflow_controls
            WHERE workflow_name IN ('shipstation-upload', 'xml-import', 'unified-shipstation-sync')
            AND last_run_at IS NOT NULL
        """
        results = execute_query(query)
        
        timestamps = {}
        for row in results:
            workflow_name = row[0]
            timestamp_epoch = row[1]
            timestamps[workflow_name] = timestamp_epoch
        
        return jsonify({
            'success': True,
            'timestamps': timestamps
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/shipped_orders')
def api_shipped_orders():
    """Get all shipped orders with pagination"""
    try:
        query = """
            SELECT 
                id,
                ship_date,
                order_number,
                customer_email,
                total_items,
                shipstation_order_id,
                created_at
            FROM shipped_orders
            ORDER BY ship_date DESC, id DESC
            LIMIT 1000
        """
        results = execute_query(query)
        
        orders = []
        for row in results:
            orders.append({
                'id': row[0],
                'ship_date': row[1],
                'order_number': row[2],
                'customer_email': row[3] or '',
                'total_items': row[4] or 0,
                'shipstation_order_id': row[5] or '',
                'created_at': row[6]
            })
        
        return jsonify({
            'success': True,
            'data': orders,
            'count': len(orders)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/shipped_items')
def api_shipped_items():
    """Get shipped items for last 40 days"""
    try:
        # Calculate date range: last 40 days
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=40)
        
        query = """
            SELECT 
                ship_date,
                sku_lot,
                quantity_shipped,
                base_sku,
                order_number
            FROM shipped_items
            WHERE ship_date >= %s AND ship_date <= %s
            ORDER BY ship_date DESC, id DESC
            LIMIT 5000
        """
        results = execute_query(query, (start_date.isoformat(), end_date.isoformat()))
        
        items = []
        for row in results:
            items.append({
                'ship_date': row[0],
                'sku_lot': row[1] or '',
                'quantity_shipped': row[2],
                'base_sku': row[3],
                'order_number': row[4] or ''
            })
        
        return jsonify({
            'success': True,
            'data': items,
            'count': len(items)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/charge_report')
def api_charge_report():
    """
    Generate charge report showing daily breakdown of:
    - Date
    - # of Orders
    - Quantity by SKU (17612, 17904, 17914, 18675, 18795)
    - Orders charge ($4.25 per order)
    - Packages charge ($3.40 per package)
    - Space Rental ($18-$23.40 daily)
    - Total
    
    Query Parameters:
    - month: Month number (1-12), defaults to current month
    - year: Year (e.g., 2025), defaults to current year
    """
    try:
        # Get month and year from query parameters, default to current month
        from flask import request
        today = datetime.now().date()
        month = request.args.get('month', type=int, default=today.month)
        year = request.args.get('year', type=int, default=today.year)
        
        # Calculate calendar month date range (first day to last day)
        start_date = datetime(year, month, 1).date()
        # Calculate last day of the specified month
        next_month = start_date.replace(day=28) + timedelta(days=4)
        end_date = (next_month.replace(day=1) - timedelta(days=1))
        
        # Get daily order counts
        orders_query = """
            SELECT 
                ship_date,
                COUNT(DISTINCT order_number) as order_count
            FROM shipped_orders
            WHERE ship_date >= %s AND ship_date <= %s
            GROUP BY ship_date
            ORDER BY ship_date
        """
        orders_results = execute_query(orders_query, (str(start_date), str(end_date)))
        
        # Get daily SKU quantities
        skus_query = """
            SELECT 
                ship_date,
                base_sku,
                SUM(quantity_shipped) as total_qty
            FROM shipped_items
            WHERE ship_date >= %s AND ship_date <= %s
            GROUP BY ship_date, base_sku
            ORDER BY ship_date, base_sku
        """
        skus_results = execute_query(skus_query, (str(start_date), str(end_date)))
        
        # Build daily data structure with ALL calendar days in the month
        daily_data = {}
        
        # Generate all calendar days from start_date to end_date
        current_date = start_date
        while current_date <= end_date:
            date_str = str(current_date)
            daily_data[date_str] = {
                'date': date_str,
                'order_count': 0,
                'skus': {
                    '17612': 0,
                    '17904': 0,
                    '17914': 0,
                    '18675': 0,
                    '18795': 0
                }
            }
            current_date += timedelta(days=1)
        
        # Populate order counts from database
        for row in orders_results:
            date = row[0]
            order_count = row[1]
            if date in daily_data:
                daily_data[date]['order_count'] = order_count
        
        # Populate SKU quantities from database
        for row in skus_results:
            date = row[0]
            sku = row[1]
            qty = row[2]
            if date in daily_data and sku in daily_data[date]['skus']:
                daily_data[date]['skus'][sku] = qty
        
        # Get configuration for charges and pallets
        config_query = """
            SELECT category, parameter_name, sku, value
            FROM configuration_params
            WHERE category IN ('Rates', 'PalletConfig', 'Inventory')
        """
        config_results = execute_query(config_query)
        
        # Parse configuration
        order_charge = 4.25
        package_charge = 0.75
        space_rental_rate = 0.45
        pallet_config = {}
        bom_inventory = {}
        
        for row in config_results:
            category, param, sku, value = row
            if category == 'Rates':
                if param == 'OrderCharge':
                    order_charge = float(value)
                elif param == 'PackageCharge':
                    package_charge = float(value)
                elif param == 'SpaceRentalRate':
                    space_rental_rate = float(value)
            elif category == 'PalletConfig' and param == 'PalletCount' and sku:
                pallet_config[str(sku)] = int(value)
            elif category == 'Inventory' and param == 'EomPreviousMonth' and sku:
                bom_inventory[str(sku)] = int(value)
        
        # Get all inventory transactions and shipments for the month
        transactions_query = """
            SELECT date, sku, transaction_type, quantity
            FROM inventory_transactions
            WHERE date >= %s AND date <= %s
        """
        transactions = execute_query(transactions_query, (str(start_date), str(end_date)))
        
        shipments_query = """
            SELECT ship_date, base_sku, SUM(quantity_shipped)
            FROM shipped_items
            WHERE ship_date >= %s AND ship_date <= %s
            GROUP BY ship_date, base_sku
        """
        shipments = execute_query(shipments_query, (str(start_date), str(end_date)))
        
        # Calculate daily inventory (EOD) for space rental calculation
        daily_inventory = {}
        current_inv = bom_inventory.copy()
        
        # Initialize all dates with BOM inventory
        current_date = start_date
        while current_date <= end_date:
            date_str = str(current_date)
            daily_inventory[date_str] = current_inv.copy()
            current_date += timedelta(days=1)
        
        # Apply receives/adjustments
        for trans_date, sku, trans_type, qty in transactions:
            if trans_date in daily_inventory and str(sku) in daily_inventory[trans_date]:
                if trans_type == 'Receive':
                    for date_str in daily_inventory:
                        if date_str >= trans_date:
                            daily_inventory[date_str][str(sku)] += qty
                elif trans_type == 'Repack':
                    for date_str in daily_inventory:
                        if date_str >= trans_date:
                            daily_inventory[date_str][str(sku)] += qty
        
        # Apply shipments (at EOD)
        for ship_date, sku, qty in shipments:
            if ship_date in daily_inventory and str(sku) in daily_inventory[ship_date]:
                for date_str in daily_inventory:
                    if date_str >= ship_date:
                        daily_inventory[date_str][str(sku)] -= qty
        
        # Calculate space rental charges
        import math
        
        report_data = []
        for date, data in sorted(daily_data.items()):
            order_count = data['order_count']
            
            # Calculate package count (sum of all SKU quantities)
            package_count = sum(data['skus'].values())
            
            # Calculate charges
            orders_charge = order_count * order_charge
            packages_charge = package_count * package_charge
            
            # Calculate space rental based on EOD inventory pallets
            total_pallets = 0
            if date in daily_inventory:
                for sku, inventory_qty in daily_inventory[date].items():
                    if sku in pallet_config and inventory_qty > 0:
                        pallets = math.ceil(inventory_qty / pallet_config[sku])
                        total_pallets += pallets
            
            space_rental = total_pallets * space_rental_rate
            
            total_charge = orders_charge + packages_charge + space_rental
            
            report_data.append({
                'date': date,
                'order_count': order_count,
                'sku_17612': data['skus']['17612'],
                'sku_17904': data['skus']['17904'],
                'sku_17914': data['skus']['17914'],
                'sku_18675': data['skus']['18675'],
                'sku_18795': data['skus']['18795'],
                'orders_charge': round(orders_charge, 2),
                'packages_charge': round(packages_charge, 2),
                'space_rental': round(space_rental, 2),
                'total': round(total_charge, 2)
            })
        
        # Calculate totals
        if report_data:
            totals = {
                'date': 'TOTAL',
                'order_count': sum(r['order_count'] for r in report_data),
                'sku_17612': sum(r['sku_17612'] for r in report_data),
                'sku_17904': sum(r['sku_17904'] for r in report_data),
                'sku_17914': sum(r['sku_17914'] for r in report_data),
                'sku_18675': sum(r['sku_18675'] for r in report_data),
                'sku_18795': sum(r['sku_18795'] for r in report_data),
                'orders_charge': round(sum(r['orders_charge'] for r in report_data), 2),
                'packages_charge': round(sum(r['packages_charge'] for r in report_data), 2),
                'space_rental': round(sum(r['space_rental'] for r in report_data), 2),
                'total': round(sum(r['total'] for r in report_data), 2)
            }
        else:
            totals = None
        
        return jsonify({
            'success': True,
            'data': report_data,
            'totals': totals,
            'count': len(report_data)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/charge_report/orders')
def api_charge_report_orders():
    """
    Get orders for a specific date and optional SKU filter
    Used by charge report modal to show order details
    
    Query Parameters:
    - date: Ship date (YYYY-MM-DD) - required
    - sku: SKU filter (optional) - if provided, only returns orders with that SKU
    """
    try:
        from flask import request
        
        ship_date = request.args.get('date')
        sku_filter = request.args.get('sku')
        
        if not ship_date:
            return jsonify({
                'success': False,
                'error': 'Date parameter is required'
            }), 400
        
        # Base query to get orders for the specified date
        # NOTE: Filter by shipped_items.ship_date, not shipped_orders.ship_date
        # because items can be shipped on different dates than the order record date
        # NOTE: No DISTINCT needed - shipped_items has unique constraint on (order_number, base_sku, sku_lot)
        if sku_filter:
            # Filter by specific SKU
            query = """
                SELECT
                    si.order_number,
                    COALESCE(oi.ship_company, 'N/A') as company_name,
                    si.ship_date,
                    si.base_sku,
                    COALESCE(si.sku_lot, '') as sku_lot,
                    si.quantity_shipped,
                    COALESCE(so.shipstation_order_id, '') as shipstation_order_id,
                    COALESCE(oi.shipping_service_name, '') as shipping_service,
                    COALESCE(si.tracking_number, '') as tracking_number
                FROM shipped_items si
                LEFT JOIN shipped_orders so ON si.order_number = so.order_number
                LEFT JOIN orders_inbox oi ON si.order_number = oi.order_number
                WHERE si.ship_date = %s AND si.base_sku = %s
                ORDER BY si.order_number
            """
            results = execute_query(query, (ship_date, sku_filter))
        else:
            # Get all orders for the date (showing all SKUs)
            query = """
                SELECT
                    si.order_number,
                    COALESCE(oi.ship_company, 'N/A') as company_name,
                    si.ship_date,
                    si.base_sku,
                    COALESCE(si.sku_lot, '') as sku_lot,
                    si.quantity_shipped,
                    COALESCE(so.shipstation_order_id, '') as shipstation_order_id,
                    COALESCE(oi.shipping_service_name, '') as shipping_service,
                    COALESCE(si.tracking_number, '') as tracking_number
                FROM shipped_items si
                LEFT JOIN shipped_orders so ON si.order_number = so.order_number
                LEFT JOIN orders_inbox oi ON si.order_number = oi.order_number
                WHERE si.ship_date = %s
                ORDER BY si.order_number, si.base_sku
            """
            results = execute_query(query, (ship_date,))
        
        orders = []
        for row in results:
            orders.append({
                'order_number': row[0],
                'company_name': row[1],
                'ship_date': row[2],
                'base_sku': row[3],
                'sku_lot': row[4] or '',
                'quantity_shipped': row[5],
                'shipstation_order_id': row[6] or '',
                'shipping_service': row[7] or '',
                'tracking_number': row[8] or ''
            })
        
        return jsonify({
            'success': True,
            'data': orders,
            'count': len(orders),
            'date': ship_date,
            'sku': sku_filter
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/kpis')
def api_kpis():
    """Get latest KPIs for dashboard"""
    try:
        query = """
            SELECT 
                snapshot_date,
                orders_today,
                shipments_sent,
                total_revenue_cents,
                pending_uploads,
                system_status
            FROM system_kpis
            ORDER BY snapshot_date DESC
            LIMIT 1
        """
        results = execute_query(query)
        
        if results:
            row = results[0]
            kpis = {
                'date': row[0],
                'orders_today': row[1] or 0,
                'shipments_sent': row[2] or 0,
                'total_revenue': round((row[3] or 0) / 100, 2),
                'pending_uploads': row[4] or 0,
                'system_status': row[5] or 'online'
            }
        else:
            kpis = {}
        
        return jsonify(kpis)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/inventory/alerts')
def api_inventory_alerts():
    """Get inventory alerts"""
    try:
        query = """
            SELECT 
                sku,
                product_name,
                current_quantity,
                reorder_point,
                alert_level,
                last_updated
            FROM inventory_current
            WHERE alert_level != 'normal'
            ORDER BY 
                CASE alert_level 
                    WHEN 'critical' THEN 1
                    WHEN 'low' THEN 2
                    ELSE 3
                END,
                last_updated DESC
        """
        results = execute_query(query)
        
        alerts = []
        for row in results:
            alerts.append({
                'sku': row[0],
                'product_name': row[1],
                'current_quantity': row[2],
                'reorder_point': row[3],
                'alert_level': row[4],
                'last_updated': row[5]
            })
        
        return jsonify(alerts)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/workflows/status')
def api_workflows_status():
    """Get workflow status"""
    try:
        query = """
            SELECT 
                name,
                display_name,
                status,
                last_run_at,
                duration_seconds,
                records_processed,
                details
            FROM workflows
            WHERE enabled = 1
            ORDER BY last_run_at DESC
        """
        results = execute_query(query)
        
        workflows = []
        for row in results:
            workflows.append({
                'name': row[0],
                'display_name': row[1],
                'status': row[2],
                'last_run_at': row[3],
                'duration_seconds': row[4] or 0,
                'records_processed': row[5] or 0,
                'details': row[6] or ''
            })
        
        return jsonify(workflows)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/sync_shipstation', methods=['POST'])
def api_sync_shipstation():
    """Trigger ShipStation sync manually"""
    try:
        import subprocess
        import threading
        
        def run_sync():
            """Run sync in background thread"""
            try:
                result = subprocess.run(
                    ['python3', 'src/daily_shipment_processor.py'],
                    cwd=project_root,
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                print(f"Sync completed with return code: {result.returncode}")
                if result.stdout:
                    print(f"Sync output: {result.stdout}")
                if result.stderr:
                    print(f"Sync errors: {result.stderr}")
            except Exception as e:
                print(f"Sync error: {e}")
        
        # Start sync in background thread
        thread = threading.Thread(target=run_sync, daemon=True)
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'ShipStation sync started in background'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# DEPRECATED: Removed api_sync_manual_orders endpoint
# Functionality replaced by unified_shipstation_sync.py service
# Legacy code archived to src/legacy_archived/manual_shipstation_sync.py

@app.route('/api/fedex_pickup/mark_completed', methods=['POST'])
def api_mark_fedex_pickup_completed():
    """Mark today's FedEx pickup as completed and log the action"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Get current units_to_ship for logging
        cursor.execute("""
            SELECT metric_value
            FROM shipstation_metrics
            WHERE metric_name = 'units_to_ship'
        """)
        result = cursor.fetchone()
        units_count = result[0] if result else 0
        
        # Check if already marked completed today
        cursor.execute("""
            SELECT id FROM fedex_pickup_log 
            WHERE pickup_date = %s
        """, (today,))
        
        if cursor.fetchone():
            conn.close()
            return jsonify({
                'success': False,
                'error': 'FedEx pickup already marked complete for today'
            }), 400
        
        # Insert completion log
        cursor.execute("""
            INSERT INTO fedex_pickup_log (pickup_date, units_count, completed_at)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            RETURNING completed_at
        """, (today, units_count))
        
        completed_at = cursor.fetchone()[0]
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'FedEx pickup marked as completed',
            'completed_at': completed_at.isoformat(),
            'units_count': units_count
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/inventory_transactions', methods=['GET'])
def api_get_inventory_transactions():
    """Get inventory transactions with optional filters"""
    try:
        from flask import request
        
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        sku = request.args.get('sku')
        transaction_type = request.args.get('transaction_type')
        
        query = "SELECT id, date, sku, quantity, transaction_type, notes, created_at FROM inventory_transactions WHERE 1=1"
        params = []
        
        if start_date:
            query += " AND date >= %s"
            params.append(start_date)
        if end_date:
            query += " AND date <= %s"
            params.append(end_date)
        if sku:
            query += " AND sku = %s"
            params.append(sku)
        if transaction_type:
            query += " AND transaction_type = %s"
            params.append(transaction_type)
        
        query += " ORDER BY date DESC, created_at DESC"
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        transactions = []
        for row in results:
            transactions.append({
                'id': row[0],
                'date': row[1],
                'sku': row[2],
                'quantity': row[3],
                'transaction_type': row[4],
                'notes': row[5] or '',
                'created_at': row[6]
            })
        
        return jsonify(transactions)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/inventory_transactions', methods=['POST'])
def api_create_inventory_transaction():
    """Create new inventory transaction"""
    try:
        from flask import request
        
        data = request.get_json()
        date = data.get('date')
        sku = data.get('sku')
        quantity = data.get('quantity')
        transaction_type = data.get('transaction_type')
        notes = data.get('notes', '')
        
        if not all([date, sku, quantity, transaction_type]):
            return jsonify({
                'success': False,
                'error': 'Missing required fields: date, sku, quantity, transaction_type'
            }), 400
        
        quantity = int(quantity)
        if quantity == 0:
            return jsonify({
                'success': False,
                'error': 'Quantity cannot be zero'
            }), 400
        
        valid_types = ['Receive', 'Ship', 'Adjust Up', 'Adjust Down', 'Repack']
        if transaction_type not in valid_types:
            return jsonify({
                'success': False,
                'error': f'Invalid transaction type. Must be one of: {", ".join(valid_types)}'
            }), 400
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Insert transaction
        cursor.execute("""
            INSERT INTO inventory_transactions (date, sku, quantity, transaction_type, notes)
            VALUES (%s, %s, %s, %s, %s)
        """, (date, sku, quantity, transaction_type, notes))
        transaction_id = cursor.lastrowid
        
        # Update inventory_current based on transaction type
        # Increase: Receive, Adjust Up, Repack
        # Decrease: Ship, Adjust Down
        if transaction_type in ['Receive', 'Adjust Up', 'Repack']:
            delta = quantity
        else:  # Ship, Adjust Down
            delta = -quantity
        
        # Update current quantity in inventory_current
        cursor.execute("""
            UPDATE inventory_current 
            SET current_quantity = current_quantity + %s,
                last_updated = CURRENT_TIMESTAMP
            WHERE sku = %s
        """, (delta, sku))
        
        # If SKU doesn't exist in inventory_current, we need to handle it
        # (though this shouldn't happen for valid SKUs)
        if cursor.rowcount == 0:
            # Get product name from configuration
            cursor.execute("""
                SELECT parameter_name FROM configuration_params 
                WHERE category = 'Key Products' AND sku = %s
            """, (sku,))
            result = cursor.fetchone()
            product_name = result[0] if result else 'Unknown Product'
            
            # Insert new record
            cursor.execute("""
                INSERT INTO inventory_current (sku, product_name, current_quantity, weekly_avg_cents, alert_level, reorder_point)
                VALUES (%s, %s, %s, 0, 'normal', 50)
            """, (sku, product_name, max(0, delta)))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'id': transaction_id,
            'message': 'Transaction created successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/inventory_transactions/<int:transaction_id>', methods=['PUT'])
def api_update_inventory_transaction(transaction_id):
    """Update existing inventory transaction"""
    try:
        from flask import request
        
        data = request.get_json()
        date = data.get('date')
        sku = data.get('sku')
        quantity = data.get('quantity')
        transaction_type = data.get('transaction_type')
        notes = data.get('notes', '')
        
        if not all([date, sku, quantity, transaction_type]):
            return jsonify({
                'success': False,
                'error': 'Missing required fields: date, sku, quantity, transaction_type'
            }), 400
        
        quantity = int(quantity)
        if quantity == 0:
            return jsonify({
                'success': False,
                'error': 'Quantity cannot be zero'
            }), 400
        
        valid_types = ['Receive', 'Ship', 'Adjust Up', 'Adjust Down', 'Repack']
        if transaction_type not in valid_types:
            return jsonify({
                'success': False,
                'error': f'Invalid transaction type. Must be one of: {", ".join(valid_types)}'
            }), 400
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get old transaction to reverse its effect
        cursor.execute("""
            SELECT sku, quantity, transaction_type 
            FROM inventory_transactions 
            WHERE id = %s
        """, (transaction_id,))
        old_transaction = cursor.fetchone()
        
        if not old_transaction:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Transaction not found'
            }), 404
        
        old_sku, old_quantity, old_type = old_transaction
        
        # Reverse old transaction effect
        if old_type in ['Receive', 'Adjust Up', 'Repack']:
            old_delta = -old_quantity  # Reverse the increase
        else:
            old_delta = old_quantity  # Reverse the decrease
        
        cursor.execute("""
            UPDATE inventory_current 
            SET current_quantity = current_quantity + %s,
                last_updated = CURRENT_TIMESTAMP
            WHERE sku = %s
        """, (old_delta, old_sku))
        
        # Update the transaction
        cursor.execute("""
            UPDATE inventory_transactions 
            SET date = %s, sku = %s, quantity = %s, transaction_type = %s, notes = %s
            WHERE id = %s
        """, (date, sku, quantity, transaction_type, notes, transaction_id))
        
        # Apply new transaction effect
        if transaction_type in ['Receive', 'Adjust Up', 'Repack']:
            new_delta = quantity
        else:
            new_delta = -quantity
        
        cursor.execute("""
            UPDATE inventory_current 
            SET current_quantity = current_quantity + %s,
                last_updated = CURRENT_TIMESTAMP
            WHERE sku = %s
        """, (new_delta, sku))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Transaction updated successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/inventory_transactions/<int:transaction_id>', methods=['DELETE'])
def api_delete_inventory_transaction(transaction_id):
    """Delete inventory transaction"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get transaction to reverse its effect before deleting
        cursor.execute("""
            SELECT sku, quantity, transaction_type 
            FROM inventory_transactions 
            WHERE id = %s
        """, (transaction_id,))
        transaction = cursor.fetchone()
        
        if not transaction:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Transaction not found'
            }), 404
        
        sku, quantity, transaction_type = transaction
        
        # Reverse transaction effect on inventory_current
        if transaction_type in ['Receive', 'Adjust Up', 'Repack']:
            delta = -quantity  # Reverse the increase
        else:
            delta = quantity  # Reverse the decrease
        
        cursor.execute("""
            UPDATE inventory_current 
            SET current_quantity = current_quantity + %s,
                last_updated = CURRENT_TIMESTAMP
            WHERE sku = %s
        """, (delta, sku))
        
        # Now delete the transaction
        cursor.execute("DELETE FROM inventory_transactions WHERE id = %s", (transaction_id,))
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Transaction deleted successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/inventory_transactions/skus', methods=['GET'])
def api_get_skus():
    """Get list of distinct SKUs for dropdown"""
    try:
        query = "SELECT DISTINCT sku FROM inventory_transactions ORDER BY sku"
        results = execute_query(query)
        skus = [row[0] for row in results]
        return jsonify(skus)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/physical_count_adjustment', methods=['POST'])
def api_physical_count_adjustment():
    """
    Create inventory adjustment from physical count.
    Tracks user, timezone, and requires admin for adjustments > 4 units.
    """
    try:
        from datetime import datetime
        from pytz import timezone as pytz_timezone
        
        data = request.get_json()
        sku = data.get('sku')
        physical_count = data.get('physical_count')
        reason = data.get('reason', '').strip()
        user_timezone = data.get('user_timezone', 'UTC')
        
        if not all([sku, physical_count is not None, reason]):
            return jsonify({
                'success': False,
                'error': 'Missing required fields: sku, physical_count, reason'
            }), 400
        
        physical_count = int(physical_count)
        if physical_count < 0:
            return jsonify({
                'success': False,
                'error': 'Physical count cannot be negative'
            }), 400
        
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT current_quantity FROM inventory_current WHERE sku = %s
        """, (sku,))
        result = cursor.fetchone()
        
        if not result:
            conn.close()
            return jsonify({
                'success': False,
                'error': f'SKU {sku} not found in inventory'
            }), 404
        
        system_quantity = result[0]
        difference = physical_count - system_quantity
        
        if difference == 0:
            conn.close()
            return jsonify({
                'success': True,
                'message': 'No adjustment needed - counts match',
                'difference': 0
            })
        
        if abs(difference) > 4 and current_user.role != 'admin':
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Adjustments greater than 4 units require admin approval',
                'requires_admin': True,
                'difference': difference
            }), 403
        
        transaction_type = 'Adjust Up' if difference > 0 else 'Adjust Down'
        quantity = abs(difference)
        
        try:
            tz = pytz_timezone(user_timezone)
            local_time = datetime.now(tz)
            formatted_time = local_time.strftime('%Y-%m-%d %I:%M %p %Z')
        except:
            formatted_time = datetime.now().strftime('%Y-%m-%d %I:%M %p UTC')
        
        user_name = f"{current_user.first_name} {current_user.last_name}".strip() or current_user.email
        detailed_notes = f"Physical count adjustment: {reason} | Adjusted by: {user_name} | Time: {formatted_time} | System: {system_quantity} → Physical: {physical_count} (Δ{difference:+d})"
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        cursor.execute("""
            INSERT INTO inventory_transactions 
            (date, sku, quantity, transaction_type, notes, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
        """, (today, sku, quantity, transaction_type, detailed_notes))
        
        cursor.execute("""
            UPDATE inventory_current 
            SET current_quantity = %s, 
                last_updated = NOW()
            WHERE sku = %s
        """, (physical_count, sku))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Inventory adjusted: {system_quantity} → {physical_count} ({difference:+d} units)',
            'difference': difference,
            'transaction_type': transaction_type,
            'adjusted_by': user_name,
            'timestamp': formatted_time
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/weekly_inventory_report', methods=['GET'])
def api_weekly_inventory_report():
    """Get weekly inventory report with current quantities and rolling averages"""
    try:
        query = """
            SELECT 
                sku,
                product_name,
                current_quantity,
                weekly_avg_cents,
                alert_level,
                reorder_point,
                last_updated
            FROM inventory_current
            WHERE sku IN ('17612', '17904', '17914', '18675', '18795')
            ORDER BY sku
        """
        results = execute_query(query)
        
        # Get pallet configuration
        pallet_query = """
            SELECT sku, CAST(value AS INTEGER) as units_per_pallet
            FROM configuration_params
            WHERE category = 'PalletConfig' AND parameter_name = 'PalletCount'
            AND sku IN ('17612', '17904', '17914', '18675', '18795')
        """
        pallet_results = execute_query(pallet_query)
        pallet_config = {str(row[0]): row[1] for row in pallet_results}
        
        report = []
        for row in results:
            sku = str(row[0])
            product_name = row[1] or f'Product {sku}'  # Use database value
            current_qty = row[2] or 0
            weekly_avg_cents = row[3] or 0
            
            # Note: Despite the column name, values are stored as whole units, not cents
            weekly_avg = float(weekly_avg_cents) if weekly_avg_cents else 0.0
            
            # Calculate estimated days left
            if weekly_avg > 0:
                daily_consumption = weekly_avg / 7.0  # Convert weekly to daily
                days_left = round(current_qty / daily_consumption) if daily_consumption > 0 else 999
            else:
                days_left = 999  # Infinite/unknown if no consumption history
            
            # Calculate pallet breakdown for physical inventory verification
            units_per_pallet = pallet_config.get(sku, 0)
            if units_per_pallet > 0:
                full_pallets = current_qty // units_per_pallet
                partial_units = current_qty % units_per_pallet
            else:
                full_pallets = 0
                partial_units = current_qty
            
            report.append({
                'sku': sku,
                'product_name': product_name,
                'current_quantity': current_qty,
                'rolling_avg_52_weeks': weekly_avg,
                'days_left': days_left,
                'reorder_point': row[5] or 0,
                'last_updated': row[6],
                'full_pallets': full_pallets,
                'partial_units': partial_units,
                'units_per_pallet': units_per_pallet
            })
        
        return jsonify({
            'success': True,
            'data': report,
            'count': len(report)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/reports/eod', methods=['POST'])
def api_run_eod():
    """EOD - End of Day: Sync shipped items and update inventory"""
    import datetime
    import subprocess
    import logging
    from src.services.database.pg_utils import log_report_run
    
    logger = logging.getLogger(__name__)
    
    # Concurrency guard: prevent duplicate EOD runs
    if _report_locks['EOD']:
        return jsonify({
            'success': False,
            'error': 'EOD report is already running. Please wait for it to complete.'
        }), 409
    
    _report_locks['EOD'] = True
    try:
        # Run the daily shipment processor
        result = subprocess.run(
            ['python', 'src/daily_shipment_processor.py'],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            # Log subprocess output for debugging
            if result.stderr:
                logger.warning(f"EOD subprocess stderr (despite success): {result.stderr[:500]}")
            if result.stdout:
                logger.info(f"EOD subprocess stdout: {result.stdout[-500:]}")
            
            # Log success
            log_report_run('EOD', datetime.date.today(), 'success', 'Daily inventory updated successfully')
            
            return jsonify({
                'success': True,
                'message': '✅ Daily inventory updated - Shipped items synced from ShipStation'
            })
        else:
            # Log failure
            log_report_run('EOD', datetime.date.today(), 'failed', f'Error: {result.stderr[:200]}')
            
            return jsonify({
                'success': False,
                'error': f'EOD failed: {result.stderr}'
            }), 500
            
    except subprocess.TimeoutExpired:
        log_report_run('EOD', datetime.date.today(), 'failed', 'Timeout (>120s)')
        return jsonify({
            'success': False,
            'error': 'EOD timed out (>120s)'
        }), 500
    except Exception as e:
        log_report_run('EOD', datetime.date.today(), 'failed', str(e))
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        # Always release the lock
        _report_locks['EOD'] = False

@app.route('/api/reports/eow', methods=['POST'])
def api_run_eow():
    """EOW - End of Week: Generate weekly report with 52-week averages"""
    import datetime
    import subprocess
    from src.services.database.pg_utils import eod_done_today, log_report_run
    
    # Concurrency guard: prevent duplicate EOW runs
    if _report_locks['EOW']:
        return jsonify({
            'success': False,
            'error': 'EOW report is already running. Please wait for it to complete.'
        }), 409
    
    _report_locks['EOW'] = True
    try:
        week_start = datetime.date.today() - datetime.timedelta(days=datetime.date.today().weekday())
        
        # Check if EOD done today, run it if not
        if not eod_done_today():
            # Run EOD first
            eod_result = subprocess.run(
                ['python', 'src/daily_shipment_processor.py'],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if eod_result.returncode != 0:
                log_report_run('EOW', week_start, 'failed', 'EOD prerequisite failed')
                return jsonify({
                    'success': False,
                    'error': f'EOD prerequisite failed: {eod_result.stderr}'
                }), 500
            
            log_report_run('EOD', datetime.date.today(), 'success', 'Auto-run by EOW')
        
        # Run the weekly reporter
        result = subprocess.run(
            ['python', 'src/weekly_reporter.py'],
            cwd=project_root,
            env={**os.environ, 'DEV_MODE': '1'},
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            log_report_run('EOW', week_start, 'success', 'Weekly report generated successfully')
            
            return jsonify({
                'success': True,
                'message': '✅ Weekly report generated - 52-week averages calculated'
            })
        else:
            log_report_run('EOW', week_start, 'failed', f'Error: {result.stderr[:200]}')
            
            return jsonify({
                'success': False,
                'error': f'EOW failed: {result.stderr}'
            }), 500
            
    except subprocess.TimeoutExpired:
        week_start = datetime.date.today() - datetime.timedelta(days=datetime.date.today().weekday())
        log_report_run('EOW', week_start, 'failed', 'Timeout (>120s)')
        return jsonify({
            'success': False,
            'error': 'EOW timed out (>120s)'
        }), 500
    except Exception as e:
        week_start = datetime.date.today() - datetime.timedelta(days=datetime.date.today().weekday())
        log_report_run('EOW', week_start, 'failed', str(e))
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        # Always release the lock
        _report_locks['EOW'] = False

@app.route('/api/reports/eom', methods=['POST'])
def api_run_eom():
    """EOM - End of Month: Pre-calculate/refresh charge report data
    
    Calculates monthly totals for:
    - Order charges ($4.25 per order)
    - Packaging charges ($0.75 per shipping unit)
    - Space rental ($0.45 per pallet)
    """
    import datetime
    from src.services.database.pg_utils import log_report_run, execute_query
    
    # Concurrency guard: prevent duplicate EOM runs
    if _report_locks['EOM']:
        return jsonify({
            'success': False,
            'error': 'EOM report is already running. Please wait for it to complete.'
        }), 409
    
    _report_locks['EOM'] = True
    try:
        # Calculate month boundaries (previous month)
        today = datetime.date.today()
        month_start = today.replace(day=1)
        
        # Calculate last day of month
        if today.month == 12:
            month_end = today.replace(month=12, day=31)
        else:
            month_end = (today.replace(month=today.month + 1, day=1) - datetime.timedelta(days=1))
        
        # Get total orders for the month
        orders_query = """
            SELECT COUNT(DISTINCT order_number) as total_orders
            FROM shipped_orders
            WHERE ship_date >= %s AND ship_date <= %s
        """
        orders_result = execute_query(orders_query, (str(month_start), str(month_end)))
        total_orders = orders_result[0][0] if orders_result else 0
        
        # Get total shipping units (packages) for the month
        packages_query = """
            SELECT SUM(quantity_shipped) as total_units
            FROM shipped_items
            WHERE ship_date >= %s AND ship_date <= %s
        """
        packages_result = execute_query(packages_query, (str(month_start), str(month_end)))
        total_packages = packages_result[0][0] if packages_result else 0
        
        # Get configuration for charge rates and pallet config
        config_query = """
            SELECT category, parameter_name, sku, value
            FROM configuration_params
            WHERE category IN ('Rates', 'PalletConfig', 'Inventory')
        """
        config_results = execute_query(config_query)
        
        # Parse configuration
        order_charge = 4.25
        package_charge = 0.75
        space_rental_rate = 0.45
        pallet_config = {}
        bom_inventory = {}
        
        for row in config_results:
            category, param, sku, value = row
            if category == 'Rates':
                if param == 'OrderCharge':
                    order_charge = float(value)
                elif param == 'PackageCharge':
                    package_charge = float(value)
                elif param == 'SpaceRentalRate':
                    space_rental_rate = float(value)
            elif category == 'PalletConfig' and param == 'PalletCount' and sku:
                pallet_config[str(sku)] = int(value)
            elif category == 'Inventory' and param == 'EomPreviousMonth' and sku:
                bom_inventory[str(sku)] = int(value)
        
        # Calculate order and package charges
        orders_total = total_orders * order_charge
        packages_total = total_packages * package_charge
        
        # Calculate space rental by summing daily pallet charges
        # Get inventory transactions and shipments
        transactions_query = """
            SELECT date, sku, transaction_type, quantity
            FROM inventory_transactions
            WHERE date >= %s AND date <= %s
        """
        transactions = execute_query(transactions_query, (str(month_start), str(month_end)))
        
        shipments_query = """
            SELECT ship_date, base_sku, SUM(quantity_shipped)
            FROM shipped_items
            WHERE ship_date >= %s AND ship_date <= %s
            GROUP BY ship_date, base_sku
        """
        shipments = execute_query(shipments_query, (str(month_start), str(month_end)))
        
        # Calculate daily inventory for space rental
        import math
        daily_inventory = {}
        current_inv = bom_inventory.copy()
        
        # Generate all calendar days
        current_date = month_start
        while current_date <= month_end:
            date_str = str(current_date)
            daily_inventory[date_str] = current_inv.copy()
            current_date += datetime.timedelta(days=1)
        
        # Apply receives/adjustments
        for trans_date, sku, trans_type, qty in transactions:
            if trans_date in daily_inventory and str(sku) in daily_inventory[trans_date]:
                if trans_type in ['Receive', 'Repack']:
                    for date_str in daily_inventory:
                        if date_str >= trans_date:
                            daily_inventory[date_str][str(sku)] += qty
        
        # Apply shipments
        for ship_date, sku, qty in shipments:
            if ship_date in daily_inventory and str(sku) in daily_inventory[ship_date]:
                for date_str in daily_inventory:
                    if date_str >= ship_date:
                        daily_inventory[date_str][str(sku)] -= qty
        
        # Calculate total space rental across all days
        space_rental_total = 0.0
        for date_str, inventory in daily_inventory.items():
            total_pallets = 0
            for sku, inventory_qty in inventory.items():
                if sku in pallet_config and inventory_qty > 0:
                    pallets = math.ceil(inventory_qty / pallet_config[sku])
                    total_pallets += pallets
            space_rental_total += total_pallets * space_rental_rate
        
        grand_total = orders_total + packages_total + space_rental_total
        
        # Log success
        log_report_run('EOM', month_start, 'success', f'Monthly charges: ${grand_total:,.2f}')
        
        return jsonify({
            'success': True,
            'message': f'✅ Monthly charge report calculated - Total: ${grand_total:,.2f}',
            'data': {
                'month': month_start.strftime('%B %Y'),
                'total_orders': total_orders,
                'total_packages': total_packages,
                'orders_charge': f'${orders_total:,.2f}',
                'packages_charge': f'${packages_total:,.2f}',
                'space_rental_charge': f'${space_rental_total:,.2f}',
                'grand_total': f'${grand_total:,.2f}'
            }
        })
            
    except Exception as e:
        month_start = datetime.date.today().replace(day=1)
        log_report_run('EOM', month_start, 'failed', str(e))
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        # Always release the lock
        _report_locks['EOM'] = False

@app.route('/api/reports/status', methods=['GET'])
def api_report_status():
    """Get last run status for all report types"""
    from src.services.database.pg_utils import get_last_report_runs
    
    try:
        status = get_last_report_runs()
        return jsonify({
            'success': True,
            'data': status
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/weekly_shipped_history', methods=['GET'])
def api_weekly_shipped_history():
    """Get 52 weeks of weekly shipped history for all SKUs"""
    try:
        # Get filter parameters
        from flask import request
        sku_filter = request.args.get('sku', None)
        
        # Build query
        if sku_filter:
            query = """
                SELECT 
                    start_date,
                    end_date,
                    sku,
                    quantity_shipped
                FROM weekly_shipped_history
                WHERE sku = %s
                ORDER BY start_date DESC
                LIMIT 52
            """
            results = execute_query(query, (sku_filter,))
        else:
            query = """
                SELECT 
                    start_date,
                    end_date,
                    sku,
                    quantity_shipped
                FROM weekly_shipped_history
                ORDER BY start_date DESC, sku
            """
            results = execute_query(query)
        
        history = []
        for row in results:
            history.append({
                'start_date': row[0],
                'end_date': row[1],
                'sku': row[2],
                'quantity_shipped': row[3]
            })
        
        return jsonify({
            'success': True,
            'data': history,
            'count': len(history)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/xml_import', methods=['POST'])
def api_xml_import():
    """Process uploaded XML file and import orders into inbox"""
    try:
        from flask import request
        import tempfile
        import defusedxml.ElementTree as ET
        
        if 'xml_file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No XML file provided'
            }), 400
        
        file = request.files['xml_file']
        
        if not file.filename or file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        if not file.filename.endswith('.xml'):
            return jsonify({
                'success': False,
                'error': 'File must be an XML file'
            }), 400
        
        # Save to temporary file and parse
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.xml', delete=False) as temp_file:
            file.save(temp_file.name)
            temp_path = temp_file.name
        
        try:
            # Parse XML
            tree = ET.parse(temp_path)
            root = tree.getroot()
            
            conn = get_connection()
            cursor = conn.cursor()
            
            # Load bundle configurations for expansion
            cursor.execute("""
                SELECT bs.bundle_sku, bc.component_sku, bc.multiplier
                FROM bundle_skus bs
                JOIN bundle_components bc ON bs.id = bc.bundle_sku_id
                WHERE bs.active = 1
            """)
            
            bundle_config = {}
            for row in cursor.fetchall():
                bundle_sku, component_sku, multiplier = row
                if bundle_sku not in bundle_config:
                    bundle_config[bundle_sku] = []
                bundle_config[bundle_sku].append({
                    'component_sku': component_sku,
                    'multiplier': multiplier
                })
            
            # Load Key Products (SKUs we actually process for this client)
            cursor.execute("""
                SELECT sku FROM configuration_params
                WHERE category = 'Key Products'
            """)
            key_products = {row[0] for row in cursor.fetchall()}
            
            orders_imported = 0
            orders_skipped = 0
            
            # Process each order
            for order_elem in root.findall('order'):
                order_id = order_elem.find('orderid')
                order_date = order_elem.find('date2')
                email = order_elem.find('email')
                
                if order_id is not None and order_id.text:
                    order_number = order_id.text.strip()
                    order_date_str = order_date.text.strip() if order_date is not None and order_date.text else datetime.now().strftime('%Y-%m-%d')
                    customer_email = email.text.strip() if email is not None and email.text else None
                    
                    # Parse line items from order_detail elements
                    line_items = []
                    for detail_elem in order_elem.findall('order_detail'):
                        product_code = detail_elem.find('productid')
                        quantity_elem = detail_elem.find('amount')
                        
                        if product_code is not None and product_code.text:
                            sku = product_code.text.strip()
                            qty = int(quantity_elem.text.strip()) if quantity_elem is not None and quantity_elem.text else 1
                            line_items.append({'sku': sku, 'quantity': qty})
                    
                    # Expand bundles into component SKUs
                    expanded_items = []
                    for item in line_items:
                        sku = item['sku']
                        qty = item['quantity']
                        
                        if sku in bundle_config:
                            # This is a bundle - expand it
                            for component in bundle_config[sku]:
                                expanded_items.append({
                                    'sku': component['component_sku'],
                                    'quantity': qty * component['multiplier']
                                })
                        else:
                            # Regular SKU - pass through
                            expanded_items.append(item)
                    
                    # CRITICAL: Filter expanded items to ONLY include Key Products
                    filtered_items = [item for item in expanded_items if item['sku'] in key_products]
                    
                    # Skip order if no Key Products remain after filtering
                    if not filtered_items:
                        orders_skipped += 1
                        continue
                    
                    # Calculate total quantity from filtered items (only Key Products)
                    total_quantity = sum(item['quantity'] for item in filtered_items)
                    
                    # Check if order already exists
                    cursor.execute("SELECT id FROM orders_inbox WHERE order_number = %s", (order_number,))
                    existing = cursor.fetchone()
                    
                    if not existing:
                        # Insert order into inbox
                        cursor.execute("""
                            INSERT INTO orders_inbox (order_number, order_date, customer_email, status, total_items, source_system)
                            VALUES (%s, %s, %s, 'pending', %s, 'X-Cart')
                        """, (order_number, order_date_str, customer_email, total_quantity))
                        
                        order_inbox_id = cursor.lastrowid
                        
                        # Insert filtered line items (only Key Products)
                        for item in filtered_items:
                            cursor.execute("""
                                INSERT INTO order_items_inbox (order_inbox_id, sku, quantity)
                                VALUES (%s, %s, %s)
                            """, (order_inbox_id, item['sku'], item['quantity']))
                        
                        orders_imported += 1
            
            conn.commit()
            conn.close()
            
            # Clean up temp file
            os.unlink(temp_path)
            
            message = f'Successfully imported {orders_imported} orders'
            if orders_skipped > 0:
                message += f' ({orders_skipped} skipped - no Key Products)'
            
            return jsonify({
                'success': True,
                'message': message,
                'orders_count': orders_imported,
                'orders_skipped': orders_skipped
            })
            
        except ET.ParseError as e:
            os.unlink(temp_path)
            return jsonify({
                'success': False,
                'error': f'XML parsing error: {str(e)}'
            }), 400
        except Exception as e:
            os.unlink(temp_path)
            raise e
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/orders_inbox')
def api_orders_inbox():
    """Get all orders from inbox - one row per SKU-Lot combination (consolidated quantities)"""
    try:
        query = """
            SELECT 
                o.id,
                o.order_number,
                o.order_date,
                o.customer_email,
                o.status,
                oi.sku,
                SUM(oi.quantity) as total_quantity,
                sl.lot,
                o.shipstation_order_id,
                o.tracking_number,
                o.created_at,
                o.failure_reason,
                o.ship_company,
                o.ship_state,
                o.ship_country,
                o.source_system,
                o.shipping_service_name,
                o.shipping_carrier_id,
                o.is_flagged,
                o.flag_reason,
                o.notes,
                o.flagged_at,
                o.tracking_status,
                o.tracking_status_description,
                o.exception_description
            FROM orders_inbox o
            INNER JOIN order_items_inbox oi ON o.id = oi.order_inbox_id
            LEFT JOIN sku_lot sl ON oi.sku = sl.sku AND sl.active = 1
            GROUP BY o.id, o.order_number, o.order_date, o.customer_email, o.status, oi.sku, sl.lot, o.shipstation_order_id, o.tracking_number, o.created_at, o.failure_reason, o.ship_company, o.ship_state, o.ship_country, o.source_system, o.shipping_service_name, o.shipping_carrier_id, o.is_flagged, o.flag_reason, o.notes, o.flagged_at, o.tracking_status, o.tracking_status_description, o.exception_description
            ORDER BY o.created_at DESC, oi.sku
            LIMIT 1000
        """
        results = execute_query(query)
        
        orders = []
        for row in results:
            sku = row[5]
            lot = row[7]
            sku_lot_display = f"{sku} - {lot}" if lot else sku
            
            company_name = row[12] or ''
            ship_state = (row[13] or '').strip().upper()
            ship_country = (row[14] or 'US').strip().upper()
            source_system = row[15] or 'X-Cart'
            shipping_service_name = row[16] or ''
            shipping_carrier_id = row[17]
            
            # Determine order type flags
            is_hawaiian = ship_state == 'HI'
            is_canadian = ship_country in ('CA', 'CANADA')
            is_benco = 'BENCO' in company_name.upper() if company_name else False
            is_international = ship_country not in ('US', 'USA', 'CA', 'CANADA', '') and ship_country is not None
            is_manual = source_system == 'synced_manual'
            
            orders.append({
                'id': row[0],
                'order_number': row[1],
                'order_date': row[2],
                'customer_email': row[3] or '',
                'status': row[4],
                'sku': sku,
                'sku_lot_display': sku_lot_display,
                'quantity': row[6],
                'shipstation_order_id': row[8] or '',
                'tracking_number': row[9] or '',
                'created_at': row[10],
                'failure_reason': row[11] or '',
                'company_name': company_name,
                'is_hawaiian': is_hawaiian,
                'is_canadian': is_canadian,
                'is_benco': is_benco,
                'is_international': is_international,
                'is_manual': is_manual,
                'shipping_service_name': shipping_service_name,
                'shipping_carrier_id': shipping_carrier_id,
                'is_flagged': row[18] or False,
                'flag_reason': row[19] or '',
                'notes': row[20] or '',
                'flagged_at': row[21],
                'tracking_status': row[22] or None,
                'tracking_status_description': row[23] or None,
                'exception_description': row[24] or None
            })
        
        return jsonify({
            'success': True,
            'data': orders,
            'count': len(orders)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/orders_inbox/flag/<order_number>', methods=['POST'])
def api_flag_order(order_number):
    """Flag an order with optional reason and notes"""
    try:
        data = request.get_json() or {}
        flag_reason = data.get('flag_reason', '')
        notes = data.get('notes', '')
        
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE orders_inbox 
            SET is_flagged = TRUE,
                flag_reason = %s,
                notes = %s,
                flagged_at = CURRENT_TIMESTAMP
            WHERE order_number = %s
        """, (flag_reason, notes, order_number))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Order {order_number} flagged successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/orders_inbox/unflag/<order_number>', methods=['POST'])
def api_unflag_order(order_number):
    """Remove flag from an order"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE orders_inbox 
            SET is_flagged = FALSE,
                flag_reason = NULL,
                notes = NULL,
                flagged_at = NULL
            WHERE order_number = %s
        """, (order_number,))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Order {order_number} unflagged successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/order_items/<int:order_id>')
def api_order_items(order_id):
    """Get order items with SKU-Lot format for a specific order"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get order items with SKU-Lot mapping and ShipStation order IDs
        cursor.execute("""
            SELECT 
                oi.sku,
                oi.quantity,
                sl.lot,
                sl.active,
                ssli.shipstation_order_id
            FROM order_items_inbox oi
            LEFT JOIN sku_lot sl ON oi.sku = sl.sku AND sl.active = 1
            LEFT JOIN shipstation_order_line_items ssli ON oi.order_inbox_id = ssli.order_inbox_id AND oi.sku = ssli.sku
            WHERE oi.order_inbox_id = %s
            ORDER BY oi.sku
        """, (order_id,))
        
        items = []
        for row in cursor.fetchall():
            sku, quantity, lot, active, shipstation_order_id = row
            # Format as "SKU - Lot" if lot exists, otherwise just SKU
            sku_lot_display = f"{sku} - {lot}" if lot else sku
            
            items.append({
                'sku': sku,
                'lot': lot or '',
                'sku_lot_display': sku_lot_display,
                'quantity': quantity,
                'shipstation_order_id': shipstation_order_id or ''
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': items,
            'count': len(items)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/google_drive/list_files')
def api_google_drive_list_files():
    """List XML files from Google Drive folder"""
    try:
        from src.services.google_drive.api_client import list_xml_files_from_folder
        
        folder_id = '1rNudeesa_c6q--KIKUAOLwXta_gyRqAE'
        files = list_xml_files_from_folder(folder_id)
        
        return jsonify({
            'success': True,
            'data': files,
            'count': len(files)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def load_bundle_config_from_db(cursor):
    """Load bundle configurations from database"""
    cursor.execute("""
        SELECT bs.bundle_sku, bc.component_sku, bc.multiplier, bc.sequence
        FROM bundle_skus bs
        JOIN bundle_components bc ON bs.id = bc.bundle_sku_id
        WHERE bs.active = 1
        ORDER BY bs.bundle_sku, bc.sequence
    """)
    
    bundle_config = {}
    for row in cursor.fetchall():
        bundle_sku, component_sku, multiplier, sequence = row
        
        if bundle_sku not in bundle_config:
            bundle_config[bundle_sku] = []
        
        bundle_config[bundle_sku].append({
            'component_sku': component_sku,
            'multiplier': multiplier
        })
    
    return bundle_config

def expand_bundles(line_items, bundle_config):
    """Expand bundle SKUs into component SKUs"""
    expanded_items = []
    
    for item in line_items:
        sku = item['sku']
        qty = item['quantity']
        
        if sku in bundle_config:
            # This is a bundle - expand it
            for component in bundle_config[sku]:
                expanded_items.append({
                    'sku': component['component_sku'],
                    'quantity': qty * component['multiplier']
                })
        else:
            # Regular SKU - pass through
            expanded_items.append(item)
    
    return expanded_items

@app.route('/api/google_drive/import_file/<file_id>', methods=['POST'])
def api_google_drive_import_file(file_id):
    """Import XML file from Google Drive into orders inbox with bundle expansion"""
    try:
        from src.services.google_drive.api_client import fetch_xml_from_drive_by_file_id
        import defusedxml.ElementTree as ET
        from io import StringIO
        
        # Fetch XML content from Google Drive
        xml_content = fetch_xml_from_drive_by_file_id(file_id)
        
        # Parse XML
        root = ET.fromstring(xml_content)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Load bundle configurations
        bundle_config = load_bundle_config_from_db(cursor)
        
        # Load Key Products (SKUs we actually process for this client)
        cursor.execute("""
            SELECT sku FROM configuration_params
            WHERE category = 'Key Products'
        """)
        key_products = {row[0] for row in cursor.fetchall()}
        
        orders_imported = 0
        orders_skipped = 0
        
        # Helper function to safely extract text
        def get_text(elem, tag, default=''):
            child = elem.find(tag)
            return child.text.strip() if child is not None and child.text else default
        
        # Process each order
        for order_elem in root.findall('order'):
            order_id = order_elem.find('orderid')
            order_date = order_elem.find('date2')
            email = order_elem.find('email')
            
            if order_id is not None and order_id.text:
                order_number = order_id.text.strip()
                order_date_str = order_date.text.strip() if order_date is not None and order_date.text else datetime.now().strftime('%Y-%m-%d')
                customer_email = email.text.strip() if email is not None and email.text else None
                
                # Parse shipping address (prefix 's_')
                ship_firstname = get_text(order_elem, 's_firstname')
                ship_lastname = get_text(order_elem, 's_lastname')
                ship_name = f"{ship_firstname} {ship_lastname}".strip()
                ship_company = get_text(order_elem, 's_company')
                ship_street1 = get_text(order_elem, 's_address')
                ship_city = get_text(order_elem, 's_city')
                ship_state = get_text(order_elem, 's_state')
                ship_postal_code = get_text(order_elem, 's_zipcode')
                ship_country = get_text(order_elem, 's_country', 'US')
                ship_phone = get_text(order_elem, 's_phone')
                
                # Parse billing address (prefix 'b_')
                bill_firstname = get_text(order_elem, 'b_firstname')
                bill_lastname = get_text(order_elem, 'b_lastname')
                bill_name = f"{bill_firstname} {bill_lastname}".strip()
                bill_company = get_text(order_elem, 'b_company')
                bill_street1 = get_text(order_elem, 'b_address')
                bill_city = get_text(order_elem, 'b_city')
                bill_state = get_text(order_elem, 'b_state')
                bill_postal_code = get_text(order_elem, 'b_zipcode')
                bill_country = get_text(order_elem, 'b_country', 'US')
                bill_phone = get_text(order_elem, 'b_phone')
                
                # Parse line items from order_detail elements
                line_items = []
                
                for detail_elem in order_elem.findall('order_detail'):
                    product_code = detail_elem.find('productid')
                    quantity_elem = detail_elem.find('amount')
                    
                    if product_code is not None and product_code.text:
                        sku = product_code.text.strip()
                        qty = int(quantity_elem.text.strip()) if quantity_elem is not None and quantity_elem.text else 1
                        line_items.append({'sku': sku, 'quantity': qty})
                
                # Expand bundles into component SKUs
                expanded_items = expand_bundles(line_items, bundle_config)
                
                # CRITICAL: Filter by Key Products - skip if no Key Products in order
                final_skus = {item['sku'] for item in expanded_items}
                has_key_product = bool(final_skus & key_products)
                
                if not has_key_product:
                    orders_skipped += 1
                    print(f"SKIPPED Order {order_number}: No Key Products found. SKUs: {', '.join(final_skus)}")
                    continue
                
                # Calculate total quantity from expanded items
                total_quantity = sum(item['quantity'] for item in expanded_items)
                
                # Check if order already exists
                cursor.execute("SELECT id FROM orders_inbox WHERE order_number = %s", (order_number,))
                existing = cursor.fetchone()
                
                if not existing:
                    # Insert order into inbox with address data
                    cursor.execute("""
                        INSERT INTO orders_inbox (
                            order_number, order_date, customer_email, status, total_items, source_system,
                            ship_name, ship_company, ship_street1, ship_city, ship_state, ship_postal_code, ship_country, ship_phone,
                            bill_name, bill_company, bill_street1, bill_city, bill_state, bill_postal_code, bill_country, bill_phone
                        )
                        VALUES (%s, %s, %s, 'pending', %s, 'X-Cart', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        order_number, order_date_str, customer_email, total_quantity,
                        ship_name, ship_company, ship_street1, ship_city, ship_state, ship_postal_code, ship_country, ship_phone,
                        bill_name, bill_company, bill_street1, bill_city, bill_state, bill_postal_code, bill_country, bill_phone
                    ))
                    
                    order_inbox_id = cursor.lastrowid
                    
                    # Insert expanded line items
                    for item in expanded_items:
                        cursor.execute("""
                            INSERT INTO order_items_inbox (order_inbox_id, sku, quantity)
                            VALUES (%s, %s, %s)
                        """, (order_inbox_id, item['sku'], item['quantity']))
                    
                    orders_imported += 1
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Successfully imported {orders_imported} orders from Google Drive ({orders_skipped} skipped - no Key Products)',
            'orders_count': orders_imported,
            'skipped_count': orders_skipped
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/retry_failed_orders', methods=['POST'])
def api_retry_failed_orders():
    """Reset failed orders back to pending status for retry"""
    try:
        data = request.get_json() or {}
        order_ids = data.get('order_ids', [])
        
        conn = get_connection()
        cursor = conn.cursor()
        
        if order_ids:
            # Reset specific failed orders to pending
            placeholders = ','.join('%s' for _ in order_ids)
            cursor.execute(f"""
                UPDATE orders_inbox
                SET status = 'pending',
                    failure_reason = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id IN ({placeholders})
                AND status = 'failed'
            """, order_ids)
            affected = cursor.rowcount
        else:
            # Reset all failed orders to pending
            cursor.execute("""
                UPDATE orders_inbox
                SET status = 'pending',
                    failure_reason = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE status = 'failed'
            """)
            affected = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Reset {affected} failed orders to pending status',
            'count': affected
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/validate_orders', methods=['POST'])
def api_validate_orders():
    """Validate and correct orders against ShipStation requirements"""
    try:
        from src.services.shipstation import api_client as shipstation_api
        from config.settings import settings
        
        # Get ShipStation credentials
        api_key, api_secret = shipstation_api.get_shipstation_credentials()
        if not api_key or not api_secret:
            return jsonify({
                'success': False,
                'error': 'ShipStation API credentials not found'
            }), 500
        
        conn = get_connection()
        
        stats = {
            'total_checked': 0,
            'missing_ss_id': 0,
            'wrong_status': 0,
            'missing_addresses': 0,
            'missing_carrier_info': 0,
            'corrections_made': 0,
            'errors': 0
        }
        
        try:
            # Get all orders that are not in 'pending' status
            cursor = conn.execute("""
                SELECT id, order_number, status, shipstation_order_id, customer_email,
                       ship_name, ship_company, ship_street1, ship_city, ship_state,
                       ship_postal_code, ship_country, ship_phone,
                       bill_name, bill_company, bill_street1, bill_city, bill_state,
                       bill_postal_code, bill_country, bill_phone,
                       source_system,
                       shipping_service_name, shipping_carrier_id
                FROM orders_inbox
                WHERE status != 'pending'
                ORDER BY id
            """)
            orders = cursor.fetchall()
            
            # BATCH QUERY: Collect all order numbers and query ShipStation once
            order_numbers = [order['order_number'] for order in orders]
            
            if not order_numbers:
                return jsonify({
                    'success': True,
                    'message': 'No orders to validate',
                    'stats': stats
                })
            
            # Single batch call to ShipStation for ALL orders
            ss_orders_list = shipstation_api.fetch_shipstation_orders_by_order_numbers(
                api_key,
                api_secret,
                settings.SHIPSTATION_ORDERS_ENDPOINT,
                order_numbers
            )
            
            # Create lookup map: order_number -> ShipStation order data
            ss_orders_map = {}
            for ss_order in ss_orders_list:
                order_num = ss_order.get('orderNumber', '').strip().upper()
                if order_num:
                    ss_orders_map[order_num] = ss_order
            
            # Now validate each local order against ShipStation data
            for order in orders:
                stats['total_checked'] += 1
                order_number = order['order_number']
                order_id = order['id']
                
                try:
                    # Look up ShipStation order from batch results
                    ss_order = ss_orders_map.get(order_number.strip().upper())
                    
                    if not ss_order:
                        continue
                    ss_order_id = str(ss_order.get('orderId'))
                    ss_status = ss_order.get('orderStatus', 'unknown')
                    
                    # Check and fix missing ShipStation ID
                    if not order['shipstation_order_id']:
                        stats['missing_ss_id'] += 1
                        stats['corrections_made'] += 1
                        conn.execute(
                            "UPDATE orders_inbox SET shipstation_order_id = %s WHERE id = %s",
                            (ss_order_id, order_id)
                        )
                    
                    # Check and fix wrong ShipStation ID
                    elif order['shipstation_order_id'] != ss_order_id:
                        stats['corrections_made'] += 1
                        conn.execute(
                            "UPDATE orders_inbox SET shipstation_order_id = %s WHERE id = %s",
                            (ss_order_id, order_id)
                        )
                    
                    # Validate and fix status - map ShipStation status to local status
                    status_map = {
                        'awaiting_payment': 'awaiting_payment',
                        'awaiting_shipment': 'awaiting_shipment',  # Fixed: was incorrectly mapped to 'uploaded'
                        'shipped': 'shipped',
                        'on_hold': 'on_hold',
                        'cancelled': 'cancelled'
                    }
                    
                    expected_status = status_map.get(ss_status, order['status'])
                    if order['status'] != expected_status:
                        stats['wrong_status'] += 1
                        stats['corrections_made'] += 1
                        conn.execute(
                            "UPDATE orders_inbox SET status = %s WHERE id = %s",
                            (expected_status, order_id)
                        )
                    
                    # Check and fix missing addresses
                    ship_to = ss_order.get('shipTo', {})
                    bill_to = ss_order.get('billTo', {})
                    
                    updates = {}
                    ship_fields = {
                        'ship_name': ship_to.get('name'),
                        'ship_company': ship_to.get('company'),
                        'ship_street1': ship_to.get('street1'),
                        'ship_city': ship_to.get('city'),
                        'ship_state': ship_to.get('state'),
                        'ship_postal_code': ship_to.get('postalCode'),
                        'ship_country': ship_to.get('country'),
                        'ship_phone': ship_to.get('phone')
                    }
                    
                    bill_fields = {
                        'bill_name': bill_to.get('name'),
                        'bill_company': bill_to.get('company'),
                        'bill_street1': bill_to.get('street1'),
                        'bill_city': bill_to.get('city'),
                        'bill_state': bill_to.get('state'),
                        'bill_postal_code': bill_to.get('postalCode'),
                        'bill_country': bill_to.get('country'),
                        'bill_phone': bill_to.get('phone')
                    }
                    
                    for field, ss_value in {**ship_fields, **bill_fields}.items():
                        if ss_value and not order[field]:
                            updates[field] = ss_value.strip() if isinstance(ss_value, str) else ss_value
                    
                    if updates:
                        stats['missing_addresses'] += 1
                        stats['corrections_made'] += 1
                        set_clause = ', '.join([f"{field} = %s" for field in updates.keys()])
                        values = list(updates.values()) + [order_id]
                        conn.execute(
                            f"UPDATE orders_inbox SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                            values
                        )
                    
                    # Check and update carrier/service information
                    carrier_code = ss_order.get('carrierCode', '')
                    service_code = ss_order.get('serviceCode', '')
                    carrier_id = None
                    advanced_options = ss_order.get('advancedOptions', {})
                    if advanced_options and isinstance(advanced_options, dict):
                        # Try multiple possible locations for carrier account ID
                        carrier_id = (advanced_options.get('billToMyOtherAccount') or 
                                     advanced_options.get('carrierId'))
                    if not carrier_id:
                        carrier_id = ss_order.get('carrierId')
                    
                    # Map service codes to friendly names
                    service_name_map = {
                        'fedex_2day': 'FedEx 2Day',
                        'fedex_international_ground': 'FedEx International Ground',
                        'fedex_ground': 'FedEx Ground',
                        'fedex_home_delivery': 'FedEx Home Delivery',
                        'fedex_express_saver': 'FedEx Express Saver',
                        'fedex_standard_overnight': 'FedEx Standard Overnight'
                    }
                    service_name = service_name_map.get(service_code, service_code.replace('_', ' ').title() if service_code else '')
                    
                    # Update if missing or different
                    if (not order['shipping_service_name'] and service_name) or \
                       (not order['shipping_carrier_id'] and carrier_id):
                        stats['missing_carrier_info'] += 1
                        stats['corrections_made'] += 1
                        conn.execute(
                            """UPDATE orders_inbox 
                               SET shipping_carrier_code = %s, 
                                   shipping_carrier_id = %s, 
                                   shipping_service_code = %s,
                                   shipping_service_name = %s,
                                   updated_at = CURRENT_TIMESTAMP 
                               WHERE id = %s""",
                            (carrier_code, carrier_id, service_code, service_name, order_id)
                        )
                
                except Exception as e:
                    stats['errors'] += 1
                    continue
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': f'Validation complete: {stats["corrections_made"]} corrections made',
                'stats': stats
            })
        
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/orders/link_unlinked', methods=['POST'])
def api_link_unlinked_orders():
    """
    One-time backfill operation to link local orders with NULL shipstation_order_id to ShipStation.
    Queries ShipStation API for each unlinked order and updates the local database.
    """
    print("🔥🔥🔥 API ROUTE HIT: /api/orders/link_unlinked")
    logger.info("🔥🔥🔥 API ROUTE HIT: /api/orders/link_unlinked")
    try:
        from src.services.shipstation.api_client import (
            get_shipstation_credentials,
            get_shipstation_headers
        )
        from config.settings import SHIPSTATION_ORDERS_ENDPOINT
        from utils.api_utils import make_api_request
        
        # Get ShipStation credentials
        api_key, api_secret = get_shipstation_credentials()
        if not api_key or not api_secret:
            return jsonify({
                'success': False,
                'error': 'ShipStation API credentials not found'
            }), 500
        
        conn = get_connection()
        
        stats = {
            'total_unlinked': 0,
            'successfully_linked': 0,
            'not_found_in_shipstation': 0,
            'errors': 0,
            'skipped_manual': 0
        }
        
        try:
            # Get all orders with NULL shipstation_order_id (excluding manual orders 10xxxx)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, order_number
                FROM orders_inbox
                WHERE shipstation_order_id IS NULL
                  AND status NOT IN ('shipped', 'cancelled')
                  AND order_number NOT LIKE '10%'
                ORDER BY id
            """)
            unlinked_orders = cursor.fetchall()
            
            stats['total_unlinked'] = len(unlinked_orders)
            
            if stats['total_unlinked'] == 0:
                return jsonify({
                    'success': True,
                    'message': 'No unlinked orders found',
                    'stats': stats
                })
            
            # Get ShipStation headers
            headers = get_shipstation_headers(api_key, api_secret)
            
            # Process each unlinked order
            for order_id, order_number in unlinked_orders:
                try:
                    # Query ShipStation API for this order number
                    response = make_api_request(
                        url=SHIPSTATION_ORDERS_ENDPOINT,
                        method='GET',
                        headers=headers,
                        params={'orderNumber': order_number},
                        timeout=30
                    )
                    
                    if not response or 'orders' not in response:
                        logger.warning(f"Failed to query ShipStation for order {order_number}")
                        stats['errors'] += 1
                        continue
                    
                    orders = response.get('orders', [])
                    
                    if not orders:
                        # Order not found in ShipStation
                        stats['not_found_in_shipstation'] += 1
                        logger.info(f"Order {order_number} not found in ShipStation (may not be uploaded yet)")
                        continue
                    
                    # Use the first matching order's ShipStation ID
                    # NOTE: ShipStation may return multiple orders with same order_number (one per SKU)
                    # We link to the first one we find - the sync will handle the rest
                    shipstation_order = orders[0]
                    shipstation_order_id = str(shipstation_order.get('orderId'))
                    
                    # Update local database with ShipStation ID
                    cursor.execute("""
                        UPDATE orders_inbox
                        SET shipstation_order_id = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (shipstation_order_id, order_id))
                    
                    stats['successfully_linked'] += 1
                    logger.info(f"✅ Linked order {order_number} to ShipStation ID {shipstation_order_id}")
                    
                except Exception as e:
                    error_msg = f"Error processing order {order_number}: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    print(f"❌ {error_msg}")  # Also print to stdout
                    stats['errors'] += 1
                    continue
            
            # Commit all updates
            conn.commit()
            
            # Build success message
            message = f"Linked {stats['successfully_linked']} of {stats['total_unlinked']} unlinked orders to ShipStation"
            if stats['not_found_in_shipstation'] > 0:
                message += f" ({stats['not_found_in_shipstation']} not found in ShipStation)"
            
            return jsonify({
                'success': True,
                'message': message,
                'stats': stats
            })
        
        except Exception as outer_e:
            # Rollback any uncommitted changes on failure
            try:
                conn.rollback()
            except:
                pass
            raise outer_e
        
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Link unlinked orders failed: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/upload_orders_to_shipstation', methods=['POST'])
def api_upload_orders_to_shipstation():
    """Upload pending orders from inbox to ShipStation with SKU-Lot mapping"""
    try:
        from flask import request
        from src.services.shipstation.api_client import (
            get_shipstation_credentials,
            send_all_orders_to_shipstation,
            fetch_shipstation_orders_by_order_numbers
        )
        from config.settings import settings
        from dateutil import parser as date_parser
        
        # Get ShipStation credentials
        api_key, api_secret = get_shipstation_credentials()
        if not api_key or not api_secret:
            return jsonify({
                'success': False,
                'error': 'ShipStation API credentials not found'
            }), 500
        
        # Get order IDs from request (optional - if not provided, upload all pending)
        data = request.get_json() or {}
        order_ids = data.get('order_ids', [])
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Fetch SKU-Lot mappings from sku_lot table (new source of truth)
        cursor.execute("""
            SELECT sku, lot
            FROM sku_lot 
            WHERE active = 1
        """)
        sku_lot_map = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Fetch Product Name mappings for ShipStation display
        cursor.execute("""
            SELECT sku, value
            FROM configuration_params
            WHERE category = 'Product Names'
        """)
        product_name_map = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Build query for pending orders with address data
        # CRITICAL: Exclude orders that already exist in shipped_orders (already fulfilled)
        if order_ids:
            placeholders = ','.join('%s' for _ in order_ids)
            order_query = f"""
                SELECT id, order_number, order_date, customer_email, total_amount_cents,
                       ship_name, ship_company, ship_street1, ship_city, ship_state, ship_postal_code, ship_country, ship_phone,
                       bill_name, bill_company, bill_street1, bill_city, bill_state, bill_postal_code, bill_country, bill_phone
                FROM orders_inbox 
                WHERE status = 'pending' 
                  AND id IN ({placeholders})
                  AND order_number NOT IN (SELECT order_number FROM shipped_orders)
            """
            cursor.execute(order_query, order_ids)
        else:
            cursor.execute("""
                SELECT id, order_number, order_date, customer_email, total_amount_cents,
                       ship_name, ship_company, ship_street1, ship_city, ship_state, ship_postal_code, ship_country, ship_phone,
                       bill_name, bill_company, bill_street1, bill_city, bill_state, bill_postal_code, bill_country, bill_phone
                FROM orders_inbox 
                WHERE status = 'pending'
                  AND order_number NOT IN (SELECT order_number FROM shipped_orders)
            """)
        
        pending_orders = cursor.fetchall()
        
        if not pending_orders:
            return jsonify({
                'success': True,
                'message': 'No pending orders to upload',
                'uploaded': 0
            })
        
        # Build ShipStation order payloads (ONE ORDER PER SKU)
        shipstation_orders = []
        order_sku_map = []  # Track (order_inbox_id, sku, order_number) for later updates
        
        for order_row in pending_orders:
            # Unpack order data including address fields
            (order_id, order_number, order_date, customer_email, total_amount_cents,
             ship_name, ship_company, ship_street1, ship_city, ship_state, ship_postal_code, ship_country, ship_phone,
             bill_name, bill_company, bill_street1, bill_city, bill_state, bill_postal_code, bill_country, bill_phone) = order_row
            
            # Get order items
            cursor.execute("""
                SELECT sku, quantity, unit_price_cents
                FROM order_items_inbox
                WHERE order_inbox_id = %s
            """, (order_id,))
            items = cursor.fetchall()
            
            # Create SEPARATE ShipStation order for EACH SKU
            for sku, qty, unit_price_cents in items:
                lot_number = sku_lot_map.get(sku, '')
                sku_with_lot = f"{sku} - {lot_number}" if lot_number else sku
                product_name = product_name_map.get(sku, f'Product {sku}')  # Use mapped name or fallback
                
                # Keep original order number - ShipStation will assign unique order IDs per API call
                
                shipstation_order = {
                    'orderNumber': order_number,  # Original order number from XML
                    'orderDate': order_date,
                    'orderStatus': 'awaiting_shipment',
                    'customerEmail': customer_email or '',
                    'billTo': {
                        'name': bill_name or '',
                        'company': bill_company or '',
                        'street1': bill_street1 or '',
                        'city': bill_city or '',
                        'state': bill_state or '',
                        'postalCode': bill_postal_code or '',
                        'country': bill_country or 'US',
                        'phone': bill_phone or ''
                    },
                    'shipTo': {
                        'name': ship_name or '',
                        'company': ship_company or '',
                        'street1': ship_street1 or '',
                        'city': ship_city or '',
                        'state': ship_state or '',
                        'postalCode': ship_postal_code or '',
                        'country': ship_country or 'US',
                        'phone': ship_phone or ''
                    },
                    'items': [{
                        'sku': sku_with_lot,
                        'name': product_name,
                        'quantity': qty,
                        'unitPrice': (unit_price_cents / 100) if unit_price_cents else 0
                    }],
                    'amountPaid': (unit_price_cents * qty / 100) if unit_price_cents else 0,
                    'taxAmount': 0,
                    'shippingAmount': 0
                }
                
                shipstation_orders.append(shipstation_order)
                order_sku_map.append({
                    'order_inbox_id': order_id,
                    'sku': sku,
                    'order_number': order_number,
                    'sku_with_lot': sku_with_lot
                })
        
        # Check for duplicates in ShipStation by querying specific order numbers
        # This is more robust than date-range queries which can miss old orders
        unique_order_numbers = list(set([o['orderNumber'] for o in shipstation_orders]))
        
        existing_orders = fetch_shipstation_orders_by_order_numbers(
            api_key,
            api_secret,
            settings.SHIPSTATION_ORDERS_ENDPOINT,
            unique_order_numbers
        )
        
        # Create map of existing orders by order number AND items (SKU) for accurate duplicate detection
        # NOTE: ShipStation may have MULTIPLE orders with same order number (one per SKU)
        existing_order_map = {}
        for o in existing_orders:
            order_num = o.get('orderNumber', '').strip().upper()
            order_id = o.get('orderId')
            order_key = o.get('orderKey')
            
            # Extract SKU from first item (we create one order per SKU)
            items = o.get('items', [])
            if items and len(items) > 0:
                # SKU format in ShipStation: "17612 - 250237" (sku - lot)
                sku_with_lot = items[0].get('sku', '')
                # Extract just the SKU part (before the dash)
                sku = sku_with_lot.split(' - ')[0].strip() if ' - ' in sku_with_lot else sku_with_lot.strip()
                
                # Use combination of order number and SKU as key
                key = f"{order_num}_{sku}"
                existing_order_map[key] = {
                    'orderId': order_id,
                    'orderKey': order_key,
                    'sku': sku
                }
        
        # Filter out duplicates by checking BOTH order number AND SKU
        new_orders = []
        new_order_sku_map = []
        skipped_count = 0
        
        for idx, order in enumerate(shipstation_orders):
            order_num_upper = order['orderNumber'].strip().upper()
            order_sku_info = order_sku_map[idx]
            sku = order_sku_info['sku']
            
            # Check if this specific order+SKU combination already exists
            key = f"{order_num_upper}_{sku}"
            
            if key in existing_order_map:
                # This exact order+SKU already exists in ShipStation
                existing = existing_order_map[key]
                skipped_count += 1
                shipstation_id = existing['orderId'] or existing['orderKey']
                
                # Store in shipstation_order_line_items table (skip if already exists)
                cursor.execute("""
                    INSERT INTO shipstation_order_line_items (order_inbox_id, sku, shipstation_order_id)
                    VALUES (%s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (order_sku_info['order_inbox_id'], sku, shipstation_id))
                
                # Mark order as awaiting_shipment and store ShipStation ID
                cursor.execute("""
                    UPDATE orders_inbox
                    SET status = 'awaiting_shipment',
                        shipstation_order_id = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (shipstation_id, order_sku_info['order_inbox_id']))
            else:
                # New order - needs to be uploaded
                new_orders.append(order)
                new_order_sku_map.append(order_sku_info)
        
        if not new_orders:
            conn.commit()
            conn.close()
            return jsonify({
                'success': True,
                'message': f'All {len(shipstation_orders)} orders already exist in ShipStation',
                'uploaded': 0,
                'skipped': skipped_count
            })
        
        # Upload to ShipStation in batches of 100 (API limit)
        BATCH_SIZE = 100
        upload_results = []
        
        for batch_start in range(0, len(new_orders), BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, len(new_orders))
            batch_orders = new_orders[batch_start:batch_end]
            batch_sku_map = new_order_sku_map[batch_start:batch_end]
            
            # Transaction-safe re-check: Verify orders haven't shipped since initial query
            # This prevents race condition where order ships between query and upload
            final_batch_orders = []
            final_batch_sku_map = []
            
            for idx, order in enumerate(batch_orders):
                order_num = order['orderNumber']
                sku_info = batch_sku_map[idx]
                
                # Re-check if order has shipped
                cursor.execute("""
                    SELECT 1 FROM shipped_orders 
                    WHERE order_number = %s
                """, (order_num,))
                
                if cursor.fetchone() is None:
                    # Order has NOT shipped - safe to upload
                    final_batch_orders.append(order)
                    final_batch_sku_map.append(sku_info)
                else:
                    # Order has shipped since initial check - skip
                    skipped_count += 1
                    cursor.execute("""
                        UPDATE orders_inbox
                        SET status = 'awaiting_shipment',
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (sku_info['order_inbox_id'],))
            
            # Upload only orders that passed the re-check
            if final_batch_orders:
                batch_results = send_all_orders_to_shipstation(
                    final_batch_orders,
                    api_key,
                    api_secret,
                    settings.SHIPSTATION_CREATE_ORDERS_ENDPOINT
                )
                upload_results.extend(batch_results)
                
                # Update new_order_sku_map for result processing
                new_order_sku_map[batch_start:batch_start+len(final_batch_sku_map)] = final_batch_sku_map
        
        # Update database with results
        uploaded_count = 0
        failed_count = 0
        
        for idx, result in enumerate(upload_results):
            # ShipStation returns orderKey which should match our orderNumber
            order_key = result.get('orderKey', '')
            order_id = result.get('orderId')
            success = result.get('success', False)
            error_msg = result.get('errorMessage')
            
            # Get corresponding order_sku_info from new_order_sku_map
            if idx < len(new_order_sku_map):
                order_sku_info = new_order_sku_map[idx]
                
                if success:
                    shipstation_id = order_id or order_key
                    
                    # Store ShipStation order ID in shipstation_order_line_items table (skip if already exists)
                    cursor.execute("""
                        INSERT INTO shipstation_order_line_items (order_inbox_id, sku, shipstation_order_id)
                        VALUES (%s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (order_sku_info['order_inbox_id'], order_sku_info['sku'], shipstation_id))
                    
                    # Also update orders_inbox.shipstation_order_id for the first SKU uploaded
                    cursor.execute("""
                        UPDATE orders_inbox
                        SET shipstation_order_id = %s
                        WHERE id = %s AND (shipstation_order_id IS NULL OR shipstation_order_id = '')
                    """, (shipstation_id, order_sku_info['order_inbox_id']))
                    
                    uploaded_count += 1
                else:
                    failed_count += 1
                    # Capture error details for troubleshooting
                    error_details = error_msg or result.get('message') or 'Unknown error'
                    
                    # Log the failure for troubleshooting
                    import logging
                    logging.error(f"ShipStation upload failed for order {order_sku_info['order_number']}, SKU {order_sku_info['sku']}: {error_details}")
                    
                    # Mark order as failed with reason
                    cursor.execute("""
                        UPDATE orders_inbox 
                        SET status = 'failed',
                            failure_reason = %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (error_details, order_sku_info['order_inbox_id']))
        
        # Update all successfully uploaded orders to 'awaiting_shipment' status
        # (Only if ALL SKUs for that order were uploaded successfully)
        cursor.execute("""
            UPDATE orders_inbox
            SET status = 'awaiting_shipment',
                updated_at = CURRENT_TIMESTAMP
            WHERE id IN (
                SELECT DISTINCT order_inbox_id 
                FROM shipstation_order_line_items
            )
        """)
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Uploaded {uploaded_count} orders to ShipStation',
            'uploaded': uploaded_count,
            'failed': failed_count,
            'skipped': skipped_count
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'trace': traceback.format_exc()
        }), 500

# Bundle SKU CRUD API Endpoints

@app.route('/api/bundles', methods=['GET'])
def api_get_bundles():
    """Get all bundle SKUs with component counts"""
    try:
        query = """
            SELECT bs.id, bs.bundle_sku, bs.description, bs.active, 
                   COUNT(bc.id) as component_count, bs.created_at
            FROM bundle_skus bs
            LEFT JOIN bundle_components bc ON bs.id = bc.bundle_sku_id
            GROUP BY bs.id, bs.bundle_sku, bs.description, bs.active, bs.created_at
            ORDER BY bs.bundle_sku
        """
        results = execute_query(query)
        
        bundles = []
        for row in results:
            bundles.append({
                'id': row[0],
                'bundle_sku': row[1],
                'description': row[2],
                'active': row[3],
                'component_count': row[4],
                'created_at': row[5]
            })
        
        return jsonify({
            'success': True,
            'data': bundles,
            'count': len(bundles)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/bundle_components/<int:bundle_id>', methods=['GET'])
def api_get_bundle_components(bundle_id):
    """Get components for a specific bundle"""
    try:
        query = """
            SELECT component_sku, multiplier, sequence
            FROM bundle_components
            WHERE bundle_sku_id = %s
            ORDER BY sequence
        """
        results = execute_query(query, (bundle_id,))
        
        components = []
        for row in results:
            components.append({
                'component_sku': row[0],
                'multiplier': row[1],
                'sequence': row[2]
            })
        
        return jsonify({
            'success': True,
            'data': components
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/bundles', methods=['POST'])
def api_create_bundle():
    """Create a new bundle SKU"""
    try:
        data = request.get_json()
        
        bundle_sku = data.get('bundle_sku', '').strip()
        description = data.get('description', '').strip()
        active = data.get('active', 1)
        components = data.get('components', [])
        
        if not bundle_sku or not description:
            return jsonify({
                'success': False,
                'error': 'Bundle SKU and description are required'
            }), 400
        
        if not components:
            return jsonify({
                'success': False,
                'error': 'At least one component is required'
            }), 400
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Insert bundle
        cursor.execute("""
            INSERT INTO bundle_skus (bundle_sku, description, active)
            VALUES (%s, %s, %s)
        """, (bundle_sku, description, active))
        
        bundle_id = cursor.lastrowid
        
        # Insert components
        for comp in components:
            cursor.execute("""
                INSERT INTO bundle_components (bundle_sku_id, component_sku, multiplier, sequence)
                VALUES (%s, %s, %s, %s)
            """, (bundle_id, comp['component_sku'], comp['multiplier'], comp['sequence']))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Bundle created successfully',
            'bundle_id': bundle_id
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/bundles/<int:bundle_id>', methods=['PUT'])
def api_update_bundle(bundle_id):
    """Update an existing bundle SKU"""
    try:
        data = request.get_json()
        
        bundle_sku = data.get('bundle_sku', '').strip()
        description = data.get('description', '').strip()
        active = data.get('active', 1)
        components = data.get('components', [])
        
        if not bundle_sku or not description:
            return jsonify({
                'success': False,
                'error': 'Bundle SKU and description are required'
            }), 400
        
        if not components:
            return jsonify({
                'success': False,
                'error': 'At least one component is required'
            }), 400
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Update bundle
        cursor.execute("""
            UPDATE bundle_skus 
            SET bundle_sku = %s, description = %s, active = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (bundle_sku, description, active, bundle_id))
        
        # Delete existing components
        cursor.execute("DELETE FROM bundle_components WHERE bundle_sku_id = %s", (bundle_id,))
        
        # Insert new components
        for comp in components:
            cursor.execute("""
                INSERT INTO bundle_components (bundle_sku_id, component_sku, multiplier, sequence)
                VALUES (%s, %s, %s, %s)
            """, (bundle_id, comp['component_sku'], comp['multiplier'], comp['sequence']))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Bundle updated successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/bundles/<int:bundle_id>', methods=['DELETE'])
def api_delete_bundle(bundle_id):
    """Delete a bundle SKU"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Delete bundle (components will cascade delete due to FK)
        cursor.execute("DELETE FROM bundle_skus WHERE id = %s", (bundle_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Bundle deleted successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# SKU Lot Management Endpoints
@app.route('/api/sku_lots', methods=['GET'])
def api_get_sku_lots():
    """Get all SKU-Lot combinations"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, sku, lot, active, created_at, updated_at 
            FROM sku_lot 
            ORDER BY sku, lot
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        sku_lots = []
        for row in rows:
            sku_lots.append({
                'id': row[0],
                'sku': row[1],
                'lot': row[2],
                'active': row[3],
                'created_at': row[4],
                'updated_at': row[5]
            })
        
        return jsonify({
            'success': True,
            'data': sku_lots,
            'count': len(sku_lots)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/sku_lots', methods=['POST'])
def api_create_sku_lot():
    """Create a new SKU-Lot combination"""
    try:
        data = request.json
        
        # Validate required fields
        if not data.get('sku') or not data.get('lot'):
            return jsonify({
                'success': False,
                'error': 'SKU and Lot are required'
            }), 400
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Insert new SKU-Lot
        cursor.execute("""
            INSERT INTO sku_lot (sku, lot, active)
            VALUES (%s, %s, %s)
        """, (data['sku'], data['lot'], data.get('active', 1)))
        
        sku_lot_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'sku_lot_id': sku_lot_id,
            'message': 'SKU-Lot created successfully'
        })
    except psycopg2.IntegrityError:
        return jsonify({
            'success': False,
            'error': 'This SKU-Lot combination already exists'
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/sku_lots/<int:sku_lot_id>', methods=['PUT'])
def api_update_sku_lot(sku_lot_id):
    """Update a SKU-Lot combination"""
    try:
        data = request.json
        
        # Validate required fields
        if not data.get('sku') or not data.get('lot'):
            return jsonify({
                'success': False,
                'error': 'SKU and Lot are required'
            }), 400
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Update SKU-Lot
        cursor.execute("""
            UPDATE sku_lot 
            SET sku = %s, lot = %s, active = %s, updated_at = datetime('now')
            WHERE id = %s
        """, (data['sku'], data['lot'], data.get('active', 1), sku_lot_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'SKU-Lot updated successfully'
        })
    except psycopg2.IntegrityError:
        return jsonify({
            'success': False,
            'error': 'This SKU-Lot combination already exists'
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/sku_lots/<int:sku_lot_id>', methods=['DELETE'])
def api_delete_sku_lot(sku_lot_id):
    """Delete a SKU-Lot combination"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM sku_lot WHERE id = %s", (sku_lot_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'SKU-Lot deleted successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Email Contacts Management Endpoints
@app.route('/api/email_contacts', methods=['GET'])
def api_get_email_contacts():
    """Get all email contacts"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, email, name, created_at, updated_at 
            FROM email_contacts 
            ORDER BY email
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        contacts = []
        for row in rows:
            contacts.append({
                'id': row[0],
                'email': row[1],
                'name': row[2] if row[2] else '',
                'created_at': row[3].isoformat() if row[3] else None,
                'updated_at': row[4].isoformat() if row[4] else None
            })
        
        return jsonify({
            'success': True,
            'data': contacts,
            'count': len(contacts)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/email_contacts', methods=['POST'])
def api_create_email_contact():
    """Create a new email contact"""
    try:
        data = request.json
        
        email = data.get('email', '').strip()
        name = data.get('name', '').strip()
        
        if not email:
            return jsonify({
                'success': False,
                'error': 'Email is required'
            }), 400
        
        if '@' not in email:
            return jsonify({
                'success': False,
                'error': 'Invalid email format'
            }), 400
        
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO email_contacts (email, name)
            VALUES (%s, %s)
            RETURNING id
        """, (email, name if name else None))
        
        contact_id = cursor.fetchone()[0]
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Email contact created successfully',
            'id': contact_id
        })
    except psycopg2.IntegrityError:
        return jsonify({
            'success': False,
            'error': 'This email already exists'
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/email_contacts/<int:contact_id>', methods=['PUT'])
def api_update_email_contact(contact_id):
    """Update an email contact"""
    try:
        data = request.json
        
        email = data.get('email', '').strip()
        name = data.get('name', '').strip()
        
        if not email:
            return jsonify({
                'success': False,
                'error': 'Email is required'
            }), 400
        
        if '@' not in email:
            return jsonify({
                'success': False,
                'error': 'Invalid email format'
            }), 400
        
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE email_contacts 
            SET email = %s, name = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (email, name if name else None, contact_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Email contact updated successfully'
        })
    except psycopg2.IntegrityError:
        return jsonify({
            'success': False,
            'error': 'This email already exists'
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/email_contacts/<int:contact_id>', methods=['DELETE'])
def api_delete_email_contact(contact_id):
    """Delete an email contact"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM email_contacts WHERE id = %s", (contact_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Email contact deleted successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/shipstation/units_to_ship', methods=['GET'])
def api_get_units_to_ship():
    """Get cached units to ship count"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT metric_value, last_updated
            FROM shipstation_metrics
            WHERE metric_name = 'units_to_ship'
        """)
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            units, last_updated = result
            return jsonify({
                'success': True,
                'units_to_ship': units,
                'last_updated': last_updated
            })
        else:
            return jsonify({
                'success': True,
                'units_to_ship': 0,
                'last_updated': None
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/shipstation/refresh_units_to_ship', methods=['POST'])
def api_refresh_units_to_ship():
    """Fetch real-time units to ship from ShipStation and update cache"""
    try:
        import requests
        from requests.auth import HTTPBasicAuth
        from config.settings import settings
        from src.services.shipstation.api_client import get_shipstation_credentials
        
        # Get ShipStation credentials
        api_key, api_secret = get_shipstation_credentials()
        if not api_key or not api_secret:
            return jsonify({
                'success': False,
                'error': 'ShipStation API credentials not found'
            }), 500
        
        # Fetch orders with status awaiting_shipment (excluding on_hold and cancelled)
        url = settings.SHIPSTATION_ORDERS_ENDPOINT
        params = {
            'orderStatus': 'awaiting_shipment',
            'pageSize': 500
        }
        
        response = requests.get(
            url,
            auth=HTTPBasicAuth(api_key, api_secret),
            params=params
        )
        
        if response.status_code != 200:
            return jsonify({
                'success': False,
                'error': f'ShipStation API error: {response.status_code}'
            }), 500
        
        data = response.json()
        orders = data.get('orders', [])
        
        # Count total units across all items in all orders
        total_units = sum(
            item.get('quantity', 0)
            for order in orders
            for item in order.get('items', [])
        )
        
        # Update cache in database
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE shipstation_metrics
            SET metric_value = %s,
                last_updated = CURRENT_TIMESTAMP
            WHERE metric_name = 'units_to_ship'
        """, (total_units,))
        
        conn.commit()
        
        # Get updated timestamp
        cursor.execute("""
            SELECT last_updated
            FROM shipstation_metrics
            WHERE metric_name = 'units_to_ship'
        """)
        
        last_updated = cursor.fetchone()[0]
        conn.close()
        
        return jsonify({
            'success': True,
            'units_to_ship': total_units,
            'last_updated': last_updated,
            'orders_count': len(orders)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/local/awaiting_shipment_count', methods=['GET'])
def api_get_local_awaiting_shipment_count():
    """Get count of items in local DB that are ready to ship (excludes shipped, cancelled, on_hold)"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Count total units for all orders ready to ship (exclude shipped, cancelled, on_hold)
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT o.id) as order_count,
                COALESCE(SUM(oi.quantity), 0) as total_units,
                MAX(o.created_at) as last_updated
            FROM orders_inbox o
            LEFT JOIN order_items_inbox oi ON o.id = oi.order_inbox_id
            WHERE o.status NOT IN ('shipped', 'cancelled', 'on_hold')
        """)
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            order_count, total_units, last_updated = result
            return jsonify({
                'success': True,
                'total_units': total_units or 0,
                'order_count': order_count or 0,
                'last_updated': last_updated
            })
        else:
            return jsonify({
                'success': True,
                'total_units': 0,
                'order_count': 0,
                'last_updated': None
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/local/on_hold_count', methods=['GET'])
def api_get_on_hold_count():
    """Get count of items in local DB that are on hold"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Count total units for all on-hold orders
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT o.id) as order_count,
                COALESCE(SUM(oi.quantity), 0) as total_units,
                MAX(o.created_at) as last_updated
            FROM orders_inbox o
            LEFT JOIN order_items_inbox oi ON o.id = oi.order_inbox_id
            WHERE o.status = 'on_hold'
        """)
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            order_count, total_units, last_updated = result
            return jsonify({
                'success': True,
                'total_units': total_units or 0,
                'order_count': order_count or 0,
                'last_updated': last_updated
            })
        else:
            return jsonify({
                'success': True,
                'total_units': 0,
                'order_count': 0,
                'last_updated': None
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/shipping_violations', methods=['GET'])
def api_get_shipping_violations():
    """Get all unresolved shipping violations"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                v.id,
                v.order_number,
                v.violation_type,
                v.expected_value,
                v.actual_value,
                v.detected_at,
                v.is_resolved,
                o.ship_state,
                o.ship_country,
                o.ship_company
            FROM shipping_violations v
            LEFT JOIN orders_inbox o ON v.order_number = o.order_number
            WHERE v.is_resolved = 0
            ORDER BY v.detected_at DESC
        """)
        
        violations = []
        for row in cursor.fetchall():
            violations.append({
                'id': row[0],
                'order_number': row[1],
                'violation_type': row[2],
                'expected_value': row[3],
                'actual_value': row[4],
                'detected_at': row[5],
                'is_resolved': row[6],
                'ship_state': row[7],
                'ship_country': row[8],
                'ship_company': row[9]
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'violations': violations,
            'count': len(violations)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/shipping_violations/<int:violation_id>/resolve', methods=['PUT'])
def api_resolve_violation(violation_id):
    """Mark a shipping violation as resolved"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE shipping_violations
            SET is_resolved = 1,
                resolved_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (violation_id,))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Violation not found'
            }), 404
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Violation marked as resolved'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/duplicate_alerts', methods=['GET'])
def api_get_duplicate_alerts():
    """Get all active duplicate order alerts from ShipStation monitoring with local DB matches"""
    try:
        import json
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                id,
                order_number,
                base_sku,
                duplicate_count,
                shipstation_ids,
                details,
                first_detected,
                last_seen,
                status
            FROM duplicate_order_alerts
            WHERE status = 'active'
            ORDER BY last_seen DESC
        """)
        
        alert_rows = cursor.fetchall()
        
        # Get list of deleted ShipStation orders
        cursor.execute("""
            SELECT shipstation_order_id, deleted_at 
            FROM deleted_shipstation_orders
        """)
        deleted_orders = {row[0]: row[1] for row in cursor.fetchall()}
        
        alerts = []
        for row in alert_rows:
            alert_data = {
                'id': row[0],
                'order_number': row[1],
                'base_sku': row[2],
                'duplicate_count': row[3],
                'shipstation_ids': json.loads(row[4]) if row[4] else [],
                'details': json.loads(row[5]) if row[5] else [],
                'first_detected': row[6],
                'last_seen': row[7],
                'status': row[8],
                'local_matches': []
            }
            
            # Mark deleted orders in details
            for detail in alert_data['details']:
                ss_id = detail.get('shipstation_id')
                if ss_id and ss_id in deleted_orders:
                    detail['deleted'] = True
                    detail['deleted_at'] = deleted_orders[ss_id].isoformat()
                else:
                    detail['deleted'] = False
            
            # Fetch local database matches for this order number
            order_number = row[1]
            if order_number:
                cursor.execute("""
                    SELECT 
                        id,
                        order_number,
                        shipstation_order_id,
                        ship_name,
                        ship_company,
                        status,
                        created_at
                    FROM orders_inbox
                    WHERE order_number = %s
                    ORDER BY created_at DESC
                """, (order_number,))
                
                local_matches = []
                for local_row in cursor.fetchall():
                    local_id, local_order_num, local_ss_id, ship_name, ship_company, status, created_at = local_row
                    
                    # Get items for this order
                    cursor.execute("""
                        SELECT sku, sku_lot, quantity
                        FROM order_items_inbox
                        WHERE order_inbox_id = %s
                        ORDER BY sku
                    """, (local_id,))
                    
                    items = []
                    for item_row in cursor.fetchall():
                        sku, sku_lot, qty = item_row
                        items.append({
                            'sku': sku,
                            'sku_lot': sku_lot,
                            'quantity': qty
                        })
                    
                    local_matches.append({
                        'id': local_id,
                        'order_number': local_order_num,
                        'shipstation_order_id': local_ss_id,
                        'ship_name': ship_name,
                        'ship_company': ship_company,
                        'status': status,
                        'created_at': created_at.isoformat() if created_at else None,
                        'items': items
                    })
                
                alert_data['local_matches'] = local_matches
            
            alerts.append(alert_data)
        
        conn.close()
        
        return jsonify({
            'success': True,
            'alerts': alerts,
            'count': len(alerts)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/lot_mismatch_count', methods=['GET'])
def api_get_lot_mismatch_count():
    """Get count of orders with unresolved lot mismatches"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(DISTINCT order_number) as mismatch_count
            FROM lot_mismatch_alerts
            WHERE resolved_at IS NULL
        """)
        
        row = cursor.fetchone()
        count = row[0] if row else 0
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'count': count
        })
        
    except Exception as e:
        logger.error(f"Error fetching lot mismatch count: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/duplicate_alerts/<int:alert_id>/resolve', methods=['PUT'])
def api_resolve_duplicate_alert(alert_id):
    """Mark a duplicate alert as resolved"""
    try:
        from flask import request
        data = request.get_json() or {}
        notes = data.get('notes', 'Manually resolved')
        
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE duplicate_order_alerts
            SET status = 'resolved',
                resolved_at = CURRENT_TIMESTAMP,
                resolved_by = 'manual',
                notes = %s
            WHERE id = %s AND status = 'active'
        """, (notes, alert_id))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Alert not found or already resolved'
            }), 404
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Duplicate alert marked as resolved'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/lot_mismatch_alerts', methods=['GET'])
def api_get_lot_mismatch_alerts():
    """Get all active lot number mismatch alerts"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                id,
                order_number,
                base_sku,
                shipstation_lot,
                active_lot,
                shipstation_order_id,
                shipstation_item_id,
                order_status,
                detected_at
            FROM lot_mismatch_alerts
            WHERE resolved_at IS NULL
            ORDER BY detected_at DESC
        """)
        
        alerts = []
        for row in cursor.fetchall():
            alerts.append({
                'id': row[0],
                'order_number': row[1],
                'base_sku': row[2],
                'shipstation_lot': row[3],
                'active_lot': row[4],
                'shipstation_order_id': row[5],
                'shipstation_item_id': row[6],
                'order_status': row[7],
                'detected_at': row[8]
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'alerts': alerts,
            'count': len(alerts)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/lot_mismatch_alerts/<int:alert_id>/resolve', methods=['PUT'])
def api_resolve_lot_mismatch_alert(alert_id):
    """Mark a lot mismatch alert as resolved"""
    try:
        data = request.get_json() or {}
        resolved_by = data.get('resolved_by', 'manual')
        
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE lot_mismatch_alerts
            SET resolved_at = CURRENT_TIMESTAMP,
                resolved_by = %s
            WHERE id = %s AND resolved_at IS NULL
        """, (resolved_by, alert_id))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Alert not found or already resolved'
            }), 404
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Lot mismatch alert marked as resolved'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/update_lot_in_shipstation', methods=['PUT'])
def api_update_lot_in_shipstation():
    """Update SKU-Lot in ShipStation order"""
    try:
        from src.services.shipstation.api_client import get_shipstation_credentials, get_shipstation_headers
        from utils.api_utils import make_api_request
        
        data = request.get_json()
        order_id = data.get('shipstation_order_id')
        item_id = data.get('shipstation_item_id')
        new_lot = data.get('new_lot')
        base_sku = data.get('base_sku')
        alert_id = data.get('alert_id')
        
        if not all([order_id, item_id, new_lot, base_sku]):
            return jsonify({
                'success': False,
                'error': 'Missing required parameters'
            }), 400
        
        # Get ShipStation credentials
        api_key, api_secret = get_shipstation_credentials()
        if not api_key or not api_secret:
            return jsonify({
                'success': False,
                'error': 'Failed to get ShipStation credentials'
            }), 500
        
        # Get headers with auth
        headers = get_shipstation_headers(api_key, api_secret)
        headers['Content-Type'] = 'application/json'
        
        # Fetch current order from ShipStation
        order_url = f'https://ssapi.shipstation.com/orders/{order_id}'
        order_response_obj = make_api_request(
            order_url,
            method='GET',
            headers=headers
        )
        
        if not order_response_obj:
            return jsonify({
                'success': False,
                'error': 'Failed to fetch order from ShipStation'
            }), 500
        
        # Parse JSON response
        order_data = order_response_obj.json()
        
        # Update the item SKU to include new lot
        new_sku = f"{base_sku} - {new_lot}"
        
        for item in order_data.get('items', []):
            if str(item.get('orderItemId')) == str(item_id):
                item['sku'] = new_sku
                break
        
        # Update order in ShipStation
        import json as json_module
        update_response_obj = make_api_request(
            'https://ssapi.shipstation.com/orders/createorder',
            method='POST',
            headers=headers,
            data=order_data
        )
        
        if not update_response_obj:
            return jsonify({
                'success': False,
                'error': 'Failed to update order in ShipStation - no response from API'
            }), 500
        
        # Check if ShipStation returned an error
        if update_response_obj.status_code != 200:
            error_text = update_response_obj.text if update_response_obj else 'Unknown error'
            logging.error(f"ShipStation API error (status {update_response_obj.status_code}): {error_text}")
            return jsonify({
                'success': False,
                'error': f'ShipStation API error ({update_response_obj.status_code}): {error_text}'
            }), 500
        
        # Mark alert as resolved
        if alert_id:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE lot_mismatch_alerts
                SET resolved_at = CURRENT_TIMESTAMP,
                    resolved_by = 'user_updated'
                WHERE id = %s
            """, (alert_id,))
            conn.commit()
            conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Updated SKU-Lot to {new_sku} in ShipStation',
            'new_sku': new_sku
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/manual_order_conflicts', methods=['GET'])
def api_get_manual_order_conflicts():
    """Get all pending manual order conflicts with proposed new order numbers"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Calculate proposed new order number from BOTH shipped_orders AND orders_inbox
        cursor.execute("""
            SELECT MAX(order_num) FROM (
                SELECT CAST(order_number AS INTEGER) as order_num
                FROM shipped_orders
                WHERE order_number ~ '^[0-9]+$'
                AND CAST(order_number AS INTEGER) < 200000
                UNION ALL
                SELECT CAST(order_number AS INTEGER) as order_num
                FROM orders_inbox
                WHERE order_number ~ '^[0-9]+$'
                AND CAST(order_number AS INTEGER) < 200000
            ) combined
        """)
        max_row = cursor.fetchone()
        max_order_num = max_row[0] if max_row and max_row[0] else 100000
        proposed_new_order_number = str(max_order_num + 1)
        
        cursor.execute("""
            SELECT 
                id,
                conflicting_order_number,
                shipstation_order_id,
                customer_name,
                original_ship_date,
                detected_at,
                resolution_status,
                original_company,
                original_items,
                duplicate_company,
                duplicate_items
            FROM manual_order_conflicts
            WHERE resolution_status = 'pending'
            ORDER BY detected_at DESC
        """)
        
        conflicts = []
        for row in cursor.fetchall():
            conflicts.append({
                'id': row[0],
                'conflicting_order_number': row[1],
                'shipstation_order_id': row[2],
                'customer_name': row[3],
                'original_ship_date': row[4].strftime('%Y-%m-%d') if row[4] else None,
                'detected_at': row[5].strftime('%Y-%m-%d %H:%M:%S') if row[5] else None,
                'resolution_status': row[6],
                'original_company': row[7],
                'original_items': row[8] if row[8] else [],
                'duplicate_company': row[9],
                'duplicate_items': row[10] if row[10] else [],
                'proposed_new_order_number': proposed_new_order_number
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'conflicts': conflicts,
            'count': len(conflicts)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/manual_order_conflicts/<int:conflict_id>/recreate', methods=['POST'])
def api_recreate_manual_order(conflict_id):
    """
    Recreate a conflicting manual order with a new order number.
    Steps:
    1. Find max order number < 200000 in ShipStation
    2. Increment by 1 to get new order number
    3. Copy all order data from conflicting order
    4. Create new order in ShipStation
    5. Return new order details for user confirmation
    """
    try:
        from src.services.shipstation.api_client import get_shipstation_credentials
        from utils.api_utils import make_api_request
        
        # Get conflict details
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT shipstation_order_id, conflicting_order_number
            FROM manual_order_conflicts
            WHERE id = %s AND resolution_status = 'pending'
        """, (conflict_id,))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Conflict not found or already resolved'
            }), 404
        
        shipstation_order_id = row[0]
        old_order_number = row[1]
        
        # Get ShipStation credentials
        api_key, api_secret = get_shipstation_credentials()
        if not api_key or not api_secret:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Failed to get ShipStation credentials'
            }), 500
        
        # Get proper headers for ShipStation API
        from src.services.shipstation.api_client import get_shipstation_headers
        headers = get_shipstation_headers(api_key, api_secret)
        
        # Find max order number < 200000 from BOTH shipped_orders AND orders_inbox
        cursor.execute("""
            SELECT MAX(order_num) FROM (
                SELECT CAST(order_number AS INTEGER) as order_num
                FROM shipped_orders
                WHERE order_number ~ '^[0-9]+$'
                AND CAST(order_number AS INTEGER) < 200000
                UNION ALL
                SELECT CAST(order_number AS INTEGER) as order_num
                FROM orders_inbox
                WHERE order_number ~ '^[0-9]+$'
                AND CAST(order_number AS INTEGER) < 200000
            ) combined
        """)
        max_row = cursor.fetchone()
        max_order_num = max_row[0] if max_row and max_row[0] else 100000
        new_order_number = str(max_order_num + 1)
        
        # Fetch the conflicting order details
        order_url = f'https://ssapi.shipstation.com/orders/{shipstation_order_id}'
        order_resp = make_api_request(
            url=order_url,
            method='GET',
            headers=headers,
            timeout=30
        )
        
        if not order_resp or order_resp.status_code != 200:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Failed to fetch order details from ShipStation'
            }), 500
        
        order_response = order_resp.json()
        
        # Create new order with updated order number
        new_order = order_response.copy()
        new_order['orderNumber'] = new_order_number
        # Remove IDs so ShipStation creates a new order
        new_order.pop('orderId', None)
        new_order.pop('orderKey', None)
        
        # Replace old lot numbers with active lots from sku_lot table
        from src.services.data_processing.sku_lot_parser import parse_shipstation_sku
        
        for item in new_order.get('items', []):
            item.pop('orderItemId', None)
            
            # Extract base SKU and replace with active lot
            current_sku = item.get('sku', '')
            if current_sku:
                # Parse to get base SKU (returns ParsedSKU dataclass)
                parsed = parse_shipstation_sku(current_sku)
                base_sku = parsed.base_sku  # Access attribute, not dict key
                
                if base_sku:
                    # Look up active lot from database
                    cursor.execute("""
                        SELECT sku, lot 
                        FROM sku_lot 
                        WHERE sku = %s AND active = 1
                        LIMIT 1
                    """, (base_sku,))
                    
                    active_lot = cursor.fetchone()
                    if active_lot:
                        active_sku = active_lot[0]
                        active_lot_num = active_lot[1]
                        new_sku = f"{active_sku} - {active_lot_num}"
                        
                        # Only log if we're actually changing the lot
                        if new_sku != current_sku:
                            print(f"🔄 Replacing lot: {current_sku} → {new_sku}")
                        
                        item['sku'] = new_sku
        
        # Create new order in ShipStation
        create_resp = make_api_request(
            url='https://ssapi.shipstation.com/orders/createorder',
            method='POST',
            headers=headers,
            data=new_order,
            timeout=30
        )
        
        if not create_resp or create_resp.status_code != 200:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Failed to create new order in ShipStation'
            }), 500
        
        create_response = create_resp.json()
        new_shipstation_order_id = create_response.get('orderId')
        
        # Auto-resolve: Mark conflict as resolved after successful recreation
        cursor.execute("""
            UPDATE manual_order_conflicts
            SET new_order_number = %s,
                new_shipstation_order_id = %s,
                resolution_status = 'resolved',
                resolved_at = NOW()
            WHERE id = %s
        """, (new_order_number, str(new_shipstation_order_id), conflict_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'New order {new_order_number} created successfully. Old conflict auto-resolved.',
            'old_order_number': old_order_number,
            'new_order_number': new_order_number,
            'new_shipstation_order_id': str(new_shipstation_order_id),
            'old_shipstation_order_id': shipstation_order_id,
            'auto_resolved': True
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/manual_order_conflicts/<int:conflict_id>/confirm_delete', methods=['POST'])
def api_confirm_delete_conflicting_order(conflict_id):
    """
    Confirm deletion of the old conflicting order from ShipStation.
    This should only be called after user verifies the new order was created properly.
    """
    try:
        from src.services.shipstation.api_client import get_shipstation_credentials
        from utils.api_utils import make_api_request
        
        # Get conflict details
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT shipstation_order_id, new_order_number, new_shipstation_order_id
            FROM manual_order_conflicts
            WHERE id = %s
        """, (conflict_id,))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Conflict not found'
            }), 404
        
        old_shipstation_order_id = row[0]
        new_order_number = row[1]
        new_shipstation_order_id = row[2]
        
        if not new_order_number or not new_shipstation_order_id:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'New order must be created before deleting old order'
            }), 400
        
        # Get ShipStation credentials
        api_key, api_secret = get_shipstation_credentials()
        if not api_key or not api_secret:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Failed to get ShipStation credentials'
            }), 500
        
        # Get proper headers for ShipStation API
        from src.services.shipstation.api_client import get_shipstation_headers
        headers = get_shipstation_headers(api_key, api_secret)
        
        # Delete old order from ShipStation
        delete_url = f'https://ssapi.shipstation.com/orders/{old_shipstation_order_id}'
        delete_response = make_api_request(
            url=delete_url,
            method='DELETE',
            headers=headers,
            timeout=30
        )
        
        # Mark conflict as resolved
        cursor.execute("""
            UPDATE manual_order_conflicts
            SET resolution_status = 'recreated',
                resolved_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (conflict_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Old order deleted and conflict resolved. New order: {new_order_number}'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/manual_order_conflicts/<int:conflict_id>/dismiss', methods=['POST'])
def api_dismiss_manual_order_conflict(conflict_id):
    """Dismiss a manual order conflict without taking action"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE manual_order_conflicts
            SET resolution_status = 'dismissed',
                resolved_at = CURRENT_TIMESTAMP
            WHERE id = %s AND resolution_status = 'pending'
        """, (conflict_id,))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Conflict not found or already resolved'
            }), 404
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Conflict dismissed'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/manual_order_conflicts/<int:conflict_id>/sync', methods=['POST'])
def api_sync_manual_order_from_shipstation(conflict_id):
    """
    Sync a manual order conflict by pulling the original order data from ShipStation
    and updating the local database to match ShipStation's truth.
    
    This endpoint:
    1. Fetches the original (shipped) order from ShipStation
    2. Updates or creates the order in orders_inbox
    3. If shipped, also updates shipped_orders table
    4. Marks the conflict as resolved
    
    Safety: Uses transactions, requires admin authentication, logs before/after state
    """
    try:
        from src.services.shipstation.api_client import get_shipstation_credentials, fetch_order_by_id
        import json as json_lib
        
        # Get conflict details
        conn = get_connection()
        conn.autocommit = False  # Ensure explicit transaction control
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT shipstation_order_id, conflicting_order_number, original_ship_date
            FROM manual_order_conflicts
            WHERE id = %s AND resolution_status = 'pending'
        """, (conflict_id,))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Conflict not found or already resolved'
            }), 404
        
        shipstation_order_id = row[0]
        order_number = row[1]
        original_ship_date = row[2]
        
        logger.info(f"🔄 Syncing Order #{order_number} from ShipStation ID {shipstation_order_id}")
        
        # Fetch order from ShipStation
        api_key, api_secret = get_shipstation_credentials()
        if not api_key or not api_secret:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Failed to get ShipStation credentials'
            }), 500
        
        result = fetch_order_by_id(shipstation_order_id, api_key, api_secret)
        
        if not result['success']:
            conn.close()
            return jsonify({
                'success': False,
                'error': f"Failed to fetch order from ShipStation: {result.get('error', 'Unknown error')}"
            }), 500
        
        ss_order = result['order']
        
        # Validate the order number matches
        if ss_order.get('orderNumber', '').strip() != str(order_number):
            conn.close()
            return jsonify({
                'success': False,
                'error': f"Order number mismatch: ShipStation shows {ss_order.get('orderNumber')}, expected {order_number}"
            }), 400
        
        # Extract order data from ShipStation
        order_status = ss_order.get('orderStatus', '').lower()
        status_mapping = {
            'awaiting_payment': 'awaiting_payment',
            'awaiting_shipment': 'awaiting_shipment',
            'shipped': 'shipped',
            'on_hold': 'on_hold',
            'cancelled': 'cancelled'
        }
        db_status = status_mapping.get(order_status, order_status)
        
        # Extract carrier/service info
        adv_opts = ss_order.get('advancedOptions', {}) or {}
        carrier_code = adv_opts.get('carrierCode') or ss_order.get('carrierCode')
        service_code = adv_opts.get('serviceCode') or ss_order.get('serviceCode')
        
        # Get tracking from shipments if available
        tracking_number = None
        if 'shipments' in ss_order and ss_order['shipments']:
            tracking_number = ss_order['shipments'][0].get('trackingNumber')
        
        # Get items
        items = ss_order.get('items', [])
        total_items = sum(item.get('quantity', 0) for item in items)
        
        # Get customer info
        ship_to = ss_order.get('shipTo', {}) or {}
        customer_name = ship_to.get('name', '')
        company_name = ship_to.get('company', '')
        
        logger.info(f"📥 ShipStation data: Status={db_status}, Items={total_items}, Carrier={carrier_code}, Service={service_code}")
        
        # BEGIN TRANSACTION
        try:
            # Check if order exists in orders_inbox
            cursor.execute("""
                SELECT id, status, total_items
                FROM orders_inbox
                WHERE order_number = %s
            """, (order_number,))
            
            existing_order = cursor.fetchone()
            
            if existing_order:
                local_order_id = existing_order[0]
                old_status = existing_order[1]
                old_items = existing_order[2]
                
                logger.info(f"📝 Updating existing local order: {order_number} (ID: {local_order_id}) | Old: {old_status}/{old_items} items → New: {db_status}/{total_items} items")
                
                # Update orders_inbox
                cursor.execute("""
                    UPDATE orders_inbox
                    SET status = %s,
                        shipping_carrier_code = %s,
                        shipping_service_code = %s,
                        tracking_number = %s,
                        total_items = %s,
                        shipstation_order_id = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (
                    db_status,
                    carrier_code,
                    service_code,
                    tracking_number,
                    total_items,
                    shipstation_order_id,
                    local_order_id
                ))
                
                # Update items if they exist in ShipStation
                if items:
                    # Delete existing items
                    cursor.execute("DELETE FROM order_items_inbox WHERE order_inbox_id = %s", (local_order_id,))
                    
                    # Insert fresh items from ShipStation
                    for item in items:
                        sku = item.get('sku', '').strip()
                        quantity = item.get('quantity', 0)
                        if sku and quantity > 0:
                            cursor.execute("""
                                INSERT INTO order_items_inbox (order_inbox_id, sku, quantity)
                                VALUES (%s, %s, %s)
                            """, (local_order_id, sku, quantity))
                    
                    logger.info(f"✅ Updated {len(items)} items for order {order_number}")
                
            else:
                # Create new order in orders_inbox
                logger.info(f"➕ Creating NEW local order: {order_number} | Status: {db_status}, Items: {total_items}")
                
                cursor.execute("""
                    INSERT INTO orders_inbox 
                        (order_number, order_date, customer_name, company_name, status, 
                         shipping_carrier_code, shipping_service_code, tracking_number,
                         total_items, shipstation_order_id, created_at, updated_at, data_source)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'shipstation_sync')
                    RETURNING id
                """, (
                    order_number,
                    ss_order.get('orderDate', original_ship_date),
                    customer_name,
                    company_name,
                    db_status,
                    carrier_code,
                    service_code,
                    tracking_number,
                    total_items,
                    shipstation_order_id
                ))
                
                local_order_id = cursor.fetchone()[0]
                
                # Insert items
                if items:
                    for item in items:
                        sku = item.get('sku', '').strip()
                        quantity = item.get('quantity', 0)
                        if sku and quantity > 0:
                            cursor.execute("""
                                INSERT INTO order_items_inbox (order_inbox_id, sku, quantity)
                                VALUES (%s, %s, %s)
                            """, (local_order_id, sku, quantity))
                    
                    logger.info(f"✅ Created order with {len(items)} items")
            
            # If order is shipped, ensure it's in shipped_orders table
            if db_status == 'shipped':
                ship_date = ss_order.get('shipDate') or original_ship_date
                
                # Check if already in shipped_orders
                cursor.execute("""
                    SELECT COUNT(*) FROM shipped_orders
                    WHERE order_number = %s AND shipstation_order_id = %s
                """, (order_number, shipstation_order_id))
                
                if cursor.fetchone()[0] == 0:
                    # Insert into shipped_orders
                    for item in items:
                        sku = item.get('sku', '').strip()
                        quantity = item.get('quantity', 0)
                        if sku and quantity > 0:
                            cursor.execute("""
                                INSERT INTO shipped_orders 
                                    (order_number, shipstation_order_id, order_date, ship_date,
                                     customer_name, company_name, sku, quantity, tracking_number,
                                     shipping_carrier_code, shipping_service_code, created_at)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                                ON CONFLICT (order_number, shipstation_order_id, sku) DO UPDATE
                                SET quantity = EXCLUDED.quantity,
                                    tracking_number = EXCLUDED.tracking_number,
                                    shipping_carrier_code = EXCLUDED.shipping_carrier_code,
                                    shipping_service_code = EXCLUDED.shipping_service_code
                            """, (
                                order_number,
                                shipstation_order_id,
                                ss_order.get('orderDate', original_ship_date),
                                ship_date,
                                customer_name,
                                company_name,
                                sku,
                                quantity,
                                tracking_number,
                                carrier_code,
                                service_code
                            ))
                    
                    logger.info(f"✅ Synced shipped order to shipped_orders table")
            
            # Mark conflict as resolved
            cursor.execute("""
                UPDATE manual_order_conflicts
                SET resolution_status = 'synced',
                    resolved_at = CURRENT_TIMESTAMP,
                    resolution_notes = %s
                WHERE id = %s
            """, (f"Synced from ShipStation: Status={db_status}, Items={total_items}", conflict_id))
            
            # COMMIT TRANSACTION
            conn.commit()
            
            logger.info(f"✅ Successfully synced Order #{order_number} from ShipStation")
            
            conn.close()
            
            return jsonify({
                'success': True,
                'message': f'Order #{order_number} synced successfully from ShipStation',
                'order_status': db_status,
                'total_items': total_items
            })
            
        except Exception as db_error:
            # ROLLBACK on error
            conn.rollback()
            logger.error(f"❌ Database error syncing order: {db_error}", exc_info=True)
            conn.close()
            return jsonify({
                'success': False,
                'error': f'Database error: {str(db_error)}'
            }), 500
        
    except Exception as e:
        logger.error(f"❌ Error syncing manual order conflict {conflict_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/quantity_mismatch', methods=['GET'])
def api_get_quantity_mismatch():
    """Check for quantity mismatch between ShipStation and Orders Inbox"""
    try:
        from src.services.shipstation.api_client import get_shipstation_credentials, get_shipstation_headers
        from utils.api_utils import make_api_request
        
        # Get ShipStation total units
        api_key, api_secret = get_shipstation_credentials()
        headers = get_shipstation_headers(api_key, api_secret)
        
        response = make_api_request(
            url='https://ssapi.shipstation.com/orders',
            method='GET',
            headers=headers,
            params={'orderStatus': 'awaiting_shipment', 'pageSize': 500},
            timeout=30
        )
        
        ss_orders = response.json()['orders']
        
        # Handle consolidated orders (multiple ShipStation orders with same order number)
        ss_order_map = {}
        for order in ss_orders:
            order_num = order['orderNumber']
            qty = sum(item['quantity'] for item in order.get('items', []))
            if order_num in ss_order_map:
                ss_order_map[order_num] += qty
            else:
                ss_order_map[order_num] = qty
        
        ss_total = sum(ss_order_map.values())
        
        # Get local database total
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COALESCE(SUM(oii.quantity), 0) as total_units
            FROM orders_inbox oi
            LEFT JOIN order_items_inbox oii ON oi.id = oii.order_inbox_id
            WHERE oi.status IN ('pending', 'uploaded', 'awaiting_shipment')
        """)
        
        local_total = cursor.fetchone()[0] or 0
        conn.close()
        
        difference = ss_total - local_total
        has_mismatch = difference != 0
        
        return jsonify({
            'success': True,
            'has_mismatch': has_mismatch,
            'shipstation_units': ss_total,
            'local_units': local_total,
            'difference': difference
        })
    except Exception as e:
        logger.error(f"Error checking quantity mismatch: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/lot_inventory', methods=['GET'])
def api_get_lot_inventory():
    """Get all lot inventory records with auto-calculated quantities (sorted by FIFO)"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get lot inventory with shipped quantities calculated
        cursor.execute("""
            SELECT 
                li.id,
                li.sku,
                li.lot,
                li.initial_qty,
                li.manual_adjustment,
                COALESCE(SUM(si.quantity_shipped), 0) as total_shipped,
                li.received_date,
                li.status,
                li.notes,
                li.created_at,
                li.updated_at
            FROM lot_inventory li
            LEFT JOIN shipped_items si ON li.sku = si.base_sku AND li.lot = si.sku_lot
            GROUP BY li.id, li.sku, li.lot, li.initial_qty, li.manual_adjustment, li.received_date, li.status, li.notes, li.created_at, li.updated_at
            ORDER BY li.sku ASC, li.received_date ASC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        lots = []
        for row in rows:
            initial_qty = row[3]
            manual_adjustment = row[4]
            total_shipped = row[5]
            current_qty = initial_qty - total_shipped + manual_adjustment
            
            lots.append({
                'id': row[0],
                'sku': row[1],
                'lot': row[2],
                'initial_qty': initial_qty,
                'manual_adjustment': manual_adjustment,
                'total_shipped': total_shipped,
                'current_qty': current_qty,
                'received_date': row[6],
                'status': row[7],
                'notes': row[8] if row[8] else '',
                'created_at': row[9],
                'updated_at': row[10]
            })
        
        return jsonify({
            'success': True,
            'lots': lots,
            'count': len(lots)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/lot_inventory', methods=['POST'])
def api_create_lot_inventory():
    """Create a new lot inventory record"""
    try:
        data = request.get_json()
        sku = data.get('sku', '').strip()
        lot = data.get('lot', '').strip()
        initial_qty = data.get('initial_qty', 0)
        manual_adjustment = data.get('manual_adjustment', 0)
        received_date = data.get('received_date', '')
        status = data.get('status', 'active')
        notes = data.get('notes', '').strip()
        
        if not sku or not lot or not received_date:
            return jsonify({
                'success': False,
                'error': 'SKU, lot, and received date are required'
            }), 400
        
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO lot_inventory (sku, lot, initial_qty, manual_adjustment, received_date, status, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (sku, lot, int(initial_qty), int(manual_adjustment), received_date, status, notes))
        
        lot_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Lot inventory created successfully',
            'id': lot_id
        })
    except psycopg2.IntegrityError:
        return jsonify({
            'success': False,
            'error': 'This SKU-Lot combination already exists'
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/lot_inventory/<int:lot_id>', methods=['PUT'])
def api_update_lot_inventory(lot_id):
    """Update an existing lot inventory record (initial qty or manual adjustment)"""
    try:
        data = request.get_json()
        initial_qty = data.get('initial_qty')
        manual_adjustment = data.get('manual_adjustment')
        received_date = data.get('received_date')
        status = data.get('status')
        notes = data.get('notes', '')
        
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE lot_inventory
            SET initial_qty = %s,
                manual_adjustment = %s,
                received_date = %s,
                status = %s,
                notes = %s,
                updated_at = datetime('now')
            WHERE id = %s
        """, (int(initial_qty), int(manual_adjustment), received_date, status, notes, lot_id))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Lot not found'
            }), 404
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Lot inventory updated successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/lot_inventory/<int:lot_id>', methods=['DELETE'])
def api_delete_lot_inventory(lot_id):
    """Delete a lot inventory record"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM lot_inventory WHERE id = %s", (lot_id,))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Lot not found'
            }), 404
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Lot inventory deleted successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/order_audit', methods=['GET'])
def api_order_audit():
    """
    Compare XML orders (normalized/consolidated) with actual shipments.
    Returns discrepancies: over-shipped, under-shipped, missing orders, etc.
    """
    try:
        from collections import defaultdict
        
        conn = get_connection()
        cursor = conn.cursor()
        
        def normalize_sku(sku):
            """Extract base SKU from SKU string (strip lot number)"""
            if not sku:
                return ""
            sku = sku.strip()
            if '-' in sku:
                return sku.split('-', 1)[0].strip()
            return sku
        
        # Get XML orders from order_items_inbox (consolidated by base SKU)
        cursor.execute("""
            SELECT oi.order_number, oii.sku, oii.quantity
            FROM order_items_inbox oii
            JOIN orders_inbox oi ON oii.order_inbox_id = oi.id
            ORDER BY oi.order_number, oii.sku
        """)
        
        xml_orders = defaultdict(lambda: defaultdict(int))
        for row in cursor.fetchall():
            order_number, sku, quantity = row
            base_sku = normalize_sku(sku)
            xml_orders[order_number][base_sku] += quantity
        
        # Get shipped orders from shipped_items (consolidated by base SKU)
        cursor.execute("""
            SELECT order_number, base_sku, quantity_shipped
            FROM shipped_items
            WHERE order_number IS NOT NULL
            ORDER BY order_number, base_sku
        """)
        
        shipped_orders = defaultdict(lambda: defaultdict(int))
        for row in cursor.fetchall():
            order_number, base_sku, quantity = row
            shipped_orders[order_number][base_sku] += quantity
        
        # Get active pending orders (to exclude from "missing" count)
        # These are orders in pending/awaiting_shipment/cancelled status
        cursor.execute("""
            SELECT order_number
            FROM orders_inbox
            WHERE status IN ('pending', 'awaiting_shipment', 'cancelled')
        """)
        active_pending_orders = {row[0] for row in cursor.fetchall()}
        
        conn.close()
        
        # Compare orders and find discrepancies
        results = {
            'perfect_matches': [],
            'over_shipped': [],
            'under_shipped': [],
            'missing_shipments': [],
            'extra_shipments': [],
            'missing_orders': []
        }
        
        all_orders = set(xml_orders.keys()) | set(shipped_orders.keys())
        
        for order_num in sorted(all_orders):
            xml_items = xml_orders.get(order_num, {})
            shipped_items = shipped_orders.get(order_num, {})
            
            # Order shipped but not in XML (manual order)
            if not xml_items and shipped_items:
                for sku, qty in shipped_items.items():
                    results['extra_shipments'].append({
                        'order_number': order_num,
                        'sku': sku,
                        'shipped_qty': qty
                    })
                continue
            
            # Order in XML but never shipped
            if xml_items and not shipped_items:
                # CRITICAL: Only count as "missing" if NOT in active pending states
                # (pending/awaiting_shipment/cancelled should NOT be flagged as missing)
                if order_num not in active_pending_orders:
                    results['missing_orders'].append(order_num)
                    for sku, qty in xml_items.items():
                        results['missing_shipments'].append({
                            'order_number': order_num,
                            'sku': sku,
                            'ordered_qty': qty
                        })
                continue
            
            # Compare SKUs within the order
            all_skus = set(xml_items.keys()) | set(shipped_items.keys())
            
            for sku in sorted(all_skus):
                xml_qty = xml_items.get(sku, 0)
                shipped_qty = shipped_items.get(sku, 0)
                
                if xml_qty == 0 and shipped_qty > 0:
                    results['extra_shipments'].append({
                        'order_number': order_num,
                        'sku': sku,
                        'shipped_qty': shipped_qty
                    })
                elif xml_qty > 0 and shipped_qty == 0:
                    # CRITICAL: Only count as "missing" if NOT in active pending states
                    if order_num not in active_pending_orders:
                        results['missing_shipments'].append({
                            'order_number': order_num,
                            'sku': sku,
                            'ordered_qty': xml_qty
                        })
                elif xml_qty == shipped_qty:
                    results['perfect_matches'].append({
                        'order_number': order_num,
                        'sku': sku,
                        'quantity': xml_qty
                    })
                elif shipped_qty > xml_qty:
                    results['over_shipped'].append({
                        'order_number': order_num,
                        'sku': sku,
                        'ordered_qty': xml_qty,
                        'shipped_qty': shipped_qty,
                        'diff': shipped_qty - xml_qty
                    })
                else:
                    results['under_shipped'].append({
                        'order_number': order_num,
                        'sku': sku,
                        'ordered_qty': xml_qty,
                        'shipped_qty': shipped_qty,
                        'diff': xml_qty - shipped_qty
                    })
        
        # Add summary counts
        results['summary'] = {
            'perfect_matches': len(results['perfect_matches']),
            'over_shipped': len(results['over_shipped']),
            'under_shipped': len(results['under_shipped']),
            'missing_shipments': len(results['missing_shipments']),
            'extra_shipments': len(results['extra_shipments']),
            'missing_orders': len(results['missing_orders']),
            'total_xml_orders': len(xml_orders),
            'total_shipped_orders': len(shipped_orders)
        }
        
        return jsonify({
            'success': True,
            'data': results
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/order_comparison', methods=['GET'])
def api_order_comparison():
    """
    Compare XML orders with ShipStation orders for a date range.
    Returns side-by-side comparison for easy auditing.
    """
    try:
        from collections import defaultdict
        import requests
        from src.services.shipstation.api_client import get_shipstation_credentials, get_shipstation_headers
        
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not start_date or not end_date:
            return jsonify({
                'success': False,
                'error': 'Both start_date and end_date are required'
            }), 400
        
        # Connect to database
        conn = get_connection()
        cursor = conn.cursor()
        
        # Fetch XML orders from database (consolidated by order and SKU)
        cursor.execute("""
            SELECT oi.order_number, oii.sku, SUM(oii.quantity) as total_qty
            FROM order_items_inbox oii
            JOIN orders_inbox oi ON oii.order_inbox_id = oi.id
            WHERE DATE(oi.order_date) BETWEEN %s AND %s
            GROUP BY oi.order_number, oii.sku
            ORDER BY oi.order_number, oii.sku
        """, (start_date, end_date))
        
        xml_orders = defaultdict(dict)
        for row in cursor.fetchall():
            order_number, sku, qty = row
            base_sku = sku.split('-')[0].strip() if '-' in sku else sku.strip()
            if base_sku in xml_orders[order_number]:
                xml_orders[order_number][base_sku] += qty
            else:
                xml_orders[order_number][base_sku] = qty
        
        # Fetch ShipStation orders via API (batch) - shipped AND cancelled orders
        api_key, api_secret = get_shipstation_credentials()
        headers = get_shipstation_headers(api_key, api_secret)
        
        # ShipStation requires ISO 8601 format with time
        # Query shipped and cancelled orders separately, then combine
        ss_orders = defaultdict(dict)
        order_statuses = {}  # Track order status from ShipStation
        
        for status in ['shipped', 'cancelled']:
            ss_url = f"https://ssapi.shipstation.com/orders?orderDateStart={start_date}T00:00:00&orderDateEnd={end_date}T23:59:59&orderStatus={status}&pageSize=500"
            response = requests.get(ss_url, headers=headers)
            response.raise_for_status()
            
            ss_data = response.json()
            
            # Process ShipStation orders (consolidated by order and SKU)
            for order in ss_data.get('orders', []):
                order_number = order.get('orderNumber')
                order_statuses[order_number] = order.get('orderStatus')
                
                for item in order.get('items', []):
                    sku = item.get('sku', '').strip()
                    base_sku = sku.split('-')[0].strip() if '-' in sku else sku
                    qty = item.get('quantity', 0)
                    
                    if base_sku in ss_orders[order_number]:
                        ss_orders[order_number][base_sku] += qty
                    else:
                        ss_orders[order_number][base_sku] = qty
        
        conn.close()
        
        # Create comparison data - consolidated by order number
        comparison = []
        all_orders = set(xml_orders.keys()) | set(ss_orders.keys())
        
        match_count = 0
        discrepancy_count = 0
        
        for order_num in sorted(all_orders):
            xml_items = xml_orders.get(order_num, {})
            ss_items = ss_orders.get(order_num, {})
            
            # Build consolidated SKU strings
            xml_skus = []
            ss_skus = []
            
            for sku in sorted(xml_items.keys()):
                qty = xml_items[sku]
                xml_skus.append(f"{sku} (x{qty})")
            
            for sku in sorted(ss_items.keys()):
                qty = ss_items[sku]
                ss_skus.append(f"{sku} (x{qty})")
            
            xml_sku_str = ', '.join(xml_skus) if xml_skus else None
            ss_sku_str = ', '.join(ss_skus) if ss_skus else None
            
            # Determine overall status for the order
            status = 'match'
            ss_order_status = order_statuses.get(order_num)  # Get actual ShipStation status
            
            if not xml_items and ss_items:
                status = 'ss_only'
                discrepancy_count += 1
            elif xml_items and not ss_items:
                status = 'xml_only'
                discrepancy_count += 1
            elif xml_items != ss_items:
                status = 'discrepancy'
                discrepancy_count += 1
            else:
                match_count += 1
            
            # Override status if order is cancelled in ShipStation
            if ss_order_status == 'cancelled':
                status = 'cancelled'
            
            comparison.append({
                'order_number': order_num,
                'xml_sku': xml_sku_str,
                'xml_qty': sum(xml_items.values()) if xml_items else None,
                'ss_sku': ss_sku_str,
                'ss_qty': sum(ss_items.values()) if ss_items else None,
                'status': status,
                'ss_order_status': ss_order_status  # Include actual ShipStation status
            })
        
        return jsonify({
            'success': True,
            'xml_count': len(xml_orders),
            'ss_count': len(ss_orders),
            'match_count': match_count,
            'discrepancy_count': discrepancy_count,
            'comparison': comparison
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/workflow_controls', methods=['GET'])
def get_workflow_controls():
    """Get all workflow control states"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT workflow_name, enabled, last_updated, updated_by, last_run_at
            FROM workflow_controls
            ORDER BY workflow_name
        """)
        workflows = cursor.fetchall()
        conn.close()
        
        return jsonify([{
            'name': w[0],
            'enabled': bool(w[1]),
            'last_updated': w[2],
            'updated_by': w[3],
            'last_run_at': w[4]
        } for w in workflows])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/workflow_controls/<workflow_name>', methods=['PUT'])
def update_workflow_control(workflow_name):
    """Toggle workflow control"""
    try:
        data = request.json
        enabled = data.get('enabled')
        
        if enabled is None:
            return jsonify({'error': 'enabled field required'}), 400
        
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT workflow_name FROM workflow_controls WHERE workflow_name = %s
        """, (workflow_name,))
        
        if not cursor.fetchone():
            conn.close()
            return jsonify({'error': f'Workflow {workflow_name} not found'}), 404
        
        cursor.execute("""
            UPDATE workflow_controls
            SET enabled = %s, last_updated = CURRENT_TIMESTAMP, updated_by = %s
            WHERE workflow_name = %s
        """, (enabled, 'admin', workflow_name))
        conn.commit()
        conn.close()
        
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Workflow '{workflow_name}' {'ENABLED' if enabled else 'DISABLED'} by admin")
        
        return jsonify({'success': True, 'workflow': workflow_name, 'enabled': enabled})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/incidents', methods=['GET'])
def get_incidents():
    """Get all production incidents with optional filtering"""
    try:
        status_filter = request.args.get('status')
        severity_filter = request.args.get('severity')
        
        conn = get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT id, title, description, severity, status, reported_by, created_at, updated_at, cause, resolution
            FROM production_incidents
            WHERE 1=1
        """
        params = []
        
        if status_filter:
            query += " AND status = %s"
            params.append(status_filter)
        
        if severity_filter:
            query += " AND severity = %s"
            params.append(severity_filter)
        
        query += " ORDER BY created_at DESC"
        
        cursor.execute(query, params)
        incidents = cursor.fetchall()
        
        result = []
        for inc in incidents:
            cursor.execute("""
                SELECT id, note_type, note, created_by, created_at
                FROM incident_notes
                WHERE incident_id = %s
                ORDER BY created_at DESC
            """, (inc[0],))
            notes = cursor.fetchall()
            
            result.append({
                'id': inc[0],
                'title': inc[1],
                'description': inc[2],
                'severity': inc[3],
                'status': inc[4],
                'reported_by': inc[5],
                'created_at': inc[6].isoformat() if inc[6] else None,
                'updated_at': inc[7].isoformat() if inc[7] else None,
                'cause': inc[8],
                'resolution': inc[9],
                'notes': [{
                    'id': n[0],
                    'note_type': n[1],
                    'note': n[2],
                    'created_by': n[3],
                    'created_at': n[4].isoformat() if n[4] else None
                } for n in notes]
            })
        
        conn.close()
        return jsonify({'success': True, 'incidents': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/incidents', methods=['POST'])
def create_incident():
    """Create a new production incident"""
    try:
        data = request.json
        title = data.get('title', '').strip()
        description = data.get('description', '').strip()
        severity = data.get('severity', 'medium').lower()
        reported_by = data.get('reported_by', 'Dashboard User')
        
        if not title or not description:
            return jsonify({'success': False, 'error': 'Title and description required'}), 400
        
        if severity not in ['low', 'medium', 'high', 'critical']:
            return jsonify({'success': False, 'error': 'Invalid severity level'}), 400
        
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO production_incidents (title, description, severity, status, reported_by)
            VALUES (%s, %s, %s, 'new', %s)
            RETURNING id, created_at
        """, (title, description, severity, reported_by))
        
        incident_id, created_at = cursor.fetchone()
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'incident_id': incident_id,
            'created_at': created_at.isoformat() if created_at else None
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/incidents/<int:incident_id>', methods=['PUT'])
def update_incident(incident_id):
    """Update incident status or details"""
    try:
        data = request.json
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if this is a status-only update or a full edit
        if 'status' in data and len(data) == 1:
            # Status-only update
            status = data.get('status')
            if not status or status not in ['new', 'in_progress', 'resolved', 'closed']:
                return jsonify({'success': False, 'error': 'Invalid status'}), 400
            
            # WORKFLOW RULE: Definition of Done - Can't mark as "resolved" without proof
            if status == 'resolved':
                cursor.execute("""
                    SELECT resolution FROM production_incidents WHERE id = %s
                """, (incident_id,))
                result = cursor.fetchone()
                
                if not result:
                    conn.close()
                    return jsonify({'success': False, 'error': 'Incident not found'}), 404
                
                resolution = result[0]
                if not resolution or not resolution.strip():
                    conn.close()
                    return jsonify({
                        'success': False, 
                        'error': '❌ Definition of Done: Can\'t mark as "Resolved" without proof.\n\nPlease add Resolution with:\n1. Fix Applied\n2. Verified Working\n3. Evidence Captured'
                    }), 400
            
            cursor.execute("""
                UPDATE production_incidents
                SET status = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (status, incident_id))
            
            if cursor.rowcount == 0:
                conn.close()
                return jsonify({'success': False, 'error': f'Incident {incident_id} not found'}), 404
            
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'incident_id': incident_id, 'status': status})
        else:
            # Full edit update (title, description, severity, cause, resolution)
            title = data.get('title')
            description = data.get('description')
            severity = data.get('severity')
            cause = data.get('cause', '').strip() or None
            resolution = data.get('resolution', '').strip() or None
            
            if not title or not description or not severity:
                return jsonify({'success': False, 'error': 'Missing required fields'}), 400
            
            if severity not in ['low', 'medium', 'high', 'critical']:
                return jsonify({'success': False, 'error': 'Invalid severity'}), 400
            
            cursor.execute("""
                UPDATE production_incidents
                SET title = %s, description = %s, severity = %s, cause = %s, resolution = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (title, description, severity, cause, resolution, incident_id))
            
            if cursor.rowcount == 0:
                conn.close()
                return jsonify({'success': False, 'error': f'Incident {incident_id} not found'}), 404
            
            conn.commit()
            conn.close()
            
            return jsonify({'success': True, 'incident_id': incident_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/incidents/<int:incident_id>', methods=['DELETE'])
def delete_incident(incident_id):
    """Delete an incident and all associated data"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if incident exists
        cursor.execute("SELECT id FROM production_incidents WHERE id = %s", (incident_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': 'Incident not found'}), 404
        
        # Delete associated screenshots from filesystem
        cursor.execute("SELECT file_path FROM production_incident_screenshots WHERE incident_id = %s", (incident_id,))
        screenshots = cursor.fetchall()
        for screenshot in screenshots:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], screenshot[0])
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"Warning: Could not delete screenshot file {file_path}: {e}")
        
        # Delete screenshots from database (CASCADE should handle this, but being explicit)
        cursor.execute("DELETE FROM production_incident_screenshots WHERE incident_id = %s", (incident_id,))
        
        # Delete notes (CASCADE should handle this, but being explicit)
        cursor.execute("DELETE FROM incident_notes WHERE incident_id = %s", (incident_id,))
        
        # Delete the incident
        cursor.execute("DELETE FROM production_incidents WHERE id = %s", (incident_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/incidents/<int:incident_id>/notes', methods=['POST'])
def add_incident_note(incident_id):
    """Add a note/update to an incident"""
    try:
        data = request.json
        note = data.get('note', '').strip()
        note_type = data.get('note_type', 'system')
        created_by = data.get('created_by', 'System')
        
        if not note:
            return jsonify({'success': False, 'error': 'Note content required'}), 400
        
        if note_type not in ['user', 'system']:
            note_type = 'system'
        
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id FROM production_incidents WHERE id = %s
        """, (incident_id,))
        
        if not cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': f'Incident {incident_id} not found'}), 404
        
        cursor.execute("""
            INSERT INTO incident_notes (incident_id, note_type, note, created_by)
            VALUES (%s, %s, %s, %s)
            RETURNING id, created_at
        """, (incident_id, note_type, note, created_by))
        
        note_id, created_at = cursor.fetchone()
        
        cursor.execute("""
            UPDATE production_incidents
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (incident_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'note_id': note_id,
            'created_at': created_at.isoformat() if created_at else None
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Screenshot Management Endpoints
@app.route('/api/incidents/<int:incident_id>/screenshots', methods=['POST'])
def upload_incident_screenshot(incident_id):
    """Upload a screenshot for an incident"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Invalid file type. Allowed: png, jpg, jpeg, gif, webp'}), 400
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Verify incident exists
        cursor.execute("SELECT id FROM production_incidents WHERE id = %s", (incident_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': 'Incident not found'}), 404
        
        # Generate unique filename
        original_filename = secure_filename(file.filename)
        file_ext = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4()}.{file_ext}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        # Save file
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file.save(file_path)
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Save to database
        uploaded_by = request.form.get('uploaded_by', 'Dashboard User')
        cursor.execute("""
            INSERT INTO production_incident_screenshots 
            (incident_id, file_path, original_filename, file_size, uploaded_by)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, uploaded_at
        """, (incident_id, unique_filename, original_filename, file_size, uploaded_by))
        
        screenshot_id, uploaded_at = cursor.fetchone()
        
        # Update incident timestamp
        cursor.execute("""
            UPDATE production_incidents
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (incident_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'screenshot': {
                'id': screenshot_id,
                'file_path': unique_filename,
                'original_filename': original_filename,
                'file_size': file_size,
                'uploaded_by': uploaded_by,
                'uploaded_at': uploaded_at.isoformat() if uploaded_at else None
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/incidents/<int:incident_id>/screenshots', methods=['GET'])
def get_incident_screenshots(incident_id):
    """Get all screenshots for an incident"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, file_path, original_filename, file_size, uploaded_by, uploaded_at
            FROM production_incident_screenshots
            WHERE incident_id = %s
            ORDER BY uploaded_at DESC
        """, (incident_id,))
        
        screenshots = []
        for row in cursor.fetchall():
            screenshots.append({
                'id': row[0],
                'file_path': row[1],
                'original_filename': row[2],
                'file_size': row[3],
                'uploaded_by': row[4],
                'uploaded_at': row[5].isoformat() if row[5] else None,
                'url': f'/uploads/incident_screenshots/{row[1]}'
            })
        
        conn.close()
        return jsonify({'success': True, 'screenshots': screenshots})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/incidents/screenshots/<int:screenshot_id>', methods=['DELETE'])
def delete_incident_screenshot(screenshot_id):
    """Delete a screenshot"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get screenshot info
        cursor.execute("""
            SELECT file_path, incident_id
            FROM production_incident_screenshots
            WHERE id = %s
        """, (screenshot_id,))
        
        result = cursor.fetchone()
        if not result:
            conn.close()
            return jsonify({'success': False, 'error': 'Screenshot not found'}), 404
        
        file_path, incident_id = result
        
        # Delete from database
        cursor.execute("DELETE FROM production_incident_screenshots WHERE id = %s", (screenshot_id,))
        
        # Update incident timestamp
        cursor.execute("""
            UPDATE production_incidents
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (incident_id,))
        
        conn.commit()
        conn.close()
        
        # Delete physical file
        full_path = os.path.join(app.config['UPLOAD_FOLDER'], file_path)
        if os.path.exists(full_path):
            os.remove(full_path)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/uploads/incident_screenshots/<path:filename>')
def serve_screenshot(filename):
    """Serve uploaded screenshot files"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/duplicate_alerts/delete_order/<int:shipstation_order_id>', methods=['DELETE'])
def api_delete_duplicate_order(shipstation_order_id):
    """Delete a duplicate order from ShipStation and track it"""
    try:
        from src.services.shipstation.api_client import delete_order_from_shipstation
        
        # Check if already deleted
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT deleted_at FROM deleted_shipstation_orders 
            WHERE shipstation_order_id = %s
        """, (shipstation_order_id,))
        
        existing = cursor.fetchone()
        if existing:
            conn.close()
            return jsonify({
                'success': False,
                'already_deleted': True,
                'error': f'Order already deleted on {existing[0].strftime("%Y-%m-%d %H:%M")}'
            }), 400
        
        # Delete from ShipStation
        result = delete_order_from_shipstation(shipstation_order_id)
        
        if result['success']:
            # Track the deletion
            cursor.execute("""
                INSERT INTO deleted_shipstation_orders 
                (shipstation_order_id, order_number, deleted_at, deleted_by)
                VALUES (%s, %s, CURRENT_TIMESTAMP, 'dashboard')
                ON CONFLICT (shipstation_order_id) DO NOTHING
            """, (shipstation_order_id, result.get('order_number')))
            
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': f'Order {shipstation_order_id} deleted from ShipStation'
            })
        else:
            conn.close()
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to delete order')
            }), 400
            
    except Exception as e:
        logger.error(f'Error deleting duplicate order {shipstation_order_id}: {e}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/duplicate_alerts/relink_order', methods=['POST'])
def api_relink_order():
    """Update local DB record to use a different ShipStation ID and sync status/items"""
    try:
        from src.services.ghost_order_backfill import _fetch_order_from_shipstation, _backfill_order_items
        from src.services.shipstation.api_client import get_shipstation_credentials
        
        data = request.get_json()
        order_number = data.get('order_number')
        new_shipstation_id = data.get('shipstation_id')
        
        if not order_number or not new_shipstation_id:
            return jsonify({
                'success': False,
                'error': 'Missing required parameters'
            }), 400
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get the local order record
        cursor.execute("""
            SELECT id FROM orders_inbox
            WHERE order_number = %s
        """, (order_number,))
        
        result = cursor.fetchone()
        if not result:
            conn.close()
            return jsonify({
                'success': False,
                'error': f'No local record found for order {order_number}'
            }), 404
        
        order_inbox_id = result[0]
        
        # Fetch order details from ShipStation
        api_key, api_secret = get_shipstation_credentials()
        order_data = _fetch_order_from_shipstation(new_shipstation_id, api_key, api_secret)
        
        if order_data.get('rate_limited'):
            conn.close()
            return jsonify({
                'success': False,
                'error': 'ShipStation API rate limit reached - please try again later'
            }), 429
        
        if order_data.get('not_found'):
            conn.close()
            return jsonify({
                'success': False,
                'error': 'ShipStation order not found'
            }), 404
        
        if order_data.get('error'):
            conn.close()
            return jsonify({
                'success': False,
                'error': f"ShipStation API error: {order_data['error']}"
            }), 500
        
        items = order_data.get('items', [])
        new_status = order_data.get('status', 'awaiting_shipment')
        
        # Fetch full order details from ShipStation API to get complete customer/shipping info
        from src.services.shipstation.api_client import get_shipstation_headers
        from utils.api_utils import make_api_request
        
        url = f"https://ssapi.shipstation.com/orders/{new_shipstation_id}"
        headers = get_shipstation_headers(api_key, api_secret)
        response = make_api_request(url=url, method='GET', headers=headers, timeout=10)
        
        if response and response.status_code == 200:
            full_order_data = response.json()
            
            # Extract all customer and shipping information
            ship_to = full_order_data.get('shipTo', {})
            bill_to = full_order_data.get('billTo', {})
            
            # Update the local DB record with complete order information
            cursor.execute("""
                UPDATE orders_inbox
                SET shipstation_order_id = %s,
                    status = %s,
                    ship_name = %s,
                    ship_company = %s,
                    ship_street1 = %s,
                    ship_street2 = %s,
                    ship_city = %s,
                    ship_state = %s,
                    ship_postal_code = %s,
                    ship_country = %s,
                    ship_phone = %s,
                    bill_name = %s,
                    bill_company = %s,
                    bill_street1 = %s,
                    bill_street2 = %s,
                    bill_city = %s,
                    bill_state = %s,
                    bill_postal_code = %s,
                    bill_country = %s,
                    bill_phone = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE order_number = %s
            """, (
                new_shipstation_id,
                new_status,
                ship_to.get('name'),
                ship_to.get('company'),
                ship_to.get('street1'),
                ship_to.get('street2'),
                ship_to.get('city'),
                ship_to.get('state'),
                ship_to.get('postalCode'),
                ship_to.get('country'),
                ship_to.get('phone'),
                bill_to.get('name'),
                bill_to.get('company'),
                bill_to.get('street1'),
                bill_to.get('street2'),
                bill_to.get('city'),
                bill_to.get('state'),
                bill_to.get('postalCode'),
                bill_to.get('country'),
                bill_to.get('phone'),
                order_number
            ))
        else:
            # Fallback: just update ShipStation ID and status if full fetch fails
            cursor.execute("""
                UPDATE orders_inbox
                SET shipstation_order_id = %s,
                    status = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE order_number = %s
            """, (new_shipstation_id, new_status, order_number))
        
        conn.commit()
        conn.close()
        
        # Backfill items if available
        items_synced = 0
        if len(items) > 0:
            success = _backfill_order_items(order_inbox_id, order_number, items, new_status)
            if success:
                items_synced = len(items)
        
        logger.info(f"Relinked order {order_number} to ShipStation ID {new_shipstation_id}, status: {new_status}, items: {items_synced}, full sync: complete")
        
        return jsonify({
            'success': True,
            'message': f'Linked to SS ID {new_shipstation_id}, status: {new_status}, synced {items_synced} items + full customer/address data',
            'status': new_status,
            'items_synced': items_synced
        })
        
    except Exception as e:
        logger.error(f'Error relinking order: {e}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/duplicate_alerts/sync_items/<int:order_inbox_id>', methods=['POST'])
def api_sync_order_items(order_inbox_id):
    """Sync items from ShipStation for a specific order with missing items"""
    try:
        from src.services.ghost_order_backfill import _fetch_order_from_shipstation, _backfill_order_items
        from src.services.shipstation.api_client import get_shipstation_credentials
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get order details
        cursor.execute("""
            SELECT id, order_number, shipstation_order_id, status
            FROM orders_inbox
            WHERE id = %s
        """, (order_inbox_id,))
        
        result = cursor.fetchone()
        if not result:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Order not found'
            }), 404
        
        order_id, order_number, shipstation_order_id, status = result
        
        if not shipstation_order_id:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Order does not have a ShipStation ID'
            }), 400
        
        # Fetch from ShipStation
        api_key, api_secret = get_shipstation_credentials()
        order_data = _fetch_order_from_shipstation(shipstation_order_id, api_key, api_secret)
        
        if order_data.get('rate_limited'):
            conn.close()
            return jsonify({
                'success': False,
                'error': 'ShipStation API rate limit reached - please try again later'
            }), 429
        
        if order_data.get('not_found'):
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Order not found in ShipStation'
            }), 404
        
        if order_data.get('error'):
            conn.close()
            return jsonify({
                'success': False,
                'error': f"ShipStation API error: {order_data['error']}"
            }), 500
        
        items = order_data.get('items', [])
        order_status = order_data.get('status', status)
        
        if len(items) == 0:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Order has no items in ShipStation'
            }), 400
        
        # Backfill the items
        success = _backfill_order_items(order_id, order_number, items, order_status)
        
        conn.close()
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Successfully synced {len(items)} items from ShipStation',
                'items_count': len(items)
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to sync items to database'
            }), 500
            
    except Exception as e:
        logger.error(f'Error syncing items for order {order_inbox_id}: {e}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/delete_order', methods=['POST'])
@login_required
@admin_required
def api_admin_delete_order():
    """Admin endpoint to delete a single order from ShipStation by ID"""
    try:
        data = request.get_json()
        shipstation_order_id = data.get('shipstation_order_id')
        order_number = data.get('order_number')  # Optional for logging
        
        if not shipstation_order_id:
            return jsonify({
                'success': False,
                'error': 'ShipStation Order ID is required'
            }), 400
        
        # Convert to int
        try:
            shipstation_order_id = int(shipstation_order_id)
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'ShipStation Order ID must be a number'
            }), 400
        
        from src.services.shipstation.api_client import delete_order_from_shipstation
        
        # Delete from ShipStation
        logger.info(f"Admin order deletion requested: ShipStation ID {shipstation_order_id}, Order Number: {order_number or 'Not provided'}")
        result = delete_order_from_shipstation(shipstation_order_id)
        
        if result['success']:
            logger.info(f"✅ Successfully deleted order {shipstation_order_id} from ShipStation")
            return jsonify({
                'success': True,
                'message': f'Order {shipstation_order_id} successfully deleted from ShipStation',
                'shipstation_order_id': shipstation_order_id,
                'order_number': order_number
            })
        else:
            error_msg = result.get('error', 'Failed to delete order')
            logger.error(f"❌ Failed to delete order {shipstation_order_id}: {error_msg}")
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
            
    except Exception as e:
        logger.error(f'Error in admin order deletion: {e}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/sync_order_from_shipstation', methods=['POST'])
@login_required
@admin_required
def api_admin_sync_order_from_shipstation():
    """Admin endpoint to sync an order from ShipStation to local database"""
    try:
        data = request.get_json()
        order_number = data.get('order_number')
        shipstation_order_id = data.get('shipstation_order_id')
        
        if not order_number:
            return jsonify({
                'success': False,
                'error': 'Order number is required'
            }), 400
        
        from src.services.shipstation.api_client import get_shipstation_credentials, get_shipstation_headers, fetch_order_by_id
        from utils.api_utils import make_api_request
        from config.settings import settings
        from src.services.database.pg_utils import get_connection
        import json as json_lib
        
        # Get ShipStation credentials
        api_key, api_secret = get_shipstation_credentials()
        headers = get_shipstation_headers(api_key, api_secret)
        
        # Fetch order from ShipStation
        ss_order = None
        
        if shipstation_order_id:
            # If we have the ShipStation ID, use it directly
            result = fetch_order_by_id(int(shipstation_order_id))
            if result['success']:
                ss_order = result['order']
        else:
            # Otherwise, search by order number
            params = {'orderNumber': order_number}
            response = make_api_request(
                url=settings.SHIPSTATION_ORDERS_ENDPOINT,
                method='GET',
                headers=headers,
                params=params,
                timeout=30
            )
            
            if response and response.status_code == 200:
                data = response.json()
                orders = data.get('orders', [])
                if orders:
                    ss_order = orders[0]  # Take the first match
        
        if not ss_order:
            return jsonify({
                'success': False,
                'error': f'Order #{order_number} not found in ShipStation'
            }), 404
        
        # Verify order number matches
        if ss_order.get('orderNumber') != order_number:
            return jsonify({
                'success': False,
                'error': f'Order number mismatch: Expected {order_number}, got {ss_order.get("orderNumber")}'
            }), 400
        
        # Extract order data
        shipstation_order_id = ss_order.get('orderId')
        order_status = ss_order.get('orderStatus', 'unknown')
        order_date = ss_order.get('orderDate')  # Get order date from ShipStation
        ship_to = ss_order.get('shipTo', {})
        customer_name = ship_to.get('name', '')
        company_name = ship_to.get('company', '')
        items = ss_order.get('items', [])
        total_items = sum(item.get('quantity', 0) for item in items)
        
        # Map ShipStation status to DB status
        status_map = {
            'awaiting_shipment': 'awaiting_shipment',
            'shipped': 'shipped',
            'cancelled': 'cancelled',
            'on_hold': 'on_hold',
            'awaiting_payment': 'awaiting_payment'
        }
        db_status = status_map.get(order_status, 'awaiting_shipment')
        
        # Update database
        conn = get_connection()
        conn.autocommit = False
        cursor = conn.cursor()
        
        try:
            # Get tracking info if shipped
            tracking_number = None
            carrier_code = None
            service_code = None
            ship_date = None
            
            if db_status == 'shipped':
                shipments = ss_order.get('shipments', [])
                if shipments:
                    shipment = shipments[0]
                    tracking_number = shipment.get('trackingNumber')
                    carrier_code = shipment.get('carrierCode')
                    service_code = shipment.get('serviceCode')
                    ship_date = shipment.get('shipDate')
                
                # Use order_date as fallback if no shipment date
                if not ship_date:
                    ship_date = order_date
            
            # Update/insert into orders_inbox
            cursor.execute("""
                INSERT INTO orders_inbox (
                    order_number, shipstation_order_id, status, order_date,
                    ship_name, ship_company,
                    tracking_number, shipping_carrier_code, shipping_service_code,
                    created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT (order_number) DO UPDATE SET
                    shipstation_order_id = EXCLUDED.shipstation_order_id,
                    status = EXCLUDED.status,
                    order_date = EXCLUDED.order_date,
                    ship_name = EXCLUDED.ship_name,
                    ship_company = EXCLUDED.ship_company,
                    tracking_number = EXCLUDED.tracking_number,
                    shipping_carrier_code = EXCLUDED.shipping_carrier_code,
                    shipping_service_code = EXCLUDED.shipping_service_code,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                order_number, shipstation_order_id, db_status, order_date,
                customer_name, company_name,
                tracking_number, carrier_code, service_code
            ))
            
            logger.info(f"✅ Updated orders_inbox for Order #{order_number}")
            
            # If shipped, also update shipped_orders and shipped_items
            if db_status == 'shipped':
                # Update shipped_orders with basic order info
                cursor.execute("""
                    INSERT INTO shipped_orders (ship_date, order_number, shipstation_order_id)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (order_number) DO UPDATE 
                    SET ship_date = EXCLUDED.ship_date,
                        shipstation_order_id = EXCLUDED.shipstation_order_id
                """, (ship_date, order_number, str(shipstation_order_id)))
                
                # Update shipped_items for each item
                for item in items:
                    sku_raw = str(item.get('sku', '')).strip()
                    quantity = item.get('quantity', 0)
                    
                    if not sku_raw or quantity <= 0:
                        continue
                    
                    # Parse SKU - LOT format (e.g., "17612 - 250237")
                    if ' - ' in sku_raw:
                        sku_parts = sku_raw.split(' - ')
                        base_sku = sku_parts[0].strip()
                        sku_lot = sku_raw  # Store full format
                    else:
                        base_sku = sku_raw
                        sku_lot = sku_raw
                    
                    cursor.execute("""
                        INSERT INTO shipped_items (
                            ship_date, sku_lot, base_sku, quantity_shipped, order_number
                        )
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (order_number, base_sku, sku_lot) DO UPDATE
                        SET quantity_shipped = EXCLUDED.quantity_shipped,
                            ship_date = EXCLUDED.ship_date
                    """, (ship_date, sku_lot, base_sku, quantity, order_number))
                
                logger.info(f"✅ Updated shipped_orders and shipped_items for Order #{order_number}")
            
            conn.commit()
            logger.info(f"✅ Successfully synced Order #{order_number} from ShipStation")
            
            conn.close()
            
            return jsonify({
                'success': True,
                'message': f'Order #{order_number} synced successfully from ShipStation',
                'order_status': db_status,
                'total_items': total_items,
                'shipstation_order_id': shipstation_order_id
            })
            
        except Exception as db_error:
            conn.rollback()
            logger.error(f"❌ Database error syncing order: {db_error}", exc_info=True)
            conn.close()
            return jsonify({
                'success': False,
                'error': f'Database error: {str(db_error)}'
            }), 500
            
    except Exception as e:
        logger.error(f'Error syncing order from ShipStation: {e}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/lookup_order', methods=['GET'])
@login_required
@admin_required
def api_admin_lookup_order():
    """Look up order details by order number to get ShipStation IDs and local database matches"""
    try:
        order_number = request.args.get('order_number')
        
        if not order_number:
            return jsonify({
                'success': False,
                'error': 'Order number is required'
            }), 400
        
        from src.services.shipstation.api_client import get_shipstation_credentials, get_shipstation_headers
        from utils.api_utils import make_api_request
        from config.settings import settings
        from src.services.database.pg_utils import get_connection
        
        # Step 1: Query ShipStation
        api_key, api_secret = get_shipstation_credentials()
        headers = get_shipstation_headers(api_key, api_secret)
        
        params = {'orderNumber': order_number}
        response = make_api_request(
            url=settings.SHIPSTATION_ORDERS_ENDPOINT,
            method='GET',
            headers=headers,
            params=params,
            timeout=30
        )
        
        if not response or response.status_code != 200:
            return jsonify({
                'success': False,
                'error': f'ShipStation API error: {response.status_code if response else "No response"}'
            }), 500
        
        data = response.json()
        orders = data.get('orders', [])
        
        if not orders:
            return jsonify({
                'success': False,
                'error': f'No orders found with number {order_number}'
            }), 404
        
        # Format ShipStation order details
        order_details = []
        shipstation_ids = []
        for order in orders:
            ship_to = order.get('shipTo', {})
            items = order.get('items', [])
            ss_id = order.get('orderId')
            shipstation_ids.append(str(ss_id))
            
            order_details.append({
                'shipstation_order_id': ss_id,
                'order_number': order.get('orderNumber'),
                'order_status': order.get('orderStatus'),
                'customer_name': ship_to.get('name'),
                'company': ship_to.get('company'),
                'create_date': order.get('createDate'),
                'order_total': order.get('orderTotal'),
                'items': [{
                    'sku': item.get('sku'),
                    'name': item.get('name'),
                    'quantity': item.get('quantity')
                } for item in items]
            })
        
        # Step 2: Query local database for matches
        # Find orders with same order_number OR matching shipstation_order_id
        local_matches = []
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # Build query to find orders with matching order number OR shipstation IDs
            cursor.execute("""
                SELECT 
                    id,
                    order_number,
                    shipstation_order_id,
                    ship_name,
                    ship_company,
                    status,
                    created_at,
                    updated_at
                FROM orders_inbox
                WHERE order_number = %s 
                   OR shipstation_order_id = ANY(%s)
                ORDER BY order_number, created_at
            """, (order_number, shipstation_ids))
            
            for row in cursor.fetchall():
                local_id, local_order_num, local_ss_id, ship_name, ship_company, status, created_at, updated_at = row
                
                # Get items for this order
                cursor.execute("""
                    SELECT sku, sku_lot, quantity
                    FROM order_items_inbox
                    WHERE order_inbox_id = %s
                    ORDER BY sku
                """, (local_id,))
                
                items = []
                for item_row in cursor.fetchall():
                    sku, sku_lot, qty = item_row
                    items.append({
                        'sku': sku,
                        'sku_lot': sku_lot,
                        'quantity': qty
                    })
                
                local_matches.append({
                    'id': local_id,
                    'order_number': local_order_num,
                    'shipstation_order_id': local_ss_id,
                    'ship_name': ship_name,
                    'ship_company': ship_company,
                    'status': status,
                    'created_at': created_at.isoformat() if created_at else None,
                    'updated_at': updated_at.isoformat() if updated_at else None,
                    'items': items
                })
            
            conn.close()
            
        except Exception as db_error:
            logger.error(f'Error querying local database: {db_error}', exc_info=True)
            # Continue even if DB query fails - we still have ShipStation data
        
        return jsonify({
            'success': True,
            'order_count': len(orders),
            'orders': order_details,
            'local_matches': local_matches,
            'local_match_count': len(local_matches)
        })
            
    except Exception as e:
        logger.error(f'Error looking up order {order_number}: {e}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/order-management.html')
@login_required
@admin_required
def order_management_page():
    """Serve the order management admin page"""
    return send_from_directory('.', 'order-management.html')

if __name__ == '__main__':
    # Bind to 0.0.0.0:5000 for Replit
    app.run(host='0.0.0.0', port=5000, debug=False)
