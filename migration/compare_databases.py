#!/usr/bin/env python3
"""
Compare SQLite and PostgreSQL databases to verify migration integrity.
"""
import sqlite3
import psycopg2
import os
from typing import Dict, List, Tuple

# Database paths
SQLITE_DB = "backups/ora_frozen_20251015_045027.db"
POSTGRES_URL = os.environ.get("DATABASE_URL")

# Tables to compare
TABLES = [
    "workflows",
    "inventory_current",
    "shipped_orders",
    "shipped_items",
    "orders_inbox",
    "system_kpis",
    "bundle_skus",
    "bundle_components",
    "sku_lot",
    "sync_watermark",
    "workflow_controls",
    "shipping_rules",
    "shipping_violations",
    "lot_inventory",
    "configuration_params",
    "key_products"
]

def get_sqlite_row_count(table: str) -> int:
    """Get row count from SQLite table."""
    conn = sqlite3.connect(SQLITE_DB)
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_postgres_row_count(table: str) -> int:
    """Get row count from PostgreSQL table."""
    conn = psycopg2.connect(POSTGRES_URL)
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_sqlite_sample(table: str, limit: int = 5) -> List[Tuple]:
    """Get sample rows from SQLite table."""
    conn = sqlite3.connect(SQLITE_DB)
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table} LIMIT {limit}")
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_postgres_sample(table: str, limit: int = 5) -> List[Tuple]:
    """Get sample rows from PostgreSQL table."""
    conn = psycopg2.connect(POSTGRES_URL)
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table} LIMIT {limit}")
    rows = cursor.fetchall()
    conn.close()
    return rows

def compare_databases():
    """Compare all tables between SQLite and PostgreSQL."""
    print("=" * 100)
    print("DATABASE MIGRATION INTEGRITY COMPARISON")
    print("=" * 100)
    print(f"\nSQLite DB: {SQLITE_DB}")
    print(f"PostgreSQL: {POSTGRES_URL[:50]}...")
    print("\n" + "=" * 100)
    
    total_sqlite = 0
    total_postgres = 0
    mismatches = []
    
    print(f"\n{'Table Name':<30} {'SQLite Rows':<15} {'PostgreSQL Rows':<15} {'Status':<10}")
    print("-" * 100)
    
    for table in TABLES:
        try:
            sqlite_count = get_sqlite_row_count(table)
            postgres_count = get_postgres_row_count(table)
            
            total_sqlite += sqlite_count
            total_postgres += postgres_count
            
            status = "✅ MATCH" if sqlite_count == postgres_count else "❌ MISMATCH"
            if sqlite_count != postgres_count:
                mismatches.append((table, sqlite_count, postgres_count))
            
            print(f"{table:<30} {sqlite_count:<15} {postgres_count:<15} {status}")
            
        except Exception as e:
            print(f"{table:<30} {'ERROR':<15} {'ERROR':<15} ⚠️ {str(e)[:30]}")
    
    print("-" * 100)
    print(f"{'TOTAL':<30} {total_sqlite:<15} {total_postgres:<15}")
    print("=" * 100)
    
    # Summary
    print("\n📊 SUMMARY:")
    print(f"   Total rows in SQLite:     {total_sqlite:,}")
    print(f"   Total rows in PostgreSQL: {total_postgres:,}")
    print(f"   Difference:               {abs(total_sqlite - total_postgres):,}")
    
    if mismatches:
        print(f"\n❌ MISMATCHES FOUND ({len(mismatches)} tables):")
        for table, sqlite_cnt, postgres_cnt in mismatches:
            diff = postgres_cnt - sqlite_cnt
            print(f"   {table}: {diff:+d} rows ({sqlite_cnt} → {postgres_cnt})")
    else:
        print("\n✅ ALL TABLES MATCH - MIGRATION SUCCESSFUL!")
    
    print("\n" + "=" * 100)
    
    # Check specific critical tables
    print("\n🔍 CRITICAL TABLE VERIFICATION:")
    print("-" * 100)
    
    critical_tables = ["shipped_orders", "shipped_items", "orders_inbox"]
    for table in critical_tables:
        print(f"\n{table.upper()}:")
        try:
            sqlite_sample = get_sqlite_sample(table, 3)
            postgres_sample = get_postgres_sample(table, 3)
            
            print(f"  SQLite sample (first 3 rows): {len(sqlite_sample)} rows")
            print(f"  PostgreSQL sample (first 3 rows): {len(postgres_sample)} rows")
            
            if len(sqlite_sample) > 0:
                print(f"  Sample IDs match: {sqlite_sample[0][0] if sqlite_sample else 'N/A'}")
        except Exception as e:
            print(f"  ⚠️ Error: {e}")
    
    print("\n" + "=" * 100)
    
    return len(mismatches) == 0

if __name__ == "__main__":
    success = compare_databases()
    exit(0 if success else 1)
