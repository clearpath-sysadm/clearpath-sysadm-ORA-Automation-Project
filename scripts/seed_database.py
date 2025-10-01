#!/usr/bin/env python3
"""
Seed minimal data for ORA database - Phase 2.2
Seeds only essential data needed for MVP scripts to run
"""

import sqlite3
import os
import sys
from datetime import datetime

DATABASE_PATH = "ora.db"

def seed_workflows(conn):
    """Seed 2 critical workflow records"""
    print("Seeding workflows...")
    
    workflows = [
        (
            'weekly_reporter',
            'Weekly Inventory Reporter',
            'scheduled',
            None,
            None,
            None,
            'Calculates inventory levels and 52-week rolling averages',
            1
        ),
        (
            'daily_shipment_processor',
            'Daily Shipment Processor',
            'scheduled',
            None,
            None,
            None,
            'Fetches shipments from ShipStation and updates database',
            1
        )
    ]
    
    conn.executemany("""
        INSERT OR IGNORE INTO workflows (
            name, display_name, status, last_run_at, 
            duration_seconds, records_processed, details, enabled
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, workflows)
    
    print(f"  ✅ Inserted {len(workflows)} workflows")

def seed_configuration_params(conn):
    """Seed critical configuration parameters"""
    print("Seeding configuration parameters...")
    
    params = [
        # Rate configurations
        ('Rates', 'pick_pack_rate_cents', '68', None, 'Pick and pack rate per item in cents', None),
        ('Rates', 'storage_rate_cents', '3', None, 'Monthly storage rate per pallet in cents', None),
        ('Rates', 'monthly_space_rental_cents', '30000', None, 'Fixed monthly space rental in cents ($300)', None),
        
        # Pallet configurations
        ('PalletConfig', 'pallet_capacity', '156', None, 'Cases per pallet', None),
        ('PalletConfig', 'items_per_case', '12', None, 'Items per case', None),
        
        # Initial inventory for key products (will be overwritten by migration)
        ('InitialInventory', 'quantity', '0', '17612', 'ORAMD Floss Picks 90ct', None),
        ('InitialInventory', 'quantity', '0', '17914', 'ORAMD Floss Picks 150ct', None),
        ('InitialInventory', 'quantity', '0', '17904', 'ORAMD Interdental Brushes', None),
        ('InitialInventory', 'quantity', '0', '17975', 'ORAMD Tongue Cleaner', None),
        ('InitialInventory', 'quantity', '0', '18675', 'ORAMD Whitening Strips', None),
        
        # System configuration
        ('System', 'database_version', '1.0', None, 'Current database schema version', None),
        ('System', 'last_migration_date', datetime.now().strftime('%Y-%m-%d'), None, 'Last successful data migration', None),
    ]
    
    conn.executemany("""
        INSERT OR IGNORE INTO configuration_params (
            category, parameter_name, value, sku, notes, last_updated
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, params)
    
    print(f"  ✅ Inserted {len(params)} configuration parameters")

def seed_inventory_current(conn):
    """Seed 5 key products in inventory_current table"""
    print("Seeding inventory_current...")
    
    products = [
        ('17612', 'ORAMD Floss Picks 90ct', 0, None, 'normal', 50),
        ('17914', 'ORAMD Floss Picks 150ct', 0, None, 'normal', 50),
        ('17904', 'ORAMD Interdental Brushes', 0, None, 'normal', 50),
        ('17975', 'ORAMD Tongue Cleaner', 0, None, 'normal', 50),
        ('18675', 'ORAMD Whitening Strips', 0, None, 'normal', 50),
    ]
    
    conn.executemany("""
        INSERT OR IGNORE INTO inventory_current (
            sku, product_name, current_quantity, weekly_avg_cents, 
            alert_level, reorder_point
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, products)
    
    print(f"  ✅ Inserted {len(products)} key products")

def seed_system_kpis(conn):
    """Seed initial KPI snapshot"""
    print("Seeding system_kpis...")
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    conn.execute("""
        INSERT OR IGNORE INTO system_kpis (
            snapshot_date, orders_today, shipments_sent, 
            pending_uploads, system_status, total_revenue_cents
        ) VALUES (?, 0, 0, 0, 'online', 0)
    """, (today,))
    
    print(f"  ✅ Inserted initial KPI snapshot for {today}")

def verify_seed_data(conn):
    """Verify all seed data was inserted correctly"""
    print("\nVerifying seed data...")
    
    tables = {
        'workflows': 2,
        'configuration_params': 12,
        'inventory_current': 5,
        'system_kpis': 1,
    }
    
    all_correct = True
    for table, expected_count in tables.items():
        cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
        actual_count = cursor.fetchone()[0]
        
        if actual_count == expected_count:
            print(f"  ✅ {table}: {actual_count} rows (expected {expected_count})")
        else:
            print(f"  ❌ {table}: {actual_count} rows (expected {expected_count})")
            all_correct = False
    
    return all_correct

def main():
    print("=" * 60)
    print("ORA DATABASE SEEDING - PHASE 2.2")
    print("=" * 60)
    
    if not os.path.exists(DATABASE_PATH):
        print(f"\n❌ Database not found: {DATABASE_PATH}")
        print("Run: OVERWRITE=1 python scripts/create_database.py")
        sys.exit(1)
    
    print(f"\nDatabase: {DATABASE_PATH}")
    print("Seeding minimal data for MVP...\n")
    
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    
    try:
        conn.execute("BEGIN IMMEDIATE")
        
        seed_workflows(conn)
        seed_configuration_params(conn)
        seed_inventory_current(conn)
        seed_system_kpis(conn)
        
        conn.commit()
        
        if verify_seed_data(conn):
            print("\n" + "=" * 60)
            print("✅ DATABASE SEEDING COMPLETED SUCCESSFULLY")
            print("=" * 60)
            print("\n20 total rows inserted across 4 tables")
            print("Database ready for historical data migration (Phase 3)")
            print("\nNote: Script is idempotent - safe to run multiple times")
        else:
            print("\n⚠️  Seeding completed with validation warnings")
            sys.exit(1)
            
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error during seeding: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
