#!/usr/bin/env python3
"""
One-shot fix: Update customField1 to '17612 - 260017' for XML-imported
ShipStation orders 10206–10210, which were stamped with stale lot 250070.

Usage:
    python src/fix_xml_lot_stamps.py

The script:
  1. Looks up each order number in ShipStation by ?orderNumber= query.
  2. Updates customField1 to '17612 - 260017' while preserving all other fields.
  3. Verifies the V2 package preset via ensure_v2_package().
"""
import os
import sys
import logging
import time
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.shipstation.api_client import (
    get_shipstation_credentials,
    get_shipstation_headers,
    update_order_custom_fields,
)
from src.lot_tagger.tagger import ensure_v2_package, SKU_SHIPPING_PROFILES
from utils.api_utils import make_api_request

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

CORRECT_CF1 = '17612 - 260017'
BASE_SKU = '17612'
ORDER_NUMBERS = ['10206', '10207', '10208', '10209', '10210']
SHIPSTATION_ORDERS_URL = 'https://ssapi.shipstation.com/orders'


def lookup_order_by_number(order_number: str, headers: dict) -> dict | None:
    """Fetch a ShipStation order by order number. Returns None if not found."""
    response = make_api_request(
        url=SHIPSTATION_ORDERS_URL,
        method='GET',
        headers=headers,
        params={'orderNumber': order_number, 'pageSize': 10},
        timeout=30,
    )
    if not response or response.status_code != 200:
        logger.error(f"Order {order_number}: lookup failed — HTTP {response.status_code if response else 'no response'}")
        return None

    data = response.json()
    orders = data.get('orders', [])
    if not orders:
        logger.warning(f"Order {order_number}: not found in ShipStation")
        return None

    if len(orders) > 1:
        logger.warning(f"Order {order_number}: {len(orders)} matches found — using first")

    return orders[0]


def fix_order(order_number: str, headers: dict) -> str:
    """
    Look up order_number, update CF1 to CORRECT_CF1 if needed, then verify V2 package.
    Returns:
        'ok'        — completed without error (already correct or updated)
        'not_found' — order does not exist in ShipStation (already shipped/removed)
        'error'     — API call failed
    """
    order = lookup_order_by_number(order_number, headers)
    if order is None:
        return 'not_found'

    order_id = order.get('orderId')
    status = order.get('orderStatus', '')
    current_cf1 = (order.get('advancedOptions') or {}).get('customField1', '')

    logger.info(
        f"Order {order_number} (SS ID: {order_id}): status={status}, "
        f"current CF1={current_cf1!r}"
    )

    if current_cf1 == CORRECT_CF1:
        logger.info(f"Order {order_number}: CF1 already correct — skipping V1 update")
    else:
        logger.info(f"Order {order_number}: updating CF1 '{current_cf1}' → '{CORRECT_CF1}'")
        result = update_order_custom_fields(order_id, CORRECT_CF1, None)
        if not result.get('success'):
            logger.error(f"Order {order_number}: CF1 update failed — {result.get('error')}")
            return 'error'
        logger.info(f"Order {order_number}: CF1 updated successfully")

    profile = SKU_SHIPPING_PROFILES.get(BASE_SKU)
    if not profile:
        logger.warning(f"Order {order_number}: SKU {BASE_SKU} not in SKU_SHIPPING_PROFILES — skipping V2")
        return 'ok'

    v2_result = ensure_v2_package(order_id, order_number, profile, num_packages=1)
    action = v2_result.get('action')
    if action == 'already_correct':
        logger.info(f"Order {order_number}: V2 package already correct")
    elif action == 'updated':
        logger.info(f"Order {order_number}: V2 package updated to {profile['package_id']}")
    elif action == 'skipped':
        logger.info(f"Order {order_number}: V2 package skipped (no package_id in profile)")
    else:
        logger.error(f"Order {order_number}: V2 package error — {v2_result.get('error')}")
        return 'error'

    return 'ok'


def main():
    api_key, api_secret = get_shipstation_credentials()
    if not api_key or not api_secret:
        logger.error("Could not retrieve ShipStation credentials — aborting")
        sys.exit(1)

    headers = get_shipstation_headers(api_key, api_secret)

    logger.info(f"Fixing lot stamps for orders: {ORDER_NUMBERS}")
    logger.info(f"Correct CF1 value: '{CORRECT_CF1}'")
    logger.info("=" * 60)

    results = {}
    for order_number in ORDER_NUMBERS:
        logger.info(f"--- Processing order {order_number} ---")
        outcome = fix_order(order_number, headers)
        results[order_number] = outcome
        time.sleep(0.5)

    logger.info("=" * 60)
    logger.info("RESULTS:")
    for order_number, outcome in results.items():
        label = {'ok': 'OK', 'not_found': 'NOT FOUND (already shipped/removed)', 'error': 'ERROR'}.get(outcome, outcome)
        logger.info(f"  Order {order_number}: {label}")

    errors = [o for o, r in results.items() if r == 'error']
    if errors:
        logger.error(f"Errors on orders: {errors}")
        sys.exit(1)
    logger.info("Fix script complete.")


if __name__ == '__main__':
    main()
