"""Startup/redeploy behavior tests for the lot-tagger worker."""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestLotTaggerStartupReconciliation(unittest.TestCase):
    def test_production_startup_runs_reconciliation(self):
        from src import scheduled_lot_tagger as scheduler

        with patch.object(scheduler, 'is_dev_silent', return_value=False), \
             patch.object(scheduler, 'run_reconciliation') as reconcile, \
             patch.object(scheduler, 'server_logger'):
            self.assertTrue(scheduler.run_startup_reconciliation(is_production=True))

        reconcile.assert_called_once_with()

    def test_enabled_development_startup_runs_reconciliation(self):
        from src import scheduled_lot_tagger as scheduler

        with patch.object(scheduler, 'is_dev_silent', return_value=False), \
             patch.object(scheduler, 'run_reconciliation') as reconcile, \
             patch.object(scheduler, 'server_logger'):
            self.assertTrue(scheduler.run_startup_reconciliation(is_production=False))

        reconcile.assert_called_once_with()

    def test_silent_development_startup_makes_no_reconciliation_call(self):
        from src import scheduled_lot_tagger as scheduler

        with patch.object(scheduler, 'is_dev_silent', return_value=True), \
             patch.object(scheduler, 'run_reconciliation') as reconcile:
            self.assertFalse(scheduler.run_startup_reconciliation(is_production=False))

        reconcile.assert_not_called()

    def test_recent_run_gate_cannot_skip_enabled_startup(self):
        """Startup must not depend on the previous scheduled-run timestamp."""
        from src import scheduled_lot_tagger as scheduler

        with patch.object(scheduler, 'is_dev_silent', return_value=False), \
             patch.object(scheduler, 'run_reconciliation') as reconcile, \
             patch.object(scheduler, 'server_logger'):
            self.assertTrue(scheduler.run_startup_reconciliation(is_production=True))

        reconcile.assert_called_once_with()

    def test_startup_failure_is_logged_but_worker_can_continue(self):
        from src import scheduled_lot_tagger as scheduler

        with patch.object(scheduler, 'is_dev_silent', return_value=False), \
             patch.object(
                 scheduler,
                 'run_reconciliation',
                 side_effect=RuntimeError('temporary ShipStation outage'),
             ), \
             patch.object(scheduler, 'server_logger') as server_log:
            self.assertFalse(scheduler.run_startup_reconciliation(is_production=True))

        server_log.error.assert_called_once()


class TestLotTaggerLaunchConfiguration(unittest.TestCase):
    def test_production_launcher_starts_one_lot_tagger_process(self):
        launcher = Path('start_all.sh').read_text()
        self.assertEqual(
            launcher.count('python src/scheduled_lot_tagger.py'),
            1,
        )

    def test_replit_project_starts_the_dedicated_lot_tagger_workflow(self):
        config = Path('.replit').read_text()
        self.assertIn('args = "python src/scheduled_lot_tagger.py"', config)
        self.assertIn('run = ["bash", "start_all.sh"]', config)


if __name__ == '__main__':
    unittest.main()