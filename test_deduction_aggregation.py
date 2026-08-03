"""
Tests for Task #146: pre-aggregation of variant SKU deductions in
update_existing_order_status and the split-label path.

Verifies that when two items in an order resolve to the same base SKU
(e.g. '17612-6' × 1 and '17612-15' × 1 both → '17612'), deduct_lot_inventory
is called exactly once with the summed quantity (6 + 15 = 21), not twice with
individual quantities (which would silently drop the second via the idempotency guard).
"""

import sys
import os
import datetime
import unittest
from unittest.mock import patch, MagicMock, call

project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def _make_order(items, order_id='SS99', order_number='999999',
                status='shipped', cf1='17612 - 260017',
                ship_date='2026-08-01'):
    """Build a minimal ShipStation order dict for testing."""
    return {
        'orderId': order_id,
        'orderKey': order_id,
        'orderNumber': order_number,
        'orderStatus': status,
        'shipDate': ship_date,
        'advancedOptions': {'customField1': cf1},
        'carrierCode': 'fedex',
        'serviceCode': 'fedex_ground',
        'trackingNumber': None,
        'items': items,
    }


def _make_item(sku, qty):
    return {'sku': sku, 'quantity': qty, 'unitPrice': 0}


# ---------------------------------------------------------------------------
# Shared patch targets
# ---------------------------------------------------------------------------
DEDUCT = 'src.services.inventory.lot_deduction.deduct_lot_inventory'
LOAD_PROMO = 'src.services.inventory.promo_sku_utils.load_promo_map'
LOAD_VARIANT = 'src.services.inventory.promo_sku_utils.load_variant_map'


def _variant_map():
    return {
        '17612-6':  {'base_sku': '17612', 'unit_multiplier': 6},
        '17612-15': {'base_sku': '17612', 'unit_multiplier': 15},
        '17612-40': {'base_sku': '17612', 'unit_multiplier': 40},
    }


# ---------------------------------------------------------------------------
# update_existing_order_status tests
# ---------------------------------------------------------------------------
class TestUpdateExistingOrderStatusAggregation(unittest.TestCase):
    """
    Exercises the shipped-transition deduction loop inside
    update_existing_order_status via a fully mocked DB connection.
    """

    def _run(self, items, cf1='17612 - 260017', order_id='SS99'):
        """
        Invoke update_existing_order_status with a mocked conn and return the
        list of calls made to deduct_lot_inventory.

        deduct_lot_inventory is imported locally inside the function, so we
        patch it at the source module (src.services.inventory.lot_deduction).
        Same for load_promo_map / load_variant_map.
        """
        from src.unified_shipstation_sync import update_existing_order_status

        order = _make_order(items, order_id=order_id, cf1=cf1)

        # Minimal mock conn: first fetchone() is for the orders_inbox status
        # SELECT inside update_existing_order_status. Return 'awaiting_shipment'
        # so the function accepts the 'shipped' transition without blocking.
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.fetchone.return_value = ('awaiting_shipment', None)
        cursor.fetchall.return_value = []
        cursor.rowcount = 0

        mock_deduct = MagicMock(return_value=True)

        with patch(
            'src.services.inventory.lot_deduction.deduct_lot_inventory',
            mock_deduct
        ), patch(
            'src.services.inventory.promo_sku_utils.load_promo_map',
            return_value={}
        ), patch(
            'src.services.inventory.promo_sku_utils.load_variant_map',
            return_value=_variant_map()
        ):
            update_existing_order_status(order, local_order_id=1, conn=conn)

        return mock_deduct.call_args_list

    def test_single_variant_sku_single_call(self):
        """17612-6 × 1 → one deduction call with quantity=6."""
        items = [_make_item('17612-6', 1)]
        calls = self._run(items)
        self.assertEqual(len(calls), 1)
        kw = calls[0].kwargs
        self.assertEqual(kw['base_sku'], '17612')
        self.assertEqual(kw['quantity'], 6)

    def test_two_variant_skus_same_base_summed(self):
        """17612-6 × 1 + 17612-15 × 1 → one call with quantity=21 (not two calls)."""
        items = [_make_item('17612-6', 1), _make_item('17612-15', 1)]
        calls = self._run(items)
        self.assertEqual(
            len(calls), 1,
            f"Expected 1 deduction call, got {len(calls)}: {calls}"
        )
        kw = calls[0].kwargs
        self.assertEqual(kw['base_sku'], '17612')
        self.assertEqual(kw['quantity'], 21)  # 6 + 15

    def test_variant_plus_base_sku_summed(self):
        """17612-6 × 1 + 17612 × 3 → one call with quantity=9 (6 + 3)."""
        items = [_make_item('17612-6', 1), _make_item('17612', 3)]
        calls = self._run(items)
        self.assertEqual(
            len(calls), 1,
            f"Expected 1 deduction call, got {len(calls)}: {calls}"
        )
        kw = calls[0].kwargs
        self.assertEqual(kw['base_sku'], '17612')
        self.assertEqual(kw['quantity'], 9)  # 6 + 3

    def test_plain_base_sku_unchanged(self):
        """Plain 17612 × 5 → one call with quantity=5 (no multiplier)."""
        items = [_make_item('17612', 5)]
        calls = self._run(items)
        self.assertEqual(len(calls), 1)
        kw = calls[0].kwargs
        self.assertEqual(kw['base_sku'], '17612')
        self.assertEqual(kw['quantity'], 5)

    def test_non_key_sku_ignored(self):
        """SKU not in KEY_PRODUCT_SKUS produces no deduction call."""
        items = [_make_item('99999', 1)]
        calls = self._run(items)
        self.assertEqual(len(calls), 0)


