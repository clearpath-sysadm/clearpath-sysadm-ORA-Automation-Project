"""
Startup migrations — run once at app boot before serving traffic.

Each migration is idempotent and safe to run repeatedly.
Failures are logged but do not crash the app.
"""

import logging
import os

logger = logging.getLogger(__name__)

IS_PRODUCTION = os.getenv('REPLIT_DEPLOYMENT') == '1'



def _seed_production_lots(cursor):
    """
    Restore skus, lots, and opening-balance inventory_transactions after the
    deployment wiped these tables on 2026-04-09.

    Only runs in production (REPLIT_DEPLOYMENT=1) when skus is empty.
    Entire seed is inside the caller's transaction — if anything fails the
    whole thing rolls back and retries cleanly on the next boot.

    Insert order respects FK constraints:
        skus  →  lots (lots.sku_id FK → skus.sku_id)
        lots  →  inventory_transactions (it.lot_id FK → lots.lot_id)

    After explicit-ID inserts the sequences are reset so future auto-inserts
    don't collide.

    Verified production state (2026-04-13, Task #31):
        skus:  5 rows (17612, 17904, 17914, 18675, 18795)
        lots:  19 total, 5 active
        lot_balances: 17612→260047=1728, 17904→250240=112,
                      17914→250297=774,  18675→240231=437, 18795→11001=174
        Lot tagger ACTIVE_LOTS_QUERY: 5 SKUs returned
        Upload worker lot query:      5 active lots returned
        Deployment log: VALIDATION PASSED — all lot/sku checks OK.
    """
    if not IS_PRODUCTION:
        return

    cursor.execute("SELECT COUNT(*) FROM skus")
    if cursor.fetchone()[0] > 0:
        logger.info("startup_migrations: skus already populated — skipping lot seed")
        return

    logger.warning("startup_migrations: skus table is EMPTY — running production lot seed")

    # ── 1. skus ──────────────────────────────────────────────────────────────
    cursor.execute("""
        INSERT INTO skus (sku_id, sku_code) VALUES
            (1, '17612'),
            (2, '17904'),
            (3, '17914'),
            (4, '18675'),
            (5, '18795')
    """)
    cursor.execute("SELECT setval('skus_sku_id_seq', 5)")
    logger.info("startup_migrations: inserted 5 skus")

    # ── 2. lots ───────────────────────────────────────────────────────────────
    # Source of truth: production sku_lot table + dev lots data.
    # Active lots confirmed by user: 260047 (17612), 250240 (17904),
    #   250297 (17914), 240231 (18675), 11001 (18795).
    # lot_id values mirror dev so dev/prod stay in sync.
    cursor.execute("""
        INSERT INTO lots
            (lot_id, sku_id, lot_number, status, received_date, notes, created_at, updated_at)
        VALUES
            -- 17612 (sku_id=1) ------------------------------------------
            (1,  1, '250101', 'inactive', NULL,           NULL,                                                              '2025-10-02 06:58:13', '2025-10-02 06:58:13'),
            (5,  1, '250172', 'inactive', NULL,           NULL,                                                              '2025-10-02 06:58:13', '2025-10-02 06:58:13'),
            (6,  1, '250195', 'inactive', NULL,           NULL,                                                              '2025-10-02 06:58:13', '2025-10-02 06:58:13'),
            (9,  1, '250216', 'inactive', NULL,           NULL,                                                              '2025-10-02 06:58:13', '2025-10-02 06:58:13'),
            (10, 1, '250237', 'depleted', '2025-09-19',   'Imported from 9/19/2025 baseline inventory (EOD Prior Week)',     '2025-10-02 06:58:13', '2025-10-06 17:05:10'),
            (13, 1, '250300', 'inactive', NULL,           NULL,                                                              '2025-10-03 20:17:08', '2025-10-06 17:05:04'),
            (14, 1, '250340', 'depleted', NULL,           NULL,                                                              '2025-10-29 20:36:34', '2025-12-03 12:37:26'),
            (15, 1, '250362', 'inactive', NULL,           NULL,                                                              '2025-11-11 21:52:12', '2025-11-11 21:52:12'),
            (16, 1, '250372', 'inactive', NULL,           NULL,                                                              '2025-11-26 14:57:37', '2026-02-05 15:26:28'),
            (17, 1, '250377', 'inactive', NULL,           NULL,                                                              '2026-02-05 15:31:13', '2026-03-05 15:24:08'),
            (18, 1, '260017', 'inactive', '2026-04-02',   'Added inventory recount Apr 2026',                               '2026-04-02 02:55:56', '2026-04-09 17:35:25'),
            (19, 1, '260047', 'active',   '2026-04-02',   'Added inventory recount Apr 2026',                               '2026-04-02 02:55:56', '2026-04-09 17:35:53'),
            -- 17904 (sku_id=2) ------------------------------------------
            (2,  2, '240276', 'inactive', NULL,           NULL,                                                              '2025-10-02 06:58:13', '2025-10-02 06:58:13'),
            (12, 2, '250240', 'active',   '2025-09-19',   'Imported from 9/19/2025 baseline inventory (EOD Prior Week)',     '2025-10-02 06:58:13', '2025-10-02 06:58:13'),
            -- 17914 (sku_id=3) ------------------------------------------
            (3,  3, '240286', 'inactive', NULL,           NULL,                                                              '2025-10-02 06:58:13', '2025-10-02 06:58:13'),
            (11, 3, '250297', 'active',   '2025-09-19',   'Imported from 9/19/2025 baseline inventory (EOD Prior Week)',     '2025-10-02 06:58:13', '2025-10-02 06:58:13'),
            -- 18675 (sku_id=4) ------------------------------------------
            (4,  4, '240231', 'active',   '2025-09-19',   'Imported from 9/19/2025 baseline inventory (EOD Prior Week)',     '2025-10-02 06:58:13', '2025-10-02 06:58:13'),
            -- 18795 (sku_id=5) ------------------------------------------
            (7,  5, '11001',  'active',   '2025-09-19',   'Imported from 9/19/2025 baseline inventory (EOD Prior Week)',     '2025-10-02 06:58:13', '2025-10-02 06:58:13'),
            (8,  5, '11002',  'inactive', NULL,           NULL,                                                              '2025-10-02 06:58:13', '2025-10-02 06:58:13')
    """)
    cursor.execute("SELECT setval('lots_lot_id_seq', 19)")
    logger.info("startup_migrations: inserted 19 lots (5 active)")

    # ── 3. inventory_transactions opening balances ────────────────────────────
    # All existing production transactions have lot_id=NULL so the lot_balances
    # VIEW shows 0 for every lot.  The lot tagger requires balance > 0.
    # These Receive transactions establish opening balances so the VIEW returns
    # positive numbers for each active lot.
    # Quantities sourced from dev lot_balances (best available reference).
    seed_date = '2026-04-10'
    seed_note = 'Opening balance — production seed restore 2026-04-10'
    cursor.execute("""
        INSERT INTO inventory_transactions
            (date, sku, lot_id, quantity, transaction_type, notes)
        VALUES
            (%s, '17612', 19, 1728, 'Receive', %s),
            (%s, '17904', 12,  112, 'Receive', %s),
            (%s, '17914', 11,  774, 'Receive', %s),
            (%s, '18675',  4,  437, 'Receive', %s),
            (%s, '18795',  7,  174, 'Receive', %s)
    """, (
        seed_date, seed_note,
        seed_date, seed_note,
        seed_date, seed_note,
        seed_date, seed_note,
        seed_date, seed_note,
    ))
    logger.info("startup_migrations: inserted 5 opening-balance Receive transactions")


