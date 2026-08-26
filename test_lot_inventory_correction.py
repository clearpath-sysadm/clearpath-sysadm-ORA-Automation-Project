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

        with patch('app.get_connection', return_value=conn), \
             patch(
                 'app.schedule_backorder_retry_after_inventory_available',
             ) as retry:
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
        self.assertTrue(data['backorder_retry_scheduled'])
        retry.assert_called_once_with('17612')
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
        self.assertIn("button.textContent = isSaving ? 'Saving…' : 'Record Correction';", html)
        self.assertIn('const refreshPromise = loadLots();', html)

    def test_zero_balance_correction_displays_empty_not_depleted(self):
        with open(
            os.path.join(project_root, 'inventory.html'),
            encoding='utf-8',
        ) as inventory_page:
            html = inventory_page.read()

        status_function = html[
            html.index('function getLotStatusBadge'):
            html.index('async function reactivateLot')
        ]
        zero_balance_check = "status === 'depleted' && numericBalance === 0"
        self.assertIn(zero_balance_check, status_function)
        self.assertLess(
            status_function.index(zero_balance_check),
            status_function.index("if (status === 'depleted')"),
        )
        self.assertIn("status-empty status-actionable", status_function)

    def test_status_badges_support_safe_activation_and_deactivation(self):
        with open(
            os.path.join(project_root, 'inventory.html'),
            encoding='utf-8',
        ) as inventory_page:
            html = inventory_page.read()

        status_function = html[
            html.index('function getLotStatusBadge'):
            html.index('async function toggleLotStatus')
        ]
        self.assertIn('title="Deactivate this lot"', status_function)
        self.assertIn('title="Activate this lot"', status_function)
        self.assertIn('onclick="toggleLotStatus(${Number(lotId)})"', status_function)

        toggle_function = html[
            html.index('async function toggleLotStatus'):
            html.index('// Kept as a compatibility alias')
        ]
        self.assertIn("const nextStatus = activating ? 'active' : 'inactive';", toggle_function)
        self.assertIn("if (activating && !(balance > 0))", toggle_function)

    def test_active_lot_can_be_deactivated_without_changing_balance(self):
        import app as dashboard_app

        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = ('active', 25, '17612')
        cursor.rowcount = 1
        conn.cursor.return_value = cursor

        with patch('app.get_connection', return_value=conn):
            with dashboard_app.app.test_request_context(
                '/api/lot_inventory/19',
                method='PUT',
                json={'status': 'inactive'},
            ):
                response = dashboard_app.api_update_lot_inventory(19)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['success'], True)
        self.assertIn('status        = COALESCE', cursor.execute.call_args_list[1].args[0])
        self.assertEqual(
            cursor.execute.call_args_list[1].args[1],
            (None, 'inactive', None, 19),
        )
        conn.commit.assert_called_once()


if __name__ == '__main__':
    unittest.main()