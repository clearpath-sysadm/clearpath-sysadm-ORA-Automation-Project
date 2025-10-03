#!/usr/bin/env python3
"""
Shipping Validation Service

Validates orders against shipping business rules and creates violation alerts.
This is an ALERT-ONLY system - it does not modify or enforce shipping rules,
but provides visibility into potential violations for manual review.

Business Rules:
1. Hawaiian orders (HI) → Should use FedEx 2Day service
2. Canadian orders (CA/CANADA) → Should use FedEx International Ground
3. Benco orders → Should use Benco FedEx carrier account (identified by carrier_id)

The system:
- DETECTS actual carrier/service assignments from ShipStation
- COMPARES against expected rules
- CREATES alerts in shipping_violations table
- DOES NOT modify ShipStation orders (manual overrides allowed)
"""

import sys
import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.services.database.db_utils import execute_query, transaction
from utils.logging_config import setup_logging

# Logging setup
log_dir = os.path.join(project_root, 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'shipping_validator.log')
setup_logging(log_file_path=log_file, log_level=logging.INFO, enable_console_logging=True)
logger = logging.getLogger(__name__)


# TODO: Get actual Benco carrier_id from ShipStation account
# This will need to be configured based on the actual carrier_id values seen in production
BENCO_CARRIER_IDS = []  # e.g., ['123456'] - update after observing actual values


def validate_order_shipping(order: Dict[str, Any]) -> tuple[str, List[Dict[str, Any]]]:
    """
    Validate a single order against ALL shipping rules.
    
    Returns:
        tuple: (status, violations_list)
        - status: 'skipped' | 'compliant' | 'violations'
        - violations_list: List of violation dicts (empty if compliant or skipped)
    """
    order_id = order['id']
    order_number = order['order_number']
    ship_state = (order.get('ship_state') or '').strip().upper()
    ship_country = (order.get('ship_country') or '').strip().upper()
    ship_company = (order.get('ship_company') or '').strip().upper()
    
    carrier_code = order.get('shipping_carrier_code')
    carrier_id = order.get('shipping_carrier_id')
    service_code = order.get('shipping_service_code')
    service_name = order.get('shipping_service_name')
    
    # Skip validation if carrier info not yet captured
    if not carrier_code and not service_code:
        logger.debug(f"Skipping order {order_number} - no carrier/service data yet")
        return ('skipped', [])
    
    violations = []
    
    # Rule 1: Hawaiian orders should use FedEx 2Day
    if ship_state == 'HI':
        expected_service = 'fedex_2day'
        if service_code != expected_service:
            violations.append({
                'order_inbox_id': order_id,
                'order_number': order_number,
                'rule_type': 'hawaiian_fedex_2day',
                'expected_carrier': 'fedex',
                'expected_service': expected_service,
                'expected_service_name': 'FedEx 2Day',
                'actual_carrier': carrier_code,
                'actual_service': service_code,
                'actual_service_name': service_name,
                'ship_state': ship_state,
                'ship_country': ship_country,
                'ship_company': ship_company,
                'severity': 'HIGH',
                'message': f'Hawaiian order should use FedEx 2Day, currently using {service_name or service_code or "unknown service"}'
            })
    
    # Rule 2: Canadian orders should use FedEx International Ground
    if ship_country in ['CA', 'CANADA']:
        expected_service = 'fedex_international_ground'
        if service_code != expected_service:
            violations.append({
                'order_inbox_id': order_id,
                'order_number': order_number,
                'rule_type': 'canadian_international_ground',
                'expected_carrier': 'fedex',
                'expected_service': expected_service,
                'expected_service_name': 'FedEx International Ground',
                'actual_carrier': carrier_code,
                'actual_service': service_code,
                'actual_service_name': service_name,
                'ship_state': ship_state,
                'ship_country': ship_country,
                'ship_company': ship_company,
                'severity': 'HIGH',
                'message': f'Canadian order should use FedEx International Ground, currently using {service_name or service_code or "unknown service"}'
            })
    
    # Rule 3: Benco orders should use Benco FedEx carrier account
    if 'BENCO' in ship_company:
        # Check if carrier_id is populated and matches Benco account
        if carrier_id and BENCO_CARRIER_IDS:
            if carrier_id not in BENCO_CARRIER_IDS:
                violations.append({
                    'order_inbox_id': order_id,
                    'order_number': order_number,
                    'rule_type': 'benco_carrier_account',
                    'expected_carrier': 'fedex',
                    'expected_service': None,
                    'expected_service_name': 'Benco FedEx Account',
                    'actual_carrier': carrier_code,
                    'actual_service': service_code,
                    'actual_service_name': service_name,
                    'ship_state': ship_state,
                    'ship_country': ship_country,
                    'ship_company': ship_company,
                    'severity': 'CRITICAL',
                    'message': f'Benco order should use Benco FedEx carrier account, currently using carrier_id: {carrier_id}'
                })
        elif not carrier_id and BENCO_CARRIER_IDS:
            # carrier_id not yet captured - log info but skip Benco validation for now
            logger.info(f"Benco order {order_number} missing carrier_id - will validate once captured")
    
    if violations:
        return ('violations', violations)
    else:
        return ('compliant', [])


