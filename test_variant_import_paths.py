"""
Path-level integration tests for variant SKU shipped-order imports (Task #138).

Verifies that both the manual-order and BigCommerce import paths write the
correct base_sku and quantity_shipped to shipped_items when a variant SKU
(e.g. '17612-6' at qty=1) is processed.

Each test runs inside a rolled-back transaction so it cannot corrupt real data.
deduct_lot_inventory is patched to prevent lot-balance side-effects; the tests
focus on what gets persisted to shipped_items.
"""

import datetime
import pytest
from unittest.mock import patch

from src.services.database.pg_utils import get_connection
from src.unified_shipstation_sync import import_new_manual_order, import_new_bigcommerce_order


# ---------------------------------------------------------------------------
# Minimal fake ShipStation order factories
# ---------------------------------------------------------------------------

def _manual_order(order_number: str, ss_order_id: int, sku: str, qty: int,
                  cf1: str = '') -> dict:
    """Build a minimal shipped manual order dict."""
    return {
        'orderNumber': order_number,
        'orderId': ss_order_id,
        'orderStatus': 'shipped',
        'orderDate': '2026-01-15T10:00:00',
        'shipDate': '2026-01-15',
        'customerEmail': 'test@example.com',
        'orderTotal': 0,
        'items': [{'sku': sku, 'quantity': qty, 'unitPrice': 0}],
        'shipTo': {'name': 'Test', 'street1': '1 Main St', 'city': 'Portland',
                   'state': 'OR', 'postalCode': '97201', 'country': 'US'},
        'billTo': {},
        'carrierCode': 'fedex',
        'serviceCode': 'fedex_ground',
        'packageCode': 'package',
        'weight': {'value': 0, 'units': 'ounces'},
        'dimensions': {},
        'advancedOptions': {'customField1': cf1},
        'tagIds': [],
    }


def _bc_order(order_number: str, ss_order_id: int, sku: str, qty: int,
              cf1: str = '') -> dict:
    """Build a minimal shipped BigCommerce order dict."""
    return {
        'orderNumber': order_number,
        'orderId': ss_order_id,
        'orderStatus': 'shipped',
        'orderDate': '2026-01-15T10:00:00',
        'shipDate': '2026-01-15',
        'customerEmail': 'bc@example.com',
        'orderTotal': 0,
        'items': [{'sku': sku, 'quantity': qty, 'unitPrice': 0}],
        'shipTo': {'name': 'BC Test', 'street1': '2 Main St', 'city': 'Portland',
                   'state': 'OR', 'postalCode': '97201', 'country': 'US'},
        'billTo': {},
        'carrierCode': 'fedex',
        'serviceCode': 'fedex_ground',
        'packageCode': 'package',
        'weight': {'value': 0, 'units': 'ounces'},
        'dimensions': {},
        'advancedOptions': {'customField1': cf1},
        'tagIds': [],
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_shipped_items(conn, order_number: str) -> list:
    """Return all shipped_items rows for the given order_number."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT base_sku, sku_lot, quantity_shipped
            FROM shipped_items
            WHERE order_number = %s
            ORDER BY base_sku, sku_lot
        """, (order_number,))
        return cur.fetchall()


# ---------------------------------------------------------------------------
# Manual order import
# ---------------------------------------------------------------------------

