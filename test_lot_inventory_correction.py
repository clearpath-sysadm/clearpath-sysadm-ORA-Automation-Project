"""Regression tests for lot inventory corrections."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch


project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestLotInventoryCorrection(unittest.TestCase):
    def test_correction_records_transaction_and_returns_live_balance(self):
        import app as dashboard_app

        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.side_effect = [
            ('17612',),  # SKU for the lot
            (42,),        # inserted transaction ID
            (0,),         # live balance after the correction
        ]
        conn.cursor.return_value = cursor

        retry_result = {
            'found': 0,
            'retried': 0,
            'retagged': 0,
            'still_backordered': 0,
            'skipped_not_awaiting_shipment': 0,
            'errors': 0,
        }
        with patch('app.get_connection', return_value=conn), \
             patch(
                 'app.retry_backorders_after_inventory_available',
                 return_value=retry_result,
             ):
            with dashboard_app.app.test_request_context(
                '/api/lot_inventory/19/correct',
                method='POST',
                json={
                    'correction_type': 'Adjust Up',
                    'amount': 4,
                    'date': '2026-08-26',
                    'notes': 'Negative balance correction',
                },
            ):
                response = dashboard_app.api_correct_lot_inventory(19)

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], 'Correction recorded successfully')
        self.assertEqual(data['transaction_id'], 42)
        self.assertEqual(data['new_balance'], 0)
        self.assertEqual(data['backorder_retry'], retry_result)
        conn.commit.assert_called_once()
        sql_statements = [call.args[0] for call in cursor.execute.call_args_list]
        self.assertFalse(any('inventory_current' in sql for sql in sql_statements))
        self.assertTrue(any('lot_balances' in sql for sql in sql_statements))

    def test_primary_inventory_modal_preserves_lot_and_previews_balance(self):
        with open(
            os.path.join(project_root, 'inventory.html'),
            encoding='utf-8',
        ) as inventory_page:
            html = inventory_page.read()

        modal_function = html[
            html.index('function openCorrectionModal'):
            html.index('function closeCorrectionModal')
        ]
        self.assertLess(
            modal_function.index("document.getElementById('correction-form').reset()"),
            modal_function.index("document.getElementById('correction-lot-id').value = lotId"),
        )
        self.assertIn('>Quantity *</label>', html)
        self.assertIn('Resulting balance:', html)
        self.assertIn('updateCorrectionResultingBalance()', html)


if __name__ == '__main__':
    unittest.main()