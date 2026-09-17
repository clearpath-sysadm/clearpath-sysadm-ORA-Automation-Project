#!/usr/bin/env python3
"""
Audit Variant-SKU Order Tagging and Deductions
===============================================

Read-only audit script that:

1. DRY-RUN TAGGING REPORT — fetches all awaiting_shipment orders from
   ShipStation, filters to BigCommerce + variant-SKU items, resolves expected
   CF1 stamp and package count (using the same promo→variant remap pipeline
   and the same reservation-aware lot selection the production tagger uses),
   then prints a diff table.

2. PRE-FIX RECORD SCAN — queries shipped_items and inventory_transactions for
   any rows that used a raw variant_sku (not the resolved base_sku).  Expected
   result is 0 rows.

Exit codes:
  0 — all checks passed (including at least one variant-SKU order evaluated in Part 1)
  1 — issues found, or Part 1 had zero variant-SKU items to evaluate (NOT_EVALUATED)

Usage:
    python3 src/audit_variant_skus.py [--allow-empty]

    --allow-empty   Suppress the NOT_EVALUATED exit-1 when the queue has no
                    variant-SKU orders (useful in off-peak CI runs).
"""

import os
import sys
import logging
import time
import argparse

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

from src.services.database.pg_utils import get_connection
from src.services.shipstation.api_client import (
    get_shipstation_credentials,
    get_shipstation_headers,
)
from src.services.inventory.promo_sku_utils import load_promo_map, load_variant_map
from src.services.inventory import lot_reservation
from src.lot_tagger.tagger import build_lot_maps
from utils.api_utils import make_api_request

SHIPSTATION_ORDERS_URL = 'https://ssapi.shipstation.com/orders'


# ---------------------------------------------------------------------------
# ShipStation helpers
# ---------------------------------------------------------------------------

def fetch_awaiting_shipment_orders(api_key: str, api_secret: str) -> tuple:
    """
    Fetch all awaiting_shipment orders (paginated).

    Returns (all_orders: list, fetch_complete: bool).
    fetch_complete is False if any page failed — callers must treat this as a
    hard error rather than auditing partial data.
    """
    headers = get_shipstation_headers(api_key, api_secret)
    all_orders = []
    page = 1

    while True:
        response = make_api_request(
            url=SHIPSTATION_ORDERS_URL,
            method='GET',
            headers=headers,
            params={'orderStatus': 'awaiting_shipment', 'pageSize': 500, 'page': page},
            timeout=30,
        )
        if not response or response.status_code != 200:
            logger.error(
                f"Failed to fetch orders page {page}: "
                f"{response.status_code if response else 'no response'}"
            )
            return all_orders, False   # incomplete — caller must fail hard

        data = response.json()
        orders = data.get('orders', [])
        all_orders.extend(orders)

        total_pages = data.get('pages', 1)
        logger.info(f"Fetched page {page}/{total_pages}: {len(orders)} orders")

        if page >= total_pages:
            break
        page += 1
        time.sleep(0.5)

    return all_orders, True


def get_v2_package_count(order_id: int) -> int:
    """
    Return the number of V2 packages currently set on the order's shipment.

    Returns:
        >=0  — actual package count
        -1   — PRODUCTION_KEY not set or V2 GET failed (sentinel: unknown)
    """
    production_key = os.getenv('PRODUCTION_KEY')
    if not production_key:
        logger.warning("PRODUCTION_KEY not set — V2 package counts will show as '?'")
        return -1

    shipment_id = f"se-{order_id}"
    url = f"https://api.shipstation.com/v2/shipments/{shipment_id}"
    headers = {'API-Key': production_key, 'Content-Type': 'application/json'}

    resp = make_api_request(url=url, method='GET', headers=headers, timeout=30)
    if not resp or resp.status_code != 200:
        status = resp.status_code if resp else 'no response'
        logger.debug(f"V2 GET for {shipment_id} failed: {status}")
        return -1

    packages = resp.json().get('packages') or []
    return len(packages)


# ---------------------------------------------------------------------------
# SKU resolution helpers — mirrors the production tagger pipeline exactly
# ---------------------------------------------------------------------------

