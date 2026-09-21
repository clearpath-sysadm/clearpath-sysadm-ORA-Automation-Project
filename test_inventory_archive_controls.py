"""Behavior and source regressions for auditable inventory archive controls."""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch
import uuid

import pytest


ROOT = Path(__file__).resolve().parent
APP = (ROOT / "app.py").read_text()
MIGRATION = (ROOT / "migrations/023_inventory_archive.py").read_text()
CANCELLATION = (
    ROOT / "src/services/inventory/lot_cancellation.py"
).read_text()


def _function_source(name):
    start = APP.index(f"def {name}(")
    next_def = APP.find("\ndef ", start + 5)
    return APP[start:next_def if next_def != -1 else None]


def test_archive_migration_has_database_and_audit_guards():
    assert "inventory_lifecycle_events" in MIGRATION
    assert "append-only" in MIGRATION
    assert "inventory_transactions_reject_archived_lot" in MIGRATION
    assert "DROP VIEW IF EXISTS lot_balances CASCADE" not in MIGRATION


def test_delete_routes_archive_without_destroying_references():
    tx_source = _function_source("api_delete_inventory_transaction")
    lot_source = _function_source("api_delete_lot_inventory")
    assert "UPDATE inventory_transactions" in tx_source
    assert "DELETE FROM inventory_transactions" not in tx_source
    assert "UPDATE lots" in lot_source
    assert "DELETE FROM inventory_transactions" not in lot_source
    assert "SET lot_id = NULL" not in lot_source


def test_restore_checks_projected_reservations_under_shared_lock():
    source = _function_source("api_restore_inventory_transaction")
    assert "_lock_inventory_sku" in source
    assert "projected_balance" in source
    assert "reserved_quantity" in source
    assert "underfund active lot reservations" in source


def test_operational_reports_filter_archived_transactions():
    expected = {
        "app.py": [
            "WHERE transaction_type = 'Receive'\n              AND archived_at IS NULL",
            "WHERE date >= %s AND date <= %s\n              AND archived_at IS NULL",
        ],
        "src/weekly_reporter.py": [
            "AND archived_at IS NULL",
        ],
        "src/backfill_daily_snapshots.py": [
            "WHERE archived_at IS NULL",
        ],
        "src/daily_shipment_processor.py": [
            "AND archived_at IS NULL",
        ],
    }
    for relative_path, snippets in expected.items():
        source = (ROOT / relative_path).read_text()
        for snippet in snippets:
            assert snippet in source, f"{relative_path} is missing {snippet!r}"


def test_balance_decreasing_restore_rejects_underfunded_reservations():
    import app as dashboard_app

    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.side_effect = [
        ('17612',),
        (19, datetime.now(timezone.utc), '17612', 8, 'Ship'),
        (None,),
        (10,),
        (5,),
    ]
    conn.cursor.return_value = cursor
    user = MagicMock(is_authenticated=True, role='admin')
    user.email = 'admin@example.test'

    with patch('app.get_connection', return_value=conn), \
         patch('app.current_user', user):
        with dashboard_app.app.test_request_context(
            '/api/inventory_transactions/77/restore',
            method='POST',
            json={'reason': 'Correct accidental archive'},
        ):
            response, status = dashboard_app.api_restore_inventory_transaction(77)

    assert status == 409
    assert response.get_json()['projected_balance'] == 2
    assert response.get_json()['reserved_quantity'] == 5
    conn.commit.assert_not_called()


def test_cancellation_never_reverses_an_archived_ship():
    from src.services.inventory.lot_cancellation import reverse_lot_inventory

    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchall.return_value = []
    conn.cursor.return_value = cursor

    assert reverse_lot_inventory('12345', '98765', '2026-09-17', conn) == 0
    query = cursor.execute.call_args_list[0].args[0]
    assert "transaction_type = 'Ship'" in query
    assert "archived_at IS NULL" in query
    assert not any(
        'INSERT INTO inventory_transactions' in call.args[0]
        for call in cursor.execute.call_args_list
    )


def test_physical_count_rejects_an_archived_lot():
    import app as dashboard_app

    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.return_value = (
        10, '17612', 'LOT-ARCHIVED', datetime.now(timezone.utc)
    )
    conn.cursor.return_value = cursor

    with patch('app.get_connection', return_value=conn):
        with dashboard_app.app.test_request_context(
            '/api/physical_count_adjustment',
            method='POST',
            json={
                'sku': '17612',
                'lot_id': 19,
                'physical_count': 12,
                'reason': 'Cycle count',
            },
        ):
            response, status = dashboard_app.api_physical_count_adjustment()

    assert status == 409
    assert 'Archived lots cannot receive' in response.get_json()['error']
    conn.commit.assert_not_called()


