import unittest
from unittest.mock import patch

from requests import Response
from requests.exceptions import HTTPError

from src.services.order_reconciliation import reconcile_orphaned_orders


class FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


class FakeCursor:
    def __init__(self, orders):
        self.orders = orders
        self.executions = []

    def execute(self, query, params=None):
        self.executions.append((" ".join(query.split()), params))

    def fetchall(self):
        return self.orders


class FakeConnection:
    def __init__(self, orders):
        self.cursor_instance = FakeCursor(orders)

    def cursor(self):
        return self.cursor_instance


class OrderReconciliationTests(unittest.TestCase):
    def run_reconciliation(self, response, local_status="pending"):
        conn = FakeConnection([(7, "862283", local_status, "278284894")])
        request_patch = {
            "side_effect": response
        } if isinstance(response, Exception) else {
            "return_value": response
        }
        with (
            patch(
                "src.services.order_reconciliation.get_shipstation_credentials",
                return_value=("key", "secret"),
            ),
            patch(
                "src.services.order_reconciliation.get_shipstation_headers",
                return_value={},
            ),
            patch(
                "src.services.order_reconciliation.make_api_request",
                **request_patch,
            ),
        ):
            summary = reconcile_orphaned_orders(
                conn,
                stale_before_hours=24,
                max_orders=25,
            )
        return summary, conn.cursor_instance.executions

    def test_missing_order_becomes_non_pickable_without_deletion(self):
        response = Response()
        response.status_code = 404
        summary, executions = self.run_reconciliation(
            HTTPError("404 Client Error", response=response)
        )

        self.assertEqual(summary["updated_to_not_found"], 1)
        self.assertTrue(
            any("SET status = 'not_found'" in query for query, _ in executions)
        )
        self.assertTrue(
            any(
                params == (7,)
                and "Order no longer exists in ShipStation" in query
                for query, params in executions
            )
        )
        self.assertFalse(any(query.startswith("DELETE") for query, _ in executions))

    def test_shipped_order_moves_to_terminal_status(self):
        summary, executions = self.run_reconciliation(
            FakeResponse(200, {"orderStatus": "shipped"})
        )

        self.assertEqual(summary["updated_to_shipped"], 1)
        self.assertTrue(
            any(
                "SET status = %s" in query and params == ("shipped", 7)
                for query, params in executions
            )
        )

    def test_confirmed_open_order_stays_pending_and_is_refreshed(self):
        summary, executions = self.run_reconciliation(
            FakeResponse(200, {"orderStatus": "awaiting_shipment"})
        )

        self.assertEqual(summary["updated_to_shipped"], 0)
        self.assertEqual(summary["updated_to_cancelled"], 0)
        self.assertEqual(summary["updated_other"], 0)
        self.assertTrue(
            any(
                "SET updated_at = CURRENT_TIMESTAMP" in query
                and "SET status" not in query
                and params == (7,)
                for query, params in executions
            )
        )

    def test_stale_sweep_is_bounded_and_excludes_resolved_missing_orders(self):
        _, executions = self.run_reconciliation(
            FakeResponse(200, {"orderStatus": "awaiting_shipment"})
        )
        select_query, select_params = executions[0]

        self.assertIn("'not_found'", select_query)
        self.assertIn("o.updated_at < NOW()", select_query)
        self.assertIn("LIMIT %s", select_query)
        self.assertEqual(select_params, (24, 25))


if __name__ == "__main__":
    unittest.main()