def resolve_order_items(items: list, promo_map: dict, variant_map: dict) -> list:
    """
    Apply the same promo → variant remap + deduplication pipeline used by the
    production lot tagger.  Returns a list of resolved item dicts, each with:
        'raw_sku'            — original SKU from ShipStation
        'base_sku'           — after all remaps
        'item_qty'           — raw order quantity
        'effective_qty'      — item_qty × unit_multiplier (packages)
        'is_variant'         — True if a variant remap was applied
        'unit_multiplier'    — 1 if not a variant SKU

    Steps (same order as tagger):
      1. Promo remap
      2. Promo-dedup (accumulate qty for duplicate SKUs post-promo)
      3. Variant remap + effective_qty
      4. Variant-dedup (accumulate effective_qty for duplicate base SKUs)
    """
    # Step 1 + 2: promo remap and dedup
    seen_promo: dict = {}
    promo_deduped: list = []
    for item in items:
        raw_sku = str(item.get('sku') or '').strip()
        qty = int(item.get('quantity') or 1)
        after_promo = promo_map.get(raw_sku, raw_sku)
        if after_promo in seen_promo:
            seen_promo[after_promo]['item_qty'] += qty
        else:
            entry = {'raw_sku': raw_sku, 'after_promo': after_promo, 'item_qty': qty}
            seen_promo[after_promo] = entry
            promo_deduped.append(entry)

    # Step 3 + 4: variant remap and dedup
    seen_variant: dict = {}
    variant_deduped: list = []
    for entry in promo_deduped:
        after_promo = entry['after_promo']
        item_qty = entry['item_qty']
        variant_entry = variant_map.get(after_promo)
        if variant_entry:
            base_sku = variant_entry['base_sku']
            multiplier = variant_entry['unit_multiplier']
            eff_qty = item_qty * multiplier
            is_variant = True
        else:
            base_sku = after_promo
            multiplier = 1
            eff_qty = item_qty
            is_variant = False

        if base_sku in seen_variant:
            seen_variant[base_sku]['item_qty'] += item_qty
            seen_variant[base_sku]['effective_qty'] += eff_qty
            # Cumulative OR — a merged entry is variant if ANY constituent line
            # was a variant SKU, regardless of which line appeared first.
            if is_variant:
                seen_variant[base_sku]['is_variant'] = True
        else:
            resolved = {
                'raw_sku': entry['raw_sku'],
                'base_sku': base_sku,
                'item_qty': item_qty,
                'effective_qty': eff_qty,
                'is_variant': is_variant,
                'unit_multiplier': multiplier,
            }
            seen_variant[base_sku] = resolved
            variant_deduped.append(resolved)

    return variant_deduped


def pick_expected_lot(
    conn,
    order_id: int,
    base_sku: str,
    expected_packages: int,
    lot_candidates: dict,
    lot_statuses: dict,
) -> tuple:
    """
    Replicate the tagger's reservation-aware lot selection (read-only).

    Mirrors tag_order_lots / reserve_lot_for_order exactly:
      1. Existing OPEN staging reservation for (order_id, base_sku) that is
         still active and has the right quantity → reuse it.
      2. Walk lot_candidates in lot_number order; for each, call
         get_available_balance (real balance minus all other open reservations)
         and return the first with available >= expected_packages.
      3. No candidate qualifies → return (None, 'no_capacity').
         Production records a tagging failure here; the audit flags this order
         rather than falling back to a lesser lot.

    Returns (lot_number: str | None, source: str) where source describes how
    the lot was determined — useful for debugging unexpected CF1 mismatches.
    """
    # 1. Existing valid reservation (read-only query)
    existing = lot_reservation.get_reservation(conn, str(order_id), base_sku)
    if existing:
        res_status = lot_statuses.get((base_sku, existing['lot_number']))
        if res_status == 'active' and existing['reserved_qty'] == expected_packages:
            return existing['lot_number'], 'existing_reservation'
        # Stale reservation (wrong qty or lot no longer active) — fall through

    # 2. Live available balance, same algorithm as reserve_lot_for_order
    candidates = lot_candidates.get(base_sku, [])
    if not candidates:
        return None, 'no_candidates'

    for lot_id, lot_number, _snapshot_balance in candidates:
        available = lot_reservation.get_available_balance(conn, lot_id)
        if available >= expected_packages:
            return lot_number, f'available={available}'

    # 3. No candidate has enough live balance — production would log a tagging failure
    return None, 'no_capacity'


# ---------------------------------------------------------------------------
# Part 1 — Dry-run tagging report
# ---------------------------------------------------------------------------

