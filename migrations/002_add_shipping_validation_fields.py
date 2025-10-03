#!/usr/bin/env python3
"""
Migration: Add shipping validation fields and violations table

Adds carrier and service tracking fields to orders_inbox table to support
shipping validation rules (Hawaiian orders, Benco carrier account, Canadian shipping).
Creates shipping_violations table for tracking and alerting.

Date: 2025-10-03
"""

import sqlite3
import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)


def migrate_up(db_path='ora.db'):
    """Apply the migration"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("Starting migration: Add shipping validation fields...")
        
        # Check if migration is needed
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='orders_inbox'")
        current_schema = cursor.fetchone()[0]
        
        if "shipping_carrier_code" in current_schema:
            print("Migration already applied - skipping")
            return
        
        print("Creating new orders_inbox table with carrier/service fields...")
        
        # Create new table with carrier/service tracking fields
        cursor.execute("""
            CREATE TABLE orders_inbox_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_number TEXT NOT NULL UNIQUE,
                order_date DATE NOT NULL,
                customer_email TEXT,
                status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'uploaded', 'failed', 'synced_manual', 'shipped', 'cancelled', 'on_hold', 'awaiting_payment')),
                shipstation_order_id TEXT,
                total_items INTEGER DEFAULT 0,
                total_amount_cents INTEGER,
                source_system TEXT DEFAULT 'X-Cart',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                failure_reason TEXT,
                ship_name TEXT,
                ship_company TEXT,
                ship_street1 TEXT,
                ship_street2 TEXT,
                ship_city TEXT,
                ship_state TEXT,
                ship_postal_code TEXT,
                ship_country TEXT,
                ship_phone TEXT,
                bill_name TEXT,
                bill_company TEXT,
                bill_street1 TEXT,
                bill_street2 TEXT,
                bill_city TEXT,
                bill_state TEXT,
                bill_postal_code TEXT,
                bill_country TEXT,
                bill_phone TEXT,
                shipping_carrier_code TEXT,
                shipping_carrier_id TEXT,
                shipping_service_code TEXT,
                shipping_service_name TEXT
            )
        """)
        
        print("Copying data from old table...")
        cursor.execute("""
            INSERT INTO orders_inbox_new 
            (id, order_number, order_date, customer_email, status, shipstation_order_id, 
             total_items, total_amount_cents, source_system, created_at, updated_at, failure_reason,
             ship_name, ship_company, ship_street1, ship_street2, ship_city, ship_state, 
             ship_postal_code, ship_country, ship_phone,
             bill_name, bill_company, bill_street1, bill_street2, bill_city, bill_state,
             bill_postal_code, bill_country, bill_phone)
            SELECT 
             id, order_number, order_date, customer_email, status, shipstation_order_id,
             total_items, total_amount_cents, source_system, created_at, updated_at, failure_reason,
             ship_name, ship_company, ship_street1, ship_street2, ship_city, ship_state,
             ship_postal_code, ship_country, ship_phone,
             bill_name, bill_company, bill_street1, bill_street2, bill_city, bill_state,
             bill_postal_code, bill_country, bill_phone
            FROM orders_inbox
        """)
        
        row_count = cursor.rowcount
        print(f"Copied {row_count} rows")
        
        print("Dropping old table...")
        cursor.execute("DROP TABLE orders_inbox")
        
        print("Renaming new table...")
        cursor.execute("ALTER TABLE orders_inbox_new RENAME TO orders_inbox")
        
        print("Creating indexes...")
        cursor.execute("CREATE INDEX idx_orders_inbox_status ON orders_inbox(status, created_at)")
        cursor.execute("CREATE INDEX idx_orders_inbox_date ON orders_inbox(order_date)")
        cursor.execute("CREATE INDEX idx_orders_inbox_carrier ON orders_inbox(shipping_carrier_code)")
        
        print("Creating shipping_violations table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shipping_violations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                order_number TEXT NOT NULL,
                violation_type TEXT NOT NULL CHECK (violation_type IN ('hawaiian_service', 'benco_carrier', 'canadian_service')),
                expected_value TEXT NOT NULL,
                actual_value TEXT,
                detected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                resolved_at DATETIME,
                is_resolved INTEGER NOT NULL DEFAULT 0 CHECK (is_resolved IN (0, 1)),
                FOREIGN KEY (order_id) REFERENCES orders_inbox(id) ON DELETE CASCADE
            )
        """)
        
        print("Creating violations indexes...")
        cursor.execute("CREATE INDEX idx_violations_resolved ON shipping_violations(is_resolved, detected_at)")
        cursor.execute("CREATE INDEX idx_violations_order ON shipping_violations(order_id)")
        cursor.execute("CREATE INDEX idx_violations_type ON shipping_violations(violation_type)")
        
        conn.commit()
        print("✅ Migration completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        conn.close()


def migrate_down(db_path='ora.db'):
    """Rollback the migration (remove carrier/service fields and violations table)"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("Rolling back migration: Remove shipping validation fields...")
        
        print("Dropping shipping_violations table...")
        cursor.execute("DROP TABLE IF EXISTS shipping_violations")
        
        print("Creating orders_inbox table without carrier/service fields...")
        cursor.execute("""
            CREATE TABLE orders_inbox_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_number TEXT NOT NULL UNIQUE,
                order_date DATE NOT NULL,
                customer_email TEXT,
                status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'uploaded', 'failed', 'synced_manual', 'shipped', 'cancelled', 'on_hold', 'awaiting_payment')),
                shipstation_order_id TEXT,
                total_items INTEGER DEFAULT 0,
                total_amount_cents INTEGER,
                source_system TEXT DEFAULT 'X-Cart',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                failure_reason TEXT,
                ship_name TEXT,
                ship_company TEXT,
                ship_street1 TEXT,
                ship_street2 TEXT,
                ship_city TEXT,
                ship_state TEXT,
                ship_postal_code TEXT,
                ship_country TEXT,
                ship_phone TEXT,
                bill_name TEXT,
                bill_company TEXT,
                bill_street1 TEXT,
                bill_street2 TEXT,
                bill_city TEXT,
                bill_state TEXT,
                bill_postal_code TEXT,
                bill_country TEXT,
                bill_phone TEXT
            )
        """)
        
        print("Copying data (dropping carrier/service columns)...")
        cursor.execute("""
            INSERT INTO orders_inbox_new 
            SELECT 
                id, order_number, order_date, customer_email, status, shipstation_order_id,
                total_items, total_amount_cents, source_system, created_at, updated_at, failure_reason,
                ship_name, ship_company, ship_street1, ship_street2, ship_city, ship_state,
                ship_postal_code, ship_country, ship_phone,
                bill_name, bill_company, bill_street1, bill_street2, bill_city, bill_state,
                bill_postal_code, bill_country, bill_phone
            FROM orders_inbox
        """)
        
        cursor.execute("DROP TABLE orders_inbox")
        cursor.execute("ALTER TABLE orders_inbox_new RENAME TO orders_inbox")
        
        print("Recreating original indexes...")
        cursor.execute("CREATE INDEX idx_orders_inbox_status ON orders_inbox(status, created_at)")
        cursor.execute("CREATE INDEX idx_orders_inbox_date ON orders_inbox(order_date)")
        
        conn.commit()
        print("✅ Rollback completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Rollback failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'down':
        migrate_down()
    else:
        migrate_up()
