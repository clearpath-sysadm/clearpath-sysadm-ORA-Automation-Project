"""Regression coverage for safe ShipStation batch creation and reconciliation."""
from unittest.mock import MagicMock, patch

import requests

import src.scheduled_batch_processor as processor
from src.services.shipstation import api_client


def _connection_with_rows(rows):
    connection = MagicMock()
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.fetchall.return_value = rows
    return connection


def test_api_refuses_to_create_empty_batch():
    with patch.object(api_client.requests, "post") as request:
        result = api_client.v2_create_batch([])
    assert result == {
        "success": False,
        "error": "At least one shipment ID is required",
    }
    request.assert_not_called()


def test_api_treats_missing_batch_id_as_ambiguous():
    response = MagicMock()
    response.json.return_value = {"count": 2}
    with patch.object(api_client.requests, "post", return_value=response):
        result = api_client.v2_create_batch(["s1", "s2"])
    assert result["success"] is False
    assert result["ambiguous"] is True


def test_api_treats_server_error_as_ambiguous():
    response = MagicMock(status_code=503, text="temporarily unavailable")
    response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        response=response
    )
    with patch.object(api_client.requests, "post", return_value=response):
        result = api_client.v2_create_batch(["s1"])
    assert result["success"] is False
    assert result["ambiguous"] is True


def test_batch_delete_timeout_is_not_retried_inside_api_helper():
    with patch.object(
        api_client.requests,
        "delete",
        side_effect=requests.exceptions.Timeout("timed out"),
    ) as request:
        result = api_client.v2_delete_batch("source")

    assert result["success"] is False
    assert result["ambiguous"] is True
    request.assert_called_once()


def test_batch_read_rejects_missing_shipment_count():
    response = MagicMock()
    response.json.return_value = {
        "batch_id": "source",
        "batch_status": "open",
        "external_batch_id": "oracare-axiom-2026-09-21",
    }
    with patch.object(api_client, "make_api_request", return_value=response):
        result = api_client.v2_get_batch("source")

    assert result["success"] is False
    assert result["error_type"] == "invalid_response"


def _api_response(data, status_code=200):
    response = MagicMock(status_code=status_code, text="")
    response.json.return_value = data
    return response


def test_pending_axiom_shipments_require_axiom_ship_from_and_assignee():
    users = _api_response(
        {
            "users": [
                {"user_id": "axiom-user", "name": "Axiom Team"},
                {"user_id": "oracare-user", "name": "Oracare Team"},
            ],
            "pages": 1,
        }
    )
    shipments = _api_response(
        {
            "shipments": [
                {
                    "shipment_id": "eligible",
                    "shipment_status": "pending",
                    "warehouse_id": "se-299625",
                    "assigned_user": "axiom-user",
                },
                {
                    "shipment_id": "home-office",
                    "shipment_status": "pending",
                    "warehouse_id": "se-566121",
                    "assigned_user": "axiom-user",
                },
                {
                    "shipment_id": "oracare",
                    "shipment_status": "pending",
                    "warehouse_id": "se-299625",
                    "assigned_user": "oracare-user",
                },
                {
                    "shipment_id": "unassigned",
                    "shipment_status": "pending",
                    "warehouse_id": "se-299625",
                    "assigned_user": None,
                },
                {
                    "shipment_id": "already-shipped",
                    "shipment_status": "shipped",
                    "warehouse_id": "se-299625",
                    "assigned_user": "axiom-user",
                },
                {
                    "shipment_id": "missing-status",
                    "warehouse_id": "se-299625",
                    "assigned_user": "axiom-user",
                },
            ],
            "pages": 1,
        }
    )
    with patch.dict("os.environ", {"PRODUCTION_KEY": "test-key"}), patch.object(
        api_client, "make_api_request", side_effect=[users, shipments]
    ):
        result = api_client.v2_get_pending_axiom_shipments()

    assert result == {
        "success": True,
        "shipment_ids": ["eligible"],
        "excluded_counts": {
            "non_pending_status": 2,
            "non_axiom_ship_from": 1,
            "non_axiom_assignee": 1,
            "missing_assignee": 1,
        },
    }


