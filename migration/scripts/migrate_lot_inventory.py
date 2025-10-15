#!/usr/bin/env python3
"""
Migrate missing lot_inventory data from SQLite backup to PostgreSQL
"""
import os
import sqlite3
import psycopg2

SQLITE_DB = "backups/ora_frozen_20251015_045027.db"
POSTGRES_URL = os.environ.get("DATABASE_URL")

print("=" * 80)
print("MIGRATING LOT_INVENTORY DATA")
print("=" * 80)

# Connect to SQLite
sqlite_conn = sqlite3.connect(SQLITE_DB)
sqlite_cur = sqlite_conn.cursor()

# Get lot_inventory data
sqlite_cur.execute("SELECT * FROM lot_inventory ORDER BY id")
rows = sqlite_cur.fetchall()

print(f"\n✅ Found {len(rows)} lot_inventory records in SQLite backup")

if len(rows) == 0:
    print("❌ No data to migrate!")
    exit(1)

# Get column names
sqlite_cur.execute("PRAGMA table_info(lot_inventory)")
columns = [col[1] for col in sqlite_cur.fetchall()]
print(f"   Columns: {', '.join(columns)}")

# Display data
print("\n📋 Data to migrate:")
for row in rows:
    print(f"   ID {row[0]}: SKU {row[1]}, Lot {row[2]}, Qty {row[3]}")

sqlite_conn.close()

# Connect to PostgreSQL
pg_conn = psycopg2.connect(POSTGRES_URL)
pg_cur = pg_conn.cursor()

# Check current PostgreSQL data
pg_cur.execute("SELECT COUNT(*) FROM lot_inventory")
pg_count = pg_cur.fetchone()[0]
print(f"\n📊 Current PostgreSQL lot_inventory rows: {pg_count}")

if pg_count > 0:
    print("⚠️  WARNING: PostgreSQL table is not empty!")
    response = input("   Continue anyway? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Migration cancelled")
        exit(0)

# Migrate data
print("\n🔄 Migrating data...")

try:
    # Prepare INSERT statement
    # Columns: id, sku, lot, initial_qty, manual_adjustment, received_date, status, notes, created_at, updated_at
    insert_sql = """
        INSERT INTO lot_inventory (id, sku, lot, initial_qty, manual_adjustment, received_date, status, notes, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    migrated = 0
    for row in rows:
        pg_cur.execute(insert_sql, row)
        migrated += 1
        print(f"   ✅ Migrated: ID {row[0]}, SKU {row[1]}, Lot {row[2]}, Qty {row[3]}")
    
    # Commit transaction
    pg_conn.commit()
    
    print(f"\n✅ SUCCESS! Migrated {migrated} lot_inventory records")
    
    # Verify
    pg_cur.execute("SELECT COUNT(*) FROM lot_inventory")
    final_count = pg_cur.fetchone()[0]
    print(f"   Final PostgreSQL count: {final_count}")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    pg_conn.rollback()
    exit(1)
finally:
    pg_conn.close()

print("\n" + "=" * 80)
print("MIGRATION COMPLETE")
print("=" * 80)
