#!/usr/bin/env python3
"""
Oracare Fulfillment System - Database Initialization Script

This script initializes a fresh PostgreSQL database with all required tables,
constraints, and essential configuration data.

Usage:
    python init_database.py

Requirements:
    - PostgreSQL database credentials in environment variables:
      DATABASE_URL (or PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE)
"""

import os
import sys
import psycopg2
from psycopg2 import sql
from datetime import datetime

def get_db_connection():
    """Get database connection from environment variables."""
    database_url = os.getenv('DATABASE_URL')
    
    if database_url:
        return psycopg2.connect(database_url)
    else:
        return psycopg2.connect(
            host=os.getenv('PGHOST', 'localhost'),
            port=os.getenv('PGPORT', '5432'),
            user=os.getenv('PGUSER'),
            password=os.getenv('PGPASSWORD'),
            database=os.getenv('PGDATABASE')
        )

def run_schema_file(cursor, schema_file='database_schema_export.sql'):
    """Run the schema export SQL file to create all tables."""
    print(f"📋 Loading schema from {schema_file}...")
    
    if not os.path.exists(schema_file):
        print(f"❌ Schema file not found: {schema_file}")
        print("   Please ensure database_schema_export.sql is in the current directory.")
        return False
    
    with open(schema_file, 'r') as f:
        schema_sql = f.read()
    
    try:
        cursor.execute(schema_sql)
        print("✅ Schema created successfully")
        return True
    except Exception as e:
        print(f"❌ Error creating schema: {e}")
        return False

def insert_essential_config(cursor):
    """Insert essential configuration data."""
    print("\n📝 Inserting essential configuration data...")
    
    # Key Products (SKUs that the system processes)
    key_products = [
        ('17612', 'PT Kit'),
        ('17904', 'Travel Kit'),
        ('17914', 'PPR Kit'),
        ('18675', 'Ortho Protect'),
        ('18795', 'OraPro Paste Peppermint')
    ]
    
    for sku, name in key_products:
        cursor.execute("""
            INSERT INTO configuration_params (category, parameter_name, value, sku, notes, created_at)
            VALUES ('Key Products', %s, '', %s, '', CURRENT_TIMESTAMP)
            ON CONFLICT DO NOTHING
        """, (name, sku))
    
    print(f"   ✅ Added {len(key_products)} Key Products")
    
    # Initial Inventory baseline (September 19, 2025)
    initial_inventory = [
        ('17612', '1019', '1049'),
        ('17904', '468', '18'),
        ('17914', '1410', '42'),
        ('18675', '714', '715'),
        ('18795', '7719', '7780')
    ]
    
    for sku, eod_value, original_notes in initial_inventory:
        cursor.execute("""
            INSERT INTO configuration_params (category, parameter_name, value, sku, notes, created_at)
            VALUES ('InitialInventory', 'EOD_Prior_Week', %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT DO NOTHING
        """, (eod_value, sku, original_notes))
    
    print(f"   ✅ Added {len(initial_inventory)} Initial Inventory records")

def insert_workflow_controls(cursor):
    """Insert workflow control records."""
    print("\n⚙️  Setting up workflow controls...")
    
    workflows = [
        ('xml_import', True, 'XML polling and order import from Google Drive'),
        ('shipstation_upload', True, 'Upload pending orders to ShipStation'),
        ('shipstation_sync', True, 'Sync order status from ShipStation'),
        ('duplicate_scanner', True, 'Monitor and resolve duplicate orders'),
        ('lot_mismatch_scanner', True, 'Detect lot number discrepancies'),
        ('orders_cleanup', True, 'Clean up old orders (60+ days)')
    ]
    
    for workflow_name, enabled, description in workflows:
        cursor.execute("""
            INSERT INTO workflow_controls (workflow_name, enabled, description, updated_at)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (workflow_name) DO UPDATE SET
                description = EXCLUDED.description
        """, (workflow_name, enabled, description))
    
    print(f"   ✅ Configured {len(workflows)} workflow controls")

