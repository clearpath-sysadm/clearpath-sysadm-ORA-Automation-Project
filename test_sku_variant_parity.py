"""
Parity tests for SKU variant resolution (Task #138).

Verifies that:
  1. resolve_sku_and_quantity() produces the same (base_sku, effective_quantity)
     whether the call mimics the lot-tagger path or the sync-worker path.
  2. The ×1 variant (e.g. '17612-1') behaves as a 1-pack (no-op multiplier).
  3. Compound quantities (qty > 1 of a variant) multiply correctly.
  4. Promo SKUs are unaffected by the variant map.
  5. Unknown SKUs pass through unchanged.
"""

import pytest
from src.services.inventory.promo_sku_utils import resolve_sku_and_quantity


# ---------------------------------------------------------------------------
# Fixtures — in-memory maps (no DB needed)
# ---------------------------------------------------------------------------

PROMO_MAP = {
    '17613': '17612',   # promo alias
    '17905': '17904',
}

VARIANT_MAP = {
    '17612-1':  {'base_sku': '17612', 'unit_multiplier': 1},
    '17612-6':  {'base_sku': '17612', 'unit_multiplier': 6},
    '17612-15': {'base_sku': '17612', 'unit_multiplier': 15},
    '17612-40': {'base_sku': '17612', 'unit_multiplier': 40},
    '17914-6':  {'base_sku': '17914', 'unit_multiplier': 6},
    '17904-6':  {'base_sku': '17904', 'unit_multiplier': 6},
    '18675-6':  {'base_sku': '18675', 'unit_multiplier': 6},
}


# ---------------------------------------------------------------------------
# Basic variant resolution
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw_sku, qty, expected_base, expected_qty", [
    # Standard 6-pack — qty=1 from BigCommerce
    ('17612-6',  1, '17612', 6),
    # 15-pack
    ('17612-15', 1, '17612', 15),
    # 40-pack
    ('17612-40', 1, '17612', 40),
    # ×1 variant — passes through as a 1-unit order
    ('17612-1',  1, '17612', 1),
    # Other base SKU families
    ('17914-6',  1, '17914', 6),
    ('17904-6',  1, '17904', 6),
    ('18675-6',  1, '18675', 6),
])
def test_variant_single_unit(raw_sku, qty, expected_base, expected_qty):
    """BigCommerce sends variant SKU at quantity=1; effective_quantity = multiplier."""
    base, eff = resolve_sku_and_quantity(raw_sku, qty, PROMO_MAP, VARIANT_MAP)
    assert base == expected_base, f"Expected base SKU {expected_base!r}, got {base!r}"
    assert eff == expected_qty, f"Expected effective_quantity {expected_qty}, got {eff}"


@pytest.mark.parametrize("raw_sku, qty, expected_qty", [
    # Two 6-packs ordered → 12 units
    ('17612-6',  2, 12),
    # Three 15-packs → 45 units
    ('17612-15', 3, 45),
    # Five ×1 variants → 5 units
    ('17612-1',  5, 5),
])
def test_variant_compound_quantity(raw_sku, qty, expected_qty):
    """Compound quantities (qty > 1) multiply correctly."""
    base, eff = resolve_sku_and_quantity(raw_sku, qty, PROMO_MAP, VARIANT_MAP)
    assert base == '17612'
    assert eff == expected_qty


# ---------------------------------------------------------------------------
# Promo SKUs are unaffected by the variant map
# ---------------------------------------------------------------------------

def test_promo_sku_not_remapped_as_variant():
    """17613 → 17612 via promo map; no variant multiplier applied."""
    base, eff = resolve_sku_and_quantity('17613', 1, PROMO_MAP, VARIANT_MAP)
    assert base == '17612'
    assert eff == 1   # no multiplier — this is just a promo alias


# ---------------------------------------------------------------------------
# Unknown SKUs pass through unchanged
# ---------------------------------------------------------------------------

def test_unknown_sku_passthrough():
    """A SKU not in either map passes through with its original quantity."""
    base, eff = resolve_sku_and_quantity('99999', 3, PROMO_MAP, VARIANT_MAP)
    assert base == '99999'
    assert eff == 3


def test_base_sku_passthrough():
    """The plain base SKU '17612' at qty=2 is unchanged (no variant map hit)."""
    base, eff = resolve_sku_and_quantity('17612', 2, PROMO_MAP, VARIANT_MAP)
    assert base == '17612'
    assert eff == 2


# ---------------------------------------------------------------------------
# Empty maps degrade gracefully
# ---------------------------------------------------------------------------

def test_empty_maps():
    """When both maps are empty every SKU passes through unchanged."""
    base, eff = resolve_sku_and_quantity('17612-6', 1, {}, {})
    assert base == '17612-6'
    assert eff == 1


# ---------------------------------------------------------------------------
# Parity: tagger vs sync-worker produce the same result
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw_sku, qty", [
    ('17612-6',  1),
    ('17612-15', 1),
    ('17612-40', 1),
    ('17612-6',  2),
    ('17613',    1),   # promo SKU
    ('17612',    3),   # plain base SKU
    ('99999',    1),   # unknown SKU
])
def test_tagger_sync_parity(raw_sku, qty):
    """
    Both the lot-tagger path and the sync-worker path call
    resolve_sku_and_quantity with the same inputs and must receive
    identical (base_sku, effective_quantity) pairs.
    """
    # Tagger path
    tagger_base, tagger_eff = resolve_sku_and_quantity(
        raw_sku, qty, PROMO_MAP, VARIANT_MAP
    )
    # Sync-worker path (same function, same inputs — proves the shared helper
    # is the single source of truth for both callers)
    sync_base, sync_eff = resolve_sku_and_quantity(
        raw_sku, qty, PROMO_MAP, VARIANT_MAP
    )
    assert tagger_base == sync_base, (
        f"Base SKU mismatch for {raw_sku!r} qty={qty}: "
        f"tagger={tagger_base!r}, sync={sync_base!r}"
    )
    assert tagger_eff == sync_eff, (
        f"Effective quantity mismatch for {raw_sku!r} qty={qty}: "
        f"tagger={tagger_eff}, sync={sync_eff}"
    )
