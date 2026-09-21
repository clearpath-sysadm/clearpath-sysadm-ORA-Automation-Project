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
            ('17612', None, 'active'),  # SKU, archive state, and status
            (42,),             # inserted transaction ID
            (0,),              # live balance after the correction
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
        self.assertEqual(data['message'], 'Quantity adjustment recorded successfully')
        self.assertEqual(data['transaction_id'], 42)
        self.assertEqual(data['new_balance'], 0)
        self.assertTrue(data['backorder_retry_scheduled'])
        retry.assert_called_once_with('17612')
        conn.commit.assert_called_once()
        sql_statements = [call.args[0] for call in cursor.execute.call_args_list]
        self.assertFalse(any('inventory_current' in sql for sql in sql_statements))
        self.assertTrue(any('lot_balances' in sql for sql in sql_statements))

    def test_correction_synchronizes_active_and_depleted_status(self):
        import app as dashboard_app

        cases = [
            ('Adjust Up', 'depleted', 5, 'active'),
            ('Adjust Down', 'active', 0, 'depleted'),
        ]
        for correction_type, starting_status, balance, expected_status in cases:
            with self.subTest(
                correction_type=correction_type,
                starting_status=starting_status,
            ):
                conn = MagicMock()
                cursor = MagicMock()
                cursor.fetchone.side_effect = [
                    ('17612', None, starting_status),
                    (42,),
                    (balance,),
                ]
                conn.cursor.return_value = cursor

                with patch('app.get_connection', return_value=conn), patch(
                    'app.schedule_backorder_retry_after_inventory_available',
                    return_value=True,
                ):
                    with dashboard_app.app.test_request_context(
                        '/api/lot_inventory/19/correct',
                        method='POST',
                        json={
                            'correction_type': correction_type,
                            'amount': 5,
                            'date': '2026-09-21',
                            'notes': 'Count correction',
                        },
                    ):
                        response = dashboard_app.api_correct_lot_inventory(19)

                self.assertEqual(response.status_code, 200)
                status_updates = [
                    call for call in cursor.execute.call_args_list
                    if 'UPDATE lots' in call.args[0]
                ]
                self.assertEqual(len(status_updates), 1)
                self.assertEqual(
                    status_updates[0].args[1],
                    (expected_status, 19, starting_status),
                )
                conn.commit.assert_called_once()

    def test_correction_preserves_inactive_and_quarantine_status(self):
        import app as dashboard_app

        for starting_status in ('inactive', 'quarantine'):
            with self.subTest(starting_status=starting_status):
                conn = MagicMock()
                cursor = MagicMock()
                cursor.fetchone.side_effect = [
                    ('17612', None, starting_status),
                    (42,),
                    (5,),
                ]
                conn.cursor.return_value = cursor

                with patch('app.get_connection', return_value=conn), patch(
                    'app.schedule_backorder_retry_after_inventory_available',
                    return_value=True,
                ):
                    with dashboard_app.app.test_request_context(
                        '/api/lot_inventory/19/correct',
                        method='POST',
                        json={
                            'correction_type': 'Adjust Up',
                            'amount': 5,
                            'date': '2026-09-21',
                            'notes': 'Count correction',
                        },
                    ):
                        response = dashboard_app.api_correct_lot_inventory(19)

                self.assertEqual(response.status_code, 200)
                self.assertFalse(any(
                    'UPDATE lots' in call.args[0]
                    for call in cursor.execute.call_args_list
                ))
                conn.commit.assert_called_once()

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

    def test_dashboard_physical_count_validates_lot_sku_and_retries_after_commit(self):
        import app as dashboard_app

        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = (10, '17612', 'LOT-ONE')
        conn.cursor.return_value = cursor
        user = MagicMock()
        user.role = 'admin'
        user.first_name = 'Test'
        user.last_name = 'Admin'
        user.email = 'test@example.com'

        def retry_after_commit(sku):
            self.assertTrue(conn.commit.called)
            self.assertEqual(sku, '17612')
            return True

        with patch('app.get_connection', return_value=conn), \
             patch('app.current_user', user), \
             patch(
                 'app.schedule_backorder_retry_after_inventory_available',
                 side_effect=retry_after_commit,
             ) as retry:
            with dashboard_app.app.test_request_context(
                '/api/physical_count_adjustment',
                method='POST',
                json={
                    'sku': '17612',
                    'lot_id': 19,
                    'physical_count': 15,
                    'reason': 'Physical count',
                    'user_timezone': 'America/Chicago',
                },
            ):
                response = dashboard_app.api_physical_count_adjustment()

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertTrue(data['backorder_retry_scheduled'])
        self.assertIn('LOT-ONE', data['message'])
        retry.assert_called_once_with('17612')
        insert_call = cursor.execute.call_args_list[1]
        self.assertIn('INSERT INTO inventory_transactions', insert_call.args[0])
        self.assertEqual(insert_call.args[1][1], '17612')
        self.assertEqual(insert_call.args[1][5], 19)

    def test_dashboard_physical_count_rejects_mismatched_lot_sku(self):
        import app as dashboard_app

        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = (10, '17612', 'LOT-ONE')
        conn.cursor.return_value = cursor

        with patch('app.get_connection', return_value=conn), \
             patch('app.schedule_backorder_retry_after_inventory_available') as retry:
            with dashboard_app.app.test_request_context(
                '/api/physical_count_adjustment',
                method='POST',
                json={
                    'sku': '18795',
                    'lot_id': 19,
                    'physical_count': 15,
                    'reason': 'Physical count',
                },
            ):
                response, status = dashboard_app.api_physical_count_adjustment()

        self.assertEqual(status, 400)
        self.assertIn('does not belong', response.get_json()['error'])
        conn.commit.assert_not_called()
        retry.assert_not_called()
        self.assertEqual(len(cursor.execute.call_args_list), 1)

    def test_dashboard_modal_is_lot_aware_on_desktop_and_mobile(self):
        with open(
            os.path.join(project_root, 'index.html'),
            encoding='utf-8',
        ) as dashboard:
            html = dashboard.read()

        self.assertIn('id="modal-lot"', html)
        self.assertIn('/api/lots_by_sku/${encodeURIComponent(sku)}', html)
        self.assertIn('function selectPhysicalCountLot()', html)
        self.assertIn('lot_id: lotId', html)
        self.assertIn('physicalCountLotRequestId', html)
        self.assertGreaterEqual(
            html.count("openPhysicalCountModal('${item.sku}'"),
            2,
        )
        self.assertIn('52w Avg', html)


if __name__ == '__main__':
    unittest.main()