def test_pending_axiom_shipments_fail_closed_without_unique_axiom_team():
    users = _api_response(
        {
            "users": [{"user_id": "oracare-user", "name": "Oracare Team"}],
            "pages": 1,
        }
    )
    with patch.dict("os.environ", {"PRODUCTION_KEY": "test-key"}), patch.object(
        api_client, "make_api_request", return_value=users
    ):
        result = api_client.v2_get_pending_axiom_shipments()

    assert result["success"] is False
    assert "exactly one" in result["error"]


def test_pending_axiom_shipments_preserve_shipment_pagination():
    users = _api_response(
        {
            "users": [{"user_id": "axiom-user", "name": "Axiom Team"}],
            "pages": 1,
        }
    )
    page_one = _api_response(
        {
            "shipments": [
                {
                    "shipment_id": "s1",
                    "shipment_status": "pending",
                    "warehouse_id": "se-299625",
                    "assigned_user": "axiom-user",
                }
            ],
            "pages": 2,
        }
    )
    page_two = _api_response(
        {
            "shipments": [
                {
                    "shipment_id": "s2",
                    "shipment_status": "pending",
                    "warehouse_id": "se-299625",
                    "assigned_user": "axiom-user",
                }
            ],
            "pages": 2,
        }
    )
    with patch.dict("os.environ", {"PRODUCTION_KEY": "test-key"}), patch.object(
        api_client,
        "make_api_request",
        side_effect=[users, page_one, page_two],
    ):
        result = api_client.v2_get_pending_axiom_shipments()

    assert result["success"] is True
    assert result["shipment_ids"] == ["s1", "s2"]


def test_pending_axiom_shipments_preserve_user_pagination():
    users_page_one = _api_response(
        {
            "users": [{"user_id": "oracare-user", "name": "Oracare Team"}],
            "pages": 2,
        }
    )
    users_page_two = _api_response(
        {
            "users": [{"user_id": "axiom-user", "name": "Axiom Team"}],
            "pages": 2,
        }
    )
    shipments = _api_response(
        {
            "shipments": [
                {
                    "shipment_id": "s1",
                    "shipment_status": "pending",
                    "warehouse_id": "se-299625",
                    "assigned_user": "axiom-user",
                }
            ],
            "pages": 1,
        }
    )
    with patch.dict("os.environ", {"PRODUCTION_KEY": "test-key"}), patch.object(
        api_client,
        "make_api_request",
        side_effect=[users_page_one, users_page_two, shipments],
    ):
        result = api_client.v2_get_pending_axiom_shipments()

    assert result["success"] is True
    assert result["shipment_ids"] == ["s1"]


def test_empty_pending_queue_does_not_create_batch():
    with patch.object(
        processor,
        "v2_get_pending_axiom_shipments",
        return_value={"success": True, "shipment_ids": []},
    ), patch.object(processor, "v2_create_batch") as create, patch.object(
        processor, "_already_batched_today", return_value=False
    ), patch.object(processor, "_is_dev_blocked", return_value=False), patch.object(
        processor, "update_workflow_last_run"
    ):
        assert processor._run_batch_job_locked() == "skipped"
    create.assert_not_called()


def test_batch_creation_uses_stable_identity_and_notes():
    with patch.object(
        processor,
        "v2_get_pending_axiom_shipments",
        return_value={"success": True, "shipment_ids": ["s1", "s2"]},
    ), patch.object(
        processor,
        "v2_get_batch_by_external_id",
        return_value={"success": False, "error_type": "not_found"},
    ), patch.object(
        processor,
        "v2_create_batch",
        return_value={"success": True, "batch_id": "b1"},
    ) as create, patch.object(
        processor, "_record_batch_run", return_value=True
    ) as record, patch.object(
        processor, "_verify_batch", return_value="ok"
    ), patch.object(
        processor, "_mark_batch_verified"
    ), patch.object(
        processor, "_already_batched_today", return_value=False
    ), patch.object(
        processor, "_is_dev_blocked", return_value=False
    ), patch.object(
        processor, "_get_batch_run_status", return_value=None
    ), patch.object(
        processor, "_claim_batch_run", return_value=True
    ), patch.object(
        processor, "update_workflow_last_run"
    ):
        assert processor._run_batch_job_locked() == "completed"

    external_id = create.call_args.kwargs["external_batch_id"]
    assert external_id.startswith("oracare-axiom-")
    assert "Oracare automated Axiom batch" in create.call_args.kwargs["batch_notes"]
    assert record.call_args.args[1:] == ("b1", external_id, ["s1", "s2"])


