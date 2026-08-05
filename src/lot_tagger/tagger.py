"""
Lot Tagger — shared tag_order_lots() function.

Called by both the webhook handler (Flask) and the reconciliation scheduler.
Callers must build active_lots and known_skus from the DB before calling this.
"""
import hashlib
import os
import logging
from datetime import datetime, timezone
from typing import Dict, Set

from src.services.shipstation.api_client import update_order_custom_fields, update_order_package_v2
from src.services.inventory import lot_reservation
from src.utils.server_logger import get_logger
from utils.api_utils import make_api_request
from src.services.shipstation.promo_sku_handler import _write_admin_alert

logger = logging.getLogger(__name__)
server_logger = get_logger()

# CRITICAL (Task #131 fix): status must be strictly 'active'. The previous
# `NOT IN ('quarantine', 'inactive')` filter silently included 'depleted'
# lots, so any positive-balance repack (even 1 unit) on a depleted lot made
# it eligible again with no explicit reactivation. Reactivating a depleted
# lot now requires an explicit status change back to 'active' — there is no
# balance-threshold auto-reactivation.
#
# Ordered by lot_number (not received_date/lot_id) per Task #131 — lot_number
# is the human-meaningful FIFO identity; internal DB ids/received_date can
# be inconsistent with lot issuance order.
#
# Task #136: lot_number is a text column, so a plain `ORDER BY l.lot_number`
# is a lexical string sort — "9" sorts after "10" ("1" < "9" as characters),
# which would silently scramble FIFO order for any SKU whose lot numbers
# differ in digit length. All observed lot numbers are purely numeric, so
# sort numerically when possible and fall back to the literal text order
# for any lot number that isn't (so a malformed value doesn't error out —
# it just sorts last, deterministically, rather than crashing the tagger).
CANDIDATE_LOTS_QUERY = """
    SELECT s.sku_code, l.lot_id, l.lot_number, lb.balance
    FROM lots l
    JOIN skus s ON s.sku_id = l.sku_id
    JOIN lot_balances lb ON lb.lot_id = l.lot_id
    WHERE lb.balance > 0
      AND l.status = 'active'
    ORDER BY
        s.sku_code,
        (l.lot_number ~ '^[0-9]+$') DESC,
        CASE WHEN l.lot_number ~ '^[0-9]+$' THEN l.lot_number::numeric END ASC,
        l.lot_number ASC
"""

KNOWN_SKUS_QUERY = "SELECT sku_code FROM skus"

LOT_STATUS_QUERY = """
    SELECT s.sku_code, l.lot_number, l.status
    FROM lots l
    JOIN skus s ON s.sku_id = l.sku_id
"""

HOME_OFFICE_SKUS = {'18751', '18760', '18565'}

LOT_OVERRIDE_TAG_ID = 49832

SKU_SHIPPING_PROFILES = {
    '17612': {'package_code': 'package', 'package_id': 'se-122675', 'length': 12.0, 'width': 12.0, 'height': 10.0, 'weight_oz': 352},
    '17914': {'package_code': 'package', 'package_id': 'se-122677', 'length': 11.0, 'width': 11.0, 'height':  8.0, 'weight_oz': 240},
    '17904': {'package_code': 'package', 'package_id': 'se-132840', 'length': 14.0, 'width': 12.0, 'height':  5.0, 'weight_oz': 160},
    '18675': {'package_code': 'package', 'package_id': 'se-122678', 'length': 12.0, 'width': 12.0, 'height': 10.0, 'weight_oz': 352},
    '18795': {'package_code': 'package', 'package_id': 'se-131836', 'length':  9.0, 'width':  5.0, 'height':  8.0, 'weight_oz':  80},
    '18751': {'package_code': 'package', 'package_id': 'se-135810', 'length':  9.0, 'width':  5.0, 'height':  7.0, 'weight_oz':  80},
    '18760': {'package_code': 'package', 'package_id': 'se-135809', 'length':  2.0, 'width':  2.0, 'height':  3.0, 'weight_oz':  32},
    '18565': {'package_code': 'package', 'package_id': 'se-135808', 'length':  9.0, 'width':  6.0, 'height':  4.0, 'weight_oz':  48},
}


def build_lot_maps(conn):
    """
    Build active_lots dict, known_skus set, lot_statuses lookup, and
    lot_candidates (per-SKU list of active lots with capacity) from the DB.

    lot_candidates is the balance-aware replacement for the old single-lot
    active_lots value: tag_order_lots() reserves against the first candidate
    (by lot_number ascending) that has enough *available* balance (real
    balance minus other orders' open reservations), never re-activating a
    depleted lot without an explicit status change.

    active_lots is retained (first candidate per SKU) for QA / display /
    the legacy lot-stamped-SKU fallback path — it is NOT used to drive the
    primary tagging decision anymore.

    Returns: (active_lots: dict[sku -> lot_number], known_skus: set[sku],
              lot_statuses: dict[(sku, lot_number) -> status],
              lot_candidates: dict[sku -> list[(lot_id, lot_number, balance)]])
    """
    cursor = conn.cursor()

    cursor.execute(CANDIDATE_LOTS_QUERY)
    lot_candidates: Dict[str, list] = {}
    for sku_code, lot_id, lot_number, balance in cursor.fetchall():
        lot_candidates.setdefault(sku_code, []).append((lot_id, lot_number, balance))

    active_lots = {sku: candidates[0][1] for sku, candidates in lot_candidates.items()}

    cursor.execute(KNOWN_SKUS_QUERY)
    known_skus = {row[0] for row in cursor.fetchall()}

    cursor.execute(LOT_STATUS_QUERY)
    lot_statuses = {(row[0], row[1]): row[2] for row in cursor.fetchall()}

    return active_lots, known_skus, lot_statuses, lot_candidates