def _reconcile_shipstation_lot_ids(cursor):
    """
    Backfill lot_id on shipstation_order_line_items rows that are missing it.

    Background: before the lots/skus tables were seeded, the lot tagger could
    not set lot_id on line items it processed.  The correct lot number is
    already stored in order_items_inbox.sku_lot (format: '{sku} - {lot_number}')
    so we can recover lot_id by joining through that field.

    Safe to run repeatedly — WHERE lot_id IS NULL means already-tagged rows
    are never touched.  Runs in both dev and production (idempotent).

    IMPORTANT: inventory_transactions rows with lot_id=NULL are intentionally
    left alone.  The opening-balance Receive transactions seeded on 2026-04-10
    already capture their net effect; backfilling those would cause
    double-deductions in the lot_balances VIEW.
    """
    cursor.execute("""
        SELECT COUNT(*) FROM shipstation_order_line_items
        WHERE lot_id IS NULL
          AND sku IN ('17612', '17904', '17914', '18675', '18795')
    """)
    pending = cursor.fetchone()[0]

    if pending == 0:
        logger.info("startup_migrations: shipstation_order_line_items — all lot_ids populated, skipping reconciliation")
        return

    logger.warning(
        f"startup_migrations: shipstation_order_line_items — {pending} rows missing lot_id, reconciling"
    )

    cursor.execute("""
        UPDATE shipstation_order_line_items soli
        SET lot_id = l.lot_id
        FROM orders_inbox oi,
             order_items_inbox oii,
             lots l
        WHERE soli.order_inbox_id = oi.id
          AND oii.order_inbox_id = oi.id
          AND oii.sku = soli.sku
          AND l.lot_number = TRIM(SPLIT_PART(oii.sku_lot, ' - ', 2))
          AND soli.lot_id IS NULL
          AND oii.sku_lot IS NOT NULL
          AND oii.sku_lot != ''
          AND soli.sku IN ('17612', '17904', '17914', '18675', '18795')
    """)
    updated = cursor.rowcount
    still_null = pending - updated

    if still_null > 0:
        logger.warning(
            f"startup_migrations: shipstation_order_line_items — updated {updated}, "
            f"{still_null} rows still have lot_id=NULL (no matching sku_lot data)"
        )
    else:
        logger.info(
            f"startup_migrations: shipstation_order_line_items — reconciled {updated} rows successfully"
        )