def test_existing_external_batch_prevents_duplicate_post():
    with patch.object(
        processor,
        "v2_get_pending_axiom_shipments",
        return_value={"success": True, "shipment_ids": ["new-pending"]},
    ) as pending, patch.object(
        processor,
        "v2_get_batch_by_external_id",
        return_value={"success": True, "batch_id": "existing", "shipment_count": 1},
    ), patch.object(processor, "v2_create_batch") as create, patch.object(
        processor, "_record_batch_run", return_value=True
    ), patch.object(processor, "_mark_batch_verified"), patch.object(
        processor, "_already_batched_today", return_value=False
    ), patch.object(
        processor, "_get_batch_run_status", return_value=None
    ), patch.object(
        processor,
        "v2_get_batch_shipment_ids",
        return_value={"success": True, "shipment_ids": ["original"]},
    ), patch.object(processor, "_is_dev_blocked", return_value=False):
        assert processor._run_batch_job_locked() == "completed"
    create.assert_not_called()
    pending.assert_not_called()


def test_creation_lock_blocks_competing_instance():
    with patch.object(processor, "_ensure_batch_run_storage", return_value=True), patch.object(
        processor, "_acquire_batch_lock", return_value=None
    ), patch.object(processor, "_run_batch_job_locked") as run:
        assert processor.run_batch_job() == "skipped_locked"
    run.assert_not_called()


def test_reconciliation_observes_proven_replacement_without_deleting():
    row = (
        "2026-09-21",
        "oracare-axiom-2026-09-21",
        "source",
        ["s1", "s2"],
        "verified",
        None,
    )
    connection = _connection_with_rows([row])
    with patch.object(processor, "get_connection", return_value=connection), patch.object(
        processor,
        "v2_get_batch",
        side_effect=[
            {
                "success": True,
                "shipment_count": 0,
                "external_batch_id": row[1],
                "status": "open",
            },
            {"success": True, "shipment_count": 2},
        ],
    ), patch.object(
        processor,
        "v2_get_shipment_batch_assignments",
        return_value={
            "success": True,
            "assignments": {"s1": ["replacement"], "s2": ["replacement"]},
        },
    ), patch.object(
        processor,
        "v2_get_batch_shipment_ids",
        return_value={"success": True, "shipment_ids": ["s1", "s2"]},
    ), patch.object(processor, "_set_reconciliation_state") as state, patch.object(
        processor, "v2_delete_batch"
    ) as delete, patch.object(
        processor, "EMPTY_BATCH_CLEANUP_ENABLED", False
    ):
        processor._reconcile_recent_batches()

    delete.assert_not_called()
    state.assert_called_once_with(
        row[0], "observed_empty", "replacement", update_daily_record=True
    )


def test_reconciliation_refuses_partial_or_split_movement():
    row = (
        "2026-09-21",
        "oracare-axiom-2026-09-21",
        "source",
        ["s1", "s2"],
        "verified",
        None,
    )
    connection = _connection_with_rows([row])
    with patch.object(processor, "get_connection", return_value=connection), patch.object(
        processor,
        "v2_get_batch",
        return_value={
            "success": True,
            "shipment_count": 0,
            "external_batch_id": row[1],
            "status": "open",
        },
    ), patch.object(
        processor,
        "v2_get_shipment_batch_assignments",
        return_value={
            "success": True,
            "assignments": {"s1": ["replacement"], "s2": []},
        },
    ), patch.object(processor, "_set_reconciliation_state") as state, patch.object(
        processor, "v2_delete_batch"
    ) as delete:
        processor._reconcile_recent_batches()

    delete.assert_not_called()
    state.assert_called_once_with(row[0], "uncertain")


