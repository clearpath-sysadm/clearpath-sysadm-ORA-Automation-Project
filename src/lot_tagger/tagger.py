"""
Lot Tagger — shared tag_order_lots() function.

Called by both the webhook handler (Flask) and the reconciliation scheduler.
Callers must build active_lots and known_skus from the DB before calling this.
"""
import os
import logging
from typing import Dict, Set

from src.services.shipstation.api_client import update_order_custom_fields, update_order_package_v2
from src.utils.server_logger import get_logger
from utils.api_utils import make_api_request

logger = logging.getLogger(__name__)
server_logger = get_logger()

ACTIVE_LOTS_QUERY = """
    SELECT DISTINCT ON (s.sku_code) s.sku_code, l.lot_id, l.lot_number
    FROM lots l
    JOIN skus s ON s.sku_id = l.sku_id
    JOIN lot_balances lb ON lb.lot_id = l.lot_id
    WHERE lb.balance > 0
      AND l.status NOT IN ('quarantine', 'inactive')
    ORDER BY s.sku_code, l.received_date ASC NULLS LAST, l.lot_id ASC
"""

KNOWN_SKUS_QUERY = "SELECT sku_code FROM skus"

HOME_OFFICE_SKUS = {'18751', '18760', '18565'}

SKU_SHIPPING_PROFILES = {
    '17612': {'package_code': 'package', 'package_id': 'se-122675', 'length': 12.0, 'width': 12.0, 'height': 10.0, 'weight_oz': 352},
    '17914': {'package_code': 'package', 'package_id': 'se-122677', 'length': 11.0, 'width': 11.0, 'height':  8.0, 'weight_oz': 176},
    '17904': {'package_code': 'package', 'package_id': 'se-132840', 'length': 14.0, 'width': 12.0, 'height':  5.0, 'weight_oz': 224},
    '18675': {'package_code': 'package', 'package_id': 'se-122678', 'length': 12.0, 'width': 12.0, 'height': 10.0, 'weight_oz': 352},
    '18795': {'package_code': 'package', 'package_id': 'se-131836', 'length':  9.0, 'width':  5.0, 'height':  8.0, 'weight_oz':  80},
    '18751': {'package_code': 'package', 'package_id': 'se-135810', 'length':  9.0, 'width':  5.0, 'height':  7.0, 'weight_oz':  80},
    '18760': {'package_code': 'package', 'package_id': 'se-135809', 'length':  2.0, 'width':  2.0, 'height':  3.0, 'weight_oz':  32},
    '18565': {'package_code': 'package', 'package_id': 'se-135808', 'length':  9.0, 'width':  6.0, 'height':  4.0, 'weight_oz':  48},
}


def build_lot_maps(conn):
    """
    Build active_lots dict and known_skus set from the database.
    Uses FIFO (oldest received_date first) to resolve multiple active lots per SKU.

    Returns: (active_lots: dict[sku -> lot_number], known_skus: set[sku])
    """
    cursor = conn.cursor()

    cursor.execute(ACTIVE_LOTS_QUERY)
    active_lots = {row[0]: row[2] for row in cursor.fetchall()}

    cursor.execute(KNOWN_SKUS_QUERY)
    known_skus = {row[0] for row in cursor.fetchall()}

    return active_lots, known_skus


def resolve_shipping_profile(order: dict, sku: str) -> dict:
    """
    Derive the correct shipping profile for an order + SKU combination.

    Service code rules (highest priority first):
      - Preserve existing fedex_2day (never downgrade)
      - HI destination  → fedex_2day
      - CA destination  → fedex_international_ground
      - Default         → fedex_ground

    Billing account:
      - Company name contains 'BENCO' → BENCO_FEDEX_ACCOUNT_ID (ShipStation shippingProviderId)
      - All others                    → ORACARE_FEDEX_ACCOUNT_ID

    Package / dimensions / weight come from SKU_SHIPPING_PROFILES.
    Unknown SKUs get None for those fields — callers must omit them from the payload.

    Returns a dict with keys:
        carrier_code, service_code, bill_to_party, bill_to_account,
        package_code, weight_oz, length, width, height
    """
    ship_to = order.get('shipTo') or {}
    state   = (ship_to.get('state')   or '').strip().upper()
    country = (ship_to.get('country') or '').strip().upper()
    company = (ship_to.get('company') or '').strip().upper()
    current_service = (order.get('serviceCode') or '').strip()

    if current_service == 'fedex_2day':
        service_code = 'fedex_2day'
    elif state == 'HI':
        service_code = 'fedex_2day'
    elif country == 'CA':
        service_code = 'fedex_international_ground'
    else:
        service_code = 'fedex_ground'

    if 'BENCO' in company:
        benco_id = os.getenv('BENCO_FEDEX_ACCOUNT_ID')
        if not benco_id:
            raise ValueError("BENCO_FEDEX_ACCOUNT_ID environment variable is not configured")
        bill_to_account = int(benco_id)
    else:
        oracare_id = os.getenv('ORACARE_FEDEX_ACCOUNT_ID')
        if not oracare_id:
            raise ValueError("ORACARE_FEDEX_ACCOUNT_ID environment variable is not configured")
        bill_to_account = int(oracare_id)

    profile = SKU_SHIPPING_PROFILES.get(sku)
    if profile is None:
        logger.warning(f"SKU {sku!r} not in SKU_SHIPPING_PROFILES — package/dims/weight will not be set")

    return {
        'carrier_code':   'fedex',
        'service_code':   service_code,
        'bill_to_party':  'my_other_account',
        'bill_to_account': bill_to_account,
        'package_code':   profile['package_code'] if profile else None,
        'package_id':     profile['package_id']   if profile else None,
        'weight_oz':      profile['weight_oz']    if profile else None,
        'length':         profile['length']        if profile else None,
        'width':          profile['width']         if profile else None,
        'height':         profile['height']        if profile else None,
    }