def _validate_production_lots(cursor):
    """
    Post-seed validation — runs after commit so it reads durable data.
    Logs a clear PASS or FAIL for each check.  Non-fatal: a validation
    failure logs ERROR but does not crash the app.
    """
    if not IS_PRODUCTION:
        return

    logger.info("=" * 70)
    logger.info("startup_migrations: VALIDATION — lot/sku seed")
    logger.info("=" * 70)

    failures = []

    # Check 1: skus count
    cursor.execute("SELECT COUNT(*) FROM skus")
    sku_count = cursor.fetchone()[0]
    if sku_count == 5:
        logger.info(f"  [PASS] skus: {sku_count} rows (expected 5)")
    else:
        msg = f"skus: {sku_count} rows (expected 5)"
        logger.error(f"  [FAIL] {msg}")
        failures.append(msg)

    # Check 2: lots total and active count
    cursor.execute("SELECT COUNT(*), COUNT(*) FILTER (WHERE status='active') FROM lots")
    total_lots, active_lots = cursor.fetchone()
    if total_lots == 19 and active_lots == 5:
        logger.info(f"  [PASS] lots: {total_lots} total, {active_lots} active (expected 19 / 5)")
    else:
        msg = f"lots: {total_lots} total, {active_lots} active (expected 19 / 5)"
        logger.error(f"  [FAIL] {msg}")
        failures.append(msg)

    # Check 3: lot_balances VIEW returns positive balances for all 5 active lots
    cursor.execute("""
        SELECT sku_code, lot_number, balance
        FROM lot_balances
        WHERE status = 'active'
        ORDER BY sku_code
    """)
    balance_rows = cursor.fetchall()
    logger.info(f"  lot_balances (active lots with balance):")
    for row in balance_rows:
        sku, lot, bal = row
        status = "PASS" if bal > 0 else "FAIL"
        logger.info(f"    [{status}] SKU {sku} → lot {lot}: balance={bal}")
        if bal <= 0:
            failures.append(f"SKU {sku} lot {lot} has zero/negative balance ({bal})")

    if len(balance_rows) != 5:
        msg = f"lot_balances returned {len(balance_rows)} active rows (expected 5)"
        logger.error(f"  [FAIL] {msg}")
        failures.append(msg)

    # Check 4: ACTIVE_LOTS_QUERY (what the lot tagger actually uses)
    cursor.execute("""
        SELECT DISTINCT ON (s.sku_code) s.sku_code, l.lot_number
        FROM lots l
        JOIN skus s ON s.sku_id = l.sku_id
        JOIN lot_balances lb ON lb.lot_id = l.lot_id
        WHERE lb.balance > 0
          AND l.status NOT IN ('quarantine', 'inactive')
        ORDER BY s.sku_code, l.received_date ASC NULLS LAST, l.lot_id ASC
    """)
    tagger_lots = cursor.fetchall()
    if len(tagger_lots) == 5:
        logger.info(f"  [PASS] Lot tagger ACTIVE_LOTS_QUERY: {len(tagger_lots)} SKUs")
        for sku, lot in tagger_lots:
            logger.info(f"    SKU {sku} → lot {lot}")
    else:
        msg = f"Lot tagger query returned {len(tagger_lots)} SKUs (expected 5)"
        logger.error(f"  [FAIL] {msg}")
        failures.append(msg)

    # Check 5: Upload worker query (WHERE status='active', no balance filter)
    cursor.execute("""
        SELECT s.sku_code, l.lot_number
        FROM lots l
        JOIN skus s ON s.sku_id = l.sku_id
        WHERE l.status = 'active'
        ORDER BY s.sku_code
    """)
    upload_lots = cursor.fetchall()
    if len(upload_lots) == 5:
        logger.info(f"  [PASS] Upload worker lot query: {len(upload_lots)} active lots")
    else:
        msg = f"Upload worker query returned {len(upload_lots)} lots (expected 5)"
        logger.error(f"  [FAIL] {msg}")
        failures.append(msg)

    logger.info("=" * 70)
    if failures:
        logger.error(
            f"startup_migrations: VALIDATION FAILED — {len(failures)} issue(s): "
            + "; ".join(failures)
        )
    else:
        logger.warning(
            "startup_migrations: VALIDATION PASSED — all lot/sku checks OK. "
            "Production lot system is restored."
        )
    logger.info("=" * 70)