def test_reconciliation_refuses_shipments_assigned_to_multiple_replacements():
    row = (
        "2026-09-21",
        "oracare-axiom-2026-09-21",
        "source",
        ["s1", "s2"],
        "verified",
        None,
    )
    connection = _connection_with_rows([row])
    with patch.object(processor, "get_connection", return_value=connection), patch.object(
        processor,
        "v2_get_batch",
        return_value={
            "success": True,
            "shipment_count": 0,
            "external_batch_id": row[1],
            "status": "open",
        },
    ), patch.object(
        processor,
        "v2_get_shipment_batch_assignments",
        return_value={
            "success": True,
            "assignments": {
                "s1": ["replacement", "other"],
                "s2": ["replacement"],
            },
        },
    ), patch.object(processor, "_set_reconciliation_state") as state, patch.object(
        processor, "v2_delete_batch"
    ) as delete:
        processor._reconcile_recent_batches()

    delete.assert_not_called()
    state.assert_called_once_with(row[0], "uncertain")


def test_reconciliation_refuses_assignment_still_listing_source_batch():
    row = (
        "2026-09-21",
        "oracare-axiom-2026-09-21",
        "source",
        ["s1"],
        "observed_empty",
        "replacement",
    )
    connection = _connection_with_rows([row])
    with patch.object(processor, "get_connection", return_value=connection), patch.object(
        processor,
        "v2_get_batch",
        return_value={
            "success": True,
            "shipment_count": 0,
            "external_batch_id": row[1],
            "status": "open",
        },
    ), patch.object(
        processor,
        "v2_get_shipment_batch_assignments",
        return_value={
            "success": True,
            "assignments": {"s1": ["source", "replacement"]},
        },
    ), patch.object(processor, "_set_reconciliation_state") as state, patch.object(
        processor, "v2_delete_batch"
    ) as delete, patch.object(processor, "EMPTY_BATCH_CLEANUP_ENABLED", True):
        processor._reconcile_recent_batches()

    delete.assert_not_called()
    state.assert_called_once_with(row[0], "uncertain")


def test_reconciliation_refuses_source_as_its_own_replacement():
    row = (
        "2026-09-21",
        "oracare-axiom-2026-09-21",
        "source",
        ["s1"],
        "observed_empty",
        "replacement",
    )
    connection = _connection_with_rows([row])
    with patch.object(processor, "get_connection", return_value=connection), patch.object(
        processor,
        "v2_get_batch",
        return_value={
            "success": True,
            "shipment_count": 0,
            "external_batch_id": row[1],
            "status": "open",
        },
    ), patch.object(
        processor,
        "v2_get_shipment_batch_assignments",
        return_value={"success": True, "assignments": {"s1": ["source"]}},
    ), patch.object(
        processor, "v2_get_batch_shipment_ids"
    ) as list_shipments, patch.object(
        processor, "_set_reconciliation_state"
    ) as state, patch.object(
        processor, "v2_delete_batch"
    ) as delete, patch.object(
        processor, "EMPTY_BATCH_CLEANUP_ENABLED", True
    ):
        processor._reconcile_recent_batches()

    list_shipments.assert_not_called()
    delete.assert_not_called()
    state.assert_called_once_with(row[0], "uncertain")


def test_reconciliation_refuses_missing_source_shipment_count():
    row = (
        "2026-09-21",
        "oracare-axiom-2026-09-21",
        "source",
        ["s1"],
        "observed_empty",
        "replacement",
    )
    connection = _connection_with_rows([row])
    with patch.object(processor, "get_connection", return_value=connection), patch.object(
        processor,
        "v2_get_batch",
        return_value={
            "success": True,
            "external_batch_id": row[1],
            "status": "open",
        },
    ), patch.object(processor, "_set_reconciliation_state") as state, patch.object(
        processor, "v2_get_shipment_batch_assignments"
    ) as assignments, patch.object(
        processor, "v2_delete_batch"
    ) as delete, patch.object(processor, "EMPTY_BATCH_CLEANUP_ENABLED", True):
        processor._reconcile_recent_batches()

    assignments.assert_not_called()
    delete.assert_not_called()
    state.assert_called_once_with(row[0], "uncertain")