class TestManualOrderVariantImport:
    """Variant SKU path for import_new_manual_order → shipped_items."""

    def _run(self, order_number, ss_id, sku, qty, cf1=''):
        """Run import inside a rolled-back transaction; return shipped_items rows."""
        conn = get_connection()
        try:
            with patch(
                'src.services.inventory.lot_deduction.deduct_lot_inventory',
                return_value=None
            ):
                result = import_new_manual_order(
                    _manual_order(order_number, ss_id, sku, qty, cf1),
                    conn,
                    api_key='dummy', api_secret='dummy',
                )
            rows = _get_shipped_items(conn, order_number)
            return result, rows
        finally:
            conn.rollback()
            conn.close()

    def test_6pack_variant_base_sku_and_quantity(self):
        """17612-6 qty=1 → shipped_items records base_sku='17612', quantity=6."""
        result, rows = self._run(
            order_number='TEST-V-601',
            ss_id=9000601,
            sku='17612-6',
            qty=1,
        )
        assert result is True, "import should succeed"
        assert len(rows) == 1, f"expected 1 shipped_items row, got {len(rows)}: {rows}"
        base_sku, sku_lot, quantity_shipped = rows[0]
        assert base_sku == '17612', f"base_sku should be '17612', got {base_sku!r}"
        assert quantity_shipped == 6, f"quantity_shipped should be 6, got {quantity_shipped}"
        assert '17612-6' not in sku_lot, (
            f"sku_lot should not contain the variant suffix, got {sku_lot!r}"
        )

    def test_15pack_variant(self):
        """17612-15 qty=1 → quantity_shipped=15."""
        result, rows = self._run('TEST-V-602', 9000602, '17612-15', 1)
        assert result is True
        assert rows[0][0] == '17612'
        assert rows[0][2] == 15

    def test_compound_quantity_variant(self):
        """17612-6 qty=2 → quantity_shipped=12."""
        result, rows = self._run('TEST-V-603', 9000603, '17612-6', 2)
        assert result is True
        assert rows[0][0] == '17612'
        assert rows[0][2] == 12

    def test_plain_sku_unchanged(self):
        """Plain '17612' qty=3 → quantity_shipped=3 (no multiplier)."""
        result, rows = self._run('TEST-V-604', 9000604, '17612', 3,
                                 cf1='17612 - 260001')
        assert result is True
        assert rows[0][0] == '17612'
        assert rows[0][2] == 3

    def test_lot_stamped_sku_preserved(self):
        """'17612 - 260001' compound SKU is NOT treated as a variant; lot stamp kept."""
        result, rows = self._run('TEST-V-605', 9000605, '17612 - 260001', 1)
        assert result is True
        assert rows[0][0] == '17612'
        assert rows[0][2] == 1   # no multiplier applied
        assert '260001' in rows[0][1]   # lot number preserved in sku_lot


# ---------------------------------------------------------------------------
# BigCommerce order import
# ---------------------------------------------------------------------------

class TestBigCommerceVariantImport:
    """Variant SKU path for import_new_bigcommerce_order → shipped_items."""

    def _run(self, order_number, ss_id, sku, qty, cf1=''):
        conn = get_connection()
        try:
            with patch(
                'src.services.inventory.lot_deduction.deduct_lot_inventory',
                return_value=None
            ):
                result = import_new_bigcommerce_order(
                    _bc_order(order_number, ss_id, sku, qty, cf1),
                    conn,
                )
            rows = _get_shipped_items(conn, order_number)
            return result, rows
        finally:
            conn.rollback()
            conn.close()

    def test_6pack_variant_base_sku_and_quantity(self):
        """17612-6 qty=1 → shipped_items records base_sku='17612', quantity=6."""
        result, rows = self._run('801601', 9000701, '17612-6', 1)
        assert result is True
        assert len(rows) == 1, f"expected 1 row, got {len(rows)}: {rows}"
        base_sku, sku_lot, quantity_shipped = rows[0]
        assert base_sku == '17612', f"expected '17612', got {base_sku!r}"
        assert quantity_shipped == 6, f"expected 6, got {quantity_shipped}"
        assert '17612-6' not in sku_lot, (
            f"sku_lot should not contain variant suffix, got {sku_lot!r}"
        )

    def test_40pack_variant(self):
        """17914-40 qty=1 → base_sku='17914', quantity=40."""
        result, rows = self._run('801602', 9000702, '17914-40', 1)
        assert result is True
        assert rows[0][0] == '17914'
        assert rows[0][2] == 40

    def test_compound_quantity_variant(self):
        """17912-6 qty=3 → quantity_shipped=18."""
        # Note: 17912 is not a known base SKU; use 17914 instead
        result, rows = self._run('801603', 9000703, '17914-6', 3)
        assert result is True
        assert rows[0][0] == '17914'
        assert rows[0][2] == 18

    def test_with_lot_stamp(self):
        """Variant order with lot stamp CF1 set: sku_lot should use CF1 value."""
        result, rows = self._run(
            '801604', 9000704, '17612-6', 1, cf1='17612 - 260082'
        )
        assert result is True
        assert rows[0][0] == '17612'
        assert rows[0][2] == 6
        # sku_lot should reference the lot stamp, not the raw variant SKU
        assert '17612-6' not in rows[0][1], (
            f"sku_lot should not be the variant SKU, got {rows[0][1]!r}"
        )