def _ensure_shipstation_line_items_index(cursor):
    """
    Create the unique index on shipstation_order_line_items that includes lot_id.

    Background: Replit's migration generator produces wrong operator classes for
    COALESCE expressions mixed with columns of varying types, causing deployment
    failures. We manage this index directly via psycopg2 (plain SQL) to bypass
    the generator, letting Replit handle only the simple ADD COLUMN lot_id step.

    Safe to call repeatedly — checks for the column and index before acting.
    Logs an ERROR (non-fatal) if index creation fails so the issue is visible.
    """
    # Only run in production — in dev this step is intentionally skipped so that
    # Replit's schema comparison sees no COALESCE index in dev and generates only
    # simple ADD COLUMN / DROP INDEX statements (avoiding its operator-class bug).
    if not IS_PRODUCTION:
        logger.info(
            "startup_migrations: skipping shipstation_order_line_items index "
            "creation in dev environment"
        )
        return

    # Skip if lot_id column doesn't exist yet (Replit migration hasn't run)
    cursor.execute("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'shipstation_order_line_items'
          AND column_name = 'lot_id'
    """)
    if not cursor.fetchone():
        logger.info(
            "startup_migrations: shipstation_order_line_items.lot_id not yet present — "
            "skipping index creation (Replit migration pending)"
        )
        return

    # Skip if index already exists
    cursor.execute("""
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'shipstation_order_line_items'
          AND indexname = 'idx_shipstation_order_line_items_unique'
    """)
    if cursor.fetchone():
        logger.info(
            "startup_migrations: idx_shipstation_order_line_items_unique already present"
        )
        return

    # Dedup first so index creation can't fail due to existing duplicates
    cursor.execute("""
        DELETE FROM shipstation_order_line_items
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM shipstation_order_line_items
            GROUP BY order_inbox_id, sku, COALESCE(lot_id, -1)
        )
    """)
    removed = cursor.rowcount
    if removed > 0:
        logger.warning(
            f"startup_migrations: shipstation_order_line_items — removed {removed} "
            "duplicate rows before index creation"
        )

    cursor.execute("""
        CREATE UNIQUE INDEX idx_shipstation_order_line_items_unique
        ON shipstation_order_line_items (order_inbox_id, sku, COALESCE(lot_id, '-1'::integer))
    """)
    logger.info(
        "startup_migrations: idx_shipstation_order_line_items_unique created successfully"
    )


def _ensure_time_logs_table(cursor):
    """
    Create the time_logs table if it doesn't already exist, then
    conditionally add the FK to users if the users table is present.

    Captures who logged time, the date, hours spent (in 0.25 increments),
    and an optional note. Runs in both dev and production.
    """
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS time_logs (
            id              SERIAL PRIMARY KEY,
            user_id         TEXT NOT NULL,
            user_display_name TEXT NOT NULL,
            log_date        DATE NOT NULL,
            hours_spent     NUMERIC(5, 2) NOT NULL
                            CHECK (hours_spent >= 0.25 AND hours_spent <= 24
                                   AND MOD(hours_spent * 4, 1) = 0),
            notes           TEXT,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    # Add FK constraint to users if: users table exists AND constraint not yet added
    cursor.execute("""
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'users'
    """)
    if cursor.fetchone():
        cursor.execute("""
            SELECT 1 FROM information_schema.table_constraints
            WHERE table_name = 'time_logs'
              AND constraint_name = 'time_logs_user_id_fkey'
        """)
        if not cursor.fetchone():
            cursor.execute("""
                ALTER TABLE time_logs
                ADD CONSTRAINT time_logs_user_id_fkey
                FOREIGN KEY (user_id) REFERENCES users(id)
            """)
            logger.info("startup_migrations: time_logs_user_id_fkey FK constraint added")
        else:
            logger.info("startup_migrations: time_logs_user_id_fkey already present")
    else:
        logger.warning(
            "startup_migrations: users table not found — time_logs FK constraint skipped"
        )

    logger.info("startup_migrations: time_logs table ensured")


def _cleanup_stale_scanner_rows(cursor):
    """
    Remove orphaned duplicate-scanner and lot-mismatch-scanner rows from
    workflow_controls.

    These were created by the original duplicate/mismatch scanner workflows
    (removed in Task #34). The backing scripts, API routes, and Replit
    workflows are all gone, but the DB rows remained in production because
    the Task #34 cleanup only ran against dev. This migration deletes them
    so the Workflow Controls page no longer shows stale entries.

    Safe to run repeatedly — idempotent DELETE with no side effects.
    Runs in both dev and production.
    """
    stale = ('duplicate-scanner', 'lot-mismatch-scanner')
    cursor.execute(
        "DELETE FROM workflow_controls WHERE workflow_name = ANY(%s)",
        (list(stale),)
    )
    removed = cursor.rowcount
    if removed:
        logger.info(
            f"startup_migrations: removed {removed} stale scanner row(s) "
            f"from workflow_controls: {stale}"
        )
    else:
        logger.info("startup_migrations: no stale scanner rows found in workflow_controls")


def _resolve_false_positive_incident_8(cursor):
    """
    Close production_incident #8 which was a false positive.

    Root cause: verify_tagging_results() checked the pre-tagging in-memory order
    snapshot, so orders correctly tagged during the startup catch-up sweep still
    showed customField1='' in memory. Fixed in tagger.py by writing the new value
    back to the in-memory dict after each successful ShipStation API update.

    Idempotent: only updates when status is still 'new'.
    Safe: skips silently when the production_incidents table does not exist.
    """
    cursor.execute(
        """
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = 'production_incidents'
        )
        """
    )
    if not cursor.fetchone()[0]:
        return

    cursor.execute(
        """
        UPDATE production_incidents
        SET status     = 'resolved',
            cause      = 'QA check read the pre-tagging in-memory order snapshot. '
                         'Orders 862266/862270/862271/862272 were correctly tagged in '
                         'ShipStation during the startup catch-up sweep, but the Python '
                         'dicts in all_orders were not updated in memory, so QA saw stale '
                         'empty customField1 values and raised a false alarm.',
            resolution = 'False positive confirmed by user ShipStation review. '
                         'Fixed in tagger.py: all three tagging paths (tracked-SKU, '
                         'lot-stamped SKU, home-office SKU) now write the new customField1 '
                         'value back to the in-memory order dict immediately after a '
                         'successful API update, so subsequent QA checks see post-tagging state.',
            updated_at = NOW()
        WHERE id = 8
          AND status = 'new'
        """,
    )
    if cursor.rowcount:
        logger.info("startup_migrations: resolved false-positive production_incident #8")


def _add_order_datetime_column(cursor):
    """
    Add order_datetime TIMESTAMPTZ column to orders_inbox and backfill existing rows.

    order_datetime stores the full ShipStation orderDate (with time, UTC) rather
    than just the date portion.  It powers the noon-to-noon CDT shipping-window
    count on the dashboard ("New Orders Today").

    Idempotent: ADD COLUMN IF NOT EXISTS prevents failures on re-runs.
    Backfill: existing rows receive  order_date::timestamptz + 12h  (noon UTC) as a
    reasonable approximation — all rows are guaranteed to have a non-null order_date.
    """
    cursor.execute("""
        ALTER TABLE orders_inbox
        ADD COLUMN IF NOT EXISTS order_datetime TIMESTAMPTZ
    """)
    cursor.execute("""
        UPDATE orders_inbox
        SET order_datetime = order_date::timestamptz + INTERVAL '12 hours'
        WHERE order_datetime IS NULL
          AND order_date IS NOT NULL
    """)
    logger.info("startup_migrations: order_datetime column ensured and backfilled")


def _fix_inventory_transactions_unique_index(cursor):
    """
    Replace the over-broad unique index on inventory_transactions with a
    correct per-order index.

    Problem (discovered 2026-04-14):
      The existing index  inventory_transactions_date_sku_lot_id_type_qty_key
      is defined on  (date, sku, COALESCE(lot_id,-1), quantity, transaction_type).
      This prevents two DIFFERENT orders from shipping the same lot/sku/qty on
      the same day — a legitimate scenario.  The sync's pre-check guards against
      true double-deduction using (lot_id, shipstation_order_id, 'Ship'), but the
      old index fires first and aborts the transaction, causing every sync run to
      roll back ALL successfully imported orders via the raise-on-error path.

    Fix:
      1. Drop the old index (IF EXISTS — safe to repeat).
      2. Create a new partial unique index on
           (lot_id, shipstation_order_id, transaction_type)
         WHERE shipstation_order_id IS NOT NULL.
         This matches the pre-check exactly and allows different orders to each
         deduct the same lot on the same day.

    Idempotent: IF NOT EXISTS / IF EXISTS guards make repeated runs safe.
    """
    cursor.execute("""
        DROP INDEX IF EXISTS inventory_transactions_date_sku_lot_id_type_qty_key
    """)
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS inventory_transactions_lot_ss_type_key
        ON inventory_transactions (lot_id, shipstation_order_id, transaction_type)
        WHERE shipstation_order_id IS NOT NULL
    """)
    logger.info("startup_migrations: inventory_transactions unique index rebuilt (per-order)")


