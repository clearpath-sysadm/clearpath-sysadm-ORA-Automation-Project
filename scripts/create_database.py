#!/usr/bin/env python3
"""
Create ORA automation database with 8 core tables.
MVP Phase 2: Database Setup
"""
import os
import sys
import sqlite3
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

DATABASE_PATH = os.getenv('DATABASE_PATH', 'ora.db')

def configure_database(conn):
    """Configure SQLite with optimal settings"""
    print("Configuring database...")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 8000")
    conn.execute("PRAGMA temp_store = MEMORY")
    conn.execute("PRAGMA cache_size = -20000")
    print("✅ Database configured with PRAGMA settings")

def create_workflows_table(conn):
    """Create workflows table for automation tracking"""
    print("Creating workflows table...")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS workflows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed', 'scheduled')),
            last_run_at TEXT,
            duration_seconds INTEGER,
            records_processed INTEGER,
            details TEXT,
            enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        ) STRICT
    """)
    
    conn.execute("CREATE INDEX IF NOT EXISTS idx_workflows_status ON workflows(status, enabled)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_workflows_enabled ON workflows(enabled)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_workflows_last_run ON workflows(status, last_run_at)")
    print("✅ workflows table created")

def create_inventory_current_table(conn):
    """Create inventory_current table for stock levels"""
    print("Creating inventory_current table...")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS inventory_current (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT NOT NULL UNIQUE,
            product_name TEXT NOT NULL,
            current_quantity INTEGER NOT NULL,
            weekly_avg_cents INTEGER,
            alert_level TEXT NOT NULL DEFAULT 'normal' CHECK (alert_level IN ('normal', 'low', 'critical')),
            reorder_point INTEGER NOT NULL DEFAULT 50,
            last_updated TEXT DEFAULT CURRENT_TIMESTAMP
        ) STRICT
    """)
    
    conn.execute("CREATE INDEX IF NOT EXISTS idx_inventory_current_alert ON inventory_current(alert_level)")
    # Note: No idx_inventory_current_sku - UNIQUE constraint already creates index
    print("✅ inventory_current table created")

def create_inventory_transactions_table(conn):
    """Create inventory_transactions table for audit trail"""
    print("Creating inventory_transactions table...")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS inventory_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            sku TEXT NOT NULL,
            quantity INTEGER NOT NULL CHECK (quantity != 0),
            transaction_type TEXT NOT NULL CHECK (transaction_type IN ('Receive', 'Ship', 'Adjust Up', 'Adjust Down')),
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date, sku, transaction_type, quantity)
        ) STRICT
    """)
    
    conn.execute("CREATE INDEX IF NOT EXISTS idx_inv_trans_sku_date ON inventory_transactions(sku, date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_inv_trans_date ON inventory_transactions(date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_inv_trans_type ON inventory_transactions(transaction_type)")
    print("✅ inventory_transactions table created")

def create_shipped_orders_table(conn):
    """Create shipped_orders table (must be created before shipped_items due to FK)"""
    print("Creating shipped_orders table...")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS shipped_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ship_date TEXT NOT NULL,
            order_number TEXT NOT NULL UNIQUE,
            customer_email TEXT,
            total_items INTEGER DEFAULT 0,
            shipstation_order_id TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        ) STRICT
    """)
    
    conn.execute("CREATE INDEX IF NOT EXISTS idx_shipped_orders_date ON shipped_orders(ship_date)")
    # Note: No idx_shipped_orders_number - UNIQUE constraint already creates index
    print("✅ shipped_orders table created")

def create_shipped_items_table(conn):
    """Create shipped_items table for line items"""
    print("Creating shipped_items table...")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS shipped_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ship_date TEXT NOT NULL,
            sku_lot TEXT NOT NULL DEFAULT '',
            base_sku TEXT NOT NULL,
            quantity_shipped INTEGER NOT NULL CHECK (quantity_shipped > 0),
            order_number TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(order_number, base_sku, sku_lot),
            FOREIGN KEY (order_number) REFERENCES shipped_orders(order_number)
        ) STRICT
    """)
    
    conn.execute("CREATE INDEX IF NOT EXISTS idx_shipped_items_date ON shipped_items(ship_date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_shipped_items_sku_date ON shipped_items(base_sku, ship_date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_shipped_items_order ON shipped_items(order_number)")
    print("✅ shipped_items table created")

def create_weekly_shipped_history_table(conn):
    """Create weekly_shipped_history table for aggregations"""
    print("Creating weekly_shipped_history table...")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS weekly_shipped_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            sku TEXT NOT NULL,
            quantity_shipped INTEGER NOT NULL CHECK (quantity_shipped >= 0),
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(start_date, end_date, sku)
        ) STRICT
    """)
    
    conn.execute("CREATE INDEX IF NOT EXISTS idx_weekly_history_dates ON weekly_shipped_history(start_date, end_date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_weekly_history_sku_start ON weekly_shipped_history(sku, start_date)")
    print("✅ weekly_shipped_history table created")