def _is_fully_enriched(order: dict, expected_cf1: str, profile: dict) -> bool:
    """
    Return True only when every field the tagger owns already matches expected values.

    Fields checked:
        customField1, carrierCode, serviceCode,
        advancedOptions.packageCode (when profile has one),
        advancedOptions.billToParty, advancedOptions.billToMyOtherAccount.

    Weight and dimensions are intentionally excluded: ShipStation recalculates
    total weight when packages are added, so the stored value will legitimately
    differ from the per-unit weight after a user adds multiple boxes. Checking
    those fields would cause a write on every sweep pass for multi-package orders.
    """
    adv = order.get('advancedOptions') or {}

    if (adv.get('customField1') or '').strip() != expected_cf1:
        return False

    if (order.get('carrierCode') or '') != profile['carrier_code']:
        return False

    if (order.get('serviceCode') or '') != profile['service_code']:
        return False

    if adv.get('billToParty') != profile['bill_to_party']:
        return False

    if adv.get('billToMyOtherAccount') != profile['bill_to_account']:
        return False

    if profile['package_code'] is not None:
        if (order.get('packageCode') or '') != profile['package_code']:
            return False

    return True


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


def ensure_v2_package(order_id: int, order_number: str, profile: dict) -> dict:
    """
    Idempotent V2 named-package setter.

    GETs the V2 shipment once, checks packages[0].package_id against the
    expected value from `profile`. Only issues a PUT when they differ.

    This runs on every tagged order — including ones whose V1 fields are
    already correct — so the named custom package is always in sync with
    ShipStation regardless of whether a V1 write was needed.

    Returns:
        {'action': 'already_correct'} — V2 already has the right package
        {'action': 'updated'}         — V2 PUT succeeded
        {'action': 'skipped'}         — no package_id in profile (unsupported SKU)
        {'action': 'error', 'error': str} — GET or PUT failed
    """
    package_id = profile.get('package_id')
    if not package_id:
        return {'action': 'skipped'}

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
    current_pkg_id = packages[0].get('package_id') if packages else None

    if current_pkg_id == package_id:
        logger.debug(f"Order {order_number} V2 package already {package_id} — skipping PUT.")
        return {'action': 'already_correct'}

    shipment['packages'] = [
        {
            'package_id': package_id,
            'weight': {'value': profile['weight_oz'], 'unit': 'ounce'},
        }
    ]

    put_resp = make_api_request(url=url, method='PUT', headers=headers, data=shipment, timeout=30)
    if put_resp and put_resp.status_code in (200, 204):
        logger.info(f"V2: set package_id={package_id} on order {order_number} ({shipment_id})")
        return {'action': 'updated'}
    else:
        status = put_resp.status_code if put_resp else 'no response'
        body   = put_resp.text[:300]  if put_resp else ''
        return {'action': 'error', 'error': f'V2 PUT failed {status}: {body}'}


