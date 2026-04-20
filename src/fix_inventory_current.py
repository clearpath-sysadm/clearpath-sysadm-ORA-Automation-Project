#!/usr/bin/env python3
"""
One-time script: correct inventory_current after a bad EOD run.
The EOD ran with unfixed code (double-deduction bug) and wrote wrong values.
This recomputes using the correct formula and writes the right values.
Delete this file after running.
"""
import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.services.database import get_connection

SKUS = ['17612', '17904', '17914', '18675', '18795']

conn = get_connection()
try:
    cursor = conn.cursor()

    cursor.execute("""
        WITH baseline AS (
            SELECT sku::text AS sku, value::integer AS qty
            FROM configuration_params
            WHERE category = 'InitialInventory'
        ),
        txn_net AS (
            SELECT sku::text AS sku,
                SUM(
                    CASE
                        WHEN transaction_type IN ('Ship', 'Adjust Down') THEN -quantity
                        WHEN transaction_type IN ('Receive', 'Repack', 'Adjust Up') THEN quantity
                        ELSE 0
                    END
                ) AS net_qty
            FROM inventory_transactions
            WHERE date > '2025-09-19'
              AND NOT (transaction_type = 'Ship' AND shipstation_order_id IS NOT NULL)
            GROUP BY sku
        ),
        shipped_net AS (
            SELECT base_sku::text AS sku, -SUM(quantity_shipped) AS net_qty
            FROM shipped_items
            WHERE ship_date > '2025-09-19'
            GROUP BY base_sku
        ),
        all_parts AS (
            SELECT sku, qty FROM baseline
            UNION ALL
            SELECT sku, net_qty FROM txn_net
            UNION ALL
            SELECT sku, net_qty FROM shipped_net
        ),
        correct AS (
            SELECT sku, SUM(qty) AS correct_qty
            FROM all_parts
            WHERE sku = ANY(%s)
            GROUP BY sku
        )
        UPDATE inventory_current ic
        SET current_quantity = c.correct_qty,
            last_updated     = NOW()
        FROM correct c
        WHERE ic.sku = c.sku
        RETURNING ic.sku, ic.current_quantity AS new_qty
    """, (SKUS,))

    rows = cursor.fetchall()
    conn.commit()

    print("inventory_current corrected:")
    for sku, qty in sorted(rows):
        print(f"  SKU {sku}: {qty}")

except Exception as e:
    conn.rollback()
    print(f"ERROR: {e}")
    raise
finally:
    cursor.close()
    conn.close()