def test_ambiguous_create_retains_claim_for_external_id_recovery():
    with patch.object(
        processor,
        "v2_get_pending_axiom_shipments",
        return_value={"success": True, "shipment_ids": ["s1"]},
    ), patch.object(
        processor,
        "v2_get_batch_by_external_id",
        return_value={"success": False, "error_type": "not_found"},
    ), patch.object(
        processor,
        "v2_create_batch",
        return_value={"success": False, "error": "timeout", "ambiguous": True},
    ), patch.object(
        processor, "_clear_definite_failed_claim"
    ) as clear, patch.object(
        processor, "_claim_batch_run", return_value=True
    ), patch.object(
        processor, "_already_batched_today", return_value=False
    ), patch.object(
        processor, "_get_batch_run_status", return_value=None
    ), patch.object(
        processor, "_is_dev_blocked", return_value=False
    ):
        assert processor._run_batch_job_locked() == "error"
    clear.assert_not_called()


def test_definite_create_rejection_releases_claim():
    with patch.object(
        processor,
        "v2_get_pending_axiom_shipments",
        return_value={"success": True, "shipment_ids": ["s1"]},
    ), patch.object(
        processor,
        "v2_get_batch_by_external_id",
        return_value={"success": False, "error_type": "not_found"},
    ), patch.object(
        processor,
        "v2_create_batch",
        return_value={"success": False, "error": "400", "ambiguous": False},
    ), patch.object(
        processor, "_clear_definite_failed_claim"
    ) as clear, patch.object(
        processor, "_claim_batch_run", return_value=True
    ), patch.object(
        processor, "_already_batched_today", return_value=False
    ), patch.object(
        processor, "_get_batch_run_status", return_value=None
    ), patch.object(
        processor, "_is_dev_blocked", return_value=False
    ):
        assert processor._run_batch_job_locked() == "error"
    assert clear.call_args.args[1].startswith("oracare-axiom-")


def test_nonempty_source_becomes_terminal_stable_observation():
    row = (
        "2026-09-21",
        "oracare-axiom-2026-09-21",
        "source",
        ["s1"],
        "verified",
        None,
    )
    connection = _connection_with_rows([row])
    with patch.object(processor, "get_connection", return_value=connection), patch.object(
        processor,
        "v2_get_batch",
        return_value={
            "success": True,
            "shipment_count": 1,
            "external_batch_id": row[1],
            "status": "open",
        },
    ), patch.object(processor, "_set_reconciliation_state") as state, patch.object(
        processor, "v2_get_shipment_batch_assignments"
    ) as assignments:
        processor._reconcile_recent_batches()
    state.assert_called_once_with(row[0], "stable")
    assignments.assert_not_called()


def test_enabled_cleanup_still_observes_before_deleting():
    row = (
        "2026-09-21",
        "oracare-axiom-2026-09-21",
        "source",
        ["s1", "s2"],
        "verified",
        None,
    )
    connection = _connection_with_rows([row])
    with patch.object(processor, "get_connection", return_value=connection), patch.object(
        processor,
        "v2_get_batch",
        side_effect=[
            {
                "success": True,
                "shipment_count": 0,
                "external_batch_id": row[1],
                "status": "open",
            },
            {"success": True, "shipment_count": 2},
        ],
    ), patch.object(
        processor,
        "v2_get_shipment_batch_assignments",
        return_value={
            "success": True,
            "assignments": {"s1": ["replacement"], "s2": ["replacement"]},
        },
    ), patch.object(
        processor,
        "v2_get_batch_shipment_ids",
        return_value={"success": True, "shipment_ids": ["s1", "s2"]},
    ), patch.object(processor, "_set_reconciliation_state") as state, patch.object(
        processor, "v2_delete_batch"
    ) as delete, patch.object(processor, "EMPTY_BATCH_CLEANUP_ENABLED", True):
        processor._reconcile_recent_batches()

    delete.assert_not_called()
    state.assert_called_once_with(
        row[0], "observed_empty", "replacement", update_daily_record=True
    )