def tag_order_lots(order: dict, active_lots: Dict[str, str], known_skus: Set[str], conn) -> None:
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
    """
    order_number = order.get('orderNumber', '').strip()
    order_id     = order.get('orderId')
    items        = order.get('items', [])

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
                    stamped_items.append(parsed)

            if not stamped_items:
                return  # Truly untracked — nothing to do

            unique_bases = {base for base, _ in stamped_items}
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

            base_sku, exp_cf1 = stamped_items[0]
            profile = resolve_shipping_profile(order, base_sku)

            if _is_fully_enriched(order, exp_cf1, profile):
                logger.debug(f"Lot-stamped order {order_number} already fully enriched — skipping V1.")
                v2_result = ensure_v2_package(order_id, order_number, profile)
                if v2_result['action'] == 'updated':
                    server_logger.info(
                        f"V2 package swept to {profile['package_id']} for lot-stamped order "
                        f"{order_number} (SS ID: {order_id})",
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
                carrier_code=profile['carrier_code'],
                service_code=profile['service_code'],
                package_code=profile['package_code'],
                weight_oz=profile['weight_oz'],
                dim_length=profile['length'],
                dim_width=profile['width'],
                dim_height=profile['height'],
                bill_to_party=profile['bill_to_party'],
                bill_to_account=profile['bill_to_account'],
            )

            if not result.get('success'):
                server_logger.error(
                    f"Failed to enrich lot-stamped order {order_number} "
                    f"(SS ID: {order_id}): {result.get('error')}",
                    source="Lot Tagger"
                )
            else:
                server_logger.info(
                    f"Enriched lot-stamped order {order_number} (SS ID: {order_id}) "
                    f"CF1={exp_cf1!r} base_sku={base_sku}",
                    source="Lot Tagger"
                )
                if profile.get('package_id'):
                    v2_result = update_order_package_v2(
                        order_id,
                        profile['package_id'],
                        profile['weight_oz'],
                        profile['length'],
                        profile['width'],
                        profile['height'],
                    )
                    if not v2_result.get('success'):
                        server_logger.error(
                            f"V2 package update failed for lot-stamped order {order_number} "
                            f"(SS ID: {order_id}): {v2_result.get('error')}",
                            source="Lot Tagger"
                        )
                    else:
                        server_logger.info(
                            f"V2 package set to {profile['package_id']} for lot-stamped order "
                            f"{order_number} (SS ID: {order_id})",
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

        sku     = str(ho_items[0].get('sku', '')).strip()
        profile = resolve_shipping_profile(order, sku)

        if _is_fully_enriched(order, sku, profile):
            logger.debug(f"Order {order_number} (home office) already fully enriched — skipping V1.")
            v2_result = ensure_v2_package(order_id, order_number, profile)
            if v2_result['action'] == 'updated':
                server_logger.info(
                    f"V2 package swept to {profile['package_id']} for home office order "
                    f"{order_number} (SS ID: {order_id})",
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
            carrier_code=profile['carrier_code'],
            service_code=profile['service_code'],
            package_code=profile['package_code'],
            weight_oz=profile['weight_oz'],
            dim_length=profile['length'],
            dim_width=profile['width'],
            dim_height=profile['height'],
            bill_to_party=profile['bill_to_party'],
            bill_to_account=profile['bill_to_account'],
        )

        if not result.get('success'):
            server_logger.error(
                f"Failed to enrich home office order {order_number} (SS ID: {order_id}): {result.get('error')}",
                source="Lot Tagger"
            )
        else:
            server_logger.info(
                f"Enriched home office order {order_number} (SS ID: {order_id}) SKU={sku}",
                source="Lot Tagger"
            )
            if profile.get('package_id'):
                v2_result = update_order_package_v2(
                    order_id,
                    profile['package_id'],
                    profile['weight_oz'],
                    profile['length'],
                    profile['width'],
                    profile['height'],
                )
                if not v2_result.get('success'):
                    server_logger.error(
                        f"V2 package update failed for home office order {order_number} "
                        f"(SS ID: {order_id}): {v2_result.get('error')}",
                        source="Lot Tagger"
                    )
                else:
                    server_logger.info(
                        f"V2 package set to {profile['package_id']} for home office order "
                        f"{order_number} (SS ID: {order_id})",
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

    item = tracked_items[0]
    sku  = str(item.get('sku', '')).strip()

    if sku not in active_lots:
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

    expected_value = f"{sku} - {active_lots[sku]}"
    profile        = resolve_shipping_profile(order, sku)

    if _is_fully_enriched(order, expected_value, profile):
        logger.debug(f"Order {order_number} already fully enriched — skipping V1.")
        v2_result = ensure_v2_package(order_id, order_number, profile)
        if v2_result['action'] == 'updated':
            server_logger.info(
                f"V2 package swept to {profile['package_id']} for order "
                f"{order_number} (SS ID: {order_id})",
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
    field2_value = current_cf1 if current_cf1 and current_cf1 != expected_value else None
    if field2_value:
        server_logger.warning(
            f"Order {order_number} (SS ID: {order_id}) customField1 currently '{current_cf1}'. "
            f"Moving to customField2 and writing correct lot.",
            source="Lot Tagger"
        )

    result = update_order_custom_fields(
        order_id, expected_value, field2_value,
        carrier_code=profile['carrier_code'],
        service_code=profile['service_code'],
        package_code=profile['package_code'],
        weight_oz=profile['weight_oz'],
        dim_length=profile['length'],
        dim_width=profile['width'],
        dim_height=profile['height'],
        bill_to_party=profile['bill_to_party'],
        bill_to_account=profile['bill_to_account'],
    )

    if not result.get('success'):
        server_logger.error(
            f"Failed to tag order {order_number} (SS ID: {order_id}): {result.get('error')}",
            source="Lot Tagger"
        )
        return

    server_logger.info(
        f"Tagged order {order_number} (SS ID: {order_id}) with '{expected_value}' "
        f"[{profile['service_code']}, account={profile['bill_to_account']}]",
        source="Lot Tagger"
    )

    if profile.get('package_id'):
        v2_result = update_order_package_v2(
            order_id,
            profile['package_id'],
            profile['weight_oz'],
            profile['length'],
            profile['width'],
            profile['height'],
        )
        if not v2_result.get('success'):
            server_logger.error(
                f"V2 package update failed for order {order_number} "
                f"(SS ID: {order_id}): {v2_result.get('error')}",
                source="Lot Tagger"
            )
        else:
            server_logger.info(
                f"V2 package set to {profile['package_id']} for order "
                f"{order_number} (SS ID: {order_id})",
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
