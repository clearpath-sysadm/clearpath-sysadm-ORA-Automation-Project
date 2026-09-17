#!/usr/bin/env python3
"""
Post-Shipment Verification for Variant-SKU Deductions (Task #144)
=================================================================

Run this script after the 08/03/2026 test orders (864770–864783) have shipped
to verify that Task #146's deduction fix is working correctly end-to-end.

Expected deductions per order (computed from ShipStation item data):
  864770 SS=309078923  17904-6 qty=1          → 17904 deduct 6
  864771 SS=309078931  17612-6 qty=2          → 17612 deduct 12
  864772 SS=309078925  17612-6+17612-15 qty=1 → 17612 deduct 21
  864773 SS=309078929  17612-6+17612-40 qty=1 → 17612 deduct 46
  864774 SS=309078955  17612-6 qty=2 + 17612-15 qty=1 → 17612 deduct 27
  864777 SS=309078942  17612-6 qty=1 (17612-1-1 unrecognized, no deduction) → 17612 deduct 6
  864778 SS=309078943  17612-15 qty=1 (17612-1-1 unrecognized) → 17612 deduct 15
  864780 SS=309078952  17904-6 qty=1          → 17904 deduct 6
  864781 SS=309078960  17612-6 qty=1          → 17612 deduct 6

Usage:
    python3 src/verify_variant_deductions.py
"""

import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.services.database.pg_utils import get_connection

# Expected deductions: (order_number, ss_order_id, base_sku, expected_qty, note)
EXPECTED = [
    ('864770', '309078923', '17904', 6,  '17904-6 qty=1'),
    ('864771', '309078931', '17612', 12, '17612-6 qty=2'),
    ('864772', '309078925', '17612', 21, '17612-6 qty=1 + 17612-15 qty=1'),
    ('864773', '309078929', '17612', 46, '17612-6 qty=1 + 17612-40 qty=1'),
    ('864774', '309078955', '17612', 27, '17612-6 qty=2 + 17612-15 qty=1'),
    ('864777', '309078942', '17612', 6,  '17612-6 qty=1 (17612-1-1 silently dropped — Task #151)'),
    ('864778', '309078943', '17612', 15, '17612-15 qty=1 (17612-1-1 silently dropped — Task #151)'),
    ('864780', '309078952', '17904', 6,  '17904-6 qty=1'),
    ('864781', '309078960', '17612', 6,  '17612-6 qty=1'),
]

PASS_SYMBOL = '✓'
FAIL_SYMBOL = '✗'
SKIP_SYMBOL = '~'


def check_order(cursor, order_number, ss_order_id, base_sku, expected_qty, note):
    """Check a single order's deduction records. Returns (status, details)."""

    # 1. Check inventory_transactions
    cursor.execute(
        """
        SELECT sku, quantity, transaction_type
          FROM inventory_transactions
         WHERE shipstation_order_id = %s
           AND sku = %s
           AND transaction_type = 'deduction'
              AND archived_at IS NULL
        """,
        (ss_order_id, base_sku),
    )
    it_rows = cursor.fetchall()

    # 2. Check shipped_items
    cursor.execute(
        """
        SELECT base_sku, quantity_shipped
          FROM shipped_items
         WHERE order_number = %s
           AND base_sku = %s
        """,
        (order_number, base_sku),
    )
    si_rows = cursor.fetchall()

    # 3. Check lot_staging_reservations
    cursor.execute(
        """
        SELECT state, lot_id, lot_number, reserved_qty
          FROM lot_staging_reservations
         WHERE shipstation_order_id = %s
           AND sku = %s
        """,
        (ss_order_id, base_sku),
    )
    lsr_rows = cursor.fetchall()

    issues = []
    passed = []

    # Evaluate inventory_transactions
    if not it_rows:
        issues.append(f'inventory_transactions: NO deduction row found (expected qty=-{expected_qty})')
    else:
        total_it_qty = sum(abs(r[1]) for r in it_rows)
        if total_it_qty != expected_qty:
            issues.append(
                f'inventory_transactions: qty mismatch — got {total_it_qty}, expected {expected_qty}'
            )
        else:
            passed.append(f'inventory_transactions: qty={-expected_qty} ✓')

        for r in it_rows:
            if r[0] != base_sku:
                issues.append(
                    f'inventory_transactions: sku is {r[0]!r}, expected {base_sku!r}'
                )

    # Evaluate shipped_items
    if not si_rows:
        issues.append(f'shipped_items: NO row found for order {order_number} / sku {base_sku}')
    else:
        total_si_qty = sum(r[1] for r in si_rows)
        if total_si_qty != expected_qty:
            issues.append(
                f'shipped_items: qty mismatch — got {total_si_qty}, expected {expected_qty}'
            )
        else:
            passed.append(f'shipped_items: quantity_shipped={expected_qty} ✓')

    # Evaluate lot_staging_reservations
    if not lsr_rows:
        issues.append(
            f'lot_staging_reservations: NO row found — reservation may predate system '
            f'(unexpected for these test orders)'
        )
    else:
        for r in lsr_rows:
            state = r[0]
            if state != 'consumed':
                issues.append(
                    f'lot_staging_reservations: state={state!r}, expected "consumed" — '
                    f'consume_reservation() may not have been called'
                )
            else:
                passed.append(
                    f'lot_staging_reservations: state=consumed (lot={r[2]}, reserved_qty={r[3]}) ✓'
                )

    return issues, passed


def main():
    print('Variant-SKU Deduction Verification (Task #144)')
    print('=' * 70)

    with get_connection() as conn:
        cursor = conn.cursor()

        total_pass = 0
        total_fail = 0
        total_skip = 0

        for (order_number, ss_order_id, base_sku, expected_qty, note) in EXPECTED:
            # First check if the order has shipped at all
            cursor.execute(
                "SELECT status FROM orders_inbox WHERE order_number = %s",
                (order_number,),
            )
            row = cursor.fetchone()
            if not row or row[0] != 'shipped':
                status_str = row[0] if row else 'not in DB'
                print(
                    f'{SKIP_SYMBOL} Order {order_number} (SS={ss_order_id}): '
                    f'SKIPPED — status={status_str!r} (not yet shipped)'
                )
                total_skip += 1
                continue

            issues, passed = check_order(
                cursor, order_number, ss_order_id, base_sku, expected_qty, note
            )

            if issues:
                print(f'{FAIL_SYMBOL} Order {order_number} (SS={ss_order_id}) | {note}')
                for issue in issues:
                    print(f'    FAIL: {issue}')
                for p in passed:
                    print(f'    PASS: {p}')
                total_fail += 1
            else:
                print(f'{PASS_SYMBOL} Order {order_number} (SS={ss_order_id}) | {note}')
                for p in passed:
                    print(f'    {p}')
                total_pass += 1

        print()
        print('=' * 70)
        print(f'Results: {total_pass} PASS  |  {total_fail} FAIL  |  {total_skip} SKIPPED (not shipped)')

        if total_fail > 0:
            print('RESULT: FAILED — see issues above')
            sys.exit(1)
        elif total_pass == 0 and total_skip > 0:
            print('RESULT: NO ORDERS SHIPPED YET — re-run after orders ship')
            sys.exit(2)
        else:
            print('RESULT: ALL SHIPPED ORDERS PASSED ✓')
            sys.exit(0)


if __name__ == '__main__':
    main()
