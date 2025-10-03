#!/usr/bin/env python3
"""
Ad-hoc validation and correction script for orders_inbox table.

This script validates existing orders against ShipStation API and corrects:
1. Missing ShipStation IDs for orders that exist in ShipStation
2. Incorrect status values
3. Missing or incomplete address information
4. Duplicate ShipStation order IDs

Usage:
    python utils/validate_and_fix_orders.py [--dry-run] [--limit N]
    
Options:
    --dry-run    Show what would be fixed without making changes
    --limit N    Only process first N orders (for testing)
"""

import sys
import os
import sqlite3
import argparse
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.services.shipstation import api_client as shipstation_api
from config import settings
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OrderValidator:
    """Validates and corrects orders against ShipStation requirements."""
    
    def __init__(self, db_path='ora.db', dry_run=False):
        self.db_path = db_path
        self.dry_run = dry_run
        
        # Get ShipStation credentials
        self.api_key, self.api_secret = shipstation_api.get_shipstation_credentials()
        self.ss_headers = shipstation_api.get_shipstation_headers(self.api_key, self.api_secret)
        self.stats = {
            'total_checked': 0,
            'missing_ss_id': 0,
            'wrong_status': 0,
            'missing_addresses': 0,
            'duplicates_found': 0,
            'corrections_made': 0,
            'errors': 0
        }
    
    def validate_all_orders(self, limit=None):
        """Validate all orders in the database."""
        logger.info("=== Starting Order Validation and Correction ===")
        logger.info(f"Mode: {'DRY RUN (no changes)' if self.dry_run else 'LIVE (making corrections)'}")
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        try:
            # Get all orders that are not in 'pending' status (already uploaded or synced)
            query = """
                SELECT id, order_number, status, shipstation_order_id, customer_email,
                       ship_name, ship_company, ship_street1, ship_city, ship_state,
                       ship_postal_code, ship_country, ship_phone,
                       bill_name, bill_company, bill_street1, bill_city, bill_state,
                       bill_postal_code, bill_country, bill_phone,
                       source_system
                FROM orders_inbox
                WHERE status != 'pending'
                ORDER BY id
            """
            if limit:
                query += f" LIMIT {limit}"
            
            cursor = conn.execute(query)
            orders = cursor.fetchall()
            
            logger.info(f"Found {len(orders)} orders to validate")
            
            for order in orders:
                self.stats['total_checked'] += 1
                self.validate_order(conn, order)
            
            if not self.dry_run:
                conn.commit()
                logger.info("Changes committed to database")
            
            self.print_summary()
            
        finally:
            conn.close()
    
    def validate_order(self, conn, order):
        """Validate a single order against ShipStation."""
        order_number = order['order_number']
        order_id = order['id']
        
        try:
            # Query ShipStation for this order
            logger.debug(f"Validating order {order_number}...")
            
            ss_orders = shipstation_api.fetch_shipstation_orders_by_order_numbers(
                self.api_key,
                self.api_secret,
                settings.SHIPSTATION_ORDERS_ENDPOINT,
                [order_number]
            )
            
            if not ss_orders or len(ss_orders) == 0:
                # Order not found in ShipStation - this might be OK if it's pending
                logger.debug(f"Order {order_number} not found in ShipStation (may not be uploaded yet)")
                return
            
            # Get the first matching order
            ss_order = ss_orders[0]
            ss_order_id = str(ss_order.get('orderId'))
            ss_status = ss_order.get('orderStatus', 'unknown')
            
            corrections = []
            
            # 1. Check if ShipStation ID is missing
            if not order['shipstation_order_id']:
                self.stats['missing_ss_id'] += 1
                corrections.append(f"Missing ShipStation ID: {ss_order_id}")
                if not self.dry_run:
                    conn.execute(
                        "UPDATE orders_inbox SET shipstation_order_id = ? WHERE id = ?",
                        (ss_order_id, order_id)
                    )
            
            # 2. Check if ShipStation ID is wrong (duplicate detection)
            elif order['shipstation_order_id'] != ss_order_id:
                self.stats['duplicates_found'] += 1
                corrections.append(f"Wrong ShipStation ID: {order['shipstation_order_id']} → {ss_order_id}")
                if not self.dry_run:
                    conn.execute(
                        "UPDATE orders_inbox SET shipstation_order_id = ? WHERE id = ?",
                        (ss_order_id, order_id)
                    )
            
            # 3. Validate status mapping
            status_map = {
                'awaiting_payment': 'awaiting_payment',
                'awaiting_shipment': 'uploaded',
                'shipped': 'shipped',
                'on_hold': 'on_hold',
                'cancelled': 'cancelled'
            }
            
            expected_status = status_map.get(ss_status, order['status'])
            if order['status'] != expected_status and expected_status != order['status']:
                self.stats['wrong_status'] += 1
                corrections.append(f"Wrong status: {order['status']} → {expected_status}")
                if not self.dry_run:
                    conn.execute(
                        "UPDATE orders_inbox SET status = ? WHERE id = ?",
                        (expected_status, order_id)
                    )
            
            # 4. Check for missing address information
            ship_to = ss_order.get('shipTo', {})
            bill_to = ss_order.get('billTo', {})
            
            address_corrections = self.validate_addresses(conn, order_id, order, ship_to, bill_to)
            if address_corrections:
                self.stats['missing_addresses'] += 1
                corrections.extend(address_corrections)
            
            if corrections:
                self.stats['corrections_made'] += 1
                logger.info(f"Order {order_number}: {len(corrections)} corrections")
                for correction in corrections:
                    logger.info(f"  - {correction}")
        
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Error validating order {order_number}: {e}")
    
    def validate_addresses(self, conn, order_id, order, ship_to, bill_to):
        """Validate and correct address information."""
        corrections = []
        updates = {}
        
        # Define address field mappings
        ship_fields = {
            'ship_name': ship_to.get('name'),
            'ship_company': ship_to.get('company'),
            'ship_street1': ship_to.get('street1'),
            'ship_city': ship_to.get('city'),
            'ship_state': ship_to.get('state'),
            'ship_postal_code': ship_to.get('postalCode'),
            'ship_country': ship_to.get('country'),
            'ship_phone': ship_to.get('phone')
        }
        
        bill_fields = {
            'bill_name': bill_to.get('name'),
            'bill_company': bill_to.get('company'),
            'bill_street1': bill_to.get('street1'),
            'bill_city': bill_to.get('city'),
            'bill_state': bill_to.get('state'),
            'bill_postal_code': bill_to.get('postalCode'),
            'bill_country': bill_to.get('country'),
            'bill_phone': bill_to.get('phone')
        }
        
        # Check shipping address
        for field, ss_value in ship_fields.items():
            if ss_value and not order[field]:
                corrections.append(f"Missing {field}: {ss_value}")
                updates[field] = ss_value.strip() if isinstance(ss_value, str) else ss_value
        
        # Check billing address
        for field, ss_value in bill_fields.items():
            if ss_value and not order[field]:
                corrections.append(f"Missing {field}: {ss_value}")
                updates[field] = ss_value.strip() if isinstance(ss_value, str) else ss_value
        
        # Apply updates if any
        if updates and not self.dry_run:
            set_clause = ', '.join([f"{field} = ?" for field in updates.keys()])
            values = list(updates.values()) + [order_id]
            conn.execute(
                f"UPDATE orders_inbox SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                values
            )
        
        return corrections
    
    def print_summary(self):
        """Print validation summary."""
        logger.info("\n=== Validation Summary ===")
        logger.info(f"Total orders checked: {self.stats['total_checked']}")
        logger.info(f"Orders with corrections: {self.stats['corrections_made']}")
        logger.info(f"  - Missing ShipStation IDs: {self.stats['missing_ss_id']}")
        logger.info(f"  - Wrong status: {self.stats['wrong_status']}")
        logger.info(f"  - Missing addresses: {self.stats['missing_addresses']}")
        logger.info(f"  - Duplicate IDs found: {self.stats['duplicates_found']}")
        logger.info(f"Errors encountered: {self.stats['errors']}")
        
        if self.dry_run:
            logger.info("\n⚠️  DRY RUN MODE - No changes were made to the database")
            logger.info("Run without --dry-run to apply corrections")
        else:
            logger.info("\n✅ All corrections have been applied to the database")


def main():
    parser = argparse.ArgumentParser(
        description='Validate and correct orders against ShipStation requirements'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be fixed without making changes'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Only process first N orders (for testing)'
    )
    
    args = parser.parse_args()
    
    validator = OrderValidator(dry_run=args.dry_run)
    validator.validate_all_orders(limit=args.limit)


if __name__ == '__main__':
    main()