def test_enabled_cleanup_deletes_only_after_recorded_observation():
    row = (
        "2026-09-21",
        "oracare-axiom-2026-09-21",
        "source",
        ["s1", "s2"],
        "observed_empty",
        "replacement",
    )
    connection = _connection_with_rows([row])
    with patch.object(processor, "get_connection", return_value=connection), patch.object(
        processor,
        "v2_get_batch",
        side_effect=[
            {
                "success": True,
                "shipment_count": 0,
                "external_batch_id": row[1],
                "status": "open",
            },
            {"success": True, "shipment_count": 2},
        ],
    ), patch.object(
        processor,
        "v2_get_shipment_batch_assignments",
        return_value={
            "success": True,
            "assignments": {"s1": ["replacement"], "s2": ["replacement"]},
        },
    ), patch.object(
        processor,
        "v2_get_batch_shipment_ids",
        return_value={"success": True, "shipment_ids": ["s1", "s2"]},
    ), patch.object(
        processor, "v2_delete_batch", return_value={"success": True}
    ) as delete, patch.object(
        processor, "_set_reconciliation_state"
    ) as state, patch.object(
        processor, "EMPTY_BATCH_CLEANUP_ENABLED", True
    ):
        processor._reconcile_recent_batches()

    delete.assert_called_once_with("source")
    state.assert_called_once_with(
        row[0], "retired", "replacement", update_daily_record=True
    )


def test_failed_delete_remains_observed_for_later_retry():
    row = (
        "2026-09-21",
        "oracare-axiom-2026-09-21",
        "source",
        ["s1"],
        "observed_empty",
        "replacement",
    )
    connection = _connection_with_rows([row])
    with patch.object(processor, "get_connection", return_value=connection), patch.object(
        processor,
        "v2_get_batch",
        side_effect=[
            {
                "success": True,
                "shipment_count": 0,
                "external_batch_id": row[1],
                "status": "open",
            },
            {"success": True, "shipment_count": 1},
        ],
    ), patch.object(
        processor,
        "v2_get_shipment_batch_assignments",
        return_value={"success": True, "assignments": {"s1": ["replacement"]}},
    ), patch.object(
        processor,
        "v2_get_batch_shipment_ids",
        return_value={"success": True, "shipment_ids": ["s1"]},
    ), patch.object(
        processor, "v2_delete_batch", return_value={"success": False, "error": "timeout"}
    ), patch.object(
        processor, "_set_reconciliation_state"
    ) as state, patch.object(
        processor, "EMPTY_BATCH_CLEANUP_ENABLED", True
    ):
        processor._reconcile_recent_batches()

    state.assert_called_once_with(
        row[0], "observed_empty", "replacement", update_daily_record=True
    )


def test_changed_replacement_restarts_observation_delay():
    row = (
        "2026-09-21",
        "oracare-axiom-2026-09-21",
        "source",
        ["s1"],
        "observed_empty",
        "old-replacement",
    )
    connection = _connection_with_rows([row])
    with patch.object(processor, "get_connection", return_value=connection), patch.object(
        processor,
        "v2_get_batch",
        side_effect=[
            {
                "success": True,
                "shipment_count": 0,
                "external_batch_id": row[1],
                "status": "open",
            },
            {"success": True, "shipment_count": 1},
        ],
    ), patch.object(
        processor,
        "v2_get_shipment_batch_assignments",
        return_value={"success": True, "assignments": {"s1": ["new-replacement"]}},
    ), patch.object(
        processor,
        "v2_get_batch_shipment_ids",
        return_value={"success": True, "shipment_ids": ["s1"]},
    ), patch.object(processor, "_set_reconciliation_state") as state, patch.object(
        processor, "v2_delete_batch"
    ) as delete, patch.object(processor, "EMPTY_BATCH_CLEANUP_ENABLED", True):
        processor._reconcile_recent_batches()

    delete.assert_not_called()
    state.assert_called_once_with(
        row[0], "observed_empty", "new-replacement", update_daily_record=True
    )


def test_missing_previously_observed_source_is_recorded_as_retired():
    row = (
        "2026-09-21",
        "oracare-axiom-2026-09-21",
        "source",
        ["s1"],
        "observed_empty",
        "replacement",
    )
    connection = _connection_with_rows([row])
    with patch.object(processor, "get_connection", return_value=connection), patch.object(
        processor,
        "v2_get_batch",
        return_value={"success": False, "error_type": "not_found"},
    ), patch.object(processor, "_set_reconciliation_state") as state, patch.object(
        processor, "v2_delete_batch"
    ) as delete, patch.object(processor, "EMPTY_BATCH_CLEANUP_ENABLED", True):
        processor._reconcile_recent_batches()

    delete.assert_not_called()
    state.assert_called_once_with(
        row[0], "retired", "replacement", update_daily_record=True
    )