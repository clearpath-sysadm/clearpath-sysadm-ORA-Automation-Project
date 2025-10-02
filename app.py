"""
ORA Automation Dashboard - Flask Application
Serves the dashboard UI and provides API endpoints for real-time data.
"""
import os
import sys
from flask import Flask, jsonify, render_template, send_from_directory
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
ALLOWED_PAGES = ['index.html', 'shipped_orders.html', 'shipped_items.html', 'charge_report.html', 'inventory_transactions.html', 'weekly_shipped_history.html', 'xml_import.html', 'settings.html']

@app.route('/')
def index():
    """Serve the main dashboard"""
    return send_from_directory(project_root, 'index.html')

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
        
        # Units to be shipped (from pending orders)
        cursor.execute("""
            SELECT COALESCE(SUM(quantity), 0)
            FROM order_items_inbox
            WHERE order_inbox_id IN (
                SELECT id FROM orders_inbox WHERE status = 'pending'
            )
        """)
        units_to_ship = cursor.fetchone()[0] or 0
        
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
        
        # Calculate charges
        ORDER_CHARGE = 4.25  # $ per order
        PACKAGE_CHARGE = 3.40  # $ per package (assumed 1 package per order)
        SPACE_RENTAL_BASE = 18.00  # $ per day base rate
        SPACE_RENTAL_INCREMENT = 0.18  # $ increment per order above base
        
        report_data = []
        for date, data in sorted(daily_data.items()):
            order_count = data['order_count']
            
            # Calculate charges
            orders_charge = order_count * ORDER_CHARGE
            packages_charge = order_count * PACKAGE_CHARGE  # Assume 1 package per order
            
            # Space rental: $18 base + variable based on volume (up to $23.40)
            # Linear scaling: adds $0.18 per order, capped at $23.40
            space_rental = SPACE_RENTAL_BASE + min(order_count * SPACE_RENTAL_INCREMENT, 5.40)
            space_rental = min(space_rental, 23.40)  # Hard cap at $23.40
            
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
        cursor.execute("""
            INSERT INTO inventory_transactions (date, sku, quantity, transaction_type, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (date, sku, quantity, transaction_type, notes))
        conn.commit()
        transaction_id = cursor.lastrowid
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
        cursor.execute("""
            UPDATE inventory_transactions 
            SET date = ?, sku = ?, quantity = ?, transaction_type = ?, notes = ?
            WHERE id = ?
        """, (date, sku, quantity, transaction_type, notes, transaction_id))
        conn.commit()
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Transaction not found'
            }), 404
        
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
        cursor.execute("DELETE FROM inventory_transactions WHERE id = ?", (transaction_id,))
        conn.commit()
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({
                'success': False,
                'error': 'Transaction not found'
            }), 404
        
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
        
        report = []
        for row in results:
            weekly_avg = round((row[3] or 0) / 100.0, 2) if row[3] else 0.0
            report.append({
                'sku': row[0],
                'product_name': row[1],
                'current_quantity': row[2] or 0,
                'rolling_avg_52_weeks': weekly_avg,
                'alert_level': row[4] or 'normal',
                'reorder_point': row[5] or 0,
                'last_updated': row[6]
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
        import xml.etree.ElementTree as ET
        
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
            orders_imported = 0
            
            # Process each order
            for order_elem in root.findall('order'):
                order_id = order_elem.find('orderid')
                order_date = order_elem.find('date2')
                email = order_elem.find('email')
                
                if order_id is not None and order_id.text:
                    order_number = order_id.text.strip()
                    order_date_str = order_date.text.strip() if order_date is not None and order_date.text else datetime.now().strftime('%Y-%m-%d')
                    customer_email = email.text.strip() if email is not None and email.text else None
                    
                    # Count items
                    items = order_elem.findall('.//product')
                    total_items = len(items)
                    
                    # Check if order already exists
                    cursor.execute("SELECT id FROM orders_inbox WHERE order_number = ?", (order_number,))
                    existing = cursor.fetchone()
                    
                    if not existing:
                        # Insert order into inbox
                        cursor.execute("""
                            INSERT INTO orders_inbox (order_number, order_date, customer_email, status, total_items, source_system)
                            VALUES (?, ?, ?, 'pending', ?, 'X-Cart')
                        """, (order_number, order_date_str, customer_email, total_items))
                        
                        order_inbox_id = cursor.lastrowid
                        
                        # Insert order items
                        for product in items:
                            product_code = product.find('productcode')
                            quantity = product.find('amount')
                            
                            if product_code is not None and product_code.text:
                                sku = product_code.text.strip()
                                qty = int(quantity.text.strip()) if quantity is not None and quantity.text else 1
                                
                                cursor.execute("""
                                    INSERT INTO order_items_inbox (order_inbox_id, sku, quantity)
                                    VALUES (?, ?, ?)
                                """, (order_inbox_id, sku, qty))
                        
                        orders_imported += 1
            
            conn.commit()
            conn.close()
            
            # Clean up temp file
            os.unlink(temp_path)
            
            return jsonify({
                'success': True,
                'message': f'Successfully imported {orders_imported} orders',
                'orders_count': orders_imported
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
    """Get all orders from inbox with calculated total_items"""
    try:
        query = """
            SELECT 
                o.id,
                o.order_number,
                o.order_date,
                o.customer_email,
                o.status,
                COALESCE(SUM(oi.quantity), o.total_items, 0) as total_items,
                o.total_amount_cents,
                o.shipstation_order_id,
                o.created_at,
                o.updated_at
            FROM orders_inbox o
            LEFT JOIN order_items_inbox oi ON o.id = oi.order_inbox_id
            GROUP BY o.id, o.order_number, o.order_date, o.customer_email, 
                     o.status, o.total_items, o.total_amount_cents, 
                     o.shipstation_order_id, o.created_at, o.updated_at
            ORDER BY o.created_at DESC
            LIMIT 500
        """
        results = execute_query(query)
        
        orders = []
        for row in results:
            orders.append({
                'id': row[0],
                'order_number': row[1],
                'order_date': row[2],
                'customer_email': row[3] or '',
                'status': row[4],
                'total_items': int(row[5]) if row[5] else 0,
                'total_amount_cents': row[6] or 0,
                'shipstation_order_id': row[7] or '',
                'created_at': row[8],
                'updated_at': row[9]
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
        import xml.etree.ElementTree as ET
        from io import StringIO
        
        # Fetch XML content from Google Drive
        xml_content = fetch_xml_from_drive_by_file_id(file_id)
        
        # Parse XML
        root = ET.fromstring(xml_content)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Load bundle configurations
        bundle_config = load_bundle_config_from_db(cursor)
        
        orders_imported = 0
        
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
                expanded_items = expand_bundles(line_items, bundle_config)
                
                # Calculate total quantity from expanded items
                total_quantity = sum(item['quantity'] for item in expanded_items)
                
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
            'message': f'Successfully imported {orders_imported} orders from Google Drive',
            'orders_count': orders_imported
        })
        
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
            fetch_shipstation_existing_orders_by_date_range
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
        
        # Fetch SKU-Lot mappings from configuration_params
        cursor.execute("""
            SELECT parameter_name, value 
            FROM configuration_params 
            WHERE category = 'SKU_Lot'
        """)
        sku_lot_map = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Build query for pending orders
        if order_ids:
            placeholders = ','.join('?' * len(order_ids))
            order_query = f"""
                SELECT id, order_number, order_date, customer_email, total_amount_cents
                FROM orders_inbox 
                WHERE status = 'pending' AND id IN ({placeholders})
            """
            cursor.execute(order_query, order_ids)
        else:
            cursor.execute("""
                SELECT id, order_number, order_date, customer_email, total_amount_cents
                FROM orders_inbox 
                WHERE status = 'pending'
            """)
        
        pending_orders = cursor.fetchall()
        
        if not pending_orders:
            return jsonify({
                'success': True,
                'message': 'No pending orders to upload',
                'uploaded': 0
            })
        
        # Build ShipStation order payloads
        shipstation_orders = []
        order_map = {}  # Map order_number to order_id for later update
        
        for order_row in pending_orders:
            order_id, order_number, order_date, customer_email, total_amount_cents = order_row
            order_map[order_number] = order_id
            
            # Get order items
            cursor.execute("""
                SELECT sku, quantity, unit_price_cents
                FROM order_items_inbox
                WHERE order_inbox_id = ?
            """, (order_id,))
            items = cursor.fetchall()
            
            # Build items with SKU-Lot mapping
            shipstation_items = []
            for sku, qty, unit_price_cents in items:
                lot_number = sku_lot_map.get(sku, '')
                sku_with_lot = f"{sku}-{lot_number}" if lot_number else sku
                
                shipstation_items.append({
                    'sku': sku_with_lot,
                    'name': f'Product {sku}',
                    'quantity': qty,
                    'unitPrice': (unit_price_cents / 100) if unit_price_cents else 0
                })
            
            # Build ShipStation order payload
            shipstation_order = {
                'orderNumber': order_number,
                'orderDate': order_date,
                'orderStatus': 'awaiting_shipment',
                'customerEmail': customer_email or '',
                'billTo': {
                    'name': 'Customer',
                    'street1': '',
                    'city': '',
                    'state': '',
                    'postalCode': '',
                    'country': 'US'
                },
                'shipTo': {
                    'name': 'Customer',
                    'street1': '',
                    'city': '',
                    'state': '',
                    'postalCode': '',
                    'country': 'US'
                },
                'items': shipstation_items,
                'amountPaid': (total_amount_cents / 100) if total_amount_cents else 0,
                'taxAmount': 0,
                'shippingAmount': 0
            }
            
            shipstation_orders.append(shipstation_order)
        
        # Check for duplicates in ShipStation
        earliest_date = min([date_parser.parse(o['orderDate']) for o in shipstation_orders])
        create_date_start = earliest_date.strftime('%Y-%m-%dT00:00:00Z')
        create_date_end = datetime.now().strftime('%Y-%m-%dT23:59:59Z')
        
        existing_orders = fetch_shipstation_existing_orders_by_date_range(
            api_key,
            api_secret,
            settings.SHIPSTATION_ORDERS_ENDPOINT,
            create_date_start,
            create_date_end
        )
        
        # Create map of existing orders by order number for efficient lookup
        existing_order_map = {o.get('orderNumber', '').strip().upper(): o for o in existing_orders}
        
        # Filter out duplicates and capture their ShipStation IDs
        new_orders = []
        skipped_count = 0
        for order in shipstation_orders:
            order_num_upper = order['orderNumber'].strip().upper()
            
            if order_num_upper in existing_order_map:
                skipped_count += 1
                # Get ShipStation order ID from existing order
                existing_order = existing_order_map[order_num_upper]
                shipstation_id = existing_order.get('orderId') or existing_order.get('orderKey')
                
                # Mark as uploaded and store ShipStation ID
                cursor.execute("""
                    UPDATE orders_inbox 
                    SET status = 'uploaded',
                        shipstation_order_id = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE order_number = ?
                """, (shipstation_id, order['orderNumber']))
            else:
                new_orders.append(order)
        
        if not new_orders:
            conn.commit()
            conn.close()
            return jsonify({
                'success': True,
                'message': f'All {len(shipstation_orders)} orders already exist in ShipStation',
                'uploaded': 0,
                'skipped': skipped_count
            })
        
        # Upload to ShipStation (single batch API call - efficient)
        upload_results = send_all_orders_to_shipstation(
            new_orders,
            api_key,
            api_secret,
            settings.SHIPSTATION_CREATE_ORDERS_ENDPOINT
        )
        
        # Create map of new orders by orderNumber for efficient matching
        order_map_by_number = {o['orderNumber']: o for o in new_orders}
        
        # Update database with results
        uploaded_count = 0
        failed_count = 0
        
        for result in upload_results:
            # ShipStation returns orderKey which should match our orderNumber
            order_key = result.get('orderKey', '')
            order_id = result.get('orderId')
            success = result.get('success', False)
            error_msg = result.get('errorMessage')
            
            if success:
                # Match by orderKey (which is our orderNumber)
                if order_key in order_map_by_number:
                    shipstation_id = order_id or order_key
                    cursor.execute("""
                        UPDATE orders_inbox 
                        SET status = 'uploaded',
                            shipstation_order_id = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE order_number = ?
                    """, (shipstation_id, order_key))
                    uploaded_count += 1
                else:
                    # Fallback: try to find by matching order number
                    for order_num, order_data in order_map_by_number.items():
                        if order_num.upper() == order_key.upper():
                            shipstation_id = order_id or order_key
                            cursor.execute("""
                                UPDATE orders_inbox 
                                SET status = 'uploaded',
                                    shipstation_order_id = ?,
                                    updated_at = CURRENT_TIMESTAMP
                                WHERE order_number = ?
                            """, (shipstation_id, order_num))
                            uploaded_count += 1
                            break
            else:
                failed_count += 1
                # Mark as failed in database
                if order_key and order_key in order_map_by_number:
                    cursor.execute("""
                        UPDATE orders_inbox 
                        SET status = 'failed',
                            updated_at = CURRENT_TIMESTAMP
                        WHERE order_number = ?
                    """, (order_key,))
        
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

if __name__ == '__main__':
    # Bind to 0.0.0.0:5000 for Replit
    app.run(host='0.0.0.0', port=5000, debug=False)