def create_system_kpis_table(conn):
    """Create system_kpis table for dashboard metrics"""
    print("Creating system_kpis table...")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS system_kpis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_date TEXT NOT NULL UNIQUE,
            orders_today INTEGER DEFAULT 0,
            shipments_sent INTEGER DEFAULT 0,
            pending_uploads INTEGER DEFAULT 0,
            system_status TEXT NOT NULL DEFAULT 'online' CHECK (system_status IN ('online', 'degraded', 'offline')),
            total_revenue_cents INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        ) STRICT
    """)
    
    # Note: No idx_kpis_date - UNIQUE constraint already creates index
    print("✅ system_kpis table created")

def create_configuration_params_table(conn):
    """Create configuration_params table for business settings"""
    print("Creating configuration_params table...")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS configuration_params (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            parameter_name TEXT NOT NULL,
            value TEXT NOT NULL,
            sku TEXT,
            notes TEXT,
            last_updated TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(category, parameter_name, sku)
        ) STRICT
    """)
    
    conn.execute("CREATE INDEX IF NOT EXISTS idx_config_category ON configuration_params(category)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_config_sku ON configuration_params(sku)")
    print("✅ configuration_params table created")

def verify_tables(conn):
    """Verify all tables were created"""
    print("\nVerifying tables...")
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    
    expected_tables = [
        'workflows',
        'inventory_current',
        'inventory_transactions',
        'shipped_orders',
        'shipped_items',
        'weekly_shipped_history',
        'system_kpis',
        'configuration_params'
    ]
    
    for table in expected_tables:
        if table in tables:
            print(f"✅ {table}")
        else:
            print(f"❌ {table} MISSING")
            return False
    
    return True

def main():
    print("=" * 60)
    print("ORA DATABASE CREATION - PHASE 2")
    print("=" * 60)
    print(f"\nDatabase path: {DATABASE_PATH}")
    
    # Check for non-interactive mode
    non_interactive = os.getenv('OVERWRITE', '').lower() in ('1', 'yes', 'true')
    
    if os.path.exists(DATABASE_PATH):
        if non_interactive:
            print(f"⚠️  Database {DATABASE_PATH} already exists. Overwriting (non-interactive mode)...")
            os.remove(DATABASE_PATH)
        else:
            response = input(f"\n⚠️  Database {DATABASE_PATH} already exists. Overwrite? (yes/no): ")
            if response.lower() != 'yes':
                print("Aborted.")
                return
            os.remove(DATABASE_PATH)
        print(f"Removed existing database: {DATABASE_PATH}")
    
    print("\nCreating new database...")
    conn = sqlite3.connect(DATABASE_PATH)
    
    try:
        # Configure database
        configure_database(conn)
        
        # Create tables (order matters due to foreign keys)
        create_workflows_table(conn)
        create_inventory_current_table(conn)
        create_inventory_transactions_table(conn)
        create_shipped_orders_table(conn)  # Must be before shipped_items
        create_shipped_items_table(conn)
        create_weekly_shipped_history_table(conn)
        create_system_kpis_table(conn)
        create_configuration_params_table(conn)
        
        # Commit changes
        conn.commit()
        
        # Verify
        if verify_tables(conn):
            print("\n" + "=" * 60)
            print("✅ DATABASE CREATED SUCCESSFULLY")
            print("=" * 60)
            print(f"\n8 tables created with STRICT typing")
            print(f"All indexes created")
            print(f"Foreign keys enabled")
            print(f"Database ready for seeding")
        else:
            print("\n❌ DATABASE CREATION FAILED - Missing tables")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