def _fix_shipstation_timestamp_timezone(cursor):
    """
    ShipStation's API returns timestamps in Pacific time (PDT/PST = America/Los_Angeles),
    not UTC.  Previous import code called .replace(tzinfo=utc) which mislabeled them,
    causing every order_datetime to be stored 7 hours too early.

    Proof (confirmed 2026-04-14):
      order 862300 — ShipStation UI shows imported at 8:29 AM CDT
      API createDate = 06:29 (Pacific) → treated as UTC → displayed as 1:29 AM CDT (wrong)
      06:29 PDT (UTC-7) → 13:29 UTC → 8:29 AM CDT (correct)

    This migration:
      1. Adds a boolean guard column _datetime_tz_corrected (idempotency).
      2. Adds +7 hours to every non-X-Cart order_datetime that was set from a real
         ShipStation timestamp.  "Real" timestamps are identified by NOT matching the
         noon-UTC backfill pattern (order_date::timestamptz + 12h) applied during
         Task #37 for pre-existing historical rows.
      3. Marks corrected rows with _datetime_tz_corrected = TRUE so the UPDATE is
         skipped on every subsequent server restart.

    Excluded:
      - X-Cart orders  (different source system, timestamps handled separately)
      - Noon-backfill rows  (approximate historical values; adjusting them would add
        spurious precision to already-approximate data)
    """
    # Step 1: Add the guard column with DEFAULT FALSE so all pre-existing rows
    # are initially marked as "not yet corrected".  New rows inserted after this
    # migration runs will also start as FALSE until Step 3 changes the default.
    cursor.execute("""
        ALTER TABLE orders_inbox
        ADD COLUMN IF NOT EXISTS _datetime_tz_corrected BOOLEAN NOT NULL DEFAULT FALSE
    """)

    # Step 2: Correct all pre-existing rows that have real ShipStation timestamps.
    # Exclusions:
    #   - _datetime_tz_corrected = TRUE  → already corrected, skip (idempotency)
    #   - order_datetime IS NULL          → no timestamp to correct
    #   - source_system IS NOT DISTINCT FROM 'X-Cart'  → different source, unaffected
    #     (IS DISTINCT FROM handles NULLs correctly; != does not)
    #   - noon-backfill pattern           → approximate historical value from Task #37;
    #     adjusting would add false precision to already-imprecise data
    cursor.execute("""
        UPDATE orders_inbox
        SET
            order_datetime         = order_datetime + INTERVAL '7 hours',
            _datetime_tz_corrected = TRUE
        WHERE _datetime_tz_corrected = FALSE
          AND order_datetime IS NOT NULL
          AND source_system IS DISTINCT FROM 'X-Cart'
          AND order_datetime IS DISTINCT FROM (order_date::timestamptz + INTERVAL '12 hours')
    """)

    # Step 3: Change the column default to TRUE so any rows inserted AFTER this
    # migration (i.e. from the fixed parser) are born already-correct and will
    # never be shifted again on subsequent restarts.
    cursor.execute("""
        ALTER TABLE orders_inbox
        ALTER COLUMN _datetime_tz_corrected SET DEFAULT TRUE
    """)
    logger.info("startup_migrations: ShipStation timezone offset corrected (+7h applied to real timestamps)")


