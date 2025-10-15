#!/usr/bin/env python3
"""
Create PostgreSQL schema from SQLite database
Automatically converts SQLite types to PostgreSQL equivalents
"""

import os
import sqlite3
import psycopg2
import sys

def sqlite_to_postgres_type(sqlite_type):
    """Convert SQLite type to PostgreSQL type"""
    sqlite_type = sqlite_type.upper()
    
    mapping = {
        'INTEGER': 'INTEGER',
        'TEXT': 'TEXT',
        'REAL': 'REAL',
        'BLOB': 'BYTEA',
        'NUMERIC': 'NUMERIC',
    }
    
    return mapping.get(sqlite_type, 'TEXT')

def convert_table_definition(sqlite_sql):
    """Convert SQLite CREATE TABLE to PostgreSQL"""
    # Remove STRICT keyword (SQLite-specific)
    pg_sql = sqlite_sql.replace(' STRICT', '')
    
    # Convert AUTOINCREMENT to SERIAL
    pg_sql = pg_sql.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY')
    
    # Convert SQLite datetime functions to PostgreSQL
    pg_sql = pg_sql.replace("datetime('now')", "CURRENT_TIMESTAMP")
    pg_sql = pg_sql.replace("DATETIME('now')", "CURRENT_TIMESTAMP")
    pg_sql = pg_sql.replace("(datetime('now'))", "CURRENT_TIMESTAMP")
    pg_sql = pg_sql.replace("(DATETIME('now'))", "CURRENT_TIMESTAMP")
    
    # Convert DATETIME type to TIMESTAMP (case-sensitive replacement)
    # Need to be careful not to replace in function calls
    import re
    pg_sql = re.sub(r'\bDATETIME\b', 'TIMESTAMP', pg_sql, flags=re.IGNORECASE)
    
    # CURRENT_TIMESTAMP already works in both
    # CHECK constraints for booleans work in both (INTEGER with 0/1)
    
    return pg_sql

def extract_and_create_schema():
    """Extract from SQLite and create in PostgreSQL"""
    
    print("🔄 CREATING POSTGRESQL SCHEMA FROM SQLITE")
    print("=" * 60)
    
    # Connect to SQLite
    print("\n📖 Reading SQLite schema...")
    sqlite_conn = sqlite3.connect('ora.db')
    sqlite_cur = sqlite_conn.cursor()
    
    # Define table creation order (respecting foreign key dependencies)
    # Parent tables first, then children
    table_order = [
        'workflows',
        'configuration_params',
        'workflow_controls',
        'inventory_current',
        'sku_lot',
        'bundle_skus',
        'bundle_components',
        'shipped_orders',
        'shipped_items',
        'orders_inbox',
        'order_items_inbox',
        'shipstation_order_line_items',
        'inventory_transactions',
        'system_kpis',
        'shipping_violations',
        'lot_inventory',
        'initial_inventory',
    ]
    
    # Get all tables from SQLite
    sqlite_cur.execute("""
        SELECT name, sql 
        FROM sqlite_master 
        WHERE type='table' 
        AND name NOT LIKE 'sqlite_%'
        AND sql IS NOT NULL
    """)
    
    all_tables = {name: sql for name, sql in sqlite_cur.fetchall()}
    
    # Order tables based on dependency list, then append any remaining
    tables = []
    for table_name in table_order:
        if table_name in all_tables:
            tables.append((table_name, all_tables[table_name]))
    
    # Add any tables not in the predefined order
    for table_name, sql in all_tables.items():
        if table_name not in table_order:
            tables.append((table_name, sql))
    print(f"  Found {len(tables)} tables to migrate")
    
    # Connect to PostgreSQL
    print("\n🔗 Connecting to PostgreSQL...")
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if not DATABASE_URL:
        print("❌ DATABASE_URL not set")
        sys.exit(1)
    
    pg_conn = psycopg2.connect(DATABASE_URL)
    pg_cur = pg_conn.cursor()
    print("  Connected successfully")
    
    # Create tables
    print("\n🏗️  Creating tables...")
    created_count = 0
    
    for table_name, sqlite_sql in tables:
        print(f"\n  Creating: {table_name}")
        
        # Convert SQL
        pg_sql = convert_table_definition(sqlite_sql)
        
        try:
            # Drop if exists (for clean migration)
            pg_cur.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")
            
            # Create table
            pg_cur.execute(pg_sql)
            
            print(f"    ✅ Created successfully")
            created_count += 1
            
        except Exception as e:
            print(f"    ❌ Error: {e}")
            print(f"    SQL: {pg_sql[:200]}...")
            pg_conn.rollback()
            sqlite_conn.close()
            pg_conn.close()
            sys.exit(1)
    
    # Get indexes
    print("\n📇 Creating indexes...")
    sqlite_cur.execute("""
        SELECT name, sql 
        FROM sqlite_master 
        WHERE type='index' 
        AND sql IS NOT NULL
        AND name NOT LIKE 'sqlite_%'
    """)
    
    indexes = sqlite_cur.fetchall()
    index_count = 0
    
    for index_name, index_sql in indexes:
        try:
            pg_cur.execute(index_sql)
            print(f"  ✅ {index_name}")
            index_count += 1
        except Exception as e:
            # Some indexes are auto-created (e.g., for PRIMARY KEY)
            # Safe to skip these
            print(f"  ⚠️  {index_name}: {str(e)[:50]}...")
    
    # Commit all changes
    print("\n💾 Committing schema...")
    pg_conn.commit()
    
    # Verify tables created
    print("\n🔍 Verifying schema...")
    pg_cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)
    
    pg_tables = [row[0] for row in pg_cur.fetchall()]
    print(f"  PostgreSQL tables: {len(pg_tables)}")
    
    for table in pg_tables[:10]:  # Show first 10
        print(f"    - {table}")
    
    if len(pg_tables) > 10:
        print(f"    ... and {len(pg_tables) - 10} more")
    
    # Close connections
    sqlite_conn.close()
    pg_conn.close()
    
    print("\n" + "=" * 60)
    print("✅ POSTGRESQL SCHEMA CREATED SUCCESSFULLY")
    print("=" * 60)
    print(f"  Tables created: {created_count}")
    print(f"  Indexes created: {index_count}")
    print(f"  Total tables in PostgreSQL: {len(pg_tables)}")
    print("\n📝 Schema ready for data migration")
    
    return True

if __name__ == '__main__':
    try:
        success = extract_and_create_schema()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ SCHEMA CREATION FAILED: {e}")
        sys.exit(1)
