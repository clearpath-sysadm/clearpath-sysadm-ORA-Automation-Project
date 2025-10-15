#!/usr/bin/env python3
"""
TRANSACTION-SAFE DATA MIGRATION
Single atomic transaction - all data migrates or nothing does
"""

import os
import sqlite3
import psycopg2
from psycopg2.extras import execute_values
import sys
from datetime import datetime

class SafeDataMigration:
    def __init__(self):
        self.sqlite_path = self.get_canonical_backup()
        self.pg_url = os.environ.get('DATABASE_URL')
        
        if not self.pg_url:
            print("❌ ERROR: DATABASE_URL environment variable not set")
            sys.exit(1)
        
        self.migration_log = []
    
    def get_canonical_backup(self):
        """Get the frozen backup from freeze process"""
        try:
            with open('migration/backup_id.txt') as f:
                backup_id = f.read().strip()
            backup_path = f'migration/backups/ora_frozen_{backup_id}.db'
            
            if not os.path.exists(backup_path):
                print(f"❌ ERROR: Canonical backup not found: {backup_path}")
                sys.exit(1)
            
            return backup_path
        except FileNotFoundError:
            print("❌ ERROR: backup_id.txt not found - was freeze_production.sh run?")
            sys.exit(1)
    
    def log(self, message):
        """Log message to console and internal log"""
        print(message)
        self.migration_log.append(f"{datetime.now()}: {message}")
    
    def validate_backup(self):
        """Verify backup integrity before migration"""
        self.log("\n🔍 Validating SQLite backup...")
        
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        
        # Integrity check
        cursor.execute("PRAGMA integrity_check;")
        result = cursor.fetchone()[0]
        
        if result != 'ok':
            self.log(f"❌ ERROR: Backup integrity check failed: {result}")
            conn.close()
            return False
        
        self.log("  ✅ Backup integrity: OK")
        
        # Count tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        self.log(f"  ✅ Tables found: {len(tables)}")
        
        conn.close()
        return True
    
    def migrate_data(self):
        """
        Migrate all data in a SINGLE TRANSACTION
        All-or-nothing - if anything fails, everything rolls back
        """
        self.log("\n📦 STARTING TRANSACTION-SAFE DATA MIGRATION")
        self.log("=" * 60)
        
        # Connect to SQLite (source)
        sqlite_conn = sqlite3.connect(self.sqlite_path)
        
        # Connect to PostgreSQL (destination)
        pg_conn = psycopg2.connect(self.pg_url)
        
        # Migration order (respects foreign keys)
        tables_config = [
            ('configuration_params', []),
            ('workflow_controls', ['enabled']),
            ('bundle_skus', []),
            ('bundle_components', []),
            ('sku_lot', ['is_active']),
            ('shipped_orders', []),  # Parent before children
            ('shipped_items', []),
            ('orders_inbox', ['uploaded_to_shipstation']),
            ('inventory_current', []),
            ('inventory_transactions', []),
            ('system_kpis', []),
            ('shipping_violations', []),
        ]
        
        try:
            # CRITICAL: Single transaction for entire migration
            pg_cur = pg_conn.cursor()
            
            self.log("\n🔒 Starting single atomic transaction...")
            self.log("  (All changes will commit together or rollback together)")
            
            total_rows = 0
            
            for table, bool_cols in tables_config:
                self.log(f"\n  Migrating {table}...")
                
                # Get data from SQLite
                sqlite_cur = sqlite_conn.cursor()
                sqlite_cur.execute(f"SELECT * FROM {table}")
                rows = sqlite_cur.fetchall()
                
                if not rows:
                    self.log(f"    ℹ️  No data (empty table)")
                    continue
                
                # Get column names
                cols = [desc[0] for desc in sqlite_cur.description]
                
                # Convert booleans (SQLite uses 0/1, PostgreSQL uses TRUE/FALSE)
                converted_rows = []
                for row in rows:
                    row_list = list(row)
                    for i, col in enumerate(cols):
                        if col in bool_cols and row_list[i] is not None:
                            row_list[i] = bool(row_list[i])
                    converted_rows.append(row_list)
                
                # Insert to PostgreSQL (NO COMMIT YET - still in transaction)
                placeholders = ','.join(['%s'] * len(cols))
                insert_sql = f"INSERT INTO {table} ({','.join(cols)}) VALUES %s ON CONFLICT DO NOTHING"
                
                execute_values(pg_cur, insert_sql, converted_rows, template=f"({placeholders})")
                
                self.log(f"    ✅ {len(rows)} rows staged (not committed yet)")
                total_rows += len(rows)
            
            # Reset sequences to match max IDs
            self.log("\n  🔧 Resetting sequences...")
            pg_cur.execute("""
                SELECT table_name, column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND column_default LIKE 'nextval%'
            """)
            
            for table, column in pg_cur.fetchall():
                pg_cur.execute(f"SELECT MAX({column}) FROM {table}")
                result = pg_cur.fetchone()
                max_id = result[0] if result else None
                if max_id:
                    sequence_name = f"{table}_{column}_seq"
                    pg_cur.execute(f"ALTER SEQUENCE {sequence_name} RESTART WITH {max_id + 1}")
                    self.log(f"    ✅ {sequence_name} → {max_id + 1}")
            
            # CRITICAL MOMENT: Commit entire transaction
            self.log("\n🔐 COMMITTING TRANSACTION...")
            self.log(f"  Total rows to commit: {total_rows}")
            self.log(f"  Tables migrated: {len(tables_config)}")
            
            pg_conn.commit()
            
            self.log("\n✅ TRANSACTION COMMITTED SUCCESSFULLY")
            self.log("  All data is now safely in PostgreSQL")
            
        except Exception as e:
            # AUTOMATIC ROLLBACK
            self.log(f"\n❌ MIGRATION ERROR: {e}")
            self.log("\n🔄 ROLLING BACK TRANSACTION...")
            pg_conn.rollback()
            self.log("✅ Transaction rolled back - PostgreSQL unchanged")
            self.log("\n💡 No data was lost - can retry migration")
            
            sqlite_conn.close()
            pg_conn.close()
            return False
        
        finally:
            sqlite_conn.close()
            pg_conn.close()
        
        return True
    
    def validate_migration(self):
        """Validate migration succeeded"""
        self.log("\n🔍 VALIDATING MIGRATION...")
        self.log("=" * 60)
        
        sqlite_conn = sqlite3.connect(self.sqlite_path)
        pg_conn = psycopg2.connect(self.pg_url)
        
        tables = [
            'shipped_orders', 'shipped_items', 'orders_inbox',
            'workflow_controls', 'bundle_skus', 'inventory_current'
        ]
        
        all_pass = True
        
        for table in tables:
            # SQLite count
            sqlite_cur = sqlite_conn.cursor()
            sqlite_cur.execute(f"SELECT COUNT(*) FROM {table}")
            sqlite_result = sqlite_cur.fetchone()
            sqlite_count = sqlite_result[0] if sqlite_result else 0
            
            # PostgreSQL count
            pg_cur = pg_conn.cursor()
            pg_cur.execute(f"SELECT COUNT(*) FROM {table}")
            pg_result = pg_cur.fetchone()
            pg_count = pg_result[0] if pg_result else 0
            
            if sqlite_count == pg_count:
                self.log(f"  ✅ {table}: {pg_count} rows (MATCH)")
            else:
                self.log(f"  ❌ {table}: MISMATCH (SQLite={sqlite_count}, PG={pg_count})")
                all_pass = False
        
        # Foreign key integrity check
        self.log("\n  🔍 Checking foreign key integrity...")
        pg_cur = pg_conn.cursor()
        pg_cur.execute("""
            SELECT COUNT(*) FROM shipped_items si
            LEFT JOIN shipped_orders so ON si.order_number = so.order_number
            WHERE so.order_number IS NULL
        """)
        orphan_result = pg_cur.fetchone()
        orphans = orphan_result[0] if orphan_result else 0
        
        if orphans == 0:
            self.log(f"  ✅ Foreign keys intact (0 orphaned records)")
        else:
            self.log(f"  ❌ Foreign key violation: {orphans} orphaned records")
            all_pass = False
        
        sqlite_conn.close()
        pg_conn.close()
        
        self.log("=" * 60)
        
        if all_pass:
            self.log("✅ VALIDATION PASSED")
            self.log("  All data migrated correctly")
            return True
        else:
            self.log("❌ VALIDATION FAILED")
            self.log("  Data integrity issues detected")
            return False
    
    def save_migration_log(self):
        """Save migration log to file"""
        log_file = f"migration/logs/data_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        with open(log_file, 'w') as f:
            f.write('\n'.join(self.migration_log))
        self.log(f"\n📝 Migration log saved: {log_file}")
    
    def run(self):
        """Execute complete migration process"""
        self.log("🚀 TRANSACTION-SAFE DATA MIGRATION")
        self.log("=" * 60)
        self.log(f"Source: {self.sqlite_path}")
        self.log(f"Destination: PostgreSQL (DATABASE_URL)")
        self.log(f"Started: {datetime.now()}")
        
        # Step 1: Validate backup
        if not self.validate_backup():
            self.log("\n❌ MIGRATION ABORTED: Backup validation failed")
            return False
        
        # Step 2: Migrate data
        if not self.migrate_data():
            self.log("\n❌ MIGRATION ABORTED: Data migration failed")
            self.save_migration_log()
            return False
        
        # Step 3: Validate migration
        if not self.validate_migration():
            self.log("\n⚠️  WARNING: Validation failed after migration")
            self.log("  Data was committed but integrity issues detected")
            self.save_migration_log()
            return False
        
        # Success!
        self.log("\n" + "=" * 60)
        self.log("✅ DATA MIGRATION SUCCESSFUL")
        self.log("=" * 60)
        self.log(f"Completed: {datetime.now()}")
        
        self.save_migration_log()
        return True

if __name__ == '__main__':
    migration = SafeDataMigration()
    success = migration.run()
    sys.exit(0 if success else 1)