def _clear_sync_interval_health_check(cursor):
    """
    The unified-shipstation-sync workflow previously ran every 5 minutes, so
    expected_interval_seconds was set to 300.  The schedule has changed to
    3 fixed times per day (6 AM / 12 PM / 12:30 PM CDT) plus webhook triggers.
    The longest legitimate gap between runs is now ~17.5 hours (overnight), so
    the 300-second interval would fire constant false 'stuck' alarms.

    Setting expected_interval_seconds to NULL opts this workflow out of the
    time-based health check entirely.  Heartbeat-based monitoring (workflow_heartbeats)
    continues to capture whether the workflow is alive when it actually runs.

    Idempotent: IF NOT EXISTS / UPDATE is safe to run on every restart.
    """
    cursor.execute("""
        UPDATE workflows
        SET expected_interval_seconds = NULL
        WHERE name = 'unified-shipstation-sync'
          AND expected_interval_seconds IS NOT NULL
    """)
    logger.info("startup_migrations: unified-shipstation-sync expected_interval_seconds cleared (schedule changed to 3x daily)")


def _add_action_type_to_deleted_orders(cursor):
    """
    Add action_type VARCHAR(20) NOT NULL DEFAULT 'deleted' to deleted_shipstation_orders.

    Distinguishes rows that represent true ShipStation deletions (legacy, action_type='deleted')
    from the new cancel-with-CF3-stamp policy (action_type='cancelled').

    DEFAULT 'deleted' preserves the semantics of all existing rows, which were
    written by the old delete_order_from_shipstation path.
    """
    cursor.execute("""
        ALTER TABLE deleted_shipstation_orders
        ADD COLUMN IF NOT EXISTS action_type VARCHAR(20) NOT NULL DEFAULT 'deleted'
    """)
    logger.info("startup_migrations: deleted_shipstation_orders.action_type column ensured")


