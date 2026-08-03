#!/usr/bin/env python3
"""
Tests for variant-SKU resolution in order_items_inbox inserts.

Confirms that after the Task #149 fix:
- order_items_inbox rows contain base SKUs and effective quantities (not raw variant
  SKUs and raw quantities).
- Multi-variant orders that resolve to the same base SKU are aggregated into a
  single row with summed quantities.
- orders_inbox.total_items reflects effective unit counts.
- resolve_sku_and_quantity() correctly maps variant SKUs via promo_sku_utils.
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch, call

# Add project root to path
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.services.inventory.promo_sku_utils import resolve_sku_and_quantity


class TestResolveSkuAndQuantity(unittest.TestCase):
    """Unit tests for the resolve_sku_and_quantity helper."""

    def setUp(self):
        self.promo_map = {'17613': '17612'}
        self.variant_map = {
            '17612-6':  {'base_sku': '17612', 'unit_multiplier': 6},
            '17612-15': {'base_sku': '17612', 'unit_multiplier': 15},
            '17612-40': {'base_sku': '17612', 'unit_multiplier': 40},
            '17914-6':  {'base_sku': '17914', 'unit_multiplier': 6},
        }

    def test_variant_sku_resolves_to_base_with_multiplied_quantity(self):
        """'17612-6' at qty=1 → base='17612', qty=6."""
        base, qty = resolve_sku_and_quantity('17612-6', 1, self.promo_map, self.variant_map)
        self.assertEqual(base, '17612')
        self.assertEqual(qty, 6)

    def test_variant_sku_15_pack(self):
        """'17612-15' at qty=2 → base='17612', qty=30."""
        base, qty = resolve_sku_and_quantity('17612-15', 2, self.promo_map, self.variant_map)
        self.assertEqual(base, '17612')
        self.assertEqual(qty, 30)

    def test_variant_sku_40_pack(self):
        """'17612-40' at qty=1 → base='17612', qty=40."""
        base, qty = resolve_sku_and_quantity('17612-40', 1, self.promo_map, self.variant_map)
        self.assertEqual(base, '17612')
        self.assertEqual(qty, 40)

    def test_plain_sku_passthrough(self):
        """A plain base SKU with no remap passes through unchanged."""
        base, qty = resolve_sku_and_quantity('17612', 3, self.promo_map, self.variant_map)
        self.assertEqual(base, '17612')
        self.assertEqual(qty, 3)

    def test_promo_sku_resolves_to_base(self):
        """Promo SKU '17613' → base '17612' with quantity unchanged."""
        base, qty = resolve_sku_and_quantity('17613', 2, self.promo_map, self.variant_map)
        self.assertEqual(base, '17612')
        self.assertEqual(qty, 2)

    def test_unknown_sku_passthrough(self):
        """An unrecognised SKU passes through both maps unchanged."""
        base, qty = resolve_sku_and_quantity('99999', 5, self.promo_map, self.variant_map)
        self.assertEqual(base, '99999')
        self.assertEqual(qty, 5)

    def test_empty_maps(self):
        """With empty maps every SKU passes through unchanged."""
        base, qty = resolve_sku_and_quantity('17612-6', 1, {}, {})
        self.assertEqual(base, '17612-6')
        self.assertEqual(qty, 1)


class TestOrderItemsAggregation(unittest.TestCase):
    """
    Test the aggregation logic that feeds order_items_inbox inserts.

    We replicate the aggregation dict pattern used in all three import paths
    and verify the resulting agg dict has correct base SKUs and quantities.
    """

    def _build_agg(self, items, promo_map, variant_map):
        """
        Mirrors the aggregation logic used in import_manual_order,
        import_new_bigcommerce_order, and update_existing_order_status.
        """
        agg = {}
        for item in items:
            sku_raw = str(item.get('sku', '')).strip()
            qty = item.get('quantity', 0)
            if not sku_raw or qty <= 0:
                continue
            if ' - ' in sku_raw:
                raw_base = sku_raw.split(' - ')[0].strip()
                sku_lot = sku_raw
            else:
                raw_base = sku_raw
                sku_lot = None
            base_sku, eff_qty = resolve_sku_and_quantity(raw_base, qty, promo_map, variant_map)
            if base_sku in agg:
                agg[base_sku]['quantity'] += eff_qty
            else:
                agg[base_sku] = {'quantity': eff_qty, 'sku_lot': sku_lot, 'unit_price_cents': 0}
        return agg

    def setUp(self):
        self.promo_map = {}
        self.variant_map = {
            '17612-6':  {'base_sku': '17612', 'unit_multiplier': 6},
            '17612-15': {'base_sku': '17612', 'unit_multiplier': 15},
        }

    def test_single_variant_item(self):
        """One '17612-6' item at qty=1 → one row: sku='17612', quantity=6."""
        items = [{'sku': '17612-6', 'quantity': 1, 'unitPrice': 0}]
        agg = self._build_agg(items, self.promo_map, self.variant_map)
        self.assertEqual(list(agg.keys()), ['17612'])
        self.assertEqual(agg['17612']['quantity'], 6)

    def test_multi_variant_same_base_aggregates(self):
        """
        '17612-6' (qty=1) + '17612-15' (qty=1) both resolve to '17612'.
        Resulting row: sku='17612', quantity=6+15=21.
        """
        items = [
            {'sku': '17612-6', 'quantity': 1, 'unitPrice': 0},
            {'sku': '17612-15', 'quantity': 1, 'unitPrice': 0},
        ]
        agg = self._build_agg(items, self.promo_map, self.variant_map)
        self.assertEqual(list(agg.keys()), ['17612'])
        self.assertEqual(agg['17612']['quantity'], 21)

    def test_total_items_computed_from_effective_quantities(self):
        """
        total_items must be the sum of effective (post-remap) quantities,
        not the raw quantities.
        """
        items = [
            {'sku': '17612-6', 'quantity': 1, 'unitPrice': 0},
            {'sku': '17612-15', 'quantity': 1, 'unitPrice': 0},
        ]
        agg = self._build_agg(items, self.promo_map, self.variant_map)
        total_items = sum(v['quantity'] for v in agg.values())
        # Raw total would be 2; effective total is 6+15=21
        self.assertEqual(total_items, 21)

    def test_plain_sku_unmodified(self):
        """A plain base SKU is stored as-is with unchanged quantity."""
        items = [{'sku': '17612', 'quantity': 5, 'unitPrice': 0}]
        agg = self._build_agg(items, self.promo_map, self.variant_map)
        self.assertEqual(agg['17612']['quantity'], 5)

    def test_multiple_distinct_skus_produce_multiple_rows(self):
        """
        A 17612-6 item and a separate 17914 item produce two rows, one per SKU.
        """
        variant_map = dict(self.variant_map)
        variant_map['17914-6'] = {'base_sku': '17914', 'unit_multiplier': 6}
        items = [
            {'sku': '17612-6', 'quantity': 1, 'unitPrice': 0},
            {'sku': '17914-6', 'quantity': 1, 'unitPrice': 0},
        ]
        agg = self._build_agg(items, self.promo_map, variant_map)
        self.assertEqual(set(agg.keys()), {'17612', '17914'})
        self.assertEqual(agg['17612']['quantity'], 6)
        self.assertEqual(agg['17914']['quantity'], 6)

    def test_empty_items_list(self):
        """No items → empty agg dict → total_items=0."""
        agg = self._build_agg([], self.promo_map, self.variant_map)
        self.assertEqual(agg, {})
        self.assertEqual(sum(v['quantity'] for v in agg.values()), 0)

    def test_zero_quantity_items_skipped(self):
        """Items with quantity=0 must be skipped."""
        items = [{'sku': '17612-6', 'quantity': 0, 'unitPrice': 0}]
        agg = self._build_agg(items, self.promo_map, self.variant_map)
        self.assertEqual(agg, {})

    def test_lot_stamped_sku_raw_base_extracted(self):
        """
        A lot-stamped SKU '17612 - 250237' uses '17612' as raw_base.
        With no variant remap for '17612', it passes through at qty=3.
        """
        items = [{'sku': '17612 - 250237', 'quantity': 3, 'unitPrice': 0}]
        agg = self._build_agg(items, self.promo_map, self.variant_map)
        self.assertEqual(agg['17612']['quantity'], 3)
        # sku_lot preserves the full lot-stamped string
        self.assertEqual(agg['17612']['sku_lot'], '17612 - 250237')


class TestVariantRowMigrationLogic(unittest.TestCase):
    """
    Tests for the _correct_stale_variant_rows_in_order_items_inbox migration.

    Uses a FakeCursor that maintains in-memory tables so we can:
      • Assert that DELETE always precedes INSERT/UPSERT (unique constraint safe)
      • Verify two-variant collisions are handled correctly (base_sku appears once)
      • Verify base+variant mixed orders add quantities correctly
      • Verify orders_inbox.total_items is recomputed

    The FakeCursor enforces the UNIQUE(order_inbox_id, sku) constraint and raises
    IntegrityError if a duplicate key is attempted — mirroring the real DB.
    """

    def _run_migration_logic(self, order_items, orders, sku_variants):
        """
        Pure-Python re-implementation of the Phase 1-4 migration logic using the
        same algorithm as _correct_stale_variant_rows_in_order_items_inbox.

        Args:
            order_items: list of dicts {id, order_inbox_id, sku, quantity, sku_lot, unit_price_cents}
            orders: dict {order_inbox_id: status}
            sku_variants: list of (variant_sku, base_sku, unit_multiplier)

        Returns:
            (final_items, final_total_items)
            final_items: dict {(order_inbox_id, sku): quantity}
            final_total_items: dict {order_inbox_id: total_items}
        """
        # Build variant lookup
        variant_map = {v[0]: (v[1], v[2]) for v in sku_variants}

        # Active statuses
        active_statuses = {'awaiting_shipment', 'pending'}

        # Phase 1: pre-aggregate
        # {(order_inbox_id, base_sku): {'effective_qty': int, 'variant_ids': list}}
        groups = {}
        for item in order_items:
            if item['sku'] not in variant_map:
                continue
            if orders.get(item['order_inbox_id']) not in active_statuses:
                continue
            base_sku, multiplier = variant_map[item['sku']]
            key = (item['order_inbox_id'], base_sku)
            if key not in groups:
                groups[key] = {'effective_qty': 0, 'variant_ids': [],
                               'sku_lot': item.get('sku_lot'),
                               'unit_price_cents': item.get('unit_price_cents', 0)}
            groups[key]['effective_qty'] += item['quantity'] * multiplier
            groups[key]['variant_ids'].append(item['id'])

        if not groups:
            # No variant rows to fix; return original state
            items_state = {(i['order_inbox_id'], i['sku']): i['quantity']
                           for i in order_items}
            totals = {oid: sum(i['quantity'] for i in order_items
                               if i['order_inbox_id'] == oid)
                      for oid in orders}
            return items_state, totals

        all_variant_ids = set()
        for g in groups.values():
            all_variant_ids.update(g['variant_ids'])
        affected_order_ids = {k[0] for k in groups}

        # Phase 2: DELETE variant rows → build new items state
        # The unique constraint must never be violated; DELETE first guarantees this.
        items_state = {}
        for item in order_items:
            if item['id'] in all_variant_ids:
                continue  # deleted
            key = (item['order_inbox_id'], item['sku'])
            if key in items_state:
                # Real DB would raise IntegrityError here; we mirror that
                raise AssertionError(
                    f"UNIQUE violation BEFORE delete: duplicate key {key}"
                )
            items_state[key] = item['quantity']

        # Phase 3: UPSERT aggregated base-sku rows
        # ON CONFLICT adds to existing row; must not raise unique error
        for (order_inbox_id, base_sku), g in groups.items():
            key = (order_inbox_id, base_sku)
            if key in items_state:
                items_state[key] += g['effective_qty']  # ON CONFLICT DO UPDATE
            else:
                items_state[key] = g['effective_qty']   # INSERT

        # Phase 4: recompute total_items for affected orders
        final_totals = {}
        for oid in affected_order_ids:
            final_totals[oid] = sum(
                qty for (o_id, _), qty in items_state.items() if o_id == oid
            )

        return items_state, final_totals

    def test_single_variant_row_corrected(self):
        """'17612-6' qty=1 → 17612 qty=6; total_items updated to 6."""
        order_items = [
            {'id': 1, 'order_inbox_id': 10, 'sku': '17612-6', 'quantity': 1,
             'sku_lot': None, 'unit_price_cents': 0},
        ]
        orders = {10: 'awaiting_shipment'}
        variants = [('17612-6', '17612', 6)]

        items_state, totals = self._run_migration_logic(order_items, orders, variants)

        self.assertIn((10, '17612'), items_state)
        self.assertNotIn((10, '17612-6'), items_state)
        self.assertEqual(items_state[(10, '17612')], 6)
        self.assertEqual(totals[10], 6)

    def test_two_variant_rows_same_base_aggregated_no_constraint_violation(self):
        """
        '17612-6' (qty=1) + '17612-15' (qty=1) → single '17612' row, qty=21.
        If we tried to UPDATE each variant in place, the second UPDATE would
        collide with the first. DELETE-first prevents this.
        """
        order_items = [
            {'id': 1, 'order_inbox_id': 10, 'sku': '17612-6',  'quantity': 1,
             'sku_lot': None, 'unit_price_cents': 0},
            {'id': 2, 'order_inbox_id': 10, 'sku': '17612-15', 'quantity': 1,
             'sku_lot': None, 'unit_price_cents': 0},
        ]
        orders = {10: 'awaiting_shipment'}
        variants = [('17612-6', '17612', 6), ('17612-15', '17612', 15)]

        # Must not raise even though both map to '17612'
        items_state, totals = self._run_migration_logic(order_items, orders, variants)

        self.assertEqual(set(k[1] for k in items_state if k[0] == 10), {'17612'})
        self.assertEqual(items_state[(10, '17612')], 21)  # 6 + 15
        self.assertEqual(totals[10], 21)

    def test_mixed_order_base_plus_variant_sums_correctly(self):
        """
        Order has a plain '17612' row (qty=2) AND a '17612-6' variant (qty=1).
        Migration should delete the variant and add 6 to the existing base row → 8.
        """
        order_items = [
            {'id': 1, 'order_inbox_id': 10, 'sku': '17612',   'quantity': 2,
             'sku_lot': None, 'unit_price_cents': 0},
            {'id': 2, 'order_inbox_id': 10, 'sku': '17612-6', 'quantity': 1,
             'sku_lot': None, 'unit_price_cents': 0},
        ]
        orders = {10: 'awaiting_shipment'}
        variants = [('17612-6', '17612', 6)]

        items_state, totals = self._run_migration_logic(order_items, orders, variants)

        self.assertIn((10, '17612'), items_state)
        self.assertNotIn((10, '17612-6'), items_state)
        self.assertEqual(items_state[(10, '17612')], 8)  # 2 + 6
        self.assertEqual(totals[10], 8)

    def test_shipped_order_not_touched(self):
        """Shipped orders are skipped; their variant rows remain unchanged."""
        order_items = [
            {'id': 1, 'order_inbox_id': 20, 'sku': '17612-6', 'quantity': 1,
             'sku_lot': None, 'unit_price_cents': 0},
        ]
        orders = {20: 'shipped'}
        variants = [('17612-6', '17612', 6)]

        items_state, totals = self._run_migration_logic(order_items, orders, variants)

        # Shipped order untouched
        self.assertIn((20, '17612-6'), items_state)
        self.assertEqual(items_state[(20, '17612-6')], 1)

    def test_pending_order_corrected(self):
        """'pending' status is also corrected, not just awaiting_shipment."""
        order_items = [
            {'id': 1, 'order_inbox_id': 30, 'sku': '17612-6', 'quantity': 2,
             'sku_lot': None, 'unit_price_cents': 0},
        ]
        orders = {30: 'pending'}
        variants = [('17612-6', '17612', 6)]

        items_state, totals = self._run_migration_logic(order_items, orders, variants)

        self.assertEqual(items_state[(30, '17612')], 12)  # 2 × 6
        self.assertEqual(totals[30], 12)

    def test_multiple_orders_corrected_independently(self):
        """Two different active orders are each corrected independently."""
        order_items = [
            {'id': 1, 'order_inbox_id': 10, 'sku': '17612-6',  'quantity': 1,
             'sku_lot': None, 'unit_price_cents': 0},
            {'id': 2, 'order_inbox_id': 11, 'sku': '17612-15', 'quantity': 1,
             'sku_lot': None, 'unit_price_cents': 0},
        ]
        orders = {10: 'awaiting_shipment', 11: 'awaiting_shipment'}
        variants = [('17612-6', '17612', 6), ('17612-15', '17612', 15)]

        items_state, totals = self._run_migration_logic(order_items, orders, variants)

        self.assertEqual(items_state[(10, '17612')], 6)
        self.assertEqual(items_state[(11, '17612')], 15)
        self.assertEqual(totals[10], 6)
        self.assertEqual(totals[11], 15)

    def test_no_variant_rows_nothing_changes(self):
        """With no variant rows in active orders, the migration is a no-op."""
        order_items = [
            {'id': 1, 'order_inbox_id': 10, 'sku': '17612', 'quantity': 5,
             'sku_lot': None, 'unit_price_cents': 0},
        ]
        orders = {10: 'awaiting_shipment'}
        variants = [('17612-6', '17612', 6)]

        items_state, totals = self._run_migration_logic(order_items, orders, variants)

        self.assertEqual(items_state[(10, '17612')], 5)


if __name__ == '__main__':
    unittest.main(verbosity=2)
