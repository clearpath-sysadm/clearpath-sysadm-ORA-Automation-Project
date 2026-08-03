"""
Shared promo SKU utilities.

Extracted from promo_sku_handler.py so that the lot tagger, the sync worker,
and the force-retag sweep can all perform promo→base SKU remapping without
importing the now-retired cancel-and-recreate handler.

Also provides variant SKU support (e.g. '17612-6' → base '17612', ×6 units)
via load_variant_map() and the unified resolve_sku_and_quantity() helper.
"""
import logging

logger = logging.getLogger(__name__)


def load_promo_map(conn) -> dict:
    """Return {promo_sku: base_sku} for all active rows in sku_promotions."""
    cursor = conn.cursor()
    cursor.execute("SELECT promo_sku, base_sku FROM sku_promotions WHERE active = TRUE")
    return {row[0]: row[1] for row in cursor.fetchall()}


def load_variant_map(conn) -> dict:
    """
    Return {variant_sku: {'base_sku': str, 'unit_multiplier': int}}
    for all active rows in sku_variants.

    Example entry: {'17612-6': {'base_sku': '17612', 'unit_multiplier': 6}}
    """
    cursor = conn.cursor()
    cursor.execute(
        "SELECT variant_sku, base_sku, unit_multiplier FROM sku_variants WHERE active = TRUE"
    )
    return {
        row[0]: {'base_sku': row[1], 'unit_multiplier': row[2]}
        for row in cursor.fetchall()
    }


def resolve_sku_and_quantity(
    raw_sku: str,
    quantity: int,
    promo_map: dict,
    variant_map: dict,
) -> tuple:
    """
    Return (base_sku, effective_quantity) after applying promo and variant remaps.

    Resolution order:
      1. Promo remap  — e.g. '17613' → '17612'  (multiplier stays 1)
      2. Variant remap — e.g. '17612-6' → '17612', quantity × 6

    The two remaps are mutually exclusive by design (a SKU must not appear in
    both sku_promotions and sku_variants), but the ordering means a hypothetical
    promo alias of a variant SKU would still be handled correctly.

    Args:
        raw_sku:     SKU string as received from ShipStation / BigCommerce.
        quantity:    Item quantity as received from the order.
        promo_map:   Output of load_promo_map(conn).
        variant_map: Output of load_variant_map(conn).

    Returns:
        (base_sku, effective_quantity) — both ready to pass to deduct_lot_inventory.
    """
    # Step 1: promo remap
    after_promo = promo_map.get(raw_sku, raw_sku)

    # Step 2: variant remap
    variant_entry = variant_map.get(after_promo)
    if variant_entry:
        base_sku = variant_entry['base_sku']
        effective_quantity = quantity * variant_entry['unit_multiplier']
        return base_sku, effective_quantity

    return after_promo, quantity