def insert_sample_bundle_skus(cursor):
    """Insert commonly used bundle SKUs."""
    print("\n📦 Setting up bundle SKUs...")
    
    # Core bundles that are frequently used
    bundles = [
        ('18235', 'OraCare Buy 12 Get 3 Free', '17612', 15),
        ('18255', 'OraCare Buy 5 Get 1 Free', '17612', 6),
        ('18345', 'Autoship; OraCare Health Rinse', '17612', 1),
        ('18355', 'Free; OraCare Health Rinse', '17612', 1),
        ('18625', 'Starter Pack = 3 * 17612', '17612', 3),
    ]
    
    for bundle_sku, description, component_sku, multiplier in bundles:
        # Insert bundle
        cursor.execute("""
            INSERT INTO bundle_skus (bundle_sku, description, active, created_at, updated_at)
            VALUES (%s, %s, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT (bundle_sku) DO NOTHING
            RETURNING id
        """, (bundle_sku, description))
        
        result = cursor.fetchone()
        if result:
            bundle_id = result[0]
            
            # Insert component
            cursor.execute("""
                INSERT INTO bundle_components (bundle_sku_id, component_sku, multiplier, sequence, created_at)
                VALUES (%s, %s, %s, 1, CURRENT_TIMESTAMP)
            """, (bundle_id, component_sku, multiplier))
    
    print(f"   ✅ Added {len(bundles)} sample bundle SKUs")

def verify_installation(cursor):
    """Verify the database was set up correctly."""
    print("\n🔍 Verifying installation...")
    
    checks = [
        ("Tables created", "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'", 33),
        ("Key Products", "SELECT COUNT(*) FROM configuration_params WHERE category = 'Key Products'", 5),
        ("Workflow controls", "SELECT COUNT(*) FROM workflow_controls", 6),
        ("Bundle SKUs", "SELECT COUNT(*) FROM bundle_skus", None),
    ]
    
    all_passed = True
    for check_name, query, expected_min in checks:
        cursor.execute(query)
        count = cursor.fetchone()[0]
        
        if expected_min and count >= expected_min:
            print(f"   ✅ {check_name}: {count} (expected >= {expected_min})")
        elif not expected_min:
            print(f"   ℹ️  {check_name}: {count}")
        else:
            print(f"   ❌ {check_name}: {count} (expected >= {expected_min})")
            all_passed = False
    
    return all_passed

def main():
    """Main initialization routine."""
    print("=" * 60)
    print("  Oracare Fulfillment System - Database Initialization")
    print("=" * 60)
    print()
    
    try:
        # Connect to database
        print("🔌 Connecting to PostgreSQL database...")
        conn = get_db_connection()
        conn.autocommit = False
        cursor = conn.cursor()
        print("   ✅ Connected successfully")
        
        # Check if database is already initialized
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'orders_inbox'
        """)
        
        if cursor.fetchone()[0] > 0:
            print("\n⚠️  WARNING: Database appears to already be initialized!")
            print("   The 'orders_inbox' table already exists.")
            response = input("\n   Continue anyway? This will skip existing data (y/N): ")
            if response.lower() != 'y':
                print("\n❌ Initialization cancelled by user")
                return 1
        
        # Run schema creation
        if not run_schema_file(cursor, 'database_schema_export.sql'):
            print("\n❌ Schema creation failed. Aborting.")
            conn.rollback()
            return 1
        
        # Insert essential data
        insert_essential_config(cursor)
        insert_workflow_controls(cursor)
        insert_sample_bundle_skus(cursor)
        
        # Verify
        if not verify_installation(cursor):
            print("\n⚠️  Some verification checks failed")
            response = input("   Commit changes anyway? (y/N): ")
            if response.lower() != 'y':
                conn.rollback()
                print("\n❌ Changes rolled back")
                return 1
        
        # Commit all changes
        conn.commit()
        print("\n" + "=" * 60)
        print("✅ DATABASE INITIALIZATION COMPLETE!")
        print("=" * 60)
        print()
        print("Next steps:")
        print("1. Set up active lot numbers in the sku_lot table")
        print("2. Configure ShipStation API credentials in Secrets")
        print("3. Set up Google Drive integration for XML imports")
        print("4. Start the application workflows")
        print()
        
        cursor.close()
        conn.close()
        return 0
        
    except psycopg2.Error as e:
        print(f"\n❌ Database error: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
