from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


HTML = (Path(__file__).resolve().parent / "inventory_transactions.html").read_text()


@pytest.mark.parametrize(
    ("transaction_type", "status", "balance", "expected"),
    [
        ("Receive", "active", 0, True),
        ("Receive", "depleted", 0, True),
        ("Receive", "inactive", 5, False),
        ("Receive", "quarantine", 5, False),
        ("Ship", "active", 5, True),
        ("Ship", "active", 0, False),
        ("Ship", "depleted", 5, False),
        ("Adjust Up", "quarantine", 0, True),
        ("Adjust Down", "inactive", 0, True),
        ("Repack", "depleted", 0, True),
        ("Cancel", "inactive", 0, True),
    ],
)
def test_lot_eligibility_rules(transaction_type, status, balance, expected):
    import app as dashboard_app

    assert (
        dashboard_app._lot_is_eligible_for_transaction(
            transaction_type, status, balance
        )
        is expected
    )


@pytest.mark.parametrize(
    ("transaction_type", "expected_ids"),
    [
        ("Receive", [1, 2, 3]),
        ("Ship", [1]),
        ("Adjust Up", [1, 2, 3, 4, 5]),
        ("Adjust Down", [1, 2, 3, 4, 5]),
        ("Repack", [1, 2, 3, 4, 5]),
        ("Cancel", [1, 2, 3, 4, 5]),
    ],
)
def test_lot_lookup_filters_by_transaction_type(transaction_type, expected_ids):
    import app as dashboard_app

    rows = [
        (1, "ACTIVE-STOCK", "active", "2026-01-01", 10, None),
        (2, "ACTIVE-EMPTY", "active", "2026-01-02", 0, None),
        (3, "DEPLETED", "depleted", "2026-01-03", 0, None),
        (4, "INACTIVE", "inactive", "2026-01-04", 4, None),
        (5, "QUARANTINE", "quarantine", "2026-01-05", 3, None),
        (6, "ARCHIVED", "active", "2026-01-06", 9, "2026-06-01"),
    ]
    conn = MagicMock()
    conn.cursor.return_value.fetchall.return_value = rows

    with patch("app.get_connection", return_value=conn):
        with dashboard_app.app.test_request_context(
            f"/api/lots_by_sku/17612?transaction_type={transaction_type}"
        ):
            response = dashboard_app.api_lots_by_sku("17612")

    assert response.status_code == 200
    assert [lot["lot_id"] for lot in response.get_json()] == expected_ids


def test_lookup_preserves_archived_saved_lot_for_editing():
    import app as dashboard_app

    conn = MagicMock()
    conn.cursor.return_value.fetchall.return_value = [
        (6, "ARCHIVED", "inactive", "2025-01-01", 0, "2026-01-01"),
    ]

    with patch("app.get_connection", return_value=conn):
        with dashboard_app.app.test_request_context(
            "/api/lots_by_sku/17612"
            "?transaction_type=Ship&include_lot_id=6"
        ):
            response = dashboard_app.api_lots_by_sku("17612")

    assert response.status_code == 200
    assert response.get_json() == [
        {
            "lot_id": 6,
            "lot_number": "ARCHIVED",
            "status": "inactive",
            "received_date": "2025-01-01",
            "balance": 0,
            "historical_selection": True,
        }
    ]


def test_create_rejects_stale_ineligible_lot_choice():
    import app as dashboard_app

    conn = MagicMock()
    cursor = conn.cursor.return_value
    cursor.fetchone.return_value = (None, "active", 0, "17612")

    with patch("app.get_connection", return_value=conn):
        with dashboard_app.app.test_request_context(
            "/api/inventory_transactions",
            method="POST",
            json={
                "date": "2026-09-21",
                "sku": "17612",
                "quantity": -1,
                "transaction_type": "Ship",
                "lot_id": 19,
            },
        ):
            response, status = dashboard_app.api_create_inventory_transaction()

    assert status == 409
    assert "not eligible" in response.get_json()["error"]
    conn.commit.assert_not_called()


def test_receiving_into_depleted_lot_reactivates_it():
    import app as dashboard_app

    conn = MagicMock()
    cursor = conn.cursor.return_value
    cursor.fetchone.side_effect = [
        (None, "depleted", 0, "17612"),
        (88,),
        (2000,),
    ]

    with patch("app.get_connection", return_value=conn), patch(
        "app.schedule_backorder_retry_after_inventory_available",
        return_value=True,
    ):
        with dashboard_app.app.test_request_context(
            "/api/inventory_transactions",
            method="POST",
            json={
                "date": "2026-09-21",
                "sku": "17612",
                "quantity": 2000,
                "transaction_type": "Receive",
                "lot_id": 19,
            },
        ):
            response = dashboard_app.api_create_inventory_transaction()

    assert response.status_code == 200
    reactivation = [
        call
        for call in cursor.execute.call_args_list
        if "SET status = 'active'" in call.args[0]
    ]
    assert len(reactivation) == 1
    assert reactivation[0].args[1] == (19,)
    conn.commit.assert_called_once()


def test_cancel_reactivates_depleted_lot_when_balance_is_restored():
    import app as dashboard_app

    conn = MagicMock()
    cursor = conn.cursor.return_value
    cursor.fetchone.side_effect = [
        (None, "depleted", 0, "17612"),
        (89,),
        (12,),
    ]

    with patch("app.get_connection", return_value=conn):
        with dashboard_app.app.test_request_context(
            "/api/inventory_transactions",
            method="POST",
            json={
                "date": "2026-09-21",
                "sku": "17612",
                "quantity": 12,
                "transaction_type": "Cancel",
                "lot_id": 19,
            },
        ):
            response = dashboard_app.api_create_inventory_transaction()

    assert response.status_code == 200
    assert any(
        "SET status = 'active'" in call.args[0]
        for call in cursor.execute.call_args_list
    )
    conn.commit.assert_called_once()


@pytest.mark.parametrize("transaction_type", ["Receive", "Cancel"])
def test_update_reactivates_depleted_lot_after_inventory_is_restored(
    transaction_type,
):
    import app as dashboard_app

    conn = MagicMock()
    cursor = conn.cursor.return_value
    cursor.fetchone.side_effect = [
        ("17612", 5, "Adjust Up", None, 19),
        (None, "depleted", 0, "17612"),
        (8,),
    ]

    with patch("app.get_connection", return_value=conn), patch(
        "app.schedule_backorder_retry_after_inventory_available",
        return_value=True,
    ):
        with dashboard_app.app.test_request_context(
            "/api/inventory_transactions/77",
            method="PUT",
            json={
                "date": "2026-09-21",
                "sku": "17612",
                "quantity": 8,
                "transaction_type": transaction_type,
                "lot_id": 19,
            },
        ):
            response = dashboard_app.api_update_inventory_transaction(77)

    assert response.status_code == 200
    assert any(
        "SET status = 'active'" in call.args[0]
        for call in cursor.execute.call_args_list
    )
    conn.commit.assert_called_once()


def test_transaction_form_orders_type_before_lot_and_explains_options():
    assert HTML.index('id="transactionType"') < HTML.index('id="transactionLot"')
    assert 'option value="Cancel"' in HTML
    assert "transaction_type: transactionType" in HTML
    assert "include_lot_id" in HTML
    assert "Available lots" in HTML
    assert "Depleted / zero-balance lots" in HTML
    assert "Restricted lots" in HTML
    assert "does not update a lot balance" in HTML