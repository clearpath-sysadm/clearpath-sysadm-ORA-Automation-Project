#!/usr/bin/env python3
"""
Migration: Add additional status values to orders_inbox CHECK constraint

Adds 'shipped', 'cancelled', 'on_hold', 'awaiting_payment' to the allowed status values
in the orders_inbox table to support status sync from ShipStation.

Date: 2025-10-02
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
        print("Starting migration: Add status values to orders_inbox...")
        
        # Check if migration is needed
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='orders_inbox'")
        current_schema = cursor.fetchone()[0]
        
        if "'shipped'" in current_schema and "'cancelled'" in current_schema:
            print("Migration already applied - skipping")
            return
        
        print("Creating new table with updated CHECK constraint...")
        
        # Create new table with updated CHECK constraint
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
        
        print("Copying data from old table...")
        cursor.execute("INSERT INTO orders_inbox_new SELECT * FROM orders_inbox")
        
        row_count = cursor.rowcount
        print(f"Copied {row_count} rows")
        
        print("Dropping old table...")
        cursor.execute("DROP TABLE orders_inbox")
        
        print("Renaming new table...")
        cursor.execute("ALTER TABLE orders_inbox_new RENAME TO orders_inbox")
        
        conn.commit()
        print("✅ Migration completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        conn.close()


def migrate_down(db_path='ora.db'):
    """Rollback the migration (restore original CHECK constraint)"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("Rolling back migration: Remove status values from orders_inbox...")
        
        # Create table with original CHECK constraint
        cursor.execute("""
            CREATE TABLE orders_inbox_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_number TEXT NOT NULL UNIQUE,
                order_date DATE NOT NULL,
                customer_email TEXT,
                status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'uploaded', 'failed', 'synced_manual')),
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
        
        # Copy data, converting any new status values to 'uploaded'
        cursor.execute("""
            INSERT INTO orders_inbox_new 
            SELECT 
                id, order_number, order_date, customer_email,
                CASE 
                    WHEN status IN ('shipped', 'cancelled', 'on_hold', 'awaiting_payment') THEN 'uploaded'
                    ELSE status 
                END as status,
                shipstation_order_id, total_items, total_amount_cents, source_system,
                created_at, updated_at, failure_reason,
                ship_name, ship_company, ship_street1, ship_street2, ship_city, ship_state, ship_postal_code, ship_country, ship_phone,
                bill_name, bill_company, bill_street1, bill_street2, bill_city, bill_state, bill_postal_code, bill_country, bill_phone
            FROM orders_inbox
        """)
        
        cursor.execute("DROP TABLE orders_inbox")
        cursor.execute("ALTER TABLE orders_inbox_new RENAME TO orders_inbox")
        
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