def run_dry_run_tagging_report(
    conn, api_key: str, api_secret: str, allow_empty: bool
) -> tuple:
    """
    Fetch awaiting_shipment orders, filter to BC + variant-SKU items,
    compare expected vs current CF1 stamp and package count.

    Returns (diff_count: int, evaluated: bool).
    """
    print()
    print("=" * 80)
    print("PART 1 — DRY-RUN TAGGING REPORT (read-only)")
    print("=" * 80)

    promo_map   = load_promo_map(conn)
    variant_map = load_variant_map(conn)

    if not variant_map:
        print("  No active entries in sku_variants — nothing to audit.")
        return 0, False

    print(f"  Loaded {len(promo_map)} promo mapping(s), "
          f"{len(variant_map)} variant mapping(s): {list(variant_map.keys())}")

    active_lots, known_skus, lot_statuses, lot_candidates = build_lot_maps(conn)
    print(f"  Lot maps loaded: {len(active_lots)} SKU(s) with active lots")

    print(f"\n  Fetching awaiting_shipment orders from ShipStation…")
    all_orders, fetch_complete = fetch_awaiting_shipment_orders(api_key, api_secret)
    print(f"  Total awaiting_shipment orders: {len(all_orders)}")

    if not fetch_complete:
        print()
        print("  ERROR: ShipStation order fetch did not complete — partial data cannot")
        print("  be audited (variant orders on unfetched pages would be silently missed).")
        print("  Fix connectivity and re-run.")
        return -1, False   # caller will sys.exit(1)

    # Filter to BigCommerce orders (order_number numeric and >= 801000)
    bc_orders = [
        o for o in all_orders
        if (str(o.get('orderNumber', '')).isdigit()
            and int(o.get('orderNumber', 0)) >= 801000)
    ]
    print(f"  BigCommerce orders: {len(bc_orders)}")

    # Resolve all items through the full promo→variant pipeline.
    # An order qualifies when it has at least one resolved tracked item
    # (base_sku in known_skus) whose is_variant flag is True.
    orders_with_variants = []
    for order in bc_orders:
        resolved_items = resolve_order_items(
            order.get('items', []), promo_map, variant_map
        )
        tracked_items = [r for r in resolved_items if r['base_sku'] in known_skus]
        variant_items = [r for r in tracked_items if r['is_variant']]
        if variant_items:
            orders_with_variants.append((order, tracked_items, variant_items))

    print(f"  BigCommerce orders with variant-SKU items: {len(orders_with_variants)}")

    if not orders_with_variants:
        msg = (
            "  ⚠ NOT EVALUATED — no variant-SKU items found in awaiting_shipment\n"
            "  BigCommerce orders. The comparison logic has not been exercised.\n"
            "  Re-run when a variant-SKU order is in the queue, or use --allow-empty\n"
            "  to suppress this warning."
        )
        print(msg)
        return 0, False

    # Header
    header = (
        f"{'ORDER':>10}  {'VARIANT_SKU':<14}  {'QTY':>4}  {'×':>2}  {'EFF':>4}  "
        f"{'CURRENT_CF1':<32}  {'EXPECTED_CF1':<32}  "
        f"{'CUR_PKG':>7}  {'EXP_PKG':>7}  {'LOT_SRC':<22}  STATUS"
    )
    print()
    print(header)
    print("-" * len(header))

    diff_count = 0

    for order, tracked_items, variant_items in orders_with_variants:
        order_number = order.get('orderNumber', '')
        order_id     = order.get('orderId')

        # Current CF1
        current_cf1 = (
            (order.get('advancedOptions') or {}).get('customField1') or ''
        ).strip()

        # V2 package count is ORDER-LEVEL — fetch once per order
        current_packages = get_v2_package_count(order_id)
        time.sleep(0.25)  # mild rate-limit courtesy

        # Multi-SKU guard: production aborts when >1 distinct *tracked* base
        # SKU is present (variant OR plain).  Check all tracked_items, not
        # just the variant subset — a variant line + a plain tracked SKU is
        # also an error the tagger would have refused to process.
        tracked_base_skus = [r['base_sku'] for r in tracked_items]
        if len(set(tracked_base_skus)) > 1:
            print(
                f"{order_number:>10}  {'(multi-base-sku)':<14}  "
                f"{'—':>4}  {'—':>2}  {'—':>4}  "
                f"{current_cf1:<32}  {'MULTI_SKU_ERROR':<32}  "
                f"{'?':>7}  {'?':>7}  {'—':<22}  multi_sku_error"
            )
            diff_count += 1
            continue

        # Single-base-sku path (normal case — may have multiple variant packs
        # deduped into one entry with accumulated effective_qty)
        resolved = variant_items[0]
        base_sku         = resolved['base_sku']
        raw_sku          = resolved['raw_sku']
        item_qty         = resolved['item_qty']
        expected_packages = resolved['effective_qty']   # order-level
        unit_multiplier  = resolved['unit_multiplier']

        # Reservation-aware lot selection (mirrors production tagger)
        expected_lot, lot_src = pick_expected_lot(
            conn, order_id, base_sku, expected_packages,
            lot_candidates, lot_statuses,
        )

        if expected_lot is None:
            if lot_src == 'no_capacity':
                expected_cf1 = f"{base_sku} - (no capacity)"
                status = "no_capacity"
            else:
                expected_cf1 = f"{base_sku} - (no active lot)"
                status = "no_active_lot"
        else:
            expected_cf1 = f"{base_sku} - {expected_lot}"
            status = None

        # Determine status
        if status is None:
            cf1_match = (current_cf1 == expected_cf1)
            if current_packages < 0:
                pkg_match = None  # unknown (V2 lookup failed)
            else:
                pkg_match = (current_packages == expected_packages)

            if cf1_match and (pkg_match is None or pkg_match):
                status = "correct"
            elif cf1_match and not pkg_match:
                status = "packages_only"
            elif not cf1_match and (pkg_match is None or pkg_match):
                status = "cf1_only"
            else:
                status = "needs_tag"

        if status != "correct":
            diff_count += 1

        pkg_display = str(current_packages) if current_packages >= 0 else "?"

        print(
            f"{order_number:>10}  {raw_sku:<14}  {item_qty:>4}  "
            f"×{unit_multiplier:>1}  {expected_packages:>4}  "
            f"{current_cf1:<32}  {expected_cf1:<32}  "
            f"{pkg_display:>7}  {expected_packages:>7}  {lot_src:<22}  {status}"
        )

    print()
    if diff_count == 0:
        print(f"  RESULT: All {len(orders_with_variants)} variant-SKU order(s) are correctly tagged. ✓")
    else:
        print(f"  RESULT: {diff_count} / {len(orders_with_variants)} variant-SKU order(s) need attention.")

    return diff_count, True


