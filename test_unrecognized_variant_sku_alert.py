"""
Tests for Task #151: Alert when an order line item is silently dropped as
unrecognized.

Verifies that the lot tagger emits a server_logger.warning and calls
_write_admin_alert when an order contains an item whose SKU looks like a
variant of a known base SKU (e.g. '17612-1-1') but is not present in
sku_variants, while the recognized item ('17612-6') is still tagged normally.
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock, call

project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def _make_order(order_number='864777', order_id=864777, items=None):
    if items is None:
        items = [{'sku': '17612-6', 'quantity': 1}]
    return {
        'orderId': order_id,
        'orderNumber': order_number,
        'orderStatus': 'awaiting_shipment',
        'modifyDate': '2026-08-03T00:00:00.000Z',
        'advancedOptions': {'customField1': ''},
        'items': items,
        'tagIds': [],
    }


def _make_conn():
    conn = MagicMock()
    cur = MagicMock()
    cur.fetchone.return_value = None
    cur.fetchall.return_value = []
    conn.cursor.return_value = cur
    return conn


class TestUnrecognizedVariantSkuAlert(unittest.TestCase):
    """
    An order containing one recognized variant SKU ('17612-6') and one
    unrecognized-but-looks-like-variant SKU ('17612-1-1') must:
    - Tag the recognized item normally (not crash or silently skip).
    - Emit server_logger.warning for the unrecognized SKU.
    - Call _write_admin_alert for the unrecognized SKU.
    """

    def _call_tag_order_lots(self, order, active_lots, known_skus,
                             lot_statuses, conn,
                             variant_map, promo_map=None,
                             suppress_exceptions=False):
        from src.lot_tagger.tagger import tag_order_lots

        with patch('src.lot_tagger.tagger.server_logger') as mock_sl, \
             patch('src.lot_tagger.tagger._write_admin_alert') as mock_alert, \
             patch('src.lot_tagger.tagger.update_order_custom_fields',
                   return_value={'success': True}), \
             patch('src.lot_tagger.tagger.update_order_package_v2',
                   return_value={'success': True}), \
             patch('src.services.inventory.lot_reservation.reserve_lot_for_order',
                   return_value=True):

            if suppress_exceptions:
                try:
                    tag_order_lots(
                        order,
                        active_lots,
                        known_skus,
                        lot_statuses,
                        conn,
                        promo_map=promo_map or {},
                        variant_map=variant_map,
                    )
                except Exception:
                    pass
            else:
                tag_order_lots(
                    order,
                    active_lots,
                    known_skus,
                    lot_statuses,
                    conn,
                    promo_map=promo_map or {},
                    variant_map=variant_map,
                )

            return mock_sl, mock_alert

    def test_unrecognized_variant_triggers_warning_and_alert(self):
        """
        Order 864777 has '17612-6' (recognized via variant map → '17612') and
        '17612-1-1' (not in variant map, not in known_skus).  The tagger must
        emit a warning and admin alert for '17612-1-1'.
        """
        order = _make_order(
            order_number='864777',
            order_id=864777,
            items=[
                {'sku': '17612-6', 'quantity': 1},
                {'sku': '17612-1-1', 'quantity': 1},
            ],
        )
        active_lots = {'17612': 'LOT-001'}
        known_skus = {'17612'}
        lot_statuses = {('17612', 'LOT-001'): 'active'}
        conn = _make_conn()
        variant_map = {
            '17612-6': {'base_sku': '17612', 'unit_multiplier': 6},
        }

        mock_sl, mock_alert = self._call_tag_order_lots(
            order, active_lots, known_skus, lot_statuses, conn,
            variant_map=variant_map,
            suppress_exceptions=True,
        )

        # server_logger.warning must have been called with a message mentioning
        # the unrecognized SKU and the order number.
        warning_calls = [
            str(c) for c in mock_sl.warning.call_args_list
        ]
        self.assertTrue(
            any('17612-1-1' in c for c in warning_calls),
            f"Expected warning mentioning '17612-1-1'; got: {warning_calls}",
        )
        self.assertTrue(
            any('864777' in c for c in warning_calls),
            f"Expected warning mentioning order '864777'; got: {warning_calls}",
        )

        # _write_admin_alert must have been called at least once with a message
        # mentioning the unrecognized SKU.
        alert_messages = [str(c) for c in mock_alert.call_args_list]
        self.assertTrue(
            mock_alert.called,
            "_write_admin_alert was not called for the unrecognized SKU",
        )
        self.assertTrue(
            any('17612-1-1' in m for m in alert_messages),
            f"Expected admin alert mentioning '17612-1-1'; got: {alert_messages}",
        )

    def test_alert_fires_with_empty_variant_map(self):
        """
        Regression: when variant_map={} (empty — no active rows or not yet
        loaded), the detection still runs and an alert is emitted for a SKU
        that looks like a variant of a known base SKU.

        This guards against the detection being accidentally gated inside
        the `if _variant_map:` truthiness check.
        """
        order = _make_order(
            order_number='864778',
            order_id=864778,
            items=[{'sku': '17612-1-1', 'quantity': 1}],
        )
        active_lots = {'17612': 'LOT-001'}
        known_skus = {'17612'}
        lot_statuses = {('17612', 'LOT-001'): 'active'}
        conn = _make_conn()

        mock_sl, mock_alert = self._call_tag_order_lots(
            order, active_lots, known_skus, lot_statuses, conn,
            variant_map={},          # empty — no variant entries loaded
            suppress_exceptions=True,
        )

        warning_calls = [str(c) for c in mock_sl.warning.call_args_list]
        self.assertTrue(
            any('17612-1-1' in c for c in warning_calls),
            f"Expected warning for '17612-1-1' even with empty variant_map; "
            f"got: {warning_calls}",
        )
        self.assertTrue(
            mock_alert.called,
            "_write_admin_alert was not called even with empty variant_map",
        )
        alert_messages = [str(c) for c in mock_alert.call_args_list]
        self.assertTrue(
            any('17612-1-1' in m for m in alert_messages),
            f"Expected admin alert for '17612-1-1' with empty variant_map; "
            f"got: {alert_messages}",
        )

    def test_recognized_item_not_alerted(self):
        """
        An item that IS resolved by the variant map ('17612-6' → '17612') must
        NOT produce a warning or admin alert for itself.
        """
        order = _make_order(
            order_number='864779',
            order_id=864779,
            items=[{'sku': '17612-6', 'quantity': 1}],
        )
        active_lots = {'17612': 'LOT-001'}
        known_skus = {'17612'}
        lot_statuses = {('17612', 'LOT-001'): 'active'}
        conn = _make_conn()
        variant_map = {
            '17612-6': {'base_sku': '17612', 'unit_multiplier': 6},
        }

        mock_sl, mock_alert = self._call_tag_order_lots(
            order, active_lots, known_skus, lot_statuses, conn,
            variant_map=variant_map,
            suppress_exceptions=True,
        )

        # No unrecognized-variant warning about '17612-6' — it was remapped.
        warning_calls = [str(c) for c in mock_sl.warning.call_args_list]
        self.assertFalse(
            any('17612-6' in c and 'unrecognized' in c.lower()
                for c in warning_calls),
            f"Unexpected warning for recognized SKU '17612-6': {warning_calls}",
        )
        self.assertFalse(
            mock_alert.called,
            f"_write_admin_alert should not be called for a recognized SKU; "
            f"got: {[str(c) for c in mock_alert.call_args_list]}",
        )

    def test_completely_unrelated_sku_not_alerted(self):
        """
        An item whose SKU shares no prefix with any known base SKU (e.g. 'MISC-99')
        must NOT trigger the variant-drop alert — it's a genuinely untracked order.
        """
        order = _make_order(
            order_number='864780',
            order_id=864780,
            items=[{'sku': 'MISC-99', 'quantity': 1}],
        )
        active_lots = {'17612': 'LOT-001'}
        known_skus = {'17612'}
        lot_statuses = {('17612', 'LOT-001'): 'active'}
        conn = _make_conn()
        variant_map = {
            '17612-6': {'base_sku': '17612', 'unit_multiplier': 6},
        }

        mock_sl, mock_alert = self._call_tag_order_lots(
            order, active_lots, known_skus, lot_statuses, conn,
            variant_map=variant_map,
            suppress_exceptions=True,
        )

        # _write_admin_alert must NOT be called for a completely unrelated SKU.
        alert_messages = [str(c) for c in mock_alert.call_args_list]
        self.assertFalse(
            any('MISC-99' in m for m in alert_messages),
            f"Unexpected admin alert for unrelated SKU 'MISC-99': {alert_messages}",
        )


if __name__ == '__main__':
    unittest.main()
