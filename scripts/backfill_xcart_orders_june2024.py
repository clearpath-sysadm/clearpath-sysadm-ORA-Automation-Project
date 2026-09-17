#!/usr/bin/env python3
"""
One-off backfill: import 5 XCart manual orders from 6/23-6/24 that were
silently skipped by the old sync router and never deducted from inventory.

Orders: 100718, 100719, 100720, 100721, 100722
Expected: 44 units of 17612 deducted from lot 260122
Expected post-backfill system balance: 907 → 863
(3-unit residual vs. physical 866 is a known pre-existing 6/22 over-deduction)

Safe to re-run — import_new_manual_order and deduct_lot_inventory are both idempotent.
"""

import os
import sys
import requests
import psycopg2

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.services.shipstation.api_client import get_shipstation_credentials, get_shipstation_headers
from src.unified_shipstation_sync import import_new_manual_order

XCART_STORE_ID = 345611
ORDER_NUMBERS = ['100718', '100719', '100720', '100721', '100722']
SS_ORDERS_URL = 'https://ssapi.shipstation.com/orders'
BALANCE_SKU = '17612'


def get_lot_balance(conn, sku: str) -> int:
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COALESCE(
            (SELECT SUM(CASE WHEN transaction_type = 'Receive' THEN quantity
                             WHEN transaction_type = 'Ship'    THEN -quantity
                             WHEN transaction_type = 'Adjust'  THEN quantity
                             ELSE 0 END)
             FROM inventory_transactions
             WHERE sku = %s
               AND archived_at IS NULL),
            0
        )
    """, (sku,))
    row = cursor.fetchone()
    return int(row[0]) if row else 0


def fetch_order_from_shipstation(order_number: str, api_key: str, api_secret: str) -> dict | None:
    headers = get_shipstation_headers(api_key, api_secret)
    resp = requests.get(
        SS_ORDERS_URL,
        params={'orderNumber': order_number, 'storeId': XCART_STORE_ID},
        headers=headers,
        timeout=30
    )
    resp.raise_for_status()
    data = resp.json()
    orders = data.get('orders', [])
    if not orders:
        print(f"  ⚠️  Order {order_number} not found in ShipStation (storeId={XCART_STORE_ID})")
        return None
    if len(orders) > 1:
        print(f"  ⚠️  Multiple orders returned for {order_number} — using first result")
    return orders[0]


def main():
    api_key, api_secret = get_shipstation_credentials()
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)

    conn = psycopg2.connect(database_url)
    conn.autocommit = False

    try:
        balance_before = get_lot_balance(conn, BALANCE_SKU)
        print(f"\n{'='*60}")
        print(f"XCart Manual Order Backfill — 5 missing orders")
        print(f"{'='*60}")
        print(f"Balance BEFORE ({BALANCE_SKU}): {balance_before}")
        print()

        results = {'imported': 0, 'skipped_conflict': 0, 'failed': 0}

        for order_number in ORDER_NUMBERS:
            print(f"--- Order {order_number} ---")
            order_data = fetch_order_from_shipstation(order_number, api_key, api_secret)
            if order_data is None:
                results['failed'] += 1
                continue

            status = order_data.get('orderStatus', 'unknown')
            cf1 = (order_data.get('advancedOptions') or {}).get('customField1', '')
            items = order_data.get('items', [])
            total_qty = sum(i.get('quantity', 0) for i in items)
            print(f"  Status: {status}  |  cf1: '{cf1}'  |  items qty: {total_qty}")

            result = import_new_manual_order(order_data, conn, api_key, api_secret)
            conn.commit()

            if result is True:
                print(f"  ✅ Imported and deducted")
                results['imported'] += 1
            elif result is None:
                print(f"  ⚠️  Conflict detected — skipped (not an error)")
                results['skipped_conflict'] += 1
            else:
                print(f"  ❌ Import returned False — check logs")
                results['failed'] += 1
                conn.rollback()

        balance_after = get_lot_balance(conn, BALANCE_SKU)
        deducted = balance_before - balance_after

        print()
        print(f"{'='*60}")
        print(f"Summary")
        print(f"{'='*60}")
        print(f"  Orders imported:        {results['imported']}")
        print(f"  Conflicts (skipped):    {results['skipped_conflict']}")
        print(f"  Failures:               {results['failed']}")
        print()
        print(f"  Balance BEFORE ({BALANCE_SKU}): {balance_before}")
        print(f"  Balance AFTER  ({BALANCE_SKU}): {balance_after}")
        print(f"  Units deducted:         {deducted}")
        print()
        if deducted == 44:
            print("  ✅ Expected 44 units deducted — correct!")
        elif deducted == 0 and results['skipped_conflict'] == len(ORDER_NUMBERS):
            print("  ℹ️  All orders already imported (idempotent re-run)")
        else:
            print(f"  ⚠️  Expected 44 units deducted, got {deducted} — review logs")

        if balance_after == 863:
            print(f"  ✅ Post-backfill balance is 863 — reconciled (3-unit residual is expected)")
        else:
            print(f"  ℹ️  Post-backfill balance: {balance_after} (expected 863 for fresh run)")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
