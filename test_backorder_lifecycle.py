"""Regression coverage for automatic backorder tagging and shipped safeguards."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def _order(cf1='', items=None):
    return {
        'orderId': 12345,
        'orderNumber': 'BO-100',
        'orderStatus': 'awaiting_shipment',
        'advancedOptions': {'customField1': cf1},
        'items': items or [{'sku': '17612', 'quantity': 1}],
        'tagIds': [],
    }


def _profile():
    return {
        'carrier_code': 'fedex',
        'service_code': 'fedex_ground',
        'package_code': 'package',
        'weight_oz': 8,
        'length': 5,
        'width': 4,
        'height': 3,
        'bill_to_party': 'my_account',
        'bill_to_account': 'ACCT',
        'package_id': None,
    }


class TestBackorderTagging(unittest.TestCase):
    def _conn(self):
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = None
        conn.cursor.return_value = cursor
        return conn

    def test_no_available_lot_marks_cf1_backordered_without_reservation(self):
        """No valid lot preserves failure work and uses normal enrichment once."""
        from src.lot_tagger.tagger import BACKORDER_CF1, tag_order_lots

        conn = self._conn()
        order = _order()
        with patch('src.lot_tagger.tagger.resolve_shipping_profile',
                   return_value=_profile()), \
             patch('src.lot_tagger.tagger._apply_shipping_enrichment',
                   return_value={'success': True, 'updated': True}) as enrich, \
             patch('src.lot_tagger.tagger._write_admin_alert'), \
             patch('src.lot_tagger.tagger.lot_reservation.reserve_lot_for_order') as reserve:
            tag_order_lots(
                order, {}, {'17612'}, {}, conn, {},
                promo_map={}, variant_map={},
            )

        reserve.assert_not_called()
        enrich.assert_called_once_with(
            order, BACKORDER_CF1, _profile(), 1, False
        )
        inserts = [
            args[0] for args, _ in conn.cursor.return_value.execute.call_args_list
            if 'INSERT INTO lot_tagging_failures' in args[0]
        ]
        self.assertTrue(inserts, 'backorders must retain an unresolved retry record')

    def test_replacing_backordered_marker_does_not_copy_it_to_cf2(self):
        """A later real lot replaces the marker rather than preserving it as history."""
        from src.lot_tagger.tagger import _apply_shipping_enrichment

        order = _order(cf1='backordered')
        with patch('src.lot_tagger.tagger.update_order_custom_fields',
                   return_value={'success': True}) as update:
            result = _apply_shipping_enrichment(
                order, '17612 - LOT-1', _profile(), 1, False
            )

        self.assertTrue(result['success'])
        self.assertEqual(update.call_args.args[2], None)
        self.assertEqual(update.call_args.args[1], '17612 - LOT-1')

    def test_multi_sku_order_does_not_receive_ambiguous_backorder_marker(self):
        """The existing auto-split guard remains the only multi-SKU path."""
        from src.lot_tagger.tagger import tag_order_lots

        conn = self._conn()
        order = _order(items=[
            {'sku': '17612', 'quantity': 1},
            {'sku': '17904', 'quantity': 1},
        ])
        with patch('src.lot_tagger.tagger._mark_order_backordered') as marker:
            tag_order_lots(
                order, {}, {'17612', '17904'}, {}, conn, {},
                promo_map={}, variant_map={},
            )
        marker.assert_not_called()

    def test_lot_override_does_not_suppress_the_backorder_marker(self):
        """A lot override is not a reason to hide an unavailable-inventory state."""
        from src.lot_tagger.tagger import BACKORDER_CF1, tag_order_lots

        conn = self._conn()
        order = _order()
        order['tagIds'] = [49832]
        with patch('src.lot_tagger.tagger.resolve_shipping_profile',
                   return_value=_profile()), \
             patch('src.lot_tagger.tagger._apply_shipping_enrichment',
                   return_value={'success': True, 'updated': True}) as enrich, \
             patch('src.lot_tagger.tagger._write_admin_alert'):
            tag_order_lots(
                order, {}, {'17612'}, {}, conn, {},
                promo_map={}, variant_map={},
            )

        self.assertFalse(enrich.call_args.args[4])
        self.assertEqual(enrich.call_args.args[1], BACKORDER_CF1)


class TestShippedBackorderSafeguard(unittest.TestCase):
    def test_shipped_backorder_creates_durable_high_priority_exception(self):
        """A shipped CF1 marker must not be silently treated as malformed data."""
        from src.services.inventory.lot_deduction import deduct_lot_inventory

        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = None
        conn.cursor.return_value = cursor
        with patch('src.services.inventory.lot_deduction._write_admin_alert') as alert:
            inserted = deduct_lot_inventory(
                order_number='BO-100',
                shipstation_order_id='12345',
                base_sku='17612',
                customField1_value='backordered',
                ship_date='2026-08-25',
                quantity=1,
                conn=conn,
            )

        self.assertFalse(inserted)
        self.assertTrue(
            any(
                'INSERT INTO lot_tagging_failures' in args[0]
                for args, _ in cursor.execute.call_args_list
            )
        )
        alert.assert_called_once()

    def test_shipped_backorder_reopens_a_resolved_failure(self):
        """A previous resolution cannot erase the durable shipped exception."""
        from src.services.inventory.lot_deduction import deduct_lot_inventory

        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = ('older alert',)
        conn.cursor.return_value = cursor
        deduct_lot_inventory(
            order_number='BO-101',
            shipstation_order_id='12346',
            base_sku='17612',
            customField1_value='backordered',
            ship_date='2026-08-25',
            quantity=1,
            conn=conn,
        )

        failure_sql = next(
            args[0] for args, _ in cursor.execute.call_args_list
            if 'INSERT INTO lot_tagging_failures' in args[0]
        )
        self.assertIn('resolved_at = NULL', failure_sql)


class TestLotActivationRetry(unittest.TestCase):
    def test_activating_positive_balance_lot_retries_matching_backorders(self):
        """The real lot update route must use the lot balance and retry post-commit."""
        import app as dashboard_app

        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = ('inactive', 8, '17612')
        cursor.rowcount = 1
        conn.cursor.return_value = cursor
        retry_summary = {
            'found': 1,
            'retried': 1,
            'retagged': 1,
            'still_backordered': 0,
            'errors': 0,
        }

        with patch('app.get_connection', return_value=conn), \
             patch('app.retry_backorders_after_inventory_available',
                   return_value=retry_summary) as retry:
            with dashboard_app.app.test_request_context(
                '/api/lot_inventory/42',
                method='PUT',
                json={'status': 'active', 'notes': 'received stock'},
            ):
                response = dashboard_app.api_update_lot_inventory(42)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['backorder_retry'], retry_summary)
        retry.assert_called_once_with('17612')
        lookup_sql = cursor.execute.call_args_list[0].args[0]
        self.assertIn('lb.lot_id = l.lot_id', lookup_sql)


if __name__ == '__main__':
    unittest.main()