def resolve_shipping_profile(order: dict, sku: str) -> dict:
    """
    Derive the correct shipping profile for an order + SKU combination.

    Carrier / billing rules:
      - Company name contains 'BENCO' → UPS Ground (carrier=ups_walleted), third-party billing
            (BENCO_UPS_ACCOUNT_NUMBER, BENCO_UPS_POSTAL_CODE, BENCO_UPS_COUNTRY_CODE)
      - All others                    → FedEx, my_other_account billing
            Service code rules (non-Benco only, highest priority first):
              - Preserve existing fedex_2day (never downgrade)
              - HI destination  → fedex_2day
              - CA destination  → fedex_ground_international
              - Default         → fedex_ground
            Account: ORACARE_FEDEX_ACCOUNT_ID (ShipStation shippingProviderId)

    Package / dimensions / weight come from SKU_SHIPPING_PROFILES.
    Unknown SKUs get None for those fields — callers must omit them from the payload.

    Returns a dict with keys:
        carrier_code, service_code, bill_to_party, bill_to_account,
        bill_to_postal_code, bill_to_country_code,
        package_code, weight_oz, length, width, height

    NOTE: internationalOptions (customs declarations) are intentionally never
    set by the tagger. ShipStation auto-populates these when destination country
    is CA. Never add internationalOptions to the update payload — it would
    overwrite ShipStation's existing customs data with null values.
    """
    ship_to = order.get('shipTo') or {}
    state   = (ship_to.get('state')   or '').strip().upper()
    country = (ship_to.get('country') or '').strip().upper()
    company = (ship_to.get('company') or '').strip().upper()
    current_service = (order.get('serviceCode') or '').strip()

    if 'BENCO' in company:
        # UPS third-party billing — Benco ships US continental only
        ups_acct = os.getenv('BENCO_UPS_ACCOUNT_NUMBER')
        if not ups_acct:
            raise ValueError("BENCO_UPS_ACCOUNT_NUMBER environment variable is not configured")
        ups_postal = os.getenv('BENCO_UPS_POSTAL_CODE')
        if not ups_postal:
            raise ValueError("BENCO_UPS_POSTAL_CODE environment variable is not configured")
        ups_country = os.getenv('BENCO_UPS_COUNTRY_CODE', 'US')
        carrier_code       = 'ups_walleted'
        service_code       = 'ups_ground'
        bill_to_party      = 'third_party'
        bill_to_account    = str(ups_acct)
        bill_to_postal_code   = str(ups_postal)
        bill_to_country_code  = str(ups_country)
    else:
        # FedEx my-other-account billing (Oracare and all non-Benco)
        if current_service == 'fedex_2day':
            service_code = 'fedex_2day'
        elif state == 'HI':
            service_code = 'fedex_2day'
        elif country == 'CA':
            service_code = 'fedex_ground_international'
        else:
            service_code = 'fedex_ground'
        oracare_id = os.getenv('ORACARE_FEDEX_ACCOUNT_ID')
        if not oracare_id:
            raise ValueError("ORACARE_FEDEX_ACCOUNT_ID environment variable is not configured")
        carrier_code       = 'fedex'
        bill_to_party      = 'my_other_account'
        bill_to_account    = int(oracare_id)
        bill_to_postal_code   = None
        bill_to_country_code  = None

    profile = SKU_SHIPPING_PROFILES.get(sku)
    if profile is None:
        logger.warning(f"SKU {sku!r} not in SKU_SHIPPING_PROFILES — package/dims/weight will not be set")

    return {
        'carrier_code':          carrier_code,
        'service_code':          service_code,
        'bill_to_party':         bill_to_party,
        'bill_to_account':       bill_to_account,
        'bill_to_postal_code':   bill_to_postal_code,
        'bill_to_country_code':  bill_to_country_code,
        'package_code':   profile['package_code'] if profile else None,
        'package_id':     profile['package_id']   if profile else None,
        'weight_oz':      profile['weight_oz']    if profile else None,
        'length':         profile['length']        if profile else None,
        'width':          profile['width']         if profile else None,
        'height':         profile['height']        if profile else None,
    }


def _get_mismatched_fields(order: dict, expected_cf1: str, profile: dict) -> list:
    """
    Return a list of field names that differ from the expected profile values.
    An empty list means the order is fully enriched (no write needed).

    Fields checked:
        customField1, carrierCode, serviceCode, packageCode (when profile has one),
        billToParty, weight, dimensions.

    Billing field checks are carrier-aware:
        my_other_account → billToMyOtherAccount
        third_party      → billToAccount, billToPostalCode, billToCountryCode
    """
    adv  = order.get('advancedOptions') or {}
    wt   = order.get('weight') or {}
    dims = order.get('dimensions') or {}
    mismatched = []

    if (adv.get('customField1') or '').strip() != expected_cf1:
        mismatched.append('customField1')

    if (order.get('carrierCode') or '') != profile['carrier_code']:
        mismatched.append('carrierCode')

    if (order.get('serviceCode') or '') != profile['service_code']:
        mismatched.append('serviceCode')

    if adv.get('billToParty') != profile['bill_to_party']:
        mismatched.append('billToParty')

    if profile.get('bill_to_party') == 'third_party':
        if str(adv.get('billToAccount') or '') != str(profile['bill_to_account'] or ''):
            mismatched.append('billToAccount')
        if str(adv.get('billToPostalCode') or '') != str(profile.get('bill_to_postal_code') or ''):
            mismatched.append('billToPostalCode')
        if str(adv.get('billToCountryCode') or '') != str(profile.get('bill_to_country_code') or ''):
            mismatched.append('billToCountryCode')
    else:
        if adv.get('billToMyOtherAccount') != profile['bill_to_account']:
            mismatched.append('billToMyOtherAccount')

    if profile['package_code'] is not None:
        if (order.get('packageCode') or '') != profile['package_code']:
            mismatched.append('packageCode')

    if profile.get('weight_oz') is not None:
        try:
            if round(float(wt.get('value') or 0), 1) != round(float(profile['weight_oz']), 1):
                mismatched.append('weight')
        except (TypeError, ValueError):
            mismatched.append('weight')

    if profile.get('length') is not None:
        try:
            if (round(float(dims.get('length') or 0), 1) != round(float(profile['length']), 1) or
                    round(float(dims.get('width') or 0), 1) != round(float(profile['width']), 1) or
                    round(float(dims.get('height') or 0), 1) != round(float(profile['height']), 1)):
                mismatched.append('dimensions')
        except (TypeError, ValueError):
            mismatched.append('dimensions')

    return mismatched