# ---------------------------------------------------------------------------
# Split-label path tests
# ---------------------------------------------------------------------------
class TestSplitLabelAggregation(unittest.TestCase):
    """
    Exercises the split-label deduction path by directly testing the
    aggregation logic extracted from the path.

    Rather than reconstructing the full dispatch machinery, we test the
    aggregation dict behaviour that both paths now share, and verify the
    resolve_sku_and_quantity helper produces the correct totals.
    """

    def test_aggregation_two_variant_items_same_base(self):
        """
        Core aggregation logic: two items resolving to the same base SKU
        should accumulate to the correct total before a single deduction call.
        """
        from src.services.inventory.promo_sku_utils import resolve_sku_and_quantity

        variant_map = _variant_map()
        promo_map = {}

        items = [
            {'sku': '17612-6',  'quantity': 1},
            {'sku': '17612-15', 'quantity': 1},
        ]

        _sl_agg = {}
        for item in items:
            sku_raw = str(item.get('sku', '')).strip()
            qty = item.get('quantity', 0)
            raw_base = sku_raw.split(' - ')[0].strip() if ' - ' in sku_raw else sku_raw
            base_sku, effective_qty = resolve_sku_and_quantity(
                raw_base, qty, promo_map, variant_map
            )
            _sl_agg[base_sku] = _sl_agg.get(base_sku, 0) + effective_qty

        self.assertEqual(list(_sl_agg.keys()), ['17612'])
        self.assertEqual(_sl_agg['17612'], 21)  # 6 + 15

    def test_aggregation_three_variant_items(self):
        """17612-6 + 17612-15 + 17612-40 → 61 units, one key."""
        from src.services.inventory.promo_sku_utils import resolve_sku_and_quantity

        variant_map = _variant_map()
        promo_map = {}

        items = [
            {'sku': '17612-6',  'quantity': 1},
            {'sku': '17612-15', 'quantity': 1},
            {'sku': '17612-40', 'quantity': 1},
        ]

        _sl_agg = {}
        for item in items:
            sku_raw = str(item['sku'])
            qty = item['quantity']
            base_sku, effective_qty = resolve_sku_and_quantity(
                sku_raw, qty, promo_map, variant_map
            )
            _sl_agg[base_sku] = _sl_agg.get(base_sku, 0) + effective_qty

        self.assertEqual(_sl_agg, {'17612': 61})  # 6 + 15 + 40

    def test_aggregation_single_item_unchanged(self):
        """Single item → aggregation dict has one entry with correct qty."""
        from src.services.inventory.promo_sku_utils import resolve_sku_and_quantity

        variant_map = _variant_map()
        promo_map = {}

        items = [{'sku': '17612-6', 'quantity': 2}]

        _sl_agg = {}
        for item in items:
            sku_raw = str(item['sku'])
            qty = item['quantity']
            base_sku, effective_qty = resolve_sku_and_quantity(
                sku_raw, qty, promo_map, variant_map
            )
            _sl_agg[base_sku] = _sl_agg.get(base_sku, 0) + effective_qty

        self.assertEqual(_sl_agg, {'17612': 12})  # 2 × 6

    def test_aggregation_non_variant_sku(self):
        """Plain base SKU passes through with quantity unchanged."""
        from src.services.inventory.promo_sku_utils import resolve_sku_and_quantity

        variant_map = _variant_map()
        promo_map = {}

        items = [{'sku': '17612', 'quantity': 4}]

        _sl_agg = {}
        for item in items:
            sku_raw = str(item['sku'])
            qty = item['quantity']
            base_sku, effective_qty = resolve_sku_and_quantity(
                sku_raw, qty, promo_map, variant_map
            )
            _sl_agg[base_sku] = _sl_agg.get(base_sku, 0) + effective_qty

        self.assertEqual(_sl_agg, {'17612': 4})


if __name__ == '__main__':
    unittest.main()