def _add_manually_resolved_status(cursor):
    """
    Extend the CHECK constraint on promo_sku_replacement_log.status to include
    the 'manually_resolved' value, which is written by the new resolve endpoint.

    Strategy:
      1. Skip entirely if the constraint already includes 'manually_resolved'
         (idempotency — subsequent boots are free).
      2. Otherwise drop the old constraint (IF EXISTS) and recreate it with the
         expanded value list.

    Runs in both dev and production.
    """
    cursor.execute("""
        SELECT pg_get_constraintdef(c.oid)
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        WHERE c.conname = 'promo_sku_replacement_log_status_check'
          AND t.relname = 'promo_sku_replacement_log'
    """)
    row = cursor.fetchone()
    if row and 'manually_resolved' in row[0]:
        logger.info("startup_migrations: promo_sku_replacement_log status constraint already includes manually_resolved — skipping")
        return

    cursor.execute("""
        ALTER TABLE promo_sku_replacement_log
        DROP CONSTRAINT IF EXISTS promo_sku_replacement_log_status_check
    """)
    cursor.execute("""
        ALTER TABLE promo_sku_replacement_log
        ADD CONSTRAINT promo_sku_replacement_log_status_check
        CHECK (status IN ('replaced', 'failed', 'verify_failed', 'skipped', 'manually_resolved'))
    """)
    logger.info("startup_migrations: promo_sku_replacement_log status constraint updated (added manually_resolved)")