def _is_fully_enriched(order: dict, expected_cf1: str, profile: dict) -> bool:
    """
    Return True only when every field the tagger owns already matches expected values.

    Fields checked:
        customField1, carrierCode, serviceCode, packageCode (when profile has one),
        billToParty, billToMyOtherAccount, weight, dimensions.
    """
    return len(_get_mismatched_fields(order, expected_cf1, profile)) == 0


def _parse_lot_stamped_sku(sku: str):
    """
    Detect compound SKU values used by XML-imported and manually-added orders.

    If sku matches '{base_sku} - {lot}' where base_sku is a key in
    SKU_SHIPPING_PROFILES, return (base_sku, full_sku_as_cf1).
    Otherwise return None.

    Examples:
        '17612 - 260017'  →  ('17612', '17612 - 260017')
        '17914 - 250297'  →  ('17914', '17914 - 250297')
        '18760'           →  None  (plain SKU, not lot-stamped)
        'UNKNOWN - X'     →  None  (base not in SKU_SHIPPING_PROFILES)
    """
    parts = sku.split(' - ', 1)
    if len(parts) == 2 and parts[0].strip() in SKU_SHIPPING_PROFILES:
        return parts[0].strip(), sku.strip()
    return None


def ensure_v2_package(order_id: int, order_number: str, profile: dict,
                      num_packages: int = 1) -> dict:
    """
    Idempotent V2 package setter.

    GETs the V2 shipment once and checks whether the packages array already
    matches the expected configuration. Only issues a PUT when it differs.

    Idempotency rules:
      - num_packages == 1: skip if packages[0].package_id already equals
                           the expected custom preset id.
      - num_packages >  1: skip if len(packages) already equals num_packages
                           (count match is sufficient — multi-package orders
                           always use the same box type for all packages).

    This runs on every tagged order — including ones whose V1 fields are
    already correct — so the V2 package configuration is always in sync.

    Returns:
        {'action': 'already_correct'} — V2 already has the right configuration
        {'action': 'updated'}         — V2 PUT succeeded
        {'action': 'skipped'}         — no package_id in profile (unsupported SKU)
        {'action': 'error', 'error': str} — GET or PUT failed
    """
    package_id = profile.get('package_id')
    if not package_id:
        return {'action': 'skipped'}

    num_packages = max(1, int(num_packages or 1))

    api_key = os.getenv('PRODUCTION_KEY')
    if not api_key:
        return {'action': 'error', 'error': 'PRODUCTION_KEY not set'}

    shipment_id = f"se-{order_id}"
    url         = f"https://api.shipstation.com/v2/shipments/{shipment_id}"
    headers     = {'API-Key': api_key, 'Content-Type': 'application/json'}

    get_resp = make_api_request(url=url, method='GET', headers=headers, timeout=30)
    if not get_resp or get_resp.status_code != 200:
        status = get_resp.status_code if get_resp else 'no response'
        body   = get_resp.text[:200]  if get_resp else ''
        return {'action': 'error', 'error': f'V2 GET failed {status}: {body}'}

    shipment = get_resp.json()
    packages = shipment.get('packages') or []

    if num_packages == 1:
        current_pkg_id = packages[0].get('package_id') if packages else None
        already_correct = (current_pkg_id == package_id)
    else:
        already_correct = (len(packages) == num_packages)

    if already_correct:
        logger.debug(
            f"Order {order_number} V2 already has {num_packages} package(s) "
            f"(package_id={package_id}) — skipping PUT."
        )
        return {'action': 'already_correct'}

    if num_packages == 1:
        shipment['packages'] = [
            {
                'package_id': package_id,
                'weight': {'value': profile['weight_oz'], 'unit': 'ounce'},
            }
        ]
    else:
        single_pkg = {
            'package_code': 'package',
            'weight': {'value': profile['weight_oz'], 'unit': 'ounce'},
            'dimensions': {
                'unit': 'inch',
                'length': profile['length'],
                'width': profile['width'],
                'height': profile['height'],
            },
        }
        shipment['packages'] = [single_pkg] * num_packages

    # ShipStation V2 rejects PUTs where ship_date is in the past.  Always
    # reset to today so old orders (created before today) don't receive 400.
    shipment['ship_date'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT00:00:00Z')

    try:
        put_resp = make_api_request(url=url, method='PUT', headers=headers, data=shipment, timeout=30)
    except Exception as e:
        return {'action': 'error', 'error': str(e)}

    if put_resp and put_resp.status_code in (200, 204):
        logger.info(
            f"V2: set {num_packages}×package_id={package_id} on order "
            f"{order_number} ({shipment_id})"
        )
        return {'action': 'updated'}
    else:
        status = put_resp.status_code if put_resp else 'no response'
        body   = put_resp.text[:300]  if put_resp else ''
        return {'action': 'error', 'error': f'V2 PUT failed {status}: {body}'}


def tag_order_lots(order: dict, active_lots: Dict[str, str], known_skus: Set[str], lot_statuses: Dict,
                    conn, lot_candidates: Dict[str, list] = None,
                    promo_map: dict = None, variant_map: dict = None) -> None:
    """
    Inspect a single ShipStation order and write the correct lot stamp and full
    shipping profile only when one or more fields need updating.

    Logic:
    1. Filter order items to tracked SKUs (in known_skus).
    2. If none found, check for home office SKUs → apply shipping profile only.
    3. Multi-SKU guard: write lot_tagging_failures record and abort.
    4. No active lot → write lot_tagging_failures record.
    5. Full-field idempotency: skip only if ALL owned fields already match.
       Fields: customField1, carrierCode, serviceCode, packageCode,
               billToParty, billToMyOtherAccount.
    6. Write lot stamp + full shipping profile in one API call.
    7. Resolve any existing failure record on success.

    Args:
        promo_map:    Pre-loaded {promo_sku: base_sku} from the scheduler. If
                      None (legacy / direct call), loaded internally as before.
        variant_map:  Pre-loaded {variant_sku: {...}} from the scheduler. If
                      None (legacy / direct call), loaded internally as before.
    """
    order_number = order.get('orderNumber', '').strip()
    order_id     = order.get('orderId')
    items        = order.get('items', [])
    lot_candidates = lot_candidates if lot_candidates is not None else {}

    tag_ids      = order.get('tagIds') or []
    lot_override = LOT_OVERRIDE_TAG_ID in tag_ids
    if lot_override:
        server_logger.info(
            f"[Lot Tagger] Lot Override tag present on order {order_number} (SS ID: {order_id})"
            f" — skipping CF1 update.",
            source="Lot Tagger"
        )

    # Promo SKU remap — translate promo SKUs to base SKUs in-place so the lot
    # tagger always looks up the base SKU (17613→17612, 17905→17904, etc.).
    # When called from the scheduler, promo_map is pre-loaded before the loop
    # (a failure there aborts the batch). The None fallback supports direct /
    # test calls that don't pass the parameter.
    if promo_map is not None:
        _promo_map = promo_map
    else:
        from src.services.inventory.promo_sku_utils import load_promo_map as _load_promo_map
        _promo_map = _load_promo_map(conn)

    if _promo_map:
        for _item in items:
            _raw = str(_item.get('sku') or '').strip()
            if _raw in _promo_map:
                server_logger.debug(
                    f"[Lot Tagger] Promo SKU remap on order {order_number}: "
                    f"{_raw} → {_promo_map[_raw]}",
                    source="Lot Tagger"
                )
                _item['sku'] = _promo_map[_raw]

        # Deduplicate items that share the same SKU after remap.
        # BXGY promo orders may produce two line items that both remap to the
        # same base SKU (e.g., two 17613 items → two 17612 items).  Without
        # dedup the multi-SKU guard at line ~600 would flag a false error.
        _seen_skus: dict = {}
        _deduped: list = []
        for _item in items:
            _s = str(_item.get('sku', '')).strip()
            if _s in _seen_skus:
                _seen_skus[_s]['quantity'] = (
                    (_seen_skus[_s].get('quantity') or 0) + (_item.get('quantity') or 0)
                )
            else:
                _seen_skus[_s] = _item
                _deduped.append(_item)
        items = _deduped

    # Variant SKU remap — translate multi-unit variant SKUs to base SKUs
    # (e.g. '17612-6' → '17612') and store the effective package count in
    # _effective_quantity = item_quantity × unit_multiplier.
    # Must run AFTER the promo dedup so that a promo alias of a variant SKU
    # is correctly resolved first by the promo map, then by the variant map.
    # When called from the scheduler, variant_map is pre-loaded before the loop
    # (a failure there aborts the batch). The None fallback supports direct /
    # test calls that don't pass the parameter.
    if variant_map is not None:
        _variant_map = variant_map
    else:
        from src.services.inventory.promo_sku_utils import load_variant_map as _load_variant_map
        _variant_map = _load_variant_map(conn)

    if _variant_map:
        for _item in items:
            _raw_sku = str(_item.get('sku') or '').strip()
            _entry = _variant_map.get(_raw_sku)
            if _entry:
                _item_qty = max(1, int(_item.get('quantity') or 1))
                _eff_qty = _item_qty * _entry['unit_multiplier']
                _item['_effective_quantity'] = _eff_qty
                _item['sku'] = _entry['base_sku']
                server_logger.debug(
                    f"[Lot Tagger] Variant SKU remap on order {order_number}: "
                    f"{_raw_sku} (qty={_item_qty}) → {_entry['base_sku']} ×{_eff_qty} packages",
                    source="Lot Tagger"
                )

        # Deduplicate items sharing the same base SKU after variant remap.
        # Handles edge case where two different variant packs of the same base
        # SKU appear in one order (e.g. one 17612-6 + one 17612-15).
        _seen_variant: dict = {}
        _deduped_variant: list = []
        for _item in items:
            _s = str(_item.get('sku', '')).strip()
            if _s in _seen_variant:
                _prev = _seen_variant[_s]
                _prev['_effective_quantity'] = (
                    (_prev.get('_effective_quantity') or _prev.get('quantity') or 0)
                    + (_item.get('_effective_quantity') or _item.get('quantity') or 0)
                )
            else:
                _seen_variant[_s] = _item
                _deduped_variant.append(_item)
        items = _deduped_variant

    # Alert on items that look like unrecognized variant SKUs (e.g. '17612-1-1')
    # that were not resolved by the variant map and are not in known_skus.
    # Runs unconditionally (outside the variant_map guard) so that a missing or
    # empty variant map does not silence the alert.  The startswith pattern
    # mirrors has_key_product_skus() in unified_shipstation_sync.py.
    for _item in items:
        _raw_sku = str(_item.get('sku', '')).strip()
        if _raw_sku not in known_skus:
            for _base_sku in known_skus:
                if _raw_sku.startswith(_base_sku + '-'):
                    _alert_msg = (
                        f"Unrecognized variant SKU '{_raw_sku}' on order "
                        f"{order_number} (SS ID: {order_id}) looks like a variant "
                        f"of '{_base_sku}' but is not in sku_variants — "
                        f"item was dropped. Add it to sku_variants to enable tagging."
                    )
                    server_logger.warning(_alert_msg, source="Lot Tagger")
                    _write_admin_alert(conn, _alert_msg)
                    break

    tracked_items = [item for item in items if str(item.get('sku', '')).strip() in known_skus]

    if not tracked_items:
        ho_items = [item for item in items if str(item.get('sku', '')).strip() in HOME_OFFICE_SKUS]
        if not ho_items:
            # --- Lot-stamped SKU path (XML-imported / manually-added orders) ---
            # These orders carry a compound SKU like '17612 - 260017' instead of
            # a plain base code.  The lot is embedded in the SKU itself and must
            # be used as-is for customField1 — do NOT substitute the active lot.
            stamped_items = []
            for item in items:
                parsed = _parse_lot_stamped_sku(str(item.get('sku', '')).strip())
                if parsed:
                    qty = max(1, int(item.get('quantity') or 1))
                    stamped_items.append((*parsed, qty))

            if not stamped_items:
                return  # Truly untracked — nothing to do

            unique_bases = {base for base, _, _ in stamped_items}
            if len(unique_bases) > 1:
                skus_found = ', '.join(str(item.get('sku', '')).strip() for item in items)
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO lot_tagging_failures
                        (order_number, shipstation_order_id, sku, detected_at)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (shipstation_order_id) DO UPDATE
                        SET detected_at = CURRENT_TIMESTAMP,
                            sku = EXCLUDED.sku
                    WHERE lot_tagging_failures.resolved_at IS NULL
                """, (order_number, str(order_id), skus_found))
                conn.commit()
                server_logger.warning(
                    f"Lot-stamped order {order_number} (SS ID: {order_id}) has multiple "
                    f"base SKUs [{skus_found}]. Logged to lot_tagging_failures.",
                    source="Lot Tagger"
                )
                return

            base_sku, exp_cf1, num_packages = stamped_items[0]

            # Check whether the lot embedded in the compound SKU is still active.
            # If it has been deactivated, fall through to the current active lot
            # rather than blindly re-stamping with a lot the user retired.
            embedded_lot = exp_cf1.split(' - ', 1)[1] if ' - ' in exp_cf1 else ''
            embedded_status = lot_statuses.get((base_sku, embedded_lot), 'active')
            if embedded_status in ('inactive', 'quarantine'):
                if base_sku in active_lots:
                    new_cf1 = f"{base_sku} - {active_lots[base_sku]}"
                    server_logger.warning(
                        f"[Lot Tagger] Lot-stamped order {order_number} (SS ID: {order_id}): "
                        f"embedded lot {embedded_lot!r} is {embedded_status} — "
                        f"using active lot {active_lots[base_sku]!r} instead.",
                        source="Lot Tagger"
                    )
                    exp_cf1 = new_cf1
                else:
                    _cur = conn.cursor()
                    _cur.execute("""
                        INSERT INTO lot_tagging_failures
                            (order_number, shipstation_order_id, sku, detected_at)
                        VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (shipstation_order_id) DO UPDATE
                            SET detected_at = CURRENT_TIMESTAMP,
                                sku = EXCLUDED.sku
                        WHERE lot_tagging_failures.resolved_at IS NULL
                    """, (order_number, str(order_id), base_sku))
                    conn.commit()
                    server_logger.warning(
                        f"[Lot Tagger] Lot-stamped order {order_number} (SS ID: {order_id}): "
                        f"embedded lot {embedded_lot!r} is {embedded_status} and no active lot "
                        f"found for SKU {base_sku}. Logged to lot_tagging_failures.",
                        source="Lot Tagger"
                    )
                    return

            profile = resolve_shipping_profile(order, base_sku)

            mismatched = _get_mismatched_fields(order, exp_cf1, profile)
            if lot_override:
                mismatched = [f for f in mismatched if f != 'customField1']
            if not mismatched:
                logger.debug(f"Lot-stamped order {order_number} already correct — skipped.")
                v2_result = ensure_v2_package(order_id, order_number, profile,
                                              num_packages=num_packages)
                if v2_result['action'] == 'updated':
                    server_logger.info(
                        f"V2 package swept to {profile['package_id']} ×{num_packages} "
                        f"for lot-stamped order {order_number} (SS ID: {order_id})",
                        source="Lot Tagger"
                    )
                elif v2_result['action'] == 'error':
                    server_logger.error(
                        f"V2 package sweep failed for lot-stamped order {order_number} "
                        f"(SS ID: {order_id}): {v2_result.get('error')}",
                        source="Lot Tagger"
                    )
                return

            result = update_order_custom_fields(
                order_id, exp_cf1, None,
                skip_cf1=lot_override,
                carrier_code=profile['carrier_code'],
                service_code=profile['service_code'],
                package_code=profile['package_code'],
                weight_oz=profile['weight_oz'],
                dim_length=profile['length'],
                dim_width=profile['width'],
                dim_height=profile['height'],
                bill_to_party=profile['bill_to_party'],
                bill_to_account=profile['bill_to_account'],
                bill_to_postal_code=profile.get('bill_to_postal_code'),
                bill_to_country_code=profile.get('bill_to_country_code'),
            )

            if not result.get('success'):
                server_logger.error(
                    f"Failed to enrich lot-stamped order {order_number} "
                    f"(SS ID: {order_id}): {result.get('error')}",
                    source="Lot Tagger"
                )
            else:
                server_logger.info(
                    f"Corrected {len(mismatched)} field(s) on lot-stamped order "
                    f"{order_number} (SS ID: {order_id}) CF1={exp_cf1!r} "
                    f"base_sku={base_sku} fields={mismatched}",
                    source="Lot Tagger"
                )
                if not lot_override:
                    order.setdefault('advancedOptions', {})['customField1'] = exp_cf1
                if profile.get('package_id'):
                    v2_result = update_order_package_v2(
                        order_id,
                        profile['package_id'],
                        profile['weight_oz'],
                        profile['length'],
                        profile['width'],
                        profile['height'],
                        num_packages=num_packages,
                    )
                    if not v2_result.get('success'):
                        server_logger.error(
                            f"V2 package update failed for lot-stamped order {order_number} "
                            f"(SS ID: {order_id}): {v2_result.get('error')}",
                            source="Lot Tagger"
                        )
                    else:
                        server_logger.info(
                            f"V2 package set to {profile['package_id']} ×{num_packages} "
                            f"for lot-stamped order {order_number} (SS ID: {order_id})",
                            source="Lot Tagger"
                        )
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE lot_tagging_failures
                    SET resolved_at = CURRENT_TIMESTAMP,
                        resolved_by = 'auto'
                    WHERE shipstation_order_id = %s
                      AND resolved_at IS NULL
                """, (str(order_id),))
                conn.commit()
            return

        sku          = str(ho_items[0].get('sku', '')).strip()
        num_packages = max(1, int(ho_items[0].get('quantity') or 1))
        profile      = resolve_shipping_profile(order, sku)

        mismatched = _get_mismatched_fields(order, sku, profile)
        if lot_override:
            mismatched = [f for f in mismatched if f != 'customField1']
        if not mismatched:
            logger.debug(f"Order {order_number} (home office) already correct — skipped.")
            v2_result = ensure_v2_package(order_id, order_number, profile,
                                          num_packages=num_packages)
            if v2_result['action'] == 'updated':
                server_logger.info(
                    f"V2 package swept to {profile['package_id']} ×{num_packages} "
                    f"for home office order {order_number} (SS ID: {order_id})",
                    source="Lot Tagger"
                )
            elif v2_result['action'] == 'error':
                server_logger.error(
                    f"V2 package sweep failed for home office order {order_number} "
                    f"(SS ID: {order_id}): {v2_result.get('error')}",
                    source="Lot Tagger"
                )
            return

        result = update_order_custom_fields(
            order_id, sku, None,
            skip_cf1=lot_override,
            carrier_code=profile['carrier_code'],
            service_code=profile['service_code'],
            package_code=profile['package_code'],
            weight_oz=profile['weight_oz'],
            dim_length=profile['length'],
            dim_width=profile['width'],
            dim_height=profile['height'],
            bill_to_party=profile['bill_to_party'],
            bill_to_account=profile['bill_to_account'],
            bill_to_postal_code=profile.get('bill_to_postal_code'),
            bill_to_country_code=profile.get('bill_to_country_code'),
        )

        if not result.get('success'):
            server_logger.error(
                f"Failed to enrich home office order {order_number} (SS ID: {order_id}): {result.get('error')}",
                source="Lot Tagger"
            )
        else:
            _tag_action = "Freshly tagged" if not (order.get('advancedOptions') or {}).get('customField1') else f"Corrected {len(mismatched)} field(s) on"
            server_logger.info(
                f"{_tag_action} home office order {order_number} (SS ID: {order_id}) "
                f"SKU={sku} fields={mismatched}",
                source="Lot Tagger"
            )
            if not lot_override:
                order.setdefault('advancedOptions', {})['customField1'] = sku
            if profile.get('package_id'):
                v2_result = update_order_package_v2(
                    order_id,
                    profile['package_id'],
                    profile['weight_oz'],
                    profile['length'],
                    profile['width'],
                    profile['height'],
                    num_packages=num_packages,
                )
                if not v2_result.get('success'):
                    server_logger.error(
                        f"V2 package update failed for home office order {order_number} "
                        f"(SS ID: {order_id}): {v2_result.get('error')}",
                        source="Lot Tagger"
                    )
                else:
                    server_logger.info(
                        f"V2 package set to {profile['package_id']} ×{num_packages} "
                        f"for home office order {order_number} (SS ID: {order_id})",
                        source="Lot Tagger"
                    )
        return

    cursor = conn.cursor()

    if len(tracked_items) > 1:
        skus_found = ','.join(str(item.get('sku', '')).strip() for item in tracked_items)
        cursor.execute("""
            INSERT INTO lot_tagging_failures (order_number, shipstation_order_id, sku, detected_at)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (shipstation_order_id) DO UPDATE
                SET detected_at = CURRENT_TIMESTAMP,
                    sku = EXCLUDED.sku
            WHERE lot_tagging_failures.resolved_at IS NULL
        """, (order_number, str(order_id), skus_found))
        conn.commit()
        server_logger.warning(
            f"Order {order_number} (SS ID: {order_id}) has multiple tracked SKUs [{skus_found}]. "
            f"Auto-split should prevent this. Logged to lot_tagging_failures — will retry.",
            source="Lot Tagger"
        )
        return

    item         = tracked_items[0]
    sku          = str(item.get('sku', '')).strip()
    # Use _effective_quantity when a variant SKU remap multiplied the package
    # count (e.g. 17612-6 at qty=1 → _effective_quantity=6); otherwise fall
    # back to the raw quantity for normal single-unit orders.
    num_packages = max(1, int(item.get('_effective_quantity') or item.get('quantity') or 1))

    # --- Balance-aware, reservation-backed lot selection (Task #131 fix) ---
    # Reuse an existing OPEN reservation for this order/sku when it is still
    # valid (lot still truly 'active' and quantity unchanged) instead of
    # burning a fresh reservation on every reconciliation pass. Otherwise
    # release any stale reservation and reserve against the first candidate
    # lot (sorted by lot_number) with enough *available* balance.
    existing_reservation = lot_reservation.get_reservation(conn, order_id, sku)
    lot_number = None
    if existing_reservation:
        res_status = lot_statuses.get((sku, existing_reservation['lot_number']))
        if res_status == 'active' and existing_reservation['reserved_qty'] == num_packages:
            lot_number = existing_reservation['lot_number']
        else:
            lot_reservation.release_reservation(
                conn, order_id, sku,
                reason=f"stale reservation (status={res_status}, qty {existing_reservation['reserved_qty']}→{num_packages})"
            )
            conn.commit()

    newly_reserved = False
    if lot_number is None:
        candidates = lot_candidates.get(sku, [])
        if not candidates:
            cursor.execute("""
                INSERT INTO lot_tagging_failures (order_number, shipstation_order_id, sku, detected_at)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (shipstation_order_id) DO UPDATE
                    SET detected_at = CURRENT_TIMESTAMP,
                        sku = EXCLUDED.sku
                WHERE lot_tagging_failures.resolved_at IS NULL
            """, (order_number, str(order_id), sku))
            conn.commit()
            server_logger.warning(
                f"No active lot for SKU {sku} on order {order_number} (SS ID: {order_id}). Logged to lot_tagging_failures.",
                source="Lot Tagger"
            )
            return

        reservation = lot_reservation.reserve_lot_for_order(
            conn, order_number, order_id, sku, num_packages, candidates, source='tagger'
        )
        conn.commit()
        if not reservation:
            cursor.execute("""
                INSERT INTO lot_tagging_failures (order_number, shipstation_order_id, sku, detected_at)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (shipstation_order_id) DO UPDATE
                    SET detected_at = CURRENT_TIMESTAMP,
                        sku = EXCLUDED.sku
                WHERE lot_tagging_failures.resolved_at IS NULL
            """, (order_number, str(order_id), sku))
            conn.commit()
            server_logger.warning(
                f"No active lot with enough available balance for {num_packages} unit(s) of "
                f"SKU {sku} on order {order_number} (SS ID: {order_id}). Logged to lot_tagging_failures.",
                source="Lot Tagger"
            )
            return
        lot_number = reservation['lot_number']
        newly_reserved = True

    expected_value = f"{sku} - {lot_number}"
    profile        = resolve_shipping_profile(order, sku)

    mismatched = _get_mismatched_fields(order, expected_value, profile)
    if lot_override:
        mismatched = [f for f in mismatched if f != 'customField1']
    if not mismatched:
        logger.debug(f"Order {order_number} already correct — skipped.")
        v2_result = ensure_v2_package(order_id, order_number, profile,
                                      num_packages=num_packages)
        if v2_result['action'] == 'updated':
            server_logger.info(
                f"V2 package swept to {profile['package_id']} ×{num_packages} "
                f"for order {order_number} (SS ID: {order_id})",
                source="Lot Tagger"
            )
        elif v2_result['action'] == 'error':
            server_logger.error(
                f"V2 package sweep failed for order {order_number} "
                f"(SS ID: {order_id}): {v2_result.get('error')}",
                source="Lot Tagger"
            )
        return

    adv         = order.get('advancedOptions') or {}
    current_cf1 = (adv.get('customField1') or '').strip()
    field2_value = current_cf1 if not lot_override and current_cf1 and current_cf1 != expected_value else None
    if field2_value:
        server_logger.warning(
            f"Order {order_number} (SS ID: {order_id}) customField1 currently '{current_cf1}'. "
            f"Moving to customField2 and writing correct lot.",
            source="Lot Tagger"
        )

    result = update_order_custom_fields(
        order_id, expected_value, field2_value,
        skip_cf1=lot_override,
        carrier_code=profile['carrier_code'],
        service_code=profile['service_code'],
        package_code=profile['package_code'],
        weight_oz=profile['weight_oz'],
        dim_length=profile['length'],
        dim_width=profile['width'],
        dim_height=profile['height'],
        bill_to_party=profile['bill_to_party'],
        bill_to_account=profile['bill_to_account'],
        bill_to_postal_code=profile.get('bill_to_postal_code'),
        bill_to_country_code=profile.get('bill_to_country_code'),
    )

    if not result.get('success'):
        if newly_reserved:
            lot_reservation.release_reservation(
                conn, order_id, sku, reason=f"ShipStation CF1 write failed: {result.get('error')}"
            )
            conn.commit()
        server_logger.error(
            f"Failed to tag order {order_number} (SS ID: {order_id}): {result.get('error')}",
            source="Lot Tagger"
        )
        return

    if not current_cf1:
        server_logger.info(
            f"Freshly tagged order {order_number} (SS ID: {order_id}) with '{expected_value}' "
            f"[{profile['service_code']}, account={profile['bill_to_account']}]",
            source="Lot Tagger"
        )
    else:
        server_logger.info(
            f"Corrected {len(mismatched)} field(s) on order {order_number} (SS ID: {order_id}) "
            f"lot='{expected_value}' [{profile['service_code']}, account={profile['bill_to_account']}] "
            f"fields={mismatched}",
            source="Lot Tagger"
        )
    if not lot_override:
        order.setdefault('advancedOptions', {})['customField1'] = expected_value

    if profile.get('package_id'):
        v2_result = update_order_package_v2(
            order_id,
            profile['package_id'],
            profile['weight_oz'],
            profile['length'],
            profile['width'],
            profile['height'],
            num_packages=num_packages,
        )
        if not v2_result.get('success'):
            server_logger.error(
                f"V2 package update failed for order {order_number} "
                f"(SS ID: {order_id}): {v2_result.get('error')}",
                source="Lot Tagger"
            )
        else:
            server_logger.info(
                f"V2 package set to {profile['package_id']} ×{num_packages} "
                f"for order {order_number} (SS ID: {order_id})",
                source="Lot Tagger"
            )

    cursor.execute("""
        UPDATE lot_tagging_failures
        SET resolved_at = CURRENT_TIMESTAMP,
            resolved_by = 'auto'
        WHERE shipstation_order_id = %s
          AND resolved_at IS NULL
    """, (str(order_id),))
    conn.commit()


