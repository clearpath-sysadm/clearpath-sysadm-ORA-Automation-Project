"""
Shared promo SKU utilities.

Extracted from promo_sku_handler.py so that the lot tagger, the sync worker,
and the force-retag sweep can all perform promo→base SKU remapping without
importing the now-retired cancel-and-recreate handler.
"""
import logging

logger = logging.getLogger(__name__)


def load_promo_map(conn) -> dict:
    """Return {promo_sku: base_sku} for all active rows in sku_promotions."""
    cursor = conn.cursor()
    cursor.execute("SELECT promo_sku, base_sku FROM sku_promotions WHERE active = TRUE")
    return {row[0]: row[1] for row in cursor.fetchall()}
