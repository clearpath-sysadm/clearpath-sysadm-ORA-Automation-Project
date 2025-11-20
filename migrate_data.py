#!/usr/bin/env python3
"""
Oracare Fulfillment System - Data Migration Script

This script exports data from the current database and generates SQL to import
into a new database instance, preserving all operational data while respecting
foreign key constraints.

Usage:
    # Step 1: Export data from CURRENT database (run in original Repl)
    python migrate_data.py export
    
    # Step 2: Transfer data_migration.sql to new Repl
    
    # Step 3: Import data into NEW database (run in new Repl)
    python migrate_data.py import

Requirements:
    - PostgreSQL database credentials in environment variables
    - Write permissions in current directory
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

def export_data(output_file='data_migration.sql'):
    """Export data from current database to SQL file."""
    print("=" * 70)
    print("  Oracare Fulfillment System - Data Export")
    print("=" * 70)
    print()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tables to export in dependency order (respecting foreign keys)
    tables_to_export = [
        # Core configuration (no dependencies)
        ('configuration_params', True),
        ('workflow_controls', True),
        ('users', True),
        ('oauth', True),
        
        # Bundle configuration
        ('bundle_skus', True),
        ('bundle_components', True),
        
        # SKU and inventory management
        ('sku_lot', True),
        ('lot_inventory', True),
        ('inventory_current', True),
        ('inventory_transactions', True),
        
        # Orders and shipping
        ('orders_inbox', False),  # Skip active orders - will be imported fresh
        ('order_items_inbox', False),
        ('shipped_orders', True),  # Keep historical shipments
        ('shipped_items', True),
        ('shipstation_order_line_items', True),
        
        # Monitoring and alerts
        ('duplicate_order_alerts', True),
        ('excluded_duplicate_orders', True),
        ('deleted_shipstation_orders', True),
        ('lot_mismatch_alerts', True),
        ('shipping_violations', True),
        ('manual_order_conflicts', True),
        
        # System metrics and reporting
        ('system_kpis', True),
        ('shipstation_metrics', True),
        ('weekly_shipped_history', True),
        ('report_runs', True),
        
        # Incidents and tracking
        ('production_incidents', True),
        ('incident_notes', True),
        ('production_incident_screenshots', True),
        
        # Misc
        ('email_contacts', True),
        ('fedex_pickup_log', True),
        ('polling_state', True),
        ('sync_watermark', True),
        ('workflows', True),
    ]
    
    with open(output_file, 'w') as f:
        # Write header
        f.write("-- Oracare Fulfillment System - Data Migration\n")
        f.write(f"-- Generated: {datetime.now().isoformat()}\n")
        f.write("--\n")
        f.write("-- IMPORTANT: Run this AFTER init_database.py has created the schema\n")
        f.write("--\n\n")
        f.write("BEGIN;\n\n")
        
        total_rows = 0
        tables_exported = 0
        
        for table_name, include in tables_to_export:
            if not include:
                print(f"⏭️  Skipping {table_name} (active operational data)")
                continue
            
            # Check if table exists
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = %s
            """, (table_name,))
            
            if cursor.fetchone()[0] == 0:
                print(f"⚠️  Table {table_name} not found, skipping")
                continue
            
            # Get row count
            cursor.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(
                sql.Identifier(table_name)
            ))
            row_count = cursor.fetchone()[0]
            
            if row_count == 0:
                print(f"📭 {table_name}: 0 rows (empty)")
                continue
            
            print(f"📦 Exporting {table_name}: {row_count} rows...")
            
            # Get column names
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position
            """, (table_name,))
            
            columns = [row[0] for row in cursor.fetchall()]
            
            # Write table header
            f.write(f"-- Table: {table_name} ({row_count} rows)\n")
            f.write(f"DELETE FROM {table_name};\n")
            
            # Fetch and write data in batches
            cursor.execute(sql.SQL("SELECT * FROM {}").format(
                sql.Identifier(table_name)
            ))
            
            batch_size = 100
            batch = []
            
            for row in cursor:
                # Escape and format values
                values = []
                for val in row:
                    if val is None:
                        values.append('NULL')
                    elif isinstance(val, (int, float)):
                        values.append(str(val))
                    elif isinstance(val, bool):
                        values.append('TRUE' if val else 'FALSE')
                    else:
                        # Escape single quotes and wrap in quotes
                        escaped = str(val).replace("'", "''")
                        values.append(f"'{escaped}'")
                
                batch.append(f"({', '.join(values)})")
                
                # Write batch when full
                if len(batch) >= batch_size:
                    column_list = ', '.join(columns)
                    f.write(f"INSERT INTO {table_name} ({column_list}) VALUES\n")
                    f.write(',\n'.join(batch))
                    f.write(';\n\n')
                    batch = []
            
            # Write remaining batch
            if batch:
                column_list = ', '.join(columns)
                f.write(f"INSERT INTO {table_name} ({column_list}) VALUES\n")
                f.write(',\n'.join(batch))
                f.write(';\n\n')
            
            total_rows += row_count
            tables_exported += 1
        
        # Reset sequences to max ID values
        f.write("\n-- Reset sequences to avoid ID conflicts\n")
        
        sequence_tables = [
            'bundle_skus', 'bundle_components', 'configuration_params',
            'sku_lot', 'shipped_orders', 'shipped_items', 'production_incidents',
            'incident_notes', 'duplicate_order_alerts', 'lot_mismatch_alerts'
        ]
        
        for table in sequence_tables:
            f.write(f"SELECT setval('{table}_id_seq', COALESCE((SELECT MAX(id) FROM {table}), 1));\n")
        
        f.write("\nCOMMIT;\n")
        f.write("\n-- Migration complete!\n")
    
    cursor.close()
    conn.close()
    
    print()
    print("=" * 70)
    print(f"✅ Export complete!")
    print(f"   Tables exported: {tables_exported}")
    print(f"   Total rows: {total_rows}")
    print(f"   Output file: {output_file}")
    print("=" * 70)
    print()
    print("Next steps:")
    print(f"1. Transfer {output_file} to your new Repl")
    print("2. In new Repl, run: python migrate_data.py import")
    print()

def import_data(input_file='data_migration.sql'):
    """Import data from SQL file into current database."""
    print("=" * 70)
    print("  Oracare Fulfillment System - Data Import")
    print("=" * 70)
    print()
    
    if not os.path.exists(input_file):
        print(f"❌ Error: {input_file} not found!")
        print("   Make sure you've transferred the file from the original Repl.")
        return 1
    
    print(f"📂 Reading {input_file}...")
    
    with open(input_file, 'r') as f:
        sql_content = f.read()
    
    print(f"   File size: {len(sql_content)} bytes")
    print()
    
    # Confirm before proceeding
    print("⚠️  WARNING: This will delete and replace existing data in the following areas:")
    print("   - Configuration settings")
    print("   - Bundle SKUs")
    print("   - SKU lot assignments")
    print("   - Historical shipped orders")
    print("   - Inventory records")
    print("   - Incidents and alerts")
    print()
    
    response = input("Continue with import? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Import cancelled")
        return 1
    
    print()
    print("🔌 Connecting to database...")
    
    conn = get_db_connection()
    conn.autocommit = False
    cursor = conn.cursor()
    
    try:
        print("📥 Importing data...")
        cursor.execute(sql_content)
        
        print("✅ Data imported successfully")
        print()
        print("🔍 Verifying import...")
        
        # Verify key tables
        verification_queries = [
            ("Configuration", "SELECT COUNT(*) FROM configuration_params"),
            ("Bundle SKUs", "SELECT COUNT(*) FROM bundle_skus"),
            ("SKU Lots", "SELECT COUNT(*) FROM sku_lot"),
            ("Shipped Orders", "SELECT COUNT(*) FROM shipped_orders"),
            ("Shipped Items", "SELECT COUNT(*) FROM shipped_items"),
        ]
        
        for name, query in verification_queries:
            cursor.execute(query)
            count = cursor.fetchone()[0]
            print(f"   ✅ {name}: {count} rows")
        
        print()
        response = input("Commit changes? (yes/no): ")
        
        if response.lower() == 'yes':
            conn.commit()
            print()
            print("=" * 70)
            print("✅ DATA IMPORT COMPLETE!")
            print("=" * 70)
            print()
            print("Your new database now has:")
            print("- All configuration settings")
            print("- Historical shipped orders")
            print("- Bundle SKU definitions")
            print("- Current lot assignments")
            print("- Inventory records")
            print()
            print("Ready to start the application! 🚀")
            print()
        else:
            conn.rollback()
            print("❌ Changes rolled back")
            return 1
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Import failed: {e}")
        return 1
    finally:
        cursor.close()
        conn.close()
    
    return 0

def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python migrate_data.py export    # Export from current database")
        print("  python migrate_data.py import    # Import into new database")
        return 1
    
    command = sys.argv[1].lower()
    
    if command == 'export':
        export_data()
        return 0
    elif command == 'import':
        return import_data()
    else:
        print(f"Unknown command: {command}")
        print("Use 'export' or 'import'")
        return 1

if __name__ == '__main__':
    sys.exit(main())
