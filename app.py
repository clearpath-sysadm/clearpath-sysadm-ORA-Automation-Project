"""
ORA Automation Dashboard - Flask Application
Serves the dashboard UI and provides API endpoints for real-time data.
"""
import os
import sys
from flask import Flask, jsonify, render_template, send_from_directory, request
from datetime import datetime, timedelta
import sqlite3

# Add project root to path
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.services.database.db_utils import get_connection, execute_query

app = Flask(__name__, static_folder='static', static_url_path='/static')

# Configure Flask
app.config['JSON_SORT_KEYS'] = False

# Database path
DB_PATH = os.path.join(project_root, 'ora.db')

# List of allowed HTML files to serve (security: prevent directory traversal)
ALLOWED_PAGES = ['index.html', 'shipped_orders.html', 'shipped_items.html', 'charge_report.html', 'inventory_transactions.html', 'weekly_shipped_history.html', 'xml_import.html', 'settings.html', 'bundle_skus.html', 'sku_lot.html']

@app.route('/')
def index():
    """Serve the main dashboard"""
    return send_from_directory(project_root, 'index.html')

@app.route('/favicon.ico')
def favicon():
    """Return empty favicon to prevent 404 errors"""
    from flask import Response
    return Response(status=204)

@app.route('/<path:filename>')
def serve_page(filename):
    """Serve HTML pages only (security: whitelist approach)"""
    if filename in ALLOWED_PAGES:
        return send_from_directory(project_root, filename)
    else:
        return "Not found", 404

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
        
        # Pending uploads from orders_inbox
        cursor.execute("SELECT COUNT(*) FROM orders_inbox WHERE status = 'pending'")
        pending_uploads = cursor.fetchone()[0] or 0
        
        # Recent shipments (last 7 days)
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        cursor.execute("SELECT COUNT(*) FROM shipped_orders WHERE ship_date >= ?", (week_ago,))
        recent_shipments = cursor.fetchone()[0] or 0
        
        # Benco orders (orders with "BENCO" in company name) - awaiting shipment only
        cursor.execute("""
            SELECT COUNT(*) FROM orders_inbox 
            WHERE status = 'awaiting_shipment'
            AND (ship_company LIKE '%BENCO%' OR ship_company LIKE '%Benco%')
        """)
        benco_orders = cursor.fetchone()[0] or 0
        
        # Hawaiian orders (ship to Hawaii) - awaiting shipment only
        cursor.execute("""
            SELECT COUNT(*) FROM orders_inbox 
            WHERE status = 'awaiting_shipment'
            AND ship_state = 'HI'
        """)
        hawaiian_orders = cursor.fetchone()[0] or 0
        
        # Canadian orders (ship to Canada) - awaiting shipment only
        cursor.execute("""
            SELECT COUNT(*) FROM orders_inbox 
            WHERE status = 'awaiting_shipment'
            AND (ship_country = 'CA' OR ship_country = 'Canada')
        """)
        canadian_orders = cursor.fetchone()[0] or 0
        
        # Other international orders (not US or Canada) - awaiting shipment only
        cursor.execute("""
            SELECT COUNT(*) FROM orders_inbox 
            WHERE status = 'awaiting_shipment'
            AND ship_country IS NOT NULL
            AND ship_country NOT IN ('US', 'USA', 'United States', 'CA', 'Canada')
        """)
        other_international_orders = cursor.fetchone()[0] or 0
        
        # System status (check if we have any recent workflows)
        cursor.execute("""
            SELECT COUNT(*) FROM workflows 
            WHERE status = 'completed' 
            LIMIT 1
        """)
        completed_count = cursor.fetchone()[0] or 0
        system_status = 'operational' if completed_count > 0 else 'warning'
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'units_to_ship': units_to_ship,
                'fedex_pickup_needed': fedex_pickup_needed,
                'fedex_phone': fedex_phone,
                'pending_uploads': pending_uploads,
                'recent_shipments': recent_shipments,
                'benco_orders': benco_orders,
                'hawaiian_orders': hawaiian_orders,
                'canadian_orders': canadian_orders,
                'other_international_orders': other_international_orders,
                'system_status': system_status
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
    """Get automation workflow status"""
    try:
        query = """
            SELECT 
                name,
                display_name,
                status,
                last_run_at,
                duration_seconds,
                records_processed
            FROM workflows
            WHERE name IN ('weekly_reporter', 'daily_shipment_processor', 'shipstation_sync', 'monthly_report')
            ORDER BY last_run_at DESC
            LIMIT 10
        """
        results = execute_query(query)
        
        workflows_data = []
        for row in results:
            name = row[0]
            display_name = row[1] or name
            status = row[2]
            last_run_at = row[3]
            duration_seconds = row[4] or 0
            records = row[5] or 0
            
            workflows_data.append({
                'workflow_name': name,
                'display_name': display_name,
                'status': status,
                'last_run': last_run_at,
                'duration_seconds': duration_seconds,
                'records_processed': records
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
                base_sku
            FROM shipped_items
            WHERE ship_date >= ? AND ship_date <= ?
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
                'base_sku': row[3]
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
            WHERE ship_date >= ? AND ship_date <= ?
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
            WHERE ship_date >= ? AND ship_date <= ?
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
            WHERE date >= ? AND date <= ?
        """
        transactions = execute_query(transactions_query, (str(start_date), str(end_date)))
        
        shipments_query = """
            SELECT ship_date, base_sku, SUM(quantity_shipped)
            FROM shipped_items
            WHERE ship_date >= ? AND ship_date <= ?
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

@app.route('/api/sync_manual_orders', methods=['POST'])
def api_sync_manual_orders():
    """Trigger manual ShipStation order sync (ignores watermark, fetches last 7 days)"""
    try:
        from src.manual_shipstation_sync import (
            get_shipstation_credentials,
            fetch_shipstation_orders_since_watermark,
            is_order_from_local_system,
            has_key_product_skus,
            import_manual_order
        )
        from datetime import datetime, timedelta
        import threading
        
        def run_manual_sync():
            """Run manual order sync in background thread"""
            try:
                print("Starting manual order sync...")
                
                # Get credentials
                api_key, api_secret = get_shipstation_credentials()
                if not api_key or not api_secret:
                    print("ERROR: Failed to get ShipStation credentials")
                    return
                
                # Fetch orders from last 7 days (ignoring watermark)
                seven_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%dT00:00:00Z')
                orders = fetch_shipstation_orders_since_watermark(api_key, api_secret, seven_days_ago)
                
                print(f"Fetched {len(orders)} orders from ShipStation (last 7 days)")
                
                # Filter to manual orders
                manual_orders = []
                for order in orders:
                    order_id = order.get('orderId') or order.get('orderKey')
                    order_number = order.get('orderNumber', 'UNKNOWN')
                    
                    if is_order_from_local_system(str(order_id)):
                        continue
                    
                    if not has_key_product_skus(order):
                        continue
                    
                    manual_orders.append(order)
                
                print(f"Found {len(manual_orders)} manual orders to sync")
                
                # Import manual orders
                imported = 0
                for order in manual_orders:
                    order_number = order.get('orderNumber', 'UNKNOWN')
                    try:
                        if import_manual_order(order):
                            imported += 1
                            print(f"Imported manual order: {order_number}")
                    except Exception as e:
                        print(f"Failed to import order {order_number}: {e}")
                
                print(f"Manual sync complete: {imported} orders imported")
                
            except Exception as e:
                print(f"Manual sync error: {e}")
                import traceback
                traceback.print_exc()
        
        # Start sync in background thread
        thread = threading.Thread(target=run_manual_sync, daemon=True)
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Manual order sync started (checking last 7 days)'
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
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        if sku:
            query += " AND sku = ?"
            params.append(sku)
        if transaction_type:
            query += " AND transaction_type = ?"
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
            VALUES (?, ?, ?, ?, ?)
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
            SET current_quantity = current_quantity + ?,
                last_updated = CURRENT_TIMESTAMP
            WHERE sku = ?
        """, (delta, sku))
        
        # If SKU doesn't exist in inventory_current, we need to handle it
        # (though this shouldn't happen for valid SKUs)
        if cursor.rowcount == 0:
            # Get product name from configuration
            cursor.execute("""
                SELECT parameter_name FROM configuration_params 
                WHERE category = 'Key Products' AND sku = ?
            """, (sku,))
            result = cursor.fetchone()
            product_name = result[0] if result else 'Unknown Product'
            
            # Insert new record
            cursor.execute("""
                INSERT INTO inventory_current (sku, product_name, current_quantity, weekly_avg_cents, alert_level, reorder_point)
                VALUES (?, ?, ?, 0, 'normal', 50)
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
            WHERE id = ?
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
            SET current_quantity = current_quantity + ?,
                last_updated = CURRENT_TIMESTAMP
            WHERE sku = ?
        """, (old_delta, old_sku))
        
        # Update the transaction
        cursor.execute("""
            UPDATE inventory_transactions 
            SET date = ?, sku = ?, quantity = ?, transaction_type = ?, notes = ?
            WHERE id = ?
        """, (date, sku, quantity, transaction_type, notes, transaction_id))
        
        # Apply new transaction effect
        if transaction_type in ['Receive', 'Adjust Up', 'Repack']:
            new_delta = quantity
        else:
            new_delta = -quantity
        
        cursor.execute("""
            UPDATE inventory_current 
            SET current_quantity = current_quantity + ?,
                last_updated = CURRENT_TIMESTAMP
            WHERE sku = ?
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
            WHERE id = ?
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
            SET current_quantity = current_quantity + ?,
                last_updated = CURRENT_TIMESTAMP
            WHERE sku = ?
        """, (delta, sku))
        
        # Now delete the transaction
        cursor.execute("DELETE FROM inventory_transactions WHERE id = ?", (transaction_id,))
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
        
        # Product name mapping for clipboard
        product_names = {
            '17612': 'PT Kit',
            '17904': 'Travel Kit',
            '17914': 'PPR Kit',
            '18675': 'Ortho Protect',
            '18795': 'OraPro Paste Peppermint'
        }
        
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
            current_qty = row[2] or 0
            weekly_avg_cents = row[3] or 0
            
            # Calculate rolling average in units (convert from cents)
            weekly_avg = round(weekly_avg_cents / 100.0, 2) if weekly_avg_cents else 0.0
            
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
                'product_name': product_names.get(sku, ''),
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
                WHERE sku = ?
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
                    cursor.execute("SELECT id FROM orders_inbox WHERE order_number = ?", (order_number,))
                    existing = cursor.fetchone()
                    
                    if not existing:
                        # Insert order into inbox
                        cursor.execute("""
                            INSERT INTO orders_inbox (order_number, order_date, customer_email, status, total_items, source_system)
                            VALUES (?, ?, ?, 'pending', ?, 'X-Cart')
                        """, (order_number, order_date_str, customer_email, total_quantity))
                        
                        order_inbox_id = cursor.lastrowid
                        
                        # Insert filtered line items (only Key Products)
                        for item in filtered_items:
                            cursor.execute("""
                                INSERT INTO order_items_inbox (order_inbox_id, sku, quantity)
                                VALUES (?, ?, ?)
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
                o.created_at,
                o.failure_reason,
                o.ship_company,
                o.ship_state,
                o.ship_country,
                o.source_system,
                o.shipping_service_name,
                o.shipping_carrier_id
            FROM orders_inbox o
            INNER JOIN order_items_inbox oi ON o.id = oi.order_inbox_id
            LEFT JOIN sku_lot sl ON oi.sku = sl.sku AND sl.active = 1
            GROUP BY o.id, o.order_number, o.order_date, o.customer_email, o.status, oi.sku, sl.lot, o.shipstation_order_id, o.created_at, o.failure_reason, o.ship_company, o.ship_state, o.ship_country, o.source_system, o.shipping_service_name, o.shipping_carrier_id
            ORDER BY o.created_at DESC, oi.sku
            LIMIT 1000
        """
        results = execute_query(query)
        
        orders = []
        for row in results:
            sku = row[5]
            lot = row[7]
            sku_lot_display = f"{sku} - {lot}" if lot else sku
            
            company_name = row[11] or ''
            ship_state = (row[12] or '').strip().upper()
            ship_country = (row[13] or 'US').strip().upper()
            source_system = row[14] or 'X-Cart'
            shipping_service_name = row[15] or ''
            shipping_carrier_id = row[16]
            
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
                'created_at': row[9],
                'failure_reason': row[10] or '',
                'company_name': company_name,
                'is_hawaiian': is_hawaiian,
                'is_canadian': is_canadian,
                'is_benco': is_benco,
                'is_international': is_international,
                'is_manual': is_manual,
                'shipping_service_name': shipping_service_name,
                'shipping_carrier_id': shipping_carrier_id
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
            WHERE oi.order_inbox_id = ?
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
                cursor.execute("SELECT id FROM orders_inbox WHERE order_number = ?", (order_number,))
                existing = cursor.fetchone()
                
                if not existing:
                    # Insert order into inbox with address data
                    cursor.execute("""
                        INSERT INTO orders_inbox (
                            order_number, order_date, customer_email, status, total_items, source_system,
                            ship_name, ship_company, ship_street1, ship_city, ship_state, ship_postal_code, ship_country, ship_phone,
                            bill_name, bill_company, bill_street1, bill_city, bill_state, bill_postal_code, bill_country, bill_phone
                        )
                        VALUES (?, ?, ?, 'pending', ?, 'X-Cart', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                            VALUES (?, ?, ?)
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
            placeholders = ','.join('?' * len(order_ids))
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
        conn.row_factory = sqlite3.Row
        
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
                            "UPDATE orders_inbox SET shipstation_order_id = ? WHERE id = ?",
                            (ss_order_id, order_id)
                        )
                    
                    # Check and fix wrong ShipStation ID
                    elif order['shipstation_order_id'] != ss_order_id:
                        stats['corrections_made'] += 1
                        conn.execute(
                            "UPDATE orders_inbox SET shipstation_order_id = ? WHERE id = ?",
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
                            "UPDATE orders_inbox SET status = ? WHERE id = ?",
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
                        set_clause = ', '.join([f"{field} = ?" for field in updates.keys()])
                        values = list(updates.values()) + [order_id]
                        conn.execute(
                            f"UPDATE orders_inbox SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                            values
                        )
                    
                    # Check and update carrier/service information
                    carrier_code = ss_order.get('carrierCode', '')
                    service_code = ss_order.get('serviceCode', '')
                    carrier_id = None
                    advanced_options = ss_order.get('advancedOptions', {})
                    if advanced_options and isinstance(advanced_options, dict):
                        carrier_id = advanced_options.get('carrierId')
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
                               SET shipping_carrier_code = ?, 
                                   shipping_carrier_id = ?, 
                                   shipping_service_code = ?,
                                   shipping_service_name = ?,
                                   updated_at = CURRENT_TIMESTAMP 
                               WHERE id = ?""",
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
            placeholders = ','.join('?' * len(order_ids))
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
                WHERE order_inbox_id = ?
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
                    INSERT OR IGNORE INTO shipstation_order_line_items (order_inbox_id, sku, shipstation_order_id)
                    VALUES (?, ?, ?)
                """, (order_sku_info['order_inbox_id'], sku, shipstation_id))
                
                # Mark order as awaiting_shipment and store ShipStation ID
                cursor.execute("""
                    UPDATE orders_inbox
                    SET status = 'awaiting_shipment',
                        shipstation_order_id = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
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
                    WHERE order_number = ?
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
                        WHERE id = ?
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
                        INSERT OR IGNORE INTO shipstation_order_line_items (order_inbox_id, sku, shipstation_order_id)
                        VALUES (?, ?, ?)
                    """, (order_sku_info['order_inbox_id'], order_sku_info['sku'], shipstation_id))
                    
                    # Also update orders_inbox.shipstation_order_id for the first SKU uploaded
                    cursor.execute("""
                        UPDATE orders_inbox
                        SET shipstation_order_id = ?
                        WHERE id = ? AND (shipstation_order_id IS NULL OR shipstation_order_id = '')
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
                            failure_reason = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
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
            WHERE bundle_sku_id = ?
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
            VALUES (?, ?, ?)
        """, (bundle_sku, description, active))
        
        bundle_id = cursor.lastrowid
        
        # Insert components
        for comp in components:
            cursor.execute("""
                INSERT INTO bundle_components (bundle_sku_id, component_sku, multiplier, sequence)
                VALUES (?, ?, ?, ?)
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
            SET bundle_sku = ?, description = ?, active = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (bundle_sku, description, active, bundle_id))
        
        # Delete existing components
        cursor.execute("DELETE FROM bundle_components WHERE bundle_sku_id = ?", (bundle_id,))
        
        # Insert new components
        for comp in components:
            cursor.execute("""
                INSERT INTO bundle_components (bundle_sku_id, component_sku, multiplier, sequence)
                VALUES (?, ?, ?, ?)
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
        cursor.execute("DELETE FROM bundle_skus WHERE id = ?", (bundle_id,))
        
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
            VALUES (?, ?, ?)
        """, (data['sku'], data['lot'], data.get('active', 1)))
        
        sku_lot_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'sku_lot_id': sku_lot_id,
            'message': 'SKU-Lot created successfully'
        })
    except sqlite3.IntegrityError:
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
            SET sku = ?, lot = ?, active = ?, updated_at = datetime('now')
            WHERE id = ?
        """, (data['sku'], data['lot'], data.get('active', 1), sku_lot_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'SKU-Lot updated successfully'
        })
    except sqlite3.IntegrityError:
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
        
        cursor.execute("DELETE FROM sku_lot WHERE id = ?", (sku_lot_id,))
        
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
            SET metric_value = ?,
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
            WHERE id = ?
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

if __name__ == '__main__':
    # Bind to 0.0.0.0:5000 for Replit
    app.run(host='0.0.0.0', port=5000, debug=False)