# ---------------------------------------------------------------------------
# Part 2 — Pre-fix record scan
# ---------------------------------------------------------------------------

def run_prefix_record_scan(conn) -> int:
    """
    Scan shipped_items and inventory_transactions for rows recorded with a
    raw variant_sku instead of the resolved base_sku.

    Returns the total number of unexpected rows found.
    """
    print()
    print("=" * 80)
    print("PART 2 — PRE-FIX RECORD SCAN")
    print("=" * 80)

    variant_map = load_variant_map(conn)
    if not variant_map:
        print("  No active sku_variants entries — nothing to scan.")
        return 0

    variant_skus = list(variant_map.keys())
    print(f"  Scanning for raw variant SKUs: {variant_skus}")

    cursor = conn.cursor()
    total_unexpected = 0

    # ── shipped_items ────────────────────────────────────────────────────────
    print()
    print("  shipped_items.base_sku scan:")
    cursor.execute(
        """
        SELECT base_sku, order_number, quantity_shipped, ship_date
          FROM shipped_items
         WHERE base_sku = ANY(%s)
         ORDER BY ship_date, order_number
        """,
        (variant_skus,),
    )
    si_rows = cursor.fetchall()

    if si_rows:
        print(f"    FAIL — {len(si_rows)} unexpected row(s) found:")
        print(f"    {'BASE_SKU':<14}  {'ORDER_NUMBER':<14}  {'QTY':>6}  SHIP_DATE")
        print("    " + "-" * 55)
        for row in si_rows:
            base_sku, order_number, qty, ship_date = row
            print(f"    {base_sku:<14}  {order_number:<14}  {qty:>6}  {ship_date}")

        print()
        print("    -- Corrective SQL (review before applying):")
        for row in si_rows:
            base_sku, order_number, qty, _ = row
            entry     = variant_map[base_sku]
            true_base = entry['base_sku']
            new_qty   = qty * entry['unit_multiplier']
            print(
                f"    UPDATE shipped_items"
                f" SET base_sku = '{true_base}', quantity_shipped = {new_qty}"
                f" WHERE base_sku = '{base_sku}' AND order_number = '{order_number}';"
            )

        total_unexpected += len(si_rows)
    else:
        print("    PASS — 0 rows with raw variant_sku in shipped_items.base_sku ✓")

    # ── inventory_transactions ───────────────────────────────────────────────
    print()
    print("  inventory_transactions.sku scan:")
    cursor.execute(
        """
        SELECT it.sku, it.shipstation_order_id, it.quantity, it.transaction_type, it.date
          FROM inventory_transactions it
         WHERE it.sku = ANY(%s)
              AND it.archived_at IS NULL
         ORDER BY it.date, it.shipstation_order_id
        """,
        (variant_skus,),
    )
    it_rows = cursor.fetchall()

    if it_rows:
        print(f"    FAIL — {len(it_rows)} unexpected row(s) found:")
        print(f"    {'SKU':<14}  {'SS_ORDER_ID':<14}  {'QTY':>6}  {'TYPE':<10}  DATE")
        print("    " + "-" * 65)
        for row in it_rows:
            sku, ss_order_id, qty, txn_type, txn_date = row
            print(f"    {sku:<14}  {str(ss_order_id):<14}  {qty:>6}  {txn_type:<10}  {txn_date}")

        print()
        print("    -- Corrective SQL (review before applying):")
        for row in it_rows:
            sku, ss_order_id, qty, txn_type, _ = row
            entry     = variant_map[sku]
            true_base = entry['base_sku']
            new_qty   = qty * entry['unit_multiplier']
            print(
                f"    UPDATE inventory_transactions"
                f" SET sku = '{true_base}', quantity = {new_qty}"
                f" WHERE sku = '{sku}' AND shipstation_order_id = {ss_order_id}"
                f" AND transaction_type = '{txn_type}';"
            )

        total_unexpected += len(it_rows)
    else:
        print("    PASS — 0 rows with raw variant_sku in inventory_transactions.sku ✓")

    print()
    if total_unexpected == 0:
        print("  RESULT: Pre-fix record scan PASSED — no raw variant-SKU rows found. ✓")
    else:
        print(
            f"  RESULT: Pre-fix record scan FAILED — {total_unexpected} unexpected row(s) found."
        )

    return total_unexpected


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Audit variant-SKU order tagging and inventory deductions (read-only)."
    )
    parser.add_argument(
        '--allow-empty',
        action='store_true',
        help="Exit 0 even when no variant-SKU orders are in the queue (suppresses NOT_EVALUATED).",
    )
    args = parser.parse_args()

    print("Audit Variant-SKU Order Tagging and Deductions")
    print("(Read-only — no writes to ShipStation or database)")

    api_key, api_secret = get_shipstation_credentials()
    if not api_key or not api_secret:
        print("ERROR: Could not retrieve ShipStation credentials.", file=sys.stderr)
        sys.exit(1)

    conn = get_connection()
    try:
        diff_count, evaluated = run_dry_run_tagging_report(
            conn, api_key, api_secret, args.allow_empty
        )
        if diff_count == -1:
            # Hard fetch failure — skip Part 2 and exit immediately
            print()
            print("Aborting: ShipStation fetch was incomplete. See error above.")
            sys.exit(1)
        prefix_count = run_prefix_record_scan(conn)
    finally:
        conn.close()

    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"  Part 1 — Tagging diffs:             {diff_count}")
    print(f"  Part 1 — Variant orders evaluated:  {'yes' if evaluated else 'NO (queue empty)'}")
    print(f"  Part 2 — Pre-fix unexpected DB rows: {prefix_count}")

    issues = diff_count > 0 or prefix_count > 0
    not_evaluated = not evaluated and not args.allow_empty

    if not issues and not not_evaluated:
        print("  Overall: ALL CHECKS PASSED ✓")
        sys.exit(0)
    else:
        if not_evaluated:
            print("  Overall: NOT EVALUATED — re-run when variant-SKU orders are in the queue.")
        else:
            print("  Overall: ISSUES FOUND — see details above.")
        sys.exit(1)


if __name__ == '__main__':
    main()
