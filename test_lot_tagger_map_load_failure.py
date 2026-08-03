"""
Tests for Task #147: lot tagger batch-level abort on map-load failure.

Verifies that a failure to load promo_map or variant_map before the per-order
loop causes the entire reconciliation batch to abort rather than silently
processing orders with empty maps.
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock, call

project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_order(order_number='999001', order_id=999001):
    return {
        'orderId': order_id,
        'orderNumber': order_number,
        'orderStatus': 'awaiting_shipment',
        'modifyDate': '2026-08-01T00:00:00.000Z',
        'advancedOptions': {'customField1': ''},
        'items': [{'sku': '17612', 'quantity': 1}],
        'tagIds': [],
    }


class TestMapLoadFailureAbortsRun(unittest.TestCase):
    """
    When load_variant_map or load_promo_map raises, run_reconciliation must
    abort before processing any orders — not continue with empty maps.
    """

    def _patch_run_reconciliation(self, raise_on='variant'):
        """
        Return a context-manager stack that patches enough of the scheduler's
        dependencies to isolate the map-load-failure path.
        """
        import contextlib

        def _raise(*a, **kw):
            raise RuntimeError(f"Simulated DB failure loading map")

        patches = [
            # Credentials — always succeed
            patch('src.scheduled_lot_tagger.get_shipstation_credentials',
                  return_value=('key', 'secret')),
            patch('src.scheduled_lot_tagger.get_shipstation_headers',
                  return_value={}),
            # Return one order so the loop would run if not aborted
            patch('src.scheduled_lot_tagger._fetch_awaiting_shipment_orders',
                  return_value=[_make_order()]),
            # DB transaction context — yield a mock conn
            patch('src.scheduled_lot_tagger.transaction_with_retry'),
            # build_lot_maps — succeeds normally
            patch('src.scheduled_lot_tagger.build_lot_maps',
                  return_value=({'17612': 'LOT1'}, {'17612'}, {}, {})),
            # Stale reservation cleanup — no-op
            patch('src.scheduled_lot_tagger.release_stale_reservations',
                  return_value=0),
            # update_workflow_last_run — no-op
            patch('src.scheduled_lot_tagger.update_workflow_last_run'),
            # heartbeat — no-op
            patch('src.scheduled_lot_tagger.heartbeat', MagicMock()),
        ]

        if raise_on == 'variant':
            patches += [
                patch('src.services.inventory.promo_sku_utils.load_promo_map',
                      return_value={}),
                patch('src.services.inventory.promo_sku_utils.load_variant_map',
                      side_effect=_raise),
            ]
        else:
            patches += [
                patch('src.services.inventory.promo_sku_utils.load_promo_map',
                      side_effect=_raise),
                patch('src.services.inventory.promo_sku_utils.load_variant_map',
                      return_value={}),
            ]

        return patches

    def _run_with_patches(self, patches):
        """Apply all patches, wire the mock conn, run run_reconciliation."""
        from src.scheduled_lot_tagger import run_reconciliation

        mock_tag = MagicMock()

        with patches[0], patches[1], patches[2], \
             patches[3] as mock_txn, patches[4], patches[5], \
             patches[6], patches[7], \
             patches[8], patches[9], \
             patch('src.scheduled_lot_tagger.tag_order_lots', mock_tag):

            # Wire transaction_with_retry as a context manager returning a mock conn
            mock_conn = MagicMock()
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock_cur = MagicMock()
            mock_cur.fetchall.return_value = []
            mock_cur.fetchone.return_value = None
            mock_conn.cursor.return_value = mock_cur
            mock_txn.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_txn.return_value.__exit__ = MagicMock(return_value=False)

            try:
                run_reconciliation()
            except Exception:
                pass  # batch abort via exception is also acceptable

            return mock_tag

    def test_variant_map_failure_no_orders_processed(self):
        """
        When load_variant_map raises, tag_order_lots must NOT be called for
        any order — the batch aborts before the per-order loop.
        """
        patches = self._patch_run_reconciliation(raise_on='variant')
        mock_tag = self._run_with_patches(patches)
        self.assertEqual(
            mock_tag.call_count, 0,
            f"tag_order_lots was called {mock_tag.call_count} time(s) after "
            f"load_variant_map failure — batch should have aborted first."
        )

    def test_promo_map_failure_no_orders_processed(self):
        """
        When load_promo_map raises, tag_order_lots must NOT be called for
        any order — the batch aborts before the per-order loop.
        """
        patches = self._patch_run_reconciliation(raise_on='promo')
        mock_tag = self._run_with_patches(patches)
        self.assertEqual(
            mock_tag.call_count, 0,
            f"tag_order_lots was called {mock_tag.call_count} time(s) after "
            f"load_promo_map failure — batch should have aborted first."
        )


class TestMapLoadSuccessPassesMaps(unittest.TestCase):
    """
    When maps load successfully, tag_order_lots receives the pre-loaded maps
    via keyword arguments — not None.
    """

    def test_tag_order_lots_receives_promo_and_variant_maps(self):
        """
        After a successful map load, tag_order_lots is called with non-None
        promo_map and variant_map keyword arguments.
        """
        from src.scheduled_lot_tagger import run_reconciliation

        promo = {'17613': '17612'}
        variant = {'17612-6': {'base_sku': '17612', 'unit_multiplier': 6}}
        mock_tag = MagicMock()

        with patch('src.scheduled_lot_tagger.get_shipstation_credentials',
                   return_value=('key', 'secret')), \
             patch('src.scheduled_lot_tagger.get_shipstation_headers',
                   return_value={}), \
             patch('src.scheduled_lot_tagger._fetch_awaiting_shipment_orders',
                   return_value=[_make_order()]), \
             patch('src.scheduled_lot_tagger.transaction_with_retry') as mock_txn, \
             patch('src.scheduled_lot_tagger.build_lot_maps',
                   return_value=({'17612': 'LOT1'}, {'17612'}, {}, {})), \
             patch('src.services.inventory.promo_sku_utils.load_promo_map',
                   return_value=promo), \
             patch('src.services.inventory.promo_sku_utils.load_variant_map',
                   return_value=variant), \
             patch('src.scheduled_lot_tagger.release_stale_reservations',
                   return_value=0), \
             patch('src.scheduled_lot_tagger.update_workflow_last_run'), \
             patch('src.scheduled_lot_tagger.heartbeat', MagicMock()), \
             patch('src.scheduled_lot_tagger.tag_order_lots', mock_tag), \
             patch('src.scheduled_lot_tagger.verify_tagging_results',
                   return_value={'total_tracked': 0, 'tagged_correctly': 0,
                                 'untagged_or_wrong': 0, 'total_checked': 0}):

            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_cur.fetchall.return_value = []
            mock_cur.fetchone.return_value = None
            mock_conn.cursor.return_value = mock_cur
            mock_txn.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_txn.return_value.__exit__ = MagicMock(return_value=False)

            run_reconciliation()

        self.assertGreater(mock_tag.call_count, 0, "tag_order_lots was never called")
        call_kwargs = mock_tag.call_args.kwargs
        self.assertIs(call_kwargs.get('promo_map'), promo,
                      "promo_map not passed to tag_order_lots")
        self.assertIs(call_kwargs.get('variant_map'), variant,
                      "variant_map not passed to tag_order_lots")


class TestTagOrderLotsNoneFallback(unittest.TestCase):
    """
    tag_order_lots with promo_map=None / variant_map=None (legacy / direct call)
    falls back to loading from DB — no regression for existing call sites.
    """

    def test_none_maps_load_from_db(self):
        """
        Passing promo_map=None and variant_map=None causes internal DB loads,
        exactly as before the refactor.
        """
        from src.lot_tagger.tagger import tag_order_lots

        order = _make_order(order_number='LEGACY-001')

        with patch('src.services.inventory.promo_sku_utils.load_promo_map',
                   return_value={}) as mock_pm, \
             patch('src.services.inventory.promo_sku_utils.load_variant_map',
                   return_value={}) as mock_vm, \
             patch('src.lot_tagger.tagger.server_logger'):

            conn = MagicMock()
            cur = MagicMock()
            cur.fetchone.return_value = None
            cur.fetchall.return_value = []
            conn.cursor.return_value = cur

            try:
                # May raise (no real SS API) — we only care that the map loaders ran
                tag_order_lots(order, {}, set(), {}, conn,
                               promo_map=None, variant_map=None)
            except Exception:
                pass

            mock_pm.assert_called_once()
            mock_vm.assert_called_once()

    def test_pre_loaded_maps_skip_db(self):
        """
        Passing non-None promo_map and variant_map skips the internal DB loads.
        """
        from src.lot_tagger.tagger import tag_order_lots

        order = _make_order(order_number='PRELOADED-001')

        with patch('src.services.inventory.promo_sku_utils.load_promo_map',
                   return_value={}) as mock_pm, \
             patch('src.services.inventory.promo_sku_utils.load_variant_map',
                   return_value={}) as mock_vm, \
             patch('src.lot_tagger.tagger.server_logger'):

            conn = MagicMock()
            cur = MagicMock()
            cur.fetchone.return_value = None
            cur.fetchall.return_value = []
            conn.cursor.return_value = cur

            try:
                tag_order_lots(order, {}, set(), {}, conn,
                               promo_map={}, variant_map={})
            except Exception:
                pass

            mock_pm.assert_not_called()
            mock_vm.assert_not_called()


if __name__ == '__main__':
    unittest.main()
