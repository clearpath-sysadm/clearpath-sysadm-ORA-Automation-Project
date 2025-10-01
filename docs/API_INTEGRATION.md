# API Integration Guide

## Overview

This guide documents how the ORA automation scripts integrate with the SQLite database, replacing Google Sheets as the primary data backend. It provides code patterns, best practices, and implementation details for all database interactions.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Database Utilities Module](#database-utilities-module)
3. [Script Integration Patterns](#script-integration-patterns)
4. [External API Integrations](#external-api-integrations)
5. [Error Handling](#error-handling)
6. [Testing & Validation](#testing--validation)
7. [Migration from Google Sheets](#migration-from-google-sheets)

---

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────┐
│                  Dashboard UI                    │
│              (Real-time Data Display)            │
└───────────────────┬─────────────────────────────┘
                    │ Queries
                    ↓
┌─────────────────────────────────────────────────┐
│              SQLite Database (WAL)               │
│                    ora.db                        │
└───────────────────┬─────────────────────────────┘
                    │
        ┌───────────┴───────────┬──────────────┐
        ↓                       ↓              ↓
┌──────────────┐    ┌──────────────────┐    ┌────────────┐
│   Weekly     │    │     Daily        │    │ ShipStation│
│   Reporter   │    │   Shipment       │    │  Order     │
│              │    │   Processor      │    │  Uploader  │
└──────┬───────┘    └────────┬─────────┘    └─────┬──────┘
       │                     │                     │
       │ Reads/Writes        │ ShipStation API    │ Reads Inbox
       ↓                     ↓                     ↓ Writes Status
┌─────────────────────────────────────────────────┐
│            Database Utilities Module             │
│              (db_utils.py)                       │
└─────────────────────────────────────────────────┘
```

### Data Flow

1. **XML Polling Service** → Parses X-Cart orders → `orders_inbox` table
2. **ShipStation Uploader** → Reads `orders_inbox` → Uploads to ShipStation API → Updates status
3. **Daily Shipment Processor** → Fetches from ShipStation API → `shipped_orders` + `shipped_items`
4. **Weekly Reporter** → Aggregates data → `weekly_shipped_history` + `inventory_current`
5. **Dashboard** → Real-time queries from all tables → Display KPIs

---

## Database Utilities Module

### Module Structure

**File:** `src/services/database/db_utils.py`

```python
"""
Database utilities for ORA automation system.
Provides connection management, transaction handling, and common query patterns.
"""

import sqlite3
import os
from contextlib import contextmanager
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class DatabaseConnection:
    """SQLite database connection manager with production settings"""
    
    def __init__(self, db_path: str = None):
        """
        Initialize database connection manager.
        
        Args:
            db_path: Path to SQLite database file (defaults to DATABASE_PATH env var)
        """
        self.db_path = db_path or os.getenv('DATABASE_PATH', 'ora.db')
        
        # Verify database exists
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found: {self.db_path}")
    
    def get_connection(self) -> sqlite3.Connection:
        """
        Create new database connection with production PRAGMA settings.
        
        Returns:
            sqlite3.Connection with optimized settings
        """
        conn = sqlite3.connect(
            self.db_path,
            timeout=30.0,  # 30 second lock timeout
            check_same_thread=False,
            isolation_level=None  # Manual transaction control
        )
        
        # Apply production PRAGMA settings
        conn.executescript("""
            PRAGMA journal_mode = WAL;
            PRAGMA synchronous = NORMAL;
            PRAGMA foreign_keys = ON;
            PRAGMA busy_timeout = 8000;
            PRAGMA temp_store = MEMORY;
            PRAGMA cache_size = -20000;
        """)
        
        # Enable dict-like row access
        conn.row_factory = sqlite3.Row
        
        logger.debug(f"Database connection established: {self.db_path}")
        return conn
    
    @contextmanager
    def transaction(self):
        """
        Context manager for database transactions with automatic rollback.
        
        Usage:
            with db.transaction() as conn:
                conn.execute("INSERT INTO ...")
                conn.execute("UPDATE ...")
            # Auto-commits on success, rolls back on exception
        """
        conn = self.get_connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.commit()
            logger.debug("Transaction committed successfully")
        except Exception as e:
            conn.rollback()
            logger.error(f"Transaction rolled back due to error: {e}")
            raise
        finally:
            conn.close()
    
    def execute_query(self, query: str, params: tuple = ()) -> List[sqlite3.Row]:
        """
        Execute read-only query and return results.
        
        Args:
            query: SQL SELECT query
            params: Query parameters
            
        Returns:
            List of result rows
        """
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return cursor.fetchall()
    
    def execute_write(self, query: str, params: tuple = ()) -> int:
        """
        Execute write query (INSERT/UPDATE/DELETE) in transaction.
        
        Args:
            query: SQL write query
            params: Query parameters
            
        Returns:
            Number of affected rows
        """
        with self.transaction() as conn:
            cursor = conn.execute(query, params)
            return cursor.rowcount
    
    def upsert(self, table: str, data: Dict[str, Any], 
               conflict_columns: List[str]) -> int:
        """
        Insert or update record using UPSERT pattern.
        
        Args:
            table: Table name
            data: Column-value dictionary
            conflict_columns: Columns to check for conflicts
            
        Returns:
            Row ID of inserted/updated record
        """
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        values = tuple(data.values())
        
        update_clause = ', '.join([
            f"{col} = excluded.{col}" 
            for col in data.keys() 
            if col not in conflict_columns
        ])
        
        query = f"""
            INSERT INTO {table} ({columns}) 
            VALUES ({placeholders})
            ON CONFLICT({', '.join(conflict_columns)}) 
            DO UPDATE SET {update_clause}
        """
        
        with self.transaction() as conn:
            cursor = conn.execute(query, values)
            return cursor.lastrowid

# Global database instance
db = DatabaseConnection()
```

### Helper Functions

```python
# Common database operations

def get_workflow_status(workflow_name: str) -> Optional[Dict]:
    """Get current status of a workflow"""
    result = db.execute_query(
        "SELECT * FROM workflows WHERE name = ?",
        (workflow_name,)
    )
    return dict(result[0]) if result else None

def update_workflow_status(workflow_name: str, status: str, 
                          duration: int = None, 
                          records_processed: int = None,
                          details: str = None):
    """Update workflow execution status"""
    db.execute_write("""
        UPDATE workflows 
        SET status = ?,
            last_run_at = CURRENT_TIMESTAMP,
            duration_seconds = COALESCE(?, duration_seconds),
            records_processed = COALESCE(?, records_processed),
            details = COALESCE(?, details),
            updated_at = CURRENT_TIMESTAMP
        WHERE name = ?
    """, (status, duration, records_processed, details, workflow_name))

def get_current_inventory() -> List[Dict]:
    """Get all current inventory levels"""
    rows = db.execute_query("""
        SELECT 
            sku,
            product_name,
            current_quantity,
            weekly_avg_cents / 100.0 as weekly_avg,
            alert_level,
            reorder_point,
            last_updated
        FROM inventory_current
        ORDER BY alert_level DESC, current_quantity ASC
    """)
    return [dict(row) for row in rows]

def add_inventory_transaction(date: str, sku: str, quantity: int, 
                              trans_type: str, notes: str = None):
    """Add inventory transaction and update current levels"""
    with db.transaction() as conn:
        # Insert transaction
        conn.execute("""
            INSERT INTO inventory_transactions 
            (date, sku, quantity, transaction_type, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (date, sku, quantity, trans_type, notes))
        
        # Update current inventory
        quantity_delta = quantity if trans_type in ('Receive', 'Adjust Up') else -quantity
        conn.execute("""
            UPDATE inventory_current 
            SET current_quantity = current_quantity + ?,
                last_updated = CURRENT_TIMESTAMP
            WHERE sku = ?
        """, (quantity_delta, sku))
```

---

## Script Integration Patterns

### 1. Weekly Reporter (`weekly_reporter.py`)

**Purpose:** Calculate inventory levels and weekly averages

**Database Operations:**
- Reads: `configuration_params`, `inventory_transactions`, `shipped_items`, `weekly_shipped_history`
- Writes: `inventory_current`, `system_kpis`, `workflows`

**Implementation:**

```python
# src/weekly_reporter.py

import sys
from datetime import datetime, timedelta
from services.database.db_utils import db, update_workflow_status
import logging

logger = logging.getLogger(__name__)

def calculate_inventory_levels():
    """Calculate current inventory and alert levels"""
    
    workflow_name = 'weekly_reporter'
    start_time = datetime.now()
    
    try:
        update_workflow_status(workflow_name, 'running')
        
        # 1. Get configuration parameters
        config = db.execute_query("""
            SELECT sku, parameter_name, value 
            FROM configuration_params 
            WHERE category = 'Inventory'
        """)
        
        reorder_points = {
            row['sku']: int(row['value']) 
            for row in config 
            if row['parameter_name'] == 'ReorderPoint'
        }
        
        # 2. Calculate 12-week rolling average
        twelve_weeks_ago = (datetime.now() - timedelta(weeks=12)).strftime('%Y-%m-%d')
        
        weekly_avgs = db.execute_query("""
            SELECT 
                sku,
                AVG(quantity_shipped) as avg_shipped
            FROM weekly_shipped_history
            WHERE start_date >= ?
            GROUP BY sku
        """, (twelve_weeks_ago,))
        
        avg_by_sku = {row['sku']: row['avg_shipped'] for row in weekly_avgs}
        
        # 3. Get current inventory from transactions
        inventory_calcs = db.execute_query("""
            SELECT 
                sku,
                SUM(CASE 
                    WHEN transaction_type IN ('Receive', 'Adjust Up') THEN quantity
                    WHEN transaction_type IN ('Ship', 'Adjust Down') THEN -quantity
                    ELSE 0
                END) as current_qty
            FROM inventory_transactions
            GROUP BY sku
        """)
        
        # 4. Update inventory_current table
        with db.transaction() as conn:
            for row in inventory_calcs:
                sku = row['sku']
                current_qty = row['current_qty']
                weekly_avg = avg_by_sku.get(sku, 0)
                reorder_point = reorder_points.get(sku, 50)
                
                # Determine alert level
                if current_qty <= reorder_point * 0.5:
                    alert_level = 'critical'
                elif current_qty <= reorder_point:
                    alert_level = 'low'
                else:
                    alert_level = 'normal'
                
                # UPSERT inventory current
                conn.execute("""
                    INSERT INTO inventory_current 
                    (sku, product_name, current_quantity, weekly_avg_cents, 
                     alert_level, reorder_point, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(sku) DO UPDATE SET
                        current_quantity = excluded.current_quantity,
                        weekly_avg_cents = excluded.weekly_avg_cents,
                        alert_level = excluded.alert_level,
                        reorder_point = excluded.reorder_point,
                        last_updated = CURRENT_TIMESTAMP
                """, (
                    sku,
                    f"Product {sku}",  # Get from config in production
                    current_qty,
                    int(weekly_avg * 100),  # Store as cents
                    alert_level,
                    reorder_point
                ))
        
        # 5. Update workflow status
        duration = int((datetime.now() - start_time).total_seconds())
        update_workflow_status(
            workflow_name, 
            'completed', 
            duration=duration,
            records_processed=len(inventory_calcs),
            details='Successfully calculated inventory levels'
        )
        
        logger.info(f"Weekly reporter completed: {len(inventory_calcs)} SKUs processed")
        
    except Exception as e:
        logger.error(f"Weekly reporter failed: {e}")
        update_workflow_status(
            workflow_name,
            'failed',
            details=str(e)
        )
        raise

if __name__ == '__main__':
    calculate_inventory_levels()
```

### 2. Daily Shipment Processor (`daily_shipment_processor.py`)

**Purpose:** Fetch shipments from ShipStation API and store in database

**Database Operations:**
- Reads: ShipStation API
- Writes: `shipped_orders`, `shipped_items`, `weekly_shipped_history`, `workflows`

**Implementation:**

```python
# src/daily_shipment_processor.py

from datetime import datetime, timedelta
from services.database.db_utils import db, update_workflow_status
from services.shipstation.api_client import ShipStationClient

def process_daily_shipments():
    """Fetch and store shipments from ShipStation"""
    
    workflow_name = 'daily_shipment_processor'
    start_time = datetime.now()
    
    try:
        update_workflow_status(workflow_name, 'running')
        
        # 1. Get shipments from ShipStation API
        shipstation = ShipStationClient()
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        shipments = shipstation.get_shipments(ship_date_start=yesterday)
        
        # 2. Store in database
        with db.transaction() as conn:
            for shipment in shipments:
                # Insert order
                conn.execute("""
                    INSERT INTO shipped_orders 
                    (ship_date, order_number, customer_email, 
                     total_items, shipstation_order_id)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(order_number) DO NOTHING
                """, (
                    shipment['shipDate'],
                    shipment['orderNumber'],
                    shipment.get('customerEmail'),
                    len(shipment.get('items', [])),
                    shipment['orderId']
                ))
                
                # Insert line items
                for item in shipment.get('items', []):
                    conn.execute("""
                        INSERT INTO shipped_items 
                        (ship_date, sku_lot, base_sku, quantity_shipped, order_number)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        shipment['shipDate'],
                        item.get('sku'),
                        item.get('sku', '').split(' - ')[0],  # Extract base SKU
                        item.get('quantity', 1),
                        shipment['orderNumber']
                    ))
        
        # 3. Update weekly history
        aggregate_weekly_shipments()
        
        # 4. Update workflow status
        duration = int((datetime.now() - start_time).total_seconds())
        update_workflow_status(
            workflow_name,
            'completed',
            duration=duration,
            records_processed=len(shipments),
            details=f'Processed {len(shipments)} shipments from ShipStation'
        )
        
    except Exception as e:
        update_workflow_status(workflow_name, 'failed', details=str(e))
        raise

def aggregate_weekly_shipments():
    """Aggregate shipped items into weekly history"""
    
    with db.transaction() as conn:
        # Get this week's date range (Monday to Sunday)
        today = datetime.now()
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        
        # Aggregate and UPSERT
        conn.execute("""
            INSERT INTO weekly_shipped_history 
            (start_date, end_date, sku, quantity_shipped)
            SELECT 
                ? as start_date,
                ? as end_date,
                base_sku as sku,
                SUM(quantity_shipped) as quantity_shipped
            FROM shipped_items
            WHERE ship_date BETWEEN ? AND ?
            GROUP BY base_sku
            ON CONFLICT(start_date, end_date, sku) DO UPDATE SET
                quantity_shipped = excluded.quantity_shipped,
                created_at = CURRENT_TIMESTAMP
        """, (
            monday.strftime('%Y-%m-%d'),
            sunday.strftime('%Y-%m-%d'),
            monday.strftime('%Y-%m-%d'),
            sunday.strftime('%Y-%m-%d')
        ))
```

### 3. ShipStation Order Uploader (`shipstation_order_uploader.py`)

**Purpose:** Upload pending orders from inbox to ShipStation

**Database Operations:**
- Reads: `orders_inbox` (WHERE status='pending'), `order_items_inbox`
- Writes: Updates `orders_inbox.status` and `shipstation_order_id`

### 4. Monthly Charge Report Generator (`shipstation_reporter.py`)

**Purpose:** Generate monthly charge reports with daily breakdowns

**Database Operations:**
- Reads: `configuration_params`, `inventory_transactions`, `shipped_items`, `shipped_orders`, `weekly_shipped_history`
- Writes: `monthly_charge_reports` (optional), `workflows`

**Report Components:**
- Daily order charges (orders × OrderCharge rate)
- Daily package charges (packages × PackageCharge rate)
- Daily space rental (pallets used × SpaceRentalRate)
- Daily inventory levels (BOD/EOD)
- Shipped quantities per SKU
- Monthly totals

**Implementation:**

```python
# src/shipstation_reporter.py

import math
from datetime import datetime, timedelta
from services.database.db_utils import db, update_workflow_status

def generate_monthly_charge_report(year: int, month: int):
    """Generate monthly charge report with daily breakdown"""
    
    workflow_name = 'shipstation_reporter'
    start_time = datetime.now()
    
    try:
        update_workflow_status(workflow_name, 'running')
        
        # 1. Get configuration (rates, pallet counts)
        rates = db.execute_query("""
            SELECT parameter_name, value
            FROM configuration_params
            WHERE category = 'Rates'
        """)
        
        rates_dict = {row['parameter_name']: float(row['value']) / 100.0 for row in rates}  # Convert cents to dollars
        
        pallet_counts = db.execute_query("""
            SELECT sku, value
            FROM configuration_params
            WHERE category = 'PalletConfig'
        """)
        
        pallet_dict = {row['sku']: int(row['value']) for row in pallet_counts}
        
        # 2. Get EOM previous month inventory (starting point)
        eom_inventory = db.execute_query("""
            SELECT sku, value
            FROM configuration_params
            WHERE category = 'InitialInventory' 
            AND parameter_name = 'EOM_Previous_Month'
        """)
        
        initial_inventory = {row['sku']: int(row['value']) for row in eom_inventory}
        
        # 3. Calculate date range
        start_date = datetime(year, month, 1).date()
        end_date = (start_date.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        
        # 4. Get month's shipments
        shipped_orders = db.execute_query("""
            SELECT ship_date, order_number
            FROM shipped_orders
            WHERE ship_date BETWEEN ? AND ?
        """, (start_date, end_date))
        
        shipped_items = db.execute_query("""
            SELECT ship_date, base_sku, SUM(quantity_shipped) as total_qty
            FROM shipped_items
            WHERE ship_date BETWEEN ? AND ?
            GROUP BY ship_date, base_sku
        """, (start_date, end_date))
        
        # 5. Calculate daily charges
        daily_reports = []
        current_inventory = initial_inventory.copy()
        
        current_date = start_date
        while current_date <= end_date:
            # Orders and packages for this day
            day_orders = [o for o in shipped_orders if o['ship_date'] == str(current_date)]
            day_items = [i for i in shipped_items if i['ship_date'] == str(current_date)]
            
            num_orders = len(day_orders)
            num_packages = sum(i['total_qty'] for i in day_items)
            
            # Update inventory for shipped items
            for item in day_items:
                sku = item['base_sku']
                if sku in current_inventory:
                    current_inventory[sku] -= item['total_qty']
            
            # Calculate pallets used (EOD inventory)
            total_pallets = sum(
                math.ceil(qty / pallet_dict.get(sku, 1)) 
                for sku, qty in current_inventory.items()
                if pallet_dict.get(sku)
            )
            
            # Calculate charges (store as cents)
            orders_charge = int(num_orders * rates_dict.get('OrderCharge', 0) * 100)
            packages_charge = int(num_packages * rates_dict.get('PackageCharge', 0) * 100)
            space_charge = int(total_pallets * rates_dict.get('SpaceRentalRate', 0) * 100)
            total_charge = orders_charge + packages_charge + space_charge
            
            # Store daily report
            with db.transaction() as conn:
                conn.execute("""
                    INSERT INTO monthly_charge_reports 
                    (report_date, report_year, report_month, num_orders, num_packages,
                     orders_charge_cents, packages_charge_cents, space_rental_charge_cents,
                     total_charge_cents)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(report_year, report_month, report_date) DO UPDATE SET
                        num_orders = excluded.num_orders,
                        num_packages = excluded.num_packages,
                        orders_charge_cents = excluded.orders_charge_cents,
                        packages_charge_cents = excluded.packages_charge_cents,
                        space_rental_charge_cents = excluded.space_rental_charge_cents,
                        total_charge_cents = excluded.total_charge_cents
                """, (current_date, year, month, num_orders, num_packages,
                      orders_charge, packages_charge, space_charge, total_charge))
            
            daily_reports.append({
                'date': current_date,
                'orders': num_orders,
                'packages': num_packages,
                'total_charge': total_charge / 100.0  # Convert to dollars for display
            })
            
            current_date += timedelta(days=1)
        
        # 6. Update workflow status
        duration = int((datetime.now() - start_time).total_seconds())
        update_workflow_status(
            workflow_name,
            'completed',
            duration=duration,
            records_processed=len(daily_reports),
            details=f'Generated monthly charge report for {year}-{month:02d}'
        )
        
        return daily_reports
        
    except Exception as e:
        update_workflow_status(workflow_name, 'failed', details=str(e))
        raise
```

### 5. ShipStation Order Uploader (Continued)

```python
# src/shipstation_order_uploader.py

from services.database.db_utils import db, update_workflow_status
from services.shipstation.api_client import ShipStationClient

def upload_pending_orders():
    """Upload pending orders to ShipStation"""
    
    workflow_name = 'shipstation_order_uploader'
    start_time = datetime.now()
    
    try:
        update_workflow_status(workflow_name, 'running')
        
        # 1. Get pending orders with items
        pending_orders = db.execute_query("""
            SELECT 
                o.id,
                o.order_number,
                o.order_date,
                o.customer_email,
                o.total_amount_cents
            FROM orders_inbox o
            WHERE o.status = 'pending'
            ORDER BY o.created_at ASC
        """)
        
        shipstation = ShipStationClient()
        uploaded_count = 0
        
        for order in pending_orders:
            try:
                # Get order items
                items = db.execute_query("""
                    SELECT sku, sku_lot, quantity, unit_price_cents
                    FROM order_items_inbox
                    WHERE order_id = ?
                """, (order['id'],))
                
                # Build ShipStation order payload
                order_payload = {
                    'orderNumber': order['order_number'],
                    'orderDate': order['order_date'],
                    'orderStatus': 'awaiting_shipment',
                    'customerEmail': order['customer_email'],
                    'items': [
                        {
                            'sku': item['sku'],
                            'name': item['sku_lot'] or item['sku'],
                            'quantity': item['quantity'],
                            'unitPrice': item['unit_price_cents'] / 100.0
                        }
                        for item in items
                    ]
                }
                
                # Upload to ShipStation
                response = shipstation.create_order(order_payload)
                
                # Update status in database
                db.execute_write("""
                    UPDATE orders_inbox 
                    SET status = 'uploaded',
                        shipstation_order_id = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (response['orderId'], order['id']))
                
                uploaded_count += 1
                
            except Exception as e:
                # Mark order as failed
                db.execute_write("""
                    UPDATE orders_inbox 
                    SET status = 'failed',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (order['id'],))
                logger.error(f"Failed to upload order {order['order_number']}: {e}")
        
        # Update workflow status
        duration = int((datetime.now() - start_time).total_seconds())
        update_workflow_status(
            workflow_name,
            'completed',
            duration=duration,
            records_processed=uploaded_count,
            details=f'Uploaded {uploaded_count} orders to ShipStation'
        )
        
    except Exception as e:
        update_workflow_status(workflow_name, 'failed', details=str(e))
        raise
```

---

## External API Integrations

### ShipStation API Client

**File:** `src/services/shipstation/api_client.py`

```python
import requests
import os
from typing import Dict, List

class ShipStationClient:
    """ShipStation API client wrapper"""
    
    def __init__(self):
        self.api_key = os.getenv('SHIPSTATION_API_KEY')
        self.api_secret = os.getenv('SHIPSTATION_API_SECRET')
        self.base_url = 'https://ssapi.shipstation.com'
        
        if not self.api_key or not self.api_secret:
            raise ValueError("ShipStation API credentials not configured")
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Make authenticated API request"""
        url = f"{self.base_url}/{endpoint}"
        
        response = requests.request(
            method,
            url,
            auth=(self.api_key, self.api_secret),
            json=data,
            headers={'Content-Type': 'application/json'}
        )
        
        response.raise_for_status()
        return response.json()
    
    def get_shipments(self, ship_date_start: str, ship_date_end: str = None) -> List[Dict]:
        """Get shipments by date range"""
        params = {
            'shipDateStart': ship_date_start,
            'shipDateEnd': ship_date_end or ship_date_start
        }
        
        return self._make_request('GET', 'shipments', params)
    
    def create_order(self, order_data: Dict) -> Dict:
        """Create new order in ShipStation"""
        return self._make_request('POST', 'orders/createorder', order_data)
```

### Google Sheets (During Transition)

**File:** `src/services/google_sheets/api_client.py`

```python
# Keep for ETL migration only
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

class GoogleSheetsClient:
    """Google Sheets API client (for migration only)"""
    
    def __init__(self):
        creds = Credentials.from_service_account_file(
            'credentials/google_sheets_key.json',
            scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
        )
        self.service = build('sheets', 'v4', credentials=creds)
    
    def read_sheet(self, sheet_name: str, range_name: str = 'A:Z'):
        """Read data from Google Sheet"""
        spreadsheet_id = os.getenv('GOOGLE_SHEETS_ID')
        
        result = self.service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!{range_name}"
        ).execute()
        
        return result.get('values', [])
```

---

## Error Handling

### Standard Error Handling Pattern

```python
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def safe_database_operation(operation_name: str):
    """Decorator for database operations with error handling"""
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except sqlite3.IntegrityError as e:
                logger.error(f"{operation_name} - Integrity error: {e}")
                raise ValueError(f"Data integrity violation: {e}")
            except sqlite3.OperationalError as e:
                logger.error(f"{operation_name} - Database locked: {e}")
                raise RuntimeError(f"Database unavailable: {e}")
            except Exception as e:
                logger.error(f"{operation_name} - Unexpected error: {e}")
                raise
        return wrapper
    return decorator

@safe_database_operation("Update Inventory")
def update_inventory_with_error_handling(sku: str, quantity: int):
    """Example with error handling"""
    db.execute_write("""
        UPDATE inventory_current 
        SET current_quantity = current_quantity + ?
        WHERE sku = ?
    """, (quantity, sku))
```

### Retry Logic for API Calls

```python
import time
from functools import wraps

def retry_on_failure(max_attempts=3, delay=2):
    """Retry decorator for external API calls"""
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.RequestException as e:
                    if attempt == max_attempts - 1:
                        raise
                    logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying...")
                    time.sleep(delay * (attempt + 1))
            return None
        return wrapper
    return decorator

@retry_on_failure(max_attempts=3)
def fetch_shipstation_orders():
    """Fetch orders with retry logic"""
    client = ShipStationClient()
    return client.get_shipments(ship_date_start='2025-01-01')
```

---

## Testing & Validation

### Unit Tests

```python
# tests/test_db_utils.py

import pytest
import sqlite3
from services.database.db_utils import DatabaseConnection

@pytest.fixture
def test_db():
    """Create test database"""
    db = DatabaseConnection(':memory:')
    
    # Create test schema
    with db.transaction() as conn:
        conn.executescript("""
            CREATE TABLE workflows (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE,
                status TEXT
            );
        """)
    
    yield db

def test_upsert_operation(test_db):
    """Test UPSERT functionality"""
    
    # Insert
    test_db.upsert(
        'workflows',
        {'name': 'test_workflow', 'status': 'running'},
        conflict_columns=['name']
    )
    
    # Verify insert
    result = test_db.execute_query("SELECT * FROM workflows WHERE name = 'test_workflow'")
    assert len(result) == 1
    assert result[0]['status'] == 'running'
    
    # Update
    test_db.upsert(
        'workflows',
        {'name': 'test_workflow', 'status': 'completed'},
        conflict_columns=['name']
    )
    
    # Verify update
    result = test_db.execute_query("SELECT * FROM workflows WHERE name = 'test_workflow'")
    assert result[0]['status'] == 'completed'
```

### Integration Tests

```python
# tests/test_weekly_reporter.py

import pytest
from src.weekly_reporter import calculate_inventory_levels

@pytest.fixture
def setup_test_data(test_db):
    """Populate test data"""
    with test_db.transaction() as conn:
        # Add inventory transactions
        conn.execute("""
            INSERT INTO inventory_transactions (date, sku, quantity, transaction_type)
            VALUES ('2025-01-01', '17612', 100, 'Receive')
        """)
    
    yield test_db

def test_inventory_calculation(setup_test_data):
    """Test inventory level calculation"""
    
    calculate_inventory_levels()
    
    # Verify inventory_current updated
    result = setup_test_data.execute_query("""
        SELECT current_quantity FROM inventory_current WHERE sku = '17612'
    """)
    
    assert len(result) == 1
    assert result[0]['current_quantity'] == 100
```

---

## Migration from Google Sheets

### ETL Script Structure

See `MIGRATION_GUIDE.md` for complete ETL implementation.

**Key transformation patterns:**

```python
# Convert Google Sheets data to SQLite format

def transform_currency_to_cents(value):
    """Convert $12.34 to 1234 cents"""
    if isinstance(value, str):
        value = value.replace('$', '').replace(',', '')
    return int(float(value) * 100)

def transform_date_format(date_str):
    """Convert MM/DD/YYYY to YYYY-MM-DD"""
    from datetime import datetime
    dt = datetime.strptime(date_str, '%m/%d/%Y')
    return dt.strftime('%Y-%m-%d')

def transform_boolean(value):
    """Convert TRUE/FALSE to 1/0"""
    if isinstance(value, str):
        return 1 if value.upper() == 'TRUE' else 0
    return int(bool(value))
```

---

## Best Practices Summary

**✅ Database Operations:**
- Always use `db.transaction()` for writes
- Use UPSERT for idempotent operations
- Store money as INTEGER (cents)
- Use parameterized queries (prevent SQL injection)
- Close connections in finally blocks

**✅ API Integration:**
- Implement retry logic for external APIs
- Use environment variables for credentials
- Log all API requests and responses
- Handle rate limiting gracefully
- Validate data before database writes

**✅ Error Handling:**
- Use decorators for consistent error handling
- Log errors with context
- Update workflow status on failures
- Implement graceful degradation
- Monitor and alert on repeated failures

**✅ Testing:**
- Use in-memory SQLite for unit tests
- Mock external API calls
- Test transaction rollback scenarios
- Validate data transformations
- Test with production-like data volumes

---

## Environment Configuration

**Required environment variables:**

```bash
# Database
DATABASE_PATH=/path/to/ora.db

# ShipStation API
SHIPSTATION_API_KEY=your_api_key
SHIPSTATION_API_SECRET=your_api_secret

# Google Sheets (migration only)
GOOGLE_SHEETS_ID=your_spreadsheet_id
GOOGLE_SHEETS_CREDENTIALS=/path/to/credentials.json

# SendGrid (optional)
SENDGRID_API_KEY=your_sendgrid_key

# Development mode
DEV_MODE=0  # Set to 1 for development
```

---

## Support Resources

**Documentation:**
- Database schema: `docs/DATABASE_SCHEMA.md`
- Operations guide: `docs/DATABASE_OPERATIONS.md`
- Migration guide: `docs/MIGRATION_GUIDE.md`

**Code Examples:**
- Database utilities: `src/services/database/db_utils.py`
- Script templates: `src/weekly_reporter.py`, `src/daily_shipment_processor.py`
- Test fixtures: `tests/fixtures/`

**External APIs:**
- ShipStation docs: https://www.shipstation.com/docs/api/
- Google Sheets API: https://developers.google.com/sheets/api