def get_orders_for_validation() -> List[Dict[str, Any]]:
    """
    Get orders that need shipping validation.
    Returns orders with carrier/service data that haven't been validated yet or have changed.
    """
    try:
        rows = execute_query("""
            SELECT 
                o.id,
                o.order_number,
                o.ship_state,
                o.ship_country,
                o.ship_company,
                o.shipping_carrier_code,
                o.shipping_carrier_id,
                o.shipping_service_code,
                o.shipping_service_name,
                o.status
            FROM orders_inbox o
            WHERE o.status IN ('awaiting_shipment', 'pending', 'shipped', 'on_hold')
              AND (o.shipping_carrier_code IS NOT NULL OR o.shipping_service_code IS NOT NULL)
            ORDER BY o.order_date DESC
        """)
        
        orders = []
        for row in rows:
            orders.append({
                'id': row[0],
                'order_number': row[1],
                'ship_state': row[2],
                'ship_country': row[3],
                'ship_company': row[4],
                'shipping_carrier_code': row[5],
                'shipping_carrier_id': row[6],
                'shipping_service_code': row[7],
                'shipping_service_name': row[8],
                'status': row[9]
            })
        
        logger.info(f"Found {len(orders)} orders with carrier/service data for validation")
        return orders
        
    except Exception as e:
        logger.error(f"Error getting orders for validation: {e}", exc_info=True)
        return []


def clear_resolved_violations(order_inbox_id: int):
    """
    Mark existing violations as resolved for an order that now passes validation.
    """
    try:
        with transaction() as conn:
            conn.execute("""
                UPDATE shipping_violations
                SET is_resolved = 1,
                    resolved_at = CURRENT_TIMESTAMP
                WHERE order_id = ?
                  AND is_resolved = 0
            """, (order_inbox_id,))
    except Exception as e:
        logger.error(f"Error clearing resolved violations: {e}", exc_info=True)


def create_or_update_violation(violation: Dict[str, Any]):
    """
    Create a new violation or update existing one if already exists.
    Adapts to the simplified database schema: order_id, violation_type, expected_value, actual_value, is_resolved.
    """
    try:
        # Map rule_type to database violation_type
        rule_type_map = {
            'hawaiian_fedex_2day': 'hawaiian_service',
            'canadian_international_ground': 'canadian_service',
            'benco_carrier_account': 'benco_carrier'
        }
        db_violation_type = rule_type_map.get(violation['rule_type'], violation['rule_type'])
        
        # Build expected/actual strings
        expected_str = f"{violation['expected_service_name'] or violation['expected_service'] or 'Correct carrier'}"
        actual_str = f"{violation['actual_service_name'] or violation['actual_service'] or violation['actual_carrier'] or 'Unknown'}"
        
        with transaction() as conn:
            # Check if violation already exists
            existing = conn.execute("""
                SELECT id, is_resolved FROM shipping_violations
                WHERE order_id = ? AND violation_type = ?
                ORDER BY detected_at DESC
                LIMIT 1
            """, (violation['order_inbox_id'], db_violation_type)).fetchone()
            
            if existing:
                violation_id, is_resolved = existing
                if is_resolved == 0:
                    # Update existing unresolved violation
                    conn.execute("""
                        UPDATE shipping_violations
                        SET expected_value = ?,
                            actual_value = ?
                        WHERE id = ?
                    """, (expected_str, actual_str, violation_id))
                    logger.info(f"Updated existing violation for order {violation['order_number']}")
                else:
                    # Re-open resolved violation
                    conn.execute("""
                        UPDATE shipping_violations
                        SET is_resolved = 0,
                            resolved_at = NULL,
                            expected_value = ?,
                            actual_value = ?
                        WHERE id = ?
                    """, (expected_str, actual_str, violation_id))
                    logger.info(f"Re-opened resolved violation for order {violation['order_number']}")
            else:
                # Create new violation
                conn.execute("""
                    INSERT INTO shipping_violations (
                        order_id, order_number, violation_type,
                        expected_value, actual_value, is_resolved
                    )
                    VALUES (?, ?, ?, ?, ?, 0)
                """, (
                    violation['order_inbox_id'], violation['order_number'], db_violation_type,
                    expected_str, actual_str
                ))
                logger.info(f"Created new violation for order {violation['order_number']}: {violation['message']}")
    
    except Exception as e:
        logger.error(f"Error creating/updating violation: {e}", exc_info=True)


def run_validation() -> Dict[str, Any]:
    """
    Main validation function - checks all orders and creates/updates violations.
    Returns summary statistics.
    """
    logger.info("=== Starting Shipping Validation ===")
    
    orders = get_orders_for_validation()
    
    if not orders:
        logger.info("No orders to validate")
        return {
            'total_orders': 0,
            'violations_found': 0,
            'compliant': 0,
            'skipped': 0
        }
    
    violation_count = 0
    compliant_count = 0
    skipped_count = 0
    
    for order in orders:
        status, violations = validate_order_shipping(order)
        
        if status == 'violations':
            # Create/update violations for this order
            for violation in violations:
                create_or_update_violation(violation)
            violation_count += len(violations)
        elif status == 'compliant':
            # Order passes validation - clear any existing violations
            clear_resolved_violations(order['id'])
            compliant_count += 1
        elif status == 'skipped':
            # Order skipped due to missing data - don't touch existing violations
            skipped_count += 1
    
    logger.info(f"Validation complete: {violation_count} violations found, {compliant_count} orders compliant, {skipped_count} orders skipped")
    
    return {
        'total_orders': len(orders),
        'violations_found': violation_count,
        'compliant': compliant_count,
        'skipped': skipped_count
    }


if __name__ == '__main__':
    result = run_validation()
    print(f"Validation Results: {result}")
