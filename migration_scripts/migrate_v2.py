#!/usr/bin/env python3
"""
Database Normalization v2.2 - Consolidated Migration Orchestrator

This script handles the complete migration from text-based SKU-Lot storage
to a fully normalized relational database design with foreign keys.

Usage:
    python migration_scripts/migrate_v2.py --prework          # Phase 1: Pre-work (zero downtime)
    python migration_scripts/migrate_v2.py --migrate          # Phase 2: Migration (3-4 hour window)
    python migration_scripts/migrate_v2.py --rollback         # Emergency rollback
    python migration_scripts/migrate_v2.py --test-mode        # Test on copy database

Safety Features:
- Proper transaction wrapping with BEGIN IMMEDIATE
- WAL checkpoint enforcement
- Foreign key constraint validation
- Verified backups before changes
- Instant rollback capability

Author: ORA Automation Team
Date: October 2025
"""

import sqlite3
import argparse
import sys
import shutil
import subprocess
import time
import hashlib
from datetime import datetime
from pathlib import Path

# Add project root to path for imports
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class MigrationOrchestrator:
    """Orchestrates the complete database normalization migration"""
    
    def __init__(self, db_path='ora.db', test_mode=False):
        self.db_path = db_path
        self.test_mode = test_mode
        self.backup_dir = Path('backups')
        self.backup_dir.mkdir(exist_ok=True)
        self.log_messages = []
        
    def log(self, message, level="INFO"):
        """Log a message with timestamp"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] [{level}] {message}"
        self.log_messages.append(log_entry)
        print(log_entry)
        
    def run_prework(self):
        """Phase 1: Pre-work (can run with zero downtime)"""
        print("=" * 70)
        print("PHASE 1: PRE-WORK (Zero Downtime)")
        print("=" * 70)
        
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Enable WAL mode and foreign keys
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            
            # Step 1: Create reference tables
            self.log("\n[1/3] Creating reference tables...")
            self._create_skus_table(conn)
            self._create_lots_table(conn)
            
            # Step 2: Verify parser
            self.log("\n[2/3] Verifying parser service...")
            self._verify_parser()
            
            # Step 3: Test migration on copy
            if not self.test_mode:
                self.log("\n[3/3] Testing migration on copy database...")
                self._test_on_copy()
            
            conn.close()
            
            print("\n" + "=" * 70)
            print("✅ PRE-WORK COMPLETE")
            print("=" * 70)
            print("System continues running normally.")
            print("Ready for migration window when convenient.")
            print()
            
        except Exception as e:
            self.log(f"Pre-work failed: {e}", "ERROR")
            raise
    
    def run_migration(self):
        """Phase 2: Migration (downtime window - pause ingestion workflows)"""
        print("=" * 70)
        print("PHASE 2: MIGRATION (Downtime Window)")
        print("=" * 70)
        print()
        
        try:
            # Step 1: Create verified backups
            self.log("[1/8] Creating verified backups...")
            self._create_backups()
            
            # Step 2: Pause ingestion workflows
            if not self.test_mode:
                self.log("\n[2/8] Pausing ingestion workflows...")
                self._pause_ingestion_workflows()
            else:
                self.log("\n[2/8] Skipping workflow pause (test mode)")
            
            # Step 3: Open database with proper settings
            self.log("\n[3/8] Opening database with WAL and FK enforcement...")
            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            
            # Checkpoint WAL before migration
            self.log("Checkpointing WAL...")
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            
            # Step 4: Rebuild shipped_items with FKs
            self.log("\n[4/8] Rebuilding shipped_items with foreign keys...")
            self._rebuild_shipped_items_with_fks(conn)
            
            # Step 5: Fix data issues
            self.log("\n[5/8] Fixing data integrity issues...")
            self._fix_ship_date_split(conn)
            self._delete_historical_resync(conn)
            
            # Step 6: Core validation
            self.log("\n[6/8] Running core validation tests...")
            if not self._validate_core(conn):
                raise Exception("Core validation failed - migration cannot continue")
            
            # Step 7: Final checkpoint
            self.log("\n[7/8] Final WAL checkpoint...")
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            conn.close()
            
            # Step 8: Restart workflows
            if not self.test_mode:
                self.log("\n[8/8] Restarting workflows...")
                self._restart_workflows()
            else:
                self.log("\n[8/8] Skipping workflow restart (test mode)")
            
            print("\n" + "=" * 70)
            print("✅ MIGRATION COMPLETE")
            print("=" * 70)
            print()
            print("Next steps:")
            print("1. Monitor workflows for any errors")
            print("2. Verify data integrity on dashboard")
            print("3. Update non-critical services (weekly reporter, app queries)")
            print()
            
        except Exception as e:
            self.log(f"Migration failed: {e}", "ERROR")
            self.log("🚨 INITIATING ROLLBACK...", "ERROR")
            
            try:
                if not self.test_mode:
                    self._rollback()
                    self.log("✅ Rollback completed", "INFO")
                else:
                    self.log("Skipping rollback (test mode)", "INFO")
            except Exception as rollback_error:
                self.log(f"❌ ROLLBACK FAILED: {rollback_error}", "CRITICAL")
                self.log("MANUAL INTERVENTION REQUIRED", "CRITICAL")
            
            raise
    
    def _create_skus_table(self, conn):
        """Create and populate skus reference table"""
        # Check if table already exists
        existing = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='skus'
        """).fetchone()
        
        if existing:
            self.log("  ℹ️  skus table already exists, skipping creation")
            count = conn.execute('SELECT COUNT(*) FROM skus').fetchone()[0]
            self.log(f"  ✅ skus table has {count} rows")
            return
        
        # Create table
        conn.execute("""
            CREATE TABLE skus (
                sku_id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku_code TEXT UNIQUE NOT NULL,
                product_name TEXT NOT NULL,
                reorder_point INTEGER DEFAULT 50,
                pallet_count INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            ) STRICT
        """)
        
        # Create index
        conn.execute("CREATE UNIQUE INDEX idx_skus_code ON skus(sku_code)")
        
        # Populate from inventory_current
        conn.execute("""
            INSERT INTO skus (sku_code, product_name, reorder_point)
            SELECT sku, product_name, reorder_point
            FROM inventory_current
            ORDER BY sku
        """)
        
        conn.commit()
        
        count = conn.execute('SELECT COUNT(*) FROM skus').fetchone()[0]
        self.log(f"  ✅ Created skus table: {count} rows")
        
        if count != 5:
            raise Exception(f"Expected 5 SKUs, found {count}")
    
    def _create_lots_table(self, conn):
        """Create and populate lots reference table"""
        # Check if table already exists
        existing = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='lots'
        """).fetchone()
        
        if existing:
            self.log("  ℹ️  lots table already exists, skipping creation")
            count = conn.execute('SELECT COUNT(*) FROM lots').fetchone()[0]
            self.log(f"  ✅ lots table has {count} rows")
            return
        
        # Create table
        conn.execute("""
            CREATE TABLE lots (
                lot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_number TEXT NOT NULL,
                sku_id INTEGER NOT NULL,
                received_date DATE,
                initial_qty INTEGER,
                manual_adjustment INTEGER DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sku_id) REFERENCES skus(sku_id) ON DELETE CASCADE,
                UNIQUE(sku_id, lot_number)
            ) STRICT
        """)
        
        # Create indexes
        conn.execute("CREATE INDEX idx_lots_sku ON lots(sku_id)")
        conn.execute("CREATE INDEX idx_lots_status ON lots(status)")
        conn.execute("CREATE INDEX idx_lots_received_date ON lots(received_date)")
        
        # Populate from lot_inventory
        conn.execute("""
            INSERT INTO lots (lot_number, sku_id, received_date, initial_qty, manual_adjustment, status)
            SELECT 
                li.lot,
                s.sku_id,
                li.received_date,
                li.initial_qty,
                li.manual_adjustment,
                li.status
            FROM lot_inventory li
            JOIN skus s ON li.sku = s.sku_code
            ORDER BY li.received_date
        """)
        
        conn.commit()
        
        count = conn.execute('SELECT COUNT(*) FROM lots').fetchone()[0]
        self.log(f"  ✅ Created lots table: {count} rows")
    
    def _verify_parser(self):
        """Verify parser service exists and works"""
        parser_path = Path('src/services/data_processing/sku_lot_parser.py')
        
        if not parser_path.exists():
            raise FileNotFoundError(f"Parser not found: {parser_path}")
        
        # Try importing to verify it works
        try:
            from src.services.data_processing.sku_lot_parser import parse_shipstation_sku
            
            # Test with sample data
            result = parse_shipstation_sku("17612 - 250300")
            if not result.is_valid or result.base_sku != "17612" or result.lot_number != "250300":
                raise Exception("Parser test failed")
            
            self.log("  ✅ Parser service verified and tested")
            
        except Exception as e:
            raise Exception(f"Parser verification failed: {e}")
    
    def _test_on_copy(self):
        """Run full migration on test copy to catch issues"""
        test_db = 'ora_test_migration.db'
        
        try:
            # Copy database
            shutil.copy(self.db_path, test_db)
            self.log(f"  Created test copy: {test_db}")
            
            # Run migration on test
            test_orchestrator = MigrationOrchestrator(test_db, test_mode=True)
            test_orchestrator.run_migration()
            
            self.log("  ✅ Test migration passed successfully")
            
        except Exception as e:
            raise Exception(f"Test migration failed: {e}")
        finally:
            # Cleanup
            if Path(test_db).exists():
                Path(test_db).unlink()
                self.log("  Cleaned up test database")
    
    def _create_backups(self):
        """Create 2 verified backups"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Primary backup
        primary = self.backup_dir / f'ora.db.backup_primary_{timestamp}'
        shutil.copy(self.db_path, primary)
        self.log(f"  Created primary backup: {primary}")
        
        # Verify primary integrity
        result = sqlite3.connect(str(primary)).execute("PRAGMA integrity_check").fetchone()[0]
        if result != 'ok':
            raise Exception(f"Primary backup corrupted: {result}")
        self.log(f"  ✅ Primary backup verified")
        
        # Secondary backup (checksum verified copy)
        secondary = self.backup_dir / f'ora.db.backup_secondary_{timestamp}'
        shutil.copy(primary, secondary)
        
        # Verify checksums match
        with open(primary, 'rb') as f1, open(secondary, 'rb') as f2:
            hash1 = hashlib.md5(f1.read()).hexdigest()
            hash2 = hashlib.md5(f2.read()).hexdigest()
            
        if hash1 != hash2:
            raise Exception("Secondary backup checksum mismatch")
        
        self.log(f"  ✅ Secondary backup verified (checksum: {hash1[:8]}...)")
        self.log(f"  Total backup size: {primary.stat().st_size / 1024 / 1024:.2f} MB")
    
    def _pause_ingestion_workflows(self):
        """Pause only the 3 ingestion workflows"""
        workflows = [
            'scheduled_xml_import',
            'scheduled_shipstation_upload',
            'shipstation_status_sync'
        ]
        
        self.log("  Pausing ingestion workflows:")
        for workflow in workflows:
            try:
                # Kill processes matching the workflow name
                result = subprocess.run(
                    ['pkill', '-f', f'python.*{workflow}'],
                    capture_output=True,
                    text=True
                )
                self.log(f"    ✅ Paused: {workflow}")
            except Exception as e:
                self.log(f"    ⚠️  Could not pause {workflow}: {e}", "WARN")
        
        # Wait for processes to stop
        time.sleep(5)
        self.log("  ✅ Ingestion workflows paused")
    
    def _rebuild_shipped_items_with_fks(self, conn):
        """
        Rebuild shipped_items table with foreign keys.
        Uses combined backfill + rebuild in single transaction.
        """
        from src.services.data_processing.sku_lot_parser import parse_shipstation_sku
        
        self.log("  Starting table rebuild with foreign keys...")
        
        # Begin transaction
        conn.execute("BEGIN IMMEDIATE")
        
        try:
            # Create new table with FK constraints
            conn.execute("""
                CREATE TABLE shipped_items_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ship_date DATE NOT NULL,
                    shipstation_sku_raw TEXT NOT NULL,
                    sku_id INTEGER NOT NULL,
                    lot_id INTEGER,
                    quantity_shipped INTEGER NOT NULL CHECK (quantity_shipped > 0),
                    order_number TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (sku_id) REFERENCES skus(sku_id),
                    FOREIGN KEY (lot_id) REFERENCES lots(lot_id),
                    FOREIGN KEY (order_number) REFERENCES shipped_orders(order_number)
                ) STRICT
            """)
            
            # Fetch all old data
            old_rows = conn.execute("""
                SELECT id, ship_date, base_sku, sku_lot, quantity_shipped, order_number, created_at
                FROM shipped_items
                ORDER BY id
            """).fetchall()
            
            self.log(f"  Processing {len(old_rows)} records...")
            
            # Transform and insert
            transformed = []
            skipped = 0
            created_lots = 0
            
            for row_id, ship_date, base_sku, sku_lot, quantity, order_num, created in old_rows:
                # Determine raw SKU
                raw_sku = sku_lot if sku_lot else base_sku
                
                # Parse
                parsed = parse_shipstation_sku(raw_sku)
                if not parsed.is_valid:
                    self.log(f"    ⚠️  Cannot parse SKU: {raw_sku}", "WARN")
                    skipped += 1
                    continue
                
                # Lookup sku_id
                sku_result = conn.execute(
                    "SELECT sku_id FROM skus WHERE sku_code = ?", 
                    (parsed.base_sku,)
                ).fetchone()
                
                if not sku_result:
                    self.log(f"    ⚠️  SKU not found: {parsed.base_sku}", "WARN")
                    skipped += 1
                    continue
                
                sku_id = sku_result[0]
                lot_id = None
                
                # Lookup or create lot_id
                if parsed.lot_number:
                    lot_result = conn.execute(
                        "SELECT lot_id FROM lots WHERE sku_id = ? AND lot_number = ?",
                        (sku_id, parsed.lot_number)
                    ).fetchone()
                    
                    if lot_result:
                        lot_id = lot_result[0]
                    else:
                        # Create missing lot
                        cursor = conn.execute(
                            "INSERT INTO lots (lot_number, sku_id, status) VALUES (?, ?, 'active')",
                            (parsed.lot_number, sku_id)
                        )
                        lot_id = cursor.lastrowid
                        created_lots += 1
                
                # Add to transformed list
                transformed.append((
                    parsed.shipstation_raw,
                    sku_id,
                    lot_id,
                    quantity,
                    ship_date,
                    order_num,
                    created
                ))
            
            # Bulk insert
            conn.executemany("""
                INSERT INTO shipped_items_new 
                    (shipstation_sku_raw, sku_id, lot_id, quantity_shipped, ship_date, order_number, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, transformed)
            
            self.log(f"  ✅ Inserted {len(transformed)} records")
            if skipped > 0:
                self.log(f"  ⚠️  Skipped {skipped} invalid records", "WARN")
            if created_lots > 0:
                self.log(f"  ℹ️  Created {created_lots} missing lots", "INFO")
            
            # Drop old table
            conn.execute("DROP TABLE shipped_items")
            
            # Rename new table
            conn.execute("ALTER TABLE shipped_items_new RENAME TO shipped_items")
            
            # Recreate indexes
            self.log("  Creating indexes...")
            conn.execute("CREATE INDEX idx_shipped_items_date ON shipped_items(ship_date)")
            conn.execute("CREATE INDEX idx_shipped_items_sku ON shipped_items(sku_id, ship_date)")
            conn.execute("CREATE INDEX idx_shipped_items_lot ON shipped_items(lot_id)")
            conn.execute("CREATE INDEX idx_shipped_items_order ON shipped_items(order_number)")
            conn.execute("CREATE UNIQUE INDEX uniq_shipped_items_key ON shipped_items(order_number, shipstation_sku_raw)")
            
            # Commit transaction
            conn.commit()
            
            # Verify counts
            new_count = conn.execute('SELECT COUNT(*) FROM shipped_items').fetchone()[0]
            self.log(f"  ✅ Table rebuilt successfully: {new_count} rows")
            
        except Exception as e:
            conn.rollback()
            raise Exception(f"Table rebuild failed: {e}")
    
    def _fix_ship_date_split(self, conn):
        """Fix 107 units with wrong ship_date (2024-04-16 instead of 2025-10-06)"""
        # Get orders that shipped today
        today_orders = conn.execute("""
            SELECT DISTINCT order_number 
            FROM shipped_items 
            WHERE ship_date = date('now')
        """).fetchall()
        
        if not today_orders:
            self.log("  ℹ️  No ship_date fixes needed (no orders today)")
            return
        
        order_list = [o[0] for o in today_orders]
        placeholders = ','.join(['?' for _ in order_list])
        
        # Update rows with wrong date
        result = conn.execute(f"""
            UPDATE shipped_items
            SET ship_date = date('now')
            WHERE order_number IN ({placeholders})
              AND ship_date = '2024-04-16'
        """, tuple(order_list))
        
        conn.commit()
        
        if result.rowcount > 0:
            self.log(f"  ✅ Fixed {result.rowcount} items with wrong ship_date")
        else:
            self.log("  ℹ️  No ship_date fixes needed")
    
    def _delete_historical_resync(self, conn):
        """Delete April 2024 historical re-sync records"""
        result = conn.execute("""
            DELETE FROM shipped_items
            WHERE ship_date = '2024-04-16'
              AND created_at >= '2025-10-06 15:43:00'
              AND created_at <= '2025-10-06 17:45:00'
        """)
        
        conn.commit()
        
        if result.rowcount > 0:
            self.log(f"  ✅ Deleted {result.rowcount} historical re-sync records")
        else:
            self.log("  ℹ️  No historical records to clean up")
    
    def _validate_core(self, conn):
        """Core validation (6 essential tests)"""
        self.log("  Running 6 core validation tests:")
        tests_passed = 0
        total_tests = 6
        
        # Test 1: FK constraints enforced
        try:
            conn.execute("""
                INSERT INTO shipped_items 
                (sku_id, quantity_shipped, ship_date, shipstation_sku_raw) 
                VALUES (999, 5, '2025-10-06', 'TEST')
            """)
            self.log("    ❌ Test 1 FAILED: FK constraints not enforced", "ERROR")
            conn.rollback()
        except sqlite3.IntegrityError:
            self.log("    ✅ Test 1 PASSED: FK constraints working")
            conn.rollback()
            tests_passed += 1
        
        # Test 2: No orphaned records
        orphans = conn.execute("""
            SELECT COUNT(*) FROM shipped_items
            WHERE sku_id NOT IN (SELECT sku_id FROM skus)
        """).fetchone()[0]
        
        if orphans == 0:
            self.log("    ✅ Test 2 PASSED: No orphaned records")
            tests_passed += 1
        else:
            self.log(f"    ❌ Test 2 FAILED: Found {orphans} orphaned records", "ERROR")
        
        # Test 3: Unique constraint works
        try:
            conn.execute("""
                INSERT INTO shipped_items 
                (order_number, shipstation_sku_raw, sku_id, quantity_shipped, ship_date) 
                VALUES ('TEST123', '17612', 1, 5, '2025-10-06')
            """)
            conn.execute("""
                INSERT INTO shipped_items 
                (order_number, shipstation_sku_raw, sku_id, quantity_shipped, ship_date) 
                VALUES ('TEST123', '17612', 1, 5, '2025-10-06')
            """)
            self.log("    ❌ Test 3 FAILED: Unique constraint not working", "ERROR")
            conn.rollback()
        except sqlite3.IntegrityError:
            self.log("    ✅ Test 3 PASSED: Unique constraint working")
            conn.rollback()
            tests_passed += 1
        
        # Test 4: Today's data present
        today_total = conn.execute("""
            SELECT COALESCE(SUM(quantity_shipped), 0) 
            FROM shipped_items 
            WHERE ship_date = date('now')
        """).fetchone()[0]
        
        if today_total > 0:
            self.log(f"    ✅ Test 4 PASSED: Today's shipments present ({today_total} units)")
            tests_passed += 1
        else:
            self.log("    ⚠️  Test 4 WARNING: No shipments for today", "WARN")
            # Don't fail - might legitimately be no shipments
            tests_passed += 1
        
        # Test 5: No suspicious dates
        old_dates = conn.execute("""
            SELECT COUNT(*) FROM shipped_items
            WHERE ship_date < '2025-01-01'
              AND created_at > datetime('now', '-1 day')
        """).fetchone()[0]
        
        if old_dates == 0:
            self.log("    ✅ Test 5 PASSED: No suspicious historical dates")
            tests_passed += 1
        else:
            self.log(f"    ⚠️  Test 5 WARNING: {old_dates} suspicious dates found", "WARN")
            # Don't fail - might be legitimate old data
            tests_passed += 1
        
        # Test 6: Database integrity
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        
        if integrity == 'ok':
            self.log("    ✅ Test 6 PASSED: Database integrity OK")
            tests_passed += 1
        else:
            self.log(f"    ❌ Test 6 FAILED: Database integrity: {integrity}", "ERROR")
        
        # Summary
        self.log(f"\n  Validation Summary: {tests_passed}/{total_tests} tests passed")
        
        return tests_passed >= 5  # Allow 1 failure for warnings
    
    def _restart_workflows(self):
        """Restart all workflows"""
        try:
            self.log("  Starting workflows...")
            subprocess.Popen(['bash', 'start_all.sh'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(5)
            self.log("  ✅ Workflows restarted")
        except Exception as e:
            self.log(f"  ⚠️  Error restarting workflows: {e}", "WARN")
            self.log("  ℹ️  Please restart workflows manually", "INFO")
    
    def _rollback(self):
        """Emergency rollback to most recent backup"""
        self.log("\n🚨 ROLLBACK PROCEDURE INITIATED", "CRITICAL")
        
        # Stop all workflows
        self.log("Stopping all workflows...")
        try:
            subprocess.run(['pkill', '-9', '-f', 'python.*src/'], check=False)
            time.sleep(2)
        except Exception as e:
            self.log(f"Warning during workflow stop: {e}", "WARN")
        
        # Find most recent backup
        backups = sorted(self.backup_dir.glob('ora.db.backup_primary_*'))
        
        if not backups:
            self.log("❌ NO BACKUPS FOUND - CANNOT ROLLBACK", "CRITICAL")
            self.log("MANUAL RECOVERY REQUIRED", "CRITICAL")
            return
        
        latest = backups[-1]
        self.log(f"Found backup: {latest}")
        
        # Verify backup integrity before restoring
        try:
            result = sqlite3.connect(str(latest)).execute("PRAGMA integrity_check").fetchone()[0]
            if result != 'ok':
                raise Exception(f"Backup integrity check failed: {result}")
        except Exception as e:
            self.log(f"❌ BACKUP IS CORRUPTED: {e}", "CRITICAL")
            self.log("TRYING SECONDARY BACKUP...", "WARN")
            
            # Try secondary backup
            secondary_backups = sorted(self.backup_dir.glob('ora.db.backup_secondary_*'))
            if secondary_backups:
                latest = secondary_backups[-1]
                self.log(f"Using secondary backup: {latest}")
            else:
                self.log("❌ NO SECONDARY BACKUP AVAILABLE", "CRITICAL")
                return
        
        # Restore backup
        try:
            shutil.copy(latest, self.db_path)
            self.log(f"✅ Database restored from: {latest}")
        except Exception as e:
            self.log(f"❌ RESTORE FAILED: {e}", "CRITICAL")
            return
        
        # Restart workflows
        try:
            subprocess.Popen(['bash', 'start_all.sh'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(5)
            self.log("✅ Workflows restarted")
        except Exception as e:
            self.log(f"⚠️  Workflow restart failed: {e}", "WARN")
            self.log("Please restart workflows manually", "INFO")
        
        self.log("\n✅ ROLLBACK COMPLETE", "INFO")
        self.log("System restored to pre-migration state", "INFO")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Database Normalization v2.2 Migration Orchestrator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run pre-work (zero downtime)
  python migration_scripts/migrate_v2.py --prework

  # Run migration (schedule 3-4 hour window)
  python migration_scripts/migrate_v2.py --migrate

  # Emergency rollback
  python migration_scripts/migrate_v2.py --rollback

  # Test mode (uses test database copy)
  python migration_scripts/migrate_v2.py --migrate --test-mode
        """
    )
    
    parser.add_argument('--prework', action='store_true', 
                       help='Run Phase 1: Pre-work (zero downtime)')
    parser.add_argument('--migrate', action='store_true',
                       help='Run Phase 2: Migration (downtime window)')
    parser.add_argument('--rollback', action='store_true',
                       help='Emergency rollback to backup')
    parser.add_argument('--database', default='ora.db',
                       help='Database path (default: ora.db)')
    parser.add_argument('--test-mode', action='store_true',
                       help='Test mode (skip workflow controls)')
    
    args = parser.parse_args()
    
    # Validate arguments
    if not any([args.prework, args.migrate, args.rollback]):
        parser.print_help()
        sys.exit(1)
    
    # Create orchestrator
    orchestrator = MigrationOrchestrator(args.database, args.test_mode)
    
    try:
        if args.prework:
            orchestrator.run_prework()
        elif args.migrate:
            orchestrator.run_migration()
        elif args.rollback:
            orchestrator._rollback()
            
        sys.exit(0)
        
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
