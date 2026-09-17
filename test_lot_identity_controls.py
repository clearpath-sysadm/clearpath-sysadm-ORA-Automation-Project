"""Regression coverage for canonical SKU-lot identity controls."""

from pathlib import Path
from unittest.mock import MagicMock, patch


ROOT = Path(__file__).resolve().parent
APP_SOURCE = (ROOT / "app.py").read_text()
HTML = (ROOT / "lot_inventory.html").read_text()
LEGACY_INVENTORY_HTML = (ROOT / "inventory.html").read_text()
STARTUP = (ROOT / "src/services/database/startup_migrations.py").read_text()


def _admin():
    user = MagicMock(is_authenticated=True, role="admin")
    user.email = "admin@example.test"
    return user


def _lot_row(status="active", balance=10):
    return ("17612", "LOT-1", status, "v1", None, balance)


def _impact_row(
    balance=0, transactions=0, lines=0, reservations=0, active=0,
    alerts=0, lifecycle_events=0
):
    return (
        "17612", "LOT-1", "inactive", "v1", None, balance,
        transactions, lines, reservations, active, alerts, lifecycle_events,
    )


def test_normal_assignment_edit_cannot_change_identity():
    import app as dashboard_app

    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.side_effect = [("17612",), _lot_row()]
    conn.cursor.return_value = cursor

    with patch("app.get_connection", return_value=conn):
        with dashboard_app.app.test_request_context(
            "/api/sku_lots/19",
            method="PUT",
            json={
                "sku": "17904", "lot": "LOT-2", "active": 1,
                "expected_updated_at": "v1",
            },
        ):
            response, status = dashboard_app.api_update_sku_lot(19)

    assert status == 409
    assert "cannot change SKU or lot number" in response.get_json()["error"]
    conn.commit.assert_not_called()
    assert not any(
        "UPDATE lots" in call.args[0] for call in cursor.execute.call_args_list
    )


def test_status_activation_requires_positive_balance():
    import app as dashboard_app

    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.side_effect = [
        ("17612",), _lot_row(status="inactive", balance=0)
    ]
    conn.cursor.return_value = cursor

    with patch("app.get_connection", return_value=conn):
        with dashboard_app.app.test_request_context(
            "/api/sku_lots/19",
            method="PUT",
            json={"active": 1, "expected_updated_at": "v1"},
        ):
            response, status = dashboard_app.api_update_sku_lot(19)

    assert status == 400
    assert "balance is greater than zero" in response.get_json()["error"]
    conn.commit.assert_not_called()


def test_status_deactivation_rejects_active_reservations():
    import app as dashboard_app

    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.side_effect = [("17612",), _lot_row(), (2,)]
    conn.cursor.return_value = cursor

    with patch("app.get_connection", return_value=conn):
        with dashboard_app.app.test_request_context(
            "/api/sku_lots/19",
            method="PUT",
            json={"active": 0, "expected_updated_at": "v1"},
        ):
            response, status = dashboard_app.api_update_sku_lot(19)

    assert status == 409
    assert response.get_json()["active_reservations"] == 2
    conn.commit.assert_not_called()


def test_identity_impact_is_admin_only_before_database_access():
    import app as dashboard_app

    user = MagicMock(is_authenticated=True, role="operations")
    with patch("app.current_user", user), patch("app.get_connection") as connection:
        with dashboard_app.app.test_request_context(
            "/api/sku_lots/19/identity-impact"
        ):
            response, status = dashboard_app.api_sku_lot_identity_impact(19)

    assert status == 403
    connection.assert_not_called()


def test_status_update_requires_version_before_database_access():
    import app as dashboard_app

    with patch("app.get_connection") as connection:
        with dashboard_app.app.test_request_context(
            "/api/sku_lots/19", method="PUT", json={"active": 0}
        ):
            response, status = dashboard_app.api_update_sku_lot(19)

    assert status == 400
    assert "Refresh the lot" in response.get_json()["error"]
    connection.assert_not_called()


