"""
Focused unit tests for connection-pool hardening in pg_utils.

Covers:
  - get_connection(): dead first checkout discarded, retry returns a good connection
  - get_connection(): both dead → exception propagated, putconn(close=True) called twice
  - get_connection(): good first checkout returned immediately, pool not accessed again
  - is_workflow_enabled(): query failure after successful checkout → conn still closed (no leak)
  - cleanup worker: update_workflow_last_run() raises → terminal FAILED log still emitted
"""

import logging
import pytest
from unittest.mock import MagicMock, patch, call


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_good_conn():
    """Return a mock psycopg2 connection whose cursor().execute() succeeds."""
    conn = MagicMock()
    conn.autocommit = False
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    return conn


def _make_dead_conn():
    """Return a mock psycopg2 connection whose cursor().execute() raises."""
    conn = MagicMock()
    conn.autocommit = False
    cursor = MagicMock()
    cursor.execute.side_effect = Exception("SSL connection has been closed unexpectedly")
    conn.cursor.return_value = cursor
    return conn


# ---------------------------------------------------------------------------
# get_connection() tests
# ---------------------------------------------------------------------------

class TestGetConnectionHardening:
    """Test that get_connection() validates both first and retry checkouts."""

    def _run(self, pool):
        """Call pg_utils.get_connection() with a patched pool."""
        import src.services.database.pg_utils as pg_utils
        with patch.object(pg_utils, '_get_pool', return_value=pool):
            return pg_utils.get_connection()

    def test_first_checkout_dead_retry_succeeds(self):
        """Dead first connection is discarded; retry returns a validated live connection."""
        dead = _make_dead_conn()
        good = _make_good_conn()

        pool = MagicMock()
        pool.getconn.side_effect = [dead, good]

        conn_wrapper = self._run(pool)

        # putconn(close=True) called once for the dead connection
        pool.putconn.assert_called_once_with(dead, close=True)
        # The returned wrapper holds the good connection
        assert conn_wrapper._conn is good

    def test_first_checkout_dead_retry_also_dead_raises(self):
        """Both dead connections → exception propagated; putconn(close=True) called twice."""
        dead1 = _make_dead_conn()
        dead2 = _make_dead_conn()

        pool = MagicMock()
        pool.getconn.side_effect = [dead1, dead2]

        with pytest.raises(Exception):
            self._run(pool)

        # Both dead connections must be returned with close=True
        assert pool.putconn.call_count == 2
        pool.putconn.assert_any_call(dead1, close=True)
        pool.putconn.assert_any_call(dead2, close=True)

    def test_first_checkout_good_no_retry(self):
        """Good first connection is returned immediately without touching the pool again."""
        good = _make_good_conn()

        pool = MagicMock()
        pool.getconn.return_value = good

        conn_wrapper = self._run(pool)

        pool.getconn.assert_called_once()
        pool.putconn.assert_not_called()
        assert conn_wrapper._conn is good


# ---------------------------------------------------------------------------
# is_workflow_enabled() connection-leak test
# ---------------------------------------------------------------------------

class TestIsWorkflowEnabledConnectionLeak:
    """
    Verify that is_workflow_enabled() always closes the connection even when
    the query or fetch fails after a successful pool checkout.
    """

    def test_conn_closed_when_query_raises(self):
        """Connection must be returned to pool even if cursor.execute() raises."""
        import src.services.database.pg_utils as pg_utils

        good = _make_good_conn()
        # Simulate query failure after the health-check SELECT 1 succeeds.
        # We need the first cursor() call (SELECT 1 probe) to succeed but
        # the second (workflow query) to fail.
        call_count = [0]
        original_cursor = good.cursor

        def _cursor_side_effect():
            call_count[0] += 1
            if call_count[0] == 1:
                # First cursor call: health-check probe — succeeds
                return original_cursor()
            # Second cursor call: workflow query — raises
            cur = MagicMock()
            cur.execute.side_effect = Exception("query failed mid-flight")
            return cur

        good.cursor = _cursor_side_effect

        pool = MagicMock()
        pool.getconn.return_value = good

        # Force cache miss so the DB is actually queried
        pg_utils._workflow_cache.pop('test-wf', None)
        pg_utils._cache_ttl.pop('test-wf', None)

        with patch.object(pg_utils, '_get_pool', return_value=pool):
            result = pg_utils.is_workflow_enabled('test-wf')

        # Fail-closed: no cached value, DB unreachable after checkout → False
        assert result is False
        # The _PooledConnection.close() calls pool.putconn() — connection must be returned
        pool.putconn.assert_called_once_with(good)


# ---------------------------------------------------------------------------
# scheduled_cleanup terminal-log guarantee
# ---------------------------------------------------------------------------

class TestCleanupTerminalLog:
    """
    Verify that the cleanup worker emits a terminal SUCCESS/FAILED log line
    even when update_workflow_last_run() raises before cleanup_old_orders() runs.
    """

    def test_terminal_log_emitted_when_last_run_update_raises(self):
        """
        If update_workflow_last_run() throws, the finally block must still log
        a FAILED terminal line before the exception bubbles to the outer handler.

        We patch sc.logger.info directly because setup_logging() installs its own
        handlers at module-import time, which bypasses pytest's caplog interceptor.
        """
        import src.scheduled_cleanup as sc

        logged_info = []

        with (
            patch.object(sc, 'is_dev_silent', return_value=False),
            patch.object(sc, 'is_business_hours', return_value=True),
            patch.object(sc, 'is_workflow_enabled', return_value=True),
            patch.object(sc, 'heartbeat'),
            patch.object(sc, 'update_workflow_last_run',
                         side_effect=Exception("DB unavailable")),
            patch.object(sc, 'cleanup_old_orders') as mock_cleanup,
            patch.object(sc, 'time') as mock_time,
            # Intercept logger.info on the module-level logger directly
            patch.object(sc.logger, 'info', side_effect=lambda msg, *a, **kw: logged_info.append(msg)),
        ):
            # Exit the loop via KeyboardInterrupt injected through time.sleep
            mock_time.sleep.side_effect = KeyboardInterrupt

            try:
                sc.main()
            except (KeyboardInterrupt, SystemExit):
                pass

        # cleanup_old_orders should NOT have been called (exception was earlier)
        mock_cleanup.assert_not_called()

        # Terminal FAILED log must appear
        terminal_logs = [m for m in logged_info if "Cleanup run" in m and "FAILED" in m]
        assert terminal_logs, (
            "Expected a terminal FAILED log from the finally block, "
            f"but got: {logged_info}"
        )