def test_postgres_archive_trigger_and_operational_history_split():
    """Rollback-isolated integration proof for the central DB guard and filtering."""
    try:
        from src.services.database.pg_utils import get_connection
        conn = get_connection()
    except Exception as exc:
        pytest.skip(f"PostgreSQL is unavailable: {exc}")

    cursor = conn.cursor()
    try:
        sku = f"ARCHIVE-TEST-{uuid.uuid4().hex[:12]}"
        cursor.execute("SELECT COALESCE(MAX(lot_id), 0) + 10000 FROM lots")
        lot_id = cursor.fetchone()[0]
        cursor.execute(
            "INSERT INTO skus (sku_code) VALUES (%s) RETURNING sku_id", (sku,)
        )
        sku_id = cursor.fetchone()[0]
        cursor.execute(
            """INSERT INTO lots
               (lot_id, sku_id, lot_number, status, archived_at,
                archived_by, archive_reason)
               VALUES (%s, %s, 'ARCHIVED', 'inactive', NOW(),
                       'pytest', 'archive integration test')""",
            (lot_id, sku_id),
        )
        cursor.execute("SAVEPOINT archived_write")
        with pytest.raises(Exception, match="archived lots cannot receive"):
            cursor.execute(
                """INSERT INTO inventory_transactions
                   (date, sku, quantity, transaction_type, lot_id)
                   VALUES (CURRENT_DATE, %s, 1, 'Adjust Up', %s)""",
                (sku, lot_id),
            )
        cursor.execute("ROLLBACK TO SAVEPOINT archived_write")

        cursor.execute(
            """INSERT INTO inventory_transactions
               (date, sku, quantity, transaction_type, archived_at,
                archived_by, archive_reason)
               VALUES (CURRENT_DATE, %s, 7, 'Receive', NOW(),
                       'pytest', 'archive integration test')
               RETURNING id""",
            (sku,),
        )
        transaction_id = cursor.fetchone()[0]
        cursor.execute(
            "SELECT COUNT(*) FROM inventory_transactions "
            "WHERE id = %s AND archived_at IS NULL",
            (transaction_id,),
        )
        assert cursor.fetchone()[0] == 0
        cursor.execute(
            "SELECT COUNT(*) FROM inventory_transactions WHERE id = %s",
            (transaction_id,),
        )
        assert cursor.fetchone()[0] == 1
    finally:
        conn.rollback()
        conn.close()


def test_negative_opening_quantity_is_rejected_before_database_access():
    import app as dashboard_app

    with patch('app.get_connection') as get_connection:
        with dashboard_app.app.test_request_context(
            '/api/lot_inventory',
            method='POST',
            json={
                'sku': '17612',
                'lot': 'LOT-NEGATIVE',
                'initial_qty': -1,
                'received_date': '2026-09-17',
                'status': 'inactive',
            },
        ):
            response, status = dashboard_app.api_create_lot_inventory()

    assert status == 400
    assert response.get_json() == {
        'success': False,
        'error': 'Initial quantity must be zero or a positive whole number',
    }
    get_connection.assert_not_called()


@pytest.mark.parametrize(
    ('initial_qty', 'expects_opening_receive'),
    [(0, False), (25, True)],
)
def test_nonnegative_opening_quantity_creates_expected_records(
    initial_qty, expects_opening_receive
):
    import app as dashboard_app

    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.side_effect = [(1,), (99,)]
    conn.cursor.return_value = cursor

    with patch('app.get_connection', return_value=conn), \
         patch('app.schedule_backorder_retry_after_inventory_available'):
        with dashboard_app.app.test_request_context(
            '/api/lot_inventory',
            method='POST',
            json={
                'sku': '17612',
                'lot': f'LOT-{initial_qty}',
                'initial_qty': initial_qty,
                'received_date': '2026-09-17',
                'status': 'inactive',
            },
        ):
            response = dashboard_app.api_create_lot_inventory()

    assert response.status_code == 200
    assert response.get_json()['id'] == 99
    conn.commit.assert_called_once()
    statements = [call.args[0] for call in cursor.execute.call_args_list]
    has_opening_receive = any(
        'INSERT INTO inventory_transactions' in statement
        for statement in statements
    )
    assert has_opening_receive is expects_opening_receive


def test_lot_form_blocks_negative_and_fractional_opening_quantities():
    html = (ROOT / 'lot_inventory.html').read_text()
    assert 'id="initial-qty" min="0" step="1"' in html
    assert '!Number.isInteger(initialQty) || initialQty < 0' in html
    assert 'Initial Quantity must be zero or a positive whole number' in html


def test_large_receive_does_not_require_notes():
    import app as dashboard_app

    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.side_effect = [
        (None, 'active', 0, '17612'),
        (77,),
        (200,),
    ]
    conn.cursor.return_value = cursor

    with patch('app.get_connection', return_value=conn), \
         patch(
             'app.schedule_backorder_retry_after_inventory_available',
             return_value=True,
         ):
        with dashboard_app.app.test_request_context(
            '/api/inventory_transactions',
            method='POST',
            json={
                'date': '2026-09-17',
                'sku': '17612',
                'quantity': 200,
                'transaction_type': 'Receive',
                'notes': '',
                'lot_id': 19,
            },
        ):
            response = dashboard_app.api_create_inventory_transaction()

    assert response.status_code == 200
    assert response.get_json()['success'] is True
    conn.commit.assert_called_once()


def test_supplier_lot_note_validation_is_removed_from_create_and_update():
    assert 'LOT_NUMBER_REQUIRED_QTY' not in APP
    assert 'Lot number required: Receive transactions' not in APP
    assert 'Invalid lot reference:' not in APP