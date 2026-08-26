"""Tests for the live negative-lot balance warning in the global alert API."""

import os
import sys
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch


project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestNegativeLotBalanceAlert(unittest.TestCase):
    def _call_get_admin_alert(self, admin_row, negative_rows, authenticated=True):
        import app as dashboard_app

        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = admin_row
        cursor.fetchall.return_value = negative_rows
        conn.cursor.return_value = cursor
        user = MagicMock()
        user.is_authenticated = authenticated

        with patch('app.get_connection', return_value=conn), \
             patch('app.logger'), \
             patch('app.current_user', user):
            with dashboard_app.app.test_request_context('/api/admin/alert'):
                response = dashboard_app.get_admin_alert()

        return response.get_json(), cursor

    def test_no_negative_lots_preserves_empty_alert_state(self):
        data, cursor = self._call_get_admin_alert(
            (1, '', False, None, None),
            [],
        )

        self.assertEqual(data['message'], '')
        self.assertFalse(data['is_active'])
        self.assertEqual(data['negative_lots'], [])
        self.assertIn('balance < 0', cursor.execute.call_args_list[1].args[0])

    def test_single_negative_lot_is_named_with_balance(self):
        updated_at = datetime(2026, 8, 25, 18, 0, tzinfo=timezone.utc)
        data, _ = self._call_get_admin_alert(
            (1, '', False, updated_at, 'admin@example.com'),
            [('17612', '260192', -5)],
        )

        self.assertTrue(data['is_active'])
        self.assertIn('SKU 17612, lot 260192: -5 units', data['message'])
        self.assertEqual(
            data['negative_lots'],
            [{'sku': '17612', 'lot': '260192', 'balance': -5}],
        )

    def test_multiple_negative_lots_are_sorted_and_included(self):
        data, _ = self._call_get_admin_alert(
            (1, '', False, None, None),
            [
                ('17904', 'B-2', -3),
                ('17612', 'A-1', -8),
            ],
        )

        self.assertTrue(data['is_active'])
        self.assertEqual(
            data['message'],
            '🚨 NEGATIVE LOT BALANCES: '
            'SKU 17612, lot A-1: -8 units; '
            'SKU 17904, lot B-2: -3 units',
        )

    def test_negative_lot_warning_coexists_with_manual_alert(self):
        data, _ = self._call_get_admin_alert(
            (1, 'Warehouse closes at 5 PM', False, None, 'admin@example.com'),
            [('17612', '260192', -1)],
        )

        self.assertTrue(data['is_active'])
        self.assertEqual(
            data['message'],
            'Warehouse closes at 5 PM | '
            '🚨 NEGATIVE LOT BALANCE: SKU 17612, lot 260192: -1 units',
        )

    def test_balance_query_failure_does_not_hide_manual_alert(self):
        import app as dashboard_app

        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = (1, 'Warehouse closes at 5 PM', True, None, 'admin@example.com')
        cursor.fetchall.side_effect = RuntimeError('lot_balances unavailable')
        conn.cursor.return_value = cursor
        user = MagicMock()
        user.is_authenticated = True

        with patch('app.get_connection', return_value=conn), \
             patch('app.logger'), \
             patch('app.current_user', user):
            with dashboard_app.app.test_request_context('/api/admin/alert'):
                response = dashboard_app.get_admin_alert()

        data = response.get_json()
        self.assertEqual(data['message'], 'Warehouse closes at 5 PM')
        self.assertTrue(data['is_active'])
        self.assertEqual(data['negative_lots'], [])

    def test_anonymous_request_does_not_receive_lot_details(self):
        import app as dashboard_app

        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = (1, '', False, None, None)
        cursor.fetchall.return_value = [('17612', '260192', -5)]
        conn.cursor.return_value = cursor
        anonymous_user = MagicMock()
        anonymous_user.is_authenticated = False

        with patch('app.get_connection', return_value=conn), \
             patch('app.current_user', anonymous_user):
            response = dashboard_app.app.test_client().get('/api/admin/alert')
        data = response.get_json()

        self.assertTrue(data['is_active'])
        self.assertEqual(
            data['message'],
            '🚨 NEGATIVE LOT BALANCE: Sign in to review affected inventory.',
        )
        self.assertNotIn('negative_lots', data)
        self.assertNotIn('17612', data['message'])
        self.assertNotIn('260192', data['message'])
        self.assertNotIn('-5', data['message'])


if __name__ == '__main__':
    unittest.main()