def verify_tagging_results(
    orders: list,
    active_lots: Dict[str, str],
    known_skus: Set[str],
    conn,
    promo_map: dict = None,
) -> dict:
    """
    QA verification pass over the orders processed by the reconciliation run.

    Scans the in-memory order list (no extra API calls) and checks whether each
    tracked order has the expected customField1.  Reports a summary and creates a
    production_incidents record when failures are found.

    'Tracked' orders are those with a known SKU or a lot-stamped compound SKU.
    Home-office-only orders are excluded (they have no customField1 requirement).

    Returns:
        {
            'total_checked': int,       # total awaiting_shipment orders inspected
            'total_tracked': int,       # orders with tracked or lot-stamped SKUs
            'tagged_correctly': int,    # tracked orders whose customField1 is correct
            'untagged_or_wrong': int,   # tracked orders with missing/wrong customField1
        }
    """
    total_tracked = 0
    tagged_correctly = 0
    untagged_or_wrong = 0
    failures = []

    # Remap promo SKUs before the known_skus filter so promo-SKU orders
    # (e.g., SKU 17613) are not excluded from QA checks, masking failures.
    # When called from the scheduler, promo_map is pre-loaded before the loop
    # (a failure there aborts the batch). The None fallback supports direct /
    # test calls that don't pass the parameter.
    if promo_map is not None:
        _qa_promo_map = promo_map
    else:
        from src.services.inventory.promo_sku_utils import load_promo_map as _lpm
        _qa_promo_map = _lpm(conn)

    for order in orders:
        order_number = order.get('orderNumber', '').strip()
        order_id     = order.get('orderId')
        items        = list(order.get('items', []))
        current_cf1  = ((order.get('advancedOptions') or {}).get('customField1') or '').strip()

        if LOT_OVERRIDE_TAG_ID in (order.get('tagIds') or []):
            logger.debug(
                f"QA: order {order_number} (SS ID: {order_id}) has Lot Override tag — "
                f"excluded from CF1 QA check."
            )
            continue

        # Remap promo SKUs to base SKUs before the known_skus filter.
        if _qa_promo_map:
            items = [
                dict(_i, sku=_qa_promo_map.get(str(_i.get('sku') or '').strip(),
                                                str(_i.get('sku') or '').strip()))
                for _i in items
            ]

        tracked_items = [item for item in items if str(item.get('sku', '')).strip() in known_skus]

        if tracked_items:
            unique_skus = list({str(item.get('sku', '')).strip() for item in tracked_items})
            if len(unique_skus) > 1:
                continue
            sku = unique_skus[0]
            lot_number = active_lots.get(sku)
            if not lot_number:
                continue
            expected_cf1 = f"{sku} - {lot_number}"
            total_tracked += 1
            if current_cf1 == expected_cf1:
                tagged_correctly += 1
            else:
                untagged_or_wrong += 1
                failures.append((order_number, order_id, expected_cf1, current_cf1))
            continue

        stamped_items = []
        for item in items:
            parsed = _parse_lot_stamped_sku(str(item.get('sku', '')).strip())
            if parsed:
                stamped_items.append(parsed)

        if stamped_items:
            unique_bases = {base for base, _ in stamped_items}
            if len(unique_bases) > 1:
                continue
            _, expected_cf1 = stamped_items[0]
            total_tracked += 1
            if current_cf1 == expected_cf1:
                tagged_correctly += 1
            else:
                untagged_or_wrong += 1
                failures.append((order_number, order_id, expected_cf1, current_cf1))

    summary = {
        'total_checked': len(orders),
        'total_tracked': total_tracked,
        'tagged_correctly': tagged_correctly,
        'untagged_or_wrong': untagged_or_wrong,
    }

    failure_detail = '; '.join(
        f"{on}(SS:{oid}) exp='{ex}' got='{ac}'"
        for on, oid, ex, ac in failures[:5]
    )
    if len(failures) > 5:
        failure_detail += f' ... and {len(failures) - 5} more'

    if untagged_or_wrong == 0:
        server_logger.info(
            f"LOT TAGGER QA PASS: {tagged_correctly}/{total_tracked} tracked orders correctly tagged "
            f"({len(orders)} total awaiting_shipment scanned).",
            source="Lot Tagger"
        )
    else:
        server_logger.error(
            f"LOT TAGGER QA FAIL: {untagged_or_wrong}/{total_tracked} tracked orders have "
            f"missing or incorrect customField1 after tagging run. {failure_detail}",
            source="Lot Tagger"
        )

        try:
            cursor = conn.cursor()
            # Build a collision-proof title keyed on the exact sorted set of
            # failing order numbers. A short SHA-256 hash of the full sorted list
            # is embedded in the title so that:
            #   • exact same failure set  → same title  → deduplicated (no new incident)
            #   • any different set       → different title → new incident created
            # The human-readable truncated list is kept for operator visibility.
            failing_order_nums = sorted(on for on, oid, ex, ac in failures)
            order_hash = hashlib.sha256(
                ','.join(failing_order_nums).encode()
            ).hexdigest()[:8]
            if len(failing_order_nums) <= 5:
                order_key = ', '.join(failing_order_nums)
            else:
                order_key = ', '.join(failing_order_nums[:5]) + f' (+{len(failing_order_nums) - 5} more)'
            title = f"Lot Tagger QA: [{order_key}] untagged/wrong [ref:{order_hash}]"
            cursor.execute(
                """
                SELECT id FROM production_incidents
                WHERE title = %s AND status = 'new'
                ORDER BY created_at DESC LIMIT 1
                """,
                (title,)
            )
            if not cursor.fetchone():
                cursor.execute(
                    """
                    INSERT INTO production_incidents (title, description, severity, reported_by)
                    VALUES (%s, %s, 'high', 'lot-tagger (automated)')
                    """,
                    (
                        title,
                        (
                            f"{untagged_or_wrong} of {total_tracked} tracked awaiting_shipment orders "
                            f"still have missing or wrong customField1 after the reconciliation run. "
                            f"Order numbers: {order_key}. "
                            f"Failures: {failure_detail}"
                        ),
                    )
                )
                conn.commit()
                server_logger.error(
                    "Production incident opened for lot tagger QA failure.",
                    source="Lot Tagger"
                )
            cursor.close()
        except Exception as exc:
            logger.error(f"Failed to create production incident for QA failure: {exc}", exc_info=True)

    return summary