def test_identity_correction_rejects_any_historical_dependency():
    import app as dashboard_app

    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.side_effect = [
        ("17612", "LOT-1"),
        ("17612", "LOT-1", "v1", None),
        _impact_row(transactions=1),
    ]
    conn.cursor.return_value = cursor

    with patch("app.current_user", _admin()), \
         patch("app.get_connection", return_value=conn):
        with dashboard_app.app.test_request_context(
            "/api/sku_lots/19/correct-identity",
            method="POST",
            json={
                "sku": "17904",
                "lot": "LOT-2",
                "reason": "Correct data entry",
                "expected_updated_at": "v1",
            },
        ):
            response, status = dashboard_app.api_correct_sku_lot_identity(19)

    assert status == 409
    assert response.get_json()["dependencies"]["transaction_count"] == 1
    conn.commit.assert_not_called()


def test_unused_lot_identity_correction_is_atomic_and_audited():
    import app as dashboard_app

    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.side_effect = [
        ("17612", "LOT-1"),
        ("17612", "LOT-1", "v1", None),
        _impact_row(),
        (2,),
        None,
    ]
    conn.cursor.return_value = cursor

    with patch("app.current_user", _admin()), \
         patch("app.get_connection", return_value=conn):
        with dashboard_app.app.test_request_context(
            "/api/sku_lots/19/correct-identity",
            method="POST",
            headers={"X-Request-ID": "request-123"},
            json={
                "sku": "17904",
                "lot": "LOT-2",
                "reason": "Correct data entry",
                "expected_updated_at": "v1",
            },
        ):
            response = dashboard_app.api_correct_sku_lot_identity(19)

    assert response.status_code == 200
    assert response.get_json()["request_id"] == "request-123"
    conn.commit.assert_called_once()
    statements = [call.args[0] for call in cursor.execute.call_args_list]
    assert any("UPDATE lots" in statement for statement in statements)
    audit_call = next(
        call for call in cursor.execute.call_args_list
        if "INSERT INTO inventory_lifecycle_events" in call.args[0]
    )
    assert audit_call.args[1][2] == "identity_correct"
    assert "request-123" in audit_call.args[1][5]


def test_identity_correction_rolls_back_when_audit_insert_fails():
    import app as dashboard_app

    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.side_effect = [
        ("17612", "LOT-1"),
        ("17612", "LOT-1", "v1", None),
        _impact_row(),
        (2,),
        None,
    ]

    def execute(sql, params=None):
        if "INSERT INTO inventory_lifecycle_events" in sql:
            raise RuntimeError("audit unavailable")

    cursor.execute.side_effect = execute
    conn.cursor.return_value = cursor

    with patch("app.current_user", _admin()), \
         patch("app.get_connection", return_value=conn):
        with dashboard_app.app.test_request_context(
            "/api/sku_lots/19/correct-identity",
            method="POST",
            json={
                "sku": "17904",
                "lot": "LOT-2",
                "reason": "Correct data entry",
                "expected_updated_at": "v1",
            },
        ):
            response, status = dashboard_app.api_correct_sku_lot_identity(19)

    assert status == 500
    assert response.get_json()["error"] == "audit unavailable"
    conn.rollback.assert_called_once()
    conn.commit.assert_not_called()
    conn.close.assert_called_once()


def test_assignment_ui_distinguishes_status_from_identity_correction():
    assert "underlying SKU–lot records" in HTML
    assert "Normal edits change status only" in HTML
    assert "Correct Identity" in HTML
    assert "/correct-identity" in HTML
    assert "/identity-impact" in HTML
    assert "expected_updated_at" in HTML


def test_every_active_assignment_page_uses_status_only_versioned_updates():
    assert "Normal edits change status only" in LEGACY_INVENTORY_HTML
    assert "Change Lot Status" in LEGACY_INVENTORY_HTML
    assert "expected_updated_at: expectedUpdatedAt" in LEGACY_INVENTORY_HTML
    assert "expected_updated_at: item.updated_at" in LEGACY_INVENTORY_HTML
    assert "sku-lot-sku').disabled = true" in LEGACY_INVENTORY_HTML
    assert "sku-lot-lot').disabled = true" in LEGACY_INVENTORY_HTML
    assert "JSON.stringify({ sku: item.sku, lot: item.lot" not in LEGACY_INVENTORY_HTML


def test_lifecycle_schema_allows_identity_and_status_events():
    assert "'identity_correct','status_change'" in STARTUP
    assert "DROP CONSTRAINT IF EXISTS inventory_lifecycle_events_action_check" in STARTUP