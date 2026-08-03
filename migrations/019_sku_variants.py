#!/usr/bin/env python3
"""
Migration 019 — SKU variants table.

Purpose (Task #138 — ShipStation multi-unit variant SKU package count):
    BigCommerce sends 6-pack / 15-pack / 40-pack variants as a single line
    item at quantity=1 with a compound SKU like '17612-6' rather than
    '17612' at quantity=6.  Without a multiplier table ShipStation would
    generate 1 label instead of 6 and the inventory deduction would be
    off by the same factor.

    This migration creates `sku_variants` which maps every variant SKU
    (e.g. '17612-6') to its base SKU ('17612') and a unit_multiplier (6).
    The lot tagger reads this table to compute the correct num_packages;
    the sync worker uses it to deduct the right inventory quantity.

Schema:
    sku_variants (
        id             SERIAL PRIMARY KEY,
        variant_sku    TEXT NOT NULL UNIQUE,  -- e.g. '17612-6'
        base_sku       TEXT NOT NULL,         -- e.g. '17612'
        unit_multiplier INT  NOT NULL CHECK (unit_multiplier > 0),
        active         BOOL NOT NULL DEFAULT TRUE,
        created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )

Seed rows (16):
    base SKUs: 17612, 17914, 17904, 18675
    multipliers: 1, 6, 15, 40 (suffix matches multiplier)

    The ×1 rows are included for future-proofing so any '-1' variant
    arriving from BigCommerce is recognized and treated as a 1-unit order
    rather than being dropped as an unknown SKU.

Rollback:
    migrate_down() drops the table.
"""

import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.services.database.pg_utils import get_connection

# All 16 seed rows: (variant_sku, base_sku, unit_multiplier)
_SEED_ROWS = [
    # 17612 family
    ('17612-1',  '17612', 1),
    ('17612-6',  '17612', 6),
    ('17612-15', '17612', 15),
    ('17612-40', '17612', 40),
    # 17914 family
    ('17914-1',  '17914', 1),
    ('17914-6',  '17914', 6),
    ('17914-15', '17914', 15),
    ('17914-40', '17914', 40),
    # 17904 family
    ('17904-1',  '17904', 1),
    ('17904-6',  '17904', 6),
    ('17904-15', '17904', 15),
    ('17904-40', '17904', 40),
    # 18675 family
    ('18675-1',  '18675', 1),
    ('18675-6',  '18675', 6),
    ('18675-15', '18675', 15),
    ('18675-40', '18675', 40),
]


def migrate_up():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        print("Running migration 019: sku_variants table ...")

        print("  [1/3] Creating sku_variants table ...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sku_variants (
                id              SERIAL PRIMARY KEY,
                variant_sku     TEXT NOT NULL UNIQUE,
                base_sku        TEXT NOT NULL,
                unit_multiplier INT  NOT NULL CHECK (unit_multiplier > 0),
                active          BOOL NOT NULL DEFAULT TRUE,
                created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS sku_variants_base_sku_idx
            ON sku_variants (base_sku)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS sku_variants_active_idx
            ON sku_variants (active) WHERE active = TRUE
        """)

        print(f"  [2/3] Seeding {len(_SEED_ROWS)} variant rows ...")
        cursor.executemany("""
            INSERT INTO sku_variants (variant_sku, base_sku, unit_multiplier)
            VALUES (%s, %s, %s)
            ON CONFLICT (variant_sku) DO UPDATE
                SET base_sku        = EXCLUDED.base_sku,
                    unit_multiplier = EXCLUDED.unit_multiplier,
                    active          = TRUE
        """, _SEED_ROWS)

        # Safety checks
        cursor.execute("SELECT COUNT(*) FROM sku_variants")
        count = cursor.fetchone()[0]
        assert count == len(_SEED_ROWS), (
            f"Expected {len(_SEED_ROWS)} rows in sku_variants, got {count}"
        )

        # Verify no overlap with sku_promotions (different concerns)
        cursor.execute("""
            SELECT sv.variant_sku
            FROM sku_variants sv
            JOIN sku_promotions sp ON sv.variant_sku = sp.promo_sku
              OR sv.base_sku = sp.promo_sku
        """)
        overlap = cursor.fetchall()
        if overlap:
            raise ValueError(
                f"sku_variants rows overlap with sku_promotions: "
                f"{[r[0] for r in overlap]}"
            )

        print(f"  [3/3] Verified: {count} rows inserted, no overlap with sku_promotions.")
        conn.commit()
        print("Migration 019 completed successfully.")

    except Exception as exc:
        conn.rollback()
        print(f"Migration 019 FAILED: {exc}")
        raise
    finally:
        conn.close()


def migrate_down():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        print("Rolling back migration 019 ...")
        cursor.execute("DROP TABLE IF EXISTS sku_variants")
        conn.commit()
        print("Migration 019 rolled back successfully.")
    except Exception as exc:
        conn.rollback()
        print(f"Migration 019 rollback FAILED: {exc}")
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'down':
        migrate_down()
    else:
        migrate_up()