def _backfill_promo_lot_tagging_resolved_at(cursor):
    """
    Close stale lot_tagging_failures rows for promo SKU orders that have
    already been successfully replaced.

    Problem: before Task #48, the success path of handle_promo_sku_order did
    not write resolved_at to lot_tagging_failures.  Orders that failed then
    self-recovered (e.g. 862369, 862371) remain with resolved_at IS NULL and
    appear as false positives in the new Promo SKU Issues dashboard panel.

    Fix: set resolved_at = NOW(), resolved_by = 'backfill' on any
    lot_tagging_failures row whose order_number has at least one 'replaced'
    row in promo_sku_replacement_log.  Only touches rows where resolved_at IS
    NULL to avoid overwriting rows already resolved by the new code path.

    Idempotent: WHERE resolved_at IS NULL guard makes re-runs safe.
    Runs in both dev and production.
    """
    cursor.execute("""
        UPDATE lot_tagging_failures ltf
           SET resolved_at  = NOW(),
               resolved_by  = 'backfill'
         WHERE ltf.resolved_at IS NULL
           AND EXISTS (
               SELECT 1
                 FROM promo_sku_replacement_log prl
                WHERE prl.order_number = ltf.order_number
                  AND prl.status       = 'replaced'
           )
    """)
    updated = cursor.rowcount
    if updated:
        logger.info(
            f"startup_migrations: backfilled resolved_at on {updated} "
            f"lot_tagging_failures row(s) for already-replaced promo orders"
        )
    else:
        logger.info(
            "startup_migrations: no stale promo lot_tagging_failures to backfill"
        )


def _seed_sku_promotions(cursor):
    """
    Ensure all active promo-SKU → base-SKU mappings exist in sku_promotions.

    Uses ON CONFLICT (promo_sku) DO UPDATE so the row is created if missing
    and corrected if it exists with the wrong base_sku or active=FALSE.

    Runs in both dev and production.  The four canonical mappings are:
        17613 → 17612   (promo ring → base ring)
        17905 → 17904
        17915 → 17914
        18676 → 18675   (promo toothbrush → base toothbrush)

    18795 (toothpaste) is intentionally excluded — no promo variant.
    """
    cursor.execute("""
        INSERT INTO sku_promotions (promo_sku, base_sku, active)
        VALUES
            ('17613', '17612', TRUE),
            ('17905', '17904', TRUE),
            ('17915', '17914', TRUE),
            ('18676', '18675', TRUE)
        ON CONFLICT (promo_sku) DO UPDATE
            SET base_sku = EXCLUDED.base_sku,
                active   = EXCLUDED.active
    """)
    logger.info(f"startup_migrations: sku_promotions — {cursor.rowcount} row(s) upserted")


def run_all(conn):
    """
    Run every startup migration inside a single transaction.
    Rolls back and logs on any failure so the app can still start.
    Validation runs after commit so it reads durable data.
    """
    try:
        with conn.cursor() as cur:
            _seed_production_lots(cur)
            _reconcile_shipstation_lot_ids(cur)
            _ensure_shipstation_line_items_index(cur)
            _ensure_time_logs_table(cur)
            _cleanup_stale_scanner_rows(cur)
            _resolve_false_positive_incident_8(cur)
            _add_order_datetime_column(cur)
            _fix_inventory_transactions_unique_index(cur)
            _fix_shipstation_timestamp_timezone(cur)
            _clear_sync_interval_health_check(cur)
            _seed_sku_promotions(cur)
            _add_action_type_to_deleted_orders(cur)
            _add_manually_resolved_status(cur)
            _backfill_promo_lot_tagging_resolved_at(cur)
        conn.commit()
        logger.info("startup_migrations: all migrations completed successfully")
    except Exception as exc:
        conn.rollback()
        logger.error(f"startup_migrations: migration failed, rolled back — {exc}", exc_info=True)
        return

    # Validation is read-only and runs after commit — a failure here is
    # informational only and does not prevent the app from starting.
    try:
        with conn.cursor() as cur:
            _validate_production_lots(cur)
    except Exception as exc:
        logger.error(f"startup_migrations: validation error — {exc}", exc_info=True)
