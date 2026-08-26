"""Tests for inexpensive backorder retry short-circuits and coalescing."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch


project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestBackorderRetryEfficiency(unittest.TestCase):
    def setUp(self):
        import app as dashboard_app
        dashboard_app._backorder_retry_in_progress.clear()

    def tearDown(self):
        import app as dashboard_app
        dashboard_app._backorder_retry_in_progress.clear()

    def test_no_unresolved_failures_does_not_load_credentials(self):
        from src.lot_tagger import retry

        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchall.return_value = []
        conn.cursor.return_value = cursor

        with patch.object(retry, 'get_connection', return_value=conn), \
             patch.object(retry, 'get_shipstation_credentials') as credentials:
            summary = retry.retry_unresolved_lot_tagging_failures('17612')

        self.assertEqual(summary['found'], 0)
        credentials.assert_not_called()

    def test_zero_balance_backorder_does_not_call_shipstation(self):
        from src.lot_tagger import retry

        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchall.return_value = [(1, '865000', 'ss-1', '17612')]
        cursor.fetchone.return_value = (False,)
        conn.cursor.return_value = cursor

        with patch.object(retry, 'get_connection', return_value=conn), \
             patch.object(retry, 'get_shipstation_credentials') as credentials, \
             patch.object(retry, 'fetch_order_by_id') as fetch_order:
            summary = retry.retry_unresolved_lot_tagging_failures('17612')

        self.assertEqual(summary['found'], 1)
        credentials.assert_not_called()
        fetch_order.assert_not_called()
        self.assertTrue(any('lb.balance > 0' in call.args[0] for call in cursor.execute.call_args_list))

    def test_background_retries_for_same_sku_are_coalesced(self):
        import app as dashboard_app

        thread = MagicMock()
        with patch('app.threading.Thread', return_value=thread) as thread_factory:
            first = dashboard_app.schedule_backorder_retry_after_inventory_available('17612')
            second = dashboard_app.schedule_backorder_retry_after_inventory_available('17612')

        self.assertTrue(first)
        self.assertFalse(second)
        thread_factory.assert_called_once()
        thread.start.assert_called_once()

        # Run the captured worker to release the in-progress SKU for later tests.
        worker = thread_factory.call_args.kwargs['target']
        with patch('app.retry_backorders_after_inventory_available', return_value={'found': 0}):
            worker()


if __name__ == '__main__':
    unittest.main()