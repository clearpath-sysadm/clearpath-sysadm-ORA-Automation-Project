#!/usr/bin/env python3
"""
Migration 018 — Lot staging reservations + balance alerts.

Purpose (Task #131 — Fix depleted lot reactivation bug):
    On 2026-07-06 the auto lot-tagger stamped CF1="17612 - 260082" onto 34
    ShipStation orders (109 units) after a 1-unit repack silently reactivated
    a depleted lot, driving inventory to -108 units. Root cause: the tagger
    picked "the current active lot" from an in-memory snapshot with no
    persisted record of what was promised to which order, and depletion status
    could flip back to 'active' on any positive-balance repack regardless of
    whether the order volume already committed against that lot exceeded its
    remaining balance.

Changes:
    1. Creates `lot_staging_reservations` — a persisted ledger of "this
       order/sku is holding N units of this lot" from the moment the tagger
       stamps CF1 until the unit actually ships (consumed) or the order is
       cancelled / retagged / fails to write (released). This lets tagging be
       balance-aware (available = lot balance - open reservations) instead of
       relying on a stale in-memory read.
    2. Unique partial index ensures only one OPEN ('reserved') reservation
       exists per (shipstation_order_id, sku) at a time — retagging must
       release the old reservation before creating a new one.
    3. Creates `lot_balance_alerts` — records any lot whose computed balance
       goes negative, for operational visibility (previously silent).

Rollback:
    migrate_down() drops both tables.
"""

import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.services.database.pg_utils import get_connection


def migrate_up():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        print("Running migration 018: lot_staging_reservations + lot_balance_alerts ...")

        print("  [1/3] Creating lot_staging_reservations table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lot_staging_reservations (
                id                    SERIAL PRIMARY KEY,
                shipstation_order_id  TEXT    NOT NULL,
                order_number          TEXT    NOT NULL,
                sku                   TEXT    NOT NULL,
                lot_id                INTEGER NOT NULL REFERENCES lots(lot_id),
                lot_number            TEXT    NOT NULL,
                reserved_qty          INTEGER NOT NULL CHECK (reserved_qty > 0),
                state                 TEXT    NOT NULL DEFAULT 'reserved'
                                          CHECK (state IN ('reserved', 'consumed', 'released')),
                reservation_source    TEXT    NOT NULL DEFAULT 'tagger',
                release_reason        TEXT,
                created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                consumed_at           TIMESTAMPTZ,
                released_at           TIMESTAMPTZ
            )
        """)

        # Only one OPEN reservation per order+sku at a time. Retag/qty-change
        # flows must release the existing reservation before reserving again.
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS
                lot_staging_reservations_open_order_sku_key
            ON lot_staging_reservations (shipstation_order_id, sku)
            WHERE state = 'reserved'
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS
                lot_staging_reservations_lot_id_state_idx
            ON lot_staging_reservations (lot_id, state)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS
                lot_staging_reservations_order_idx
            ON lot_staging_reservations (shipstation_order_id)
        """)

        print("  [2/3] Creating lot_balance_alerts table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lot_balance_alerts (
                id            SERIAL PRIMARY KEY,
                lot_id        INTEGER REFERENCES lots(lot_id),
                sku           TEXT    NOT NULL,
                lot_number    TEXT    NOT NULL,
                balance       INTEGER NOT NULL,
                alert_type    TEXT    NOT NULL DEFAULT 'negative_balance',
                context       TEXT,
                detected_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                resolved_at   TIMESTAMPTZ
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS
                lot_balance_alerts_unresolved_idx
            ON lot_balance_alerts (resolved_at) WHERE resolved_at IS NULL
        """)

        print("  [3/3] Done.")
        conn.commit()
        print("Migration 018 completed successfully.")

    except Exception as exc:
        conn.rollback()
        print(f"Migration 018 FAILED: {exc}")
        raise
    finally:
        conn.close()


def migrate_down():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        print("Rolling back migration 018 ...")
        cursor.execute("DROP TABLE IF EXISTS lot_balance_alerts")
        cursor.execute("DROP TABLE IF EXISTS lot_staging_reservations")
        conn.commit()
        print("Migration 018 rolled back successfully.")
    except Exception as exc:
        conn.rollback()
        print(f"Migration 018 rollback FAILED: {exc}")
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'down':
        migrate_down()
    else:
        migrate_up()
