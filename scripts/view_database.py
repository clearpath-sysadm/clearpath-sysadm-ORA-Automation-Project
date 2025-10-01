#!/usr/bin/env python3
"""
Quick database viewer script
Usage: python scripts/view_database.py [table_name]
"""

import sqlite3
import sys
import os

DATABASE_PATH = "ora.db"

def view_all_tables(conn):
    """Show all tables and their row counts"""
    cursor = conn.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        ORDER BY name
    """)
    
    tables = cursor.fetchall()
    
    print("\n" + "=" * 60)
    print("DATABASE OVERVIEW")
    print("=" * 60)
    
    for (table_name,) in tables:
        cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"{table_name:30} {count:>10} rows")
    
    print("=" * 60)

def view_table(conn, table_name):
    """Show contents of a specific table"""
    try:
        cursor = conn.execute(f"SELECT * FROM {table_name} LIMIT 100")
        rows = cursor.fetchall()
        
        if not rows:
            print(f"\n✅ Table '{table_name}' exists but is empty")
            return
        
        columns = [description[0] for description in cursor.description]
        
        print(f"\n{'=' * 80}")
        print(f"TABLE: {table_name} (showing first 100 rows)")
        print('=' * 80)
        print(" | ".join(columns))
        print("-" * 80)
        
        for row in rows:
            print(" | ".join(str(val) for val in row))
        
        print('=' * 80)
        print(f"Total rows shown: {len(rows)}")
        
    except sqlite3.OperationalError as e:
        print(f"❌ Error: {e}")

def main():
    if not os.path.exists(DATABASE_PATH):
        print(f"❌ Database not found: {DATABASE_PATH}")
        print("Run: OVERWRITE=1 python scripts/create_database.py")
        sys.exit(1)
    
    conn = sqlite3.connect(DATABASE_PATH)
    
    if len(sys.argv) > 1:
        table_name = sys.argv[1]
        view_table(conn, table_name)
    else:
        view_all_tables(conn)
        print("\nTo view a specific table:")
        print("  python scripts/view_database.py [table_name]")
    
    conn.close()

if __name__ == "__main__":
    main()
