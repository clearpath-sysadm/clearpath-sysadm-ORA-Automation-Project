#!/usr/bin/env python3
"""
ShipStation Duplicate Cleanup Utility
Safely removes duplicate orders from ShipStation based on cleanup strategy

Usage:
    # Dry-run (safe, no changes):
    python utils/cleanup_shipstation_duplicates.py --dry-run
    
    # Execute cleanup:
    python utils/cleanup_shipstation_duplicates.py --execute
    
    # Execute with auto-confirm:
    python utils/cleanup_shipstation_duplicates.py --execute --confirm
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path
from time import sleep

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.shipstation.api_client import get_shipstation_credentials, get_shipstation_headers
from src.services.database.db_utils import get_connection
from config.settings import settings
from utils.api_utils import make_api_request
from utils.identify_shipstation_duplicates import (
    fetch_all_shipstation_orders,
    identify_duplicates
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_active_lot_map():
    """
    Get active lot numbers from sku_lot table
    
    Returns:
        Dictionary mapping base SKU (5 digits) to active lot number
        Example: {"17612": "250300"}
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT sku, lot
        FROM sku_lot
        WHERE active = 1
    """)
    
    # FIX: Normalize keys to base SKU (first 5 chars) for lookup compatibility
    lot_map = {}
    for sku, lot in cursor.fetchall():
        # Extract base SKU - handle both "17612" and "17612-250300" formats
        base_sku = sku.split('-')[0].strip()[:5]
        lot_map[base_sku] = lot
    
    conn.close()
    
    logger.info(f"Loaded {len(lot_map)} active SKU-lot mappings")
    return lot_map


def create_cleanup_plan(duplicates, active_lots):
    """
    Create cleanup plan for duplicates
    
    Strategy:
    1. For orders with different lot numbers: Keep order with ACTIVE lot
    2. For orders with same lot: Keep EARLIEST order (first uploaded)
    3. Cannot delete shipped orders (API restriction)
    
    Args:
        duplicates: Dictionary from identify_duplicates()
        active_lots: Dictionary of {sku: lot} for active lots
        
    Returns:
        Dictionary with 'keep' and 'delete' lists
    """
    plan = {
        'keep': [],
        'delete': [],
        'cannot_delete': []  # Shipped orders
    }
    
    for (order_num, base_sku), items in duplicates.items():
        # Sort by create_date (earliest first)
        items_sorted = sorted(items, key=lambda x: x['create_date'] or '')
        
        # Determine which to keep
        active_lot = active_lots.get(base_sku)
        keep_item = None
        
        if active_lot:
            # Strategy: Keep order with active lot number
            for item in items_sorted:
                full_sku = item['full_sku']
                
                # Parse SKU into (base, lot) components for robust comparison
                # Handles formats: "17612-250300", "17612 - 250300", "17612  -  250300"
                sku_parts = full_sku.replace(' ', '').split('-')
                
                if len(sku_parts) == 2:
                    sku_base, sku_lot = sku_parts
                    # Match if lot number matches active lot (base_sku already matches from grouping)
                    if sku_lot == str(active_lot):
                        keep_item = item
                        keep_item['keep_reason'] = f'Active lot: {active_lot}'
                        logger.info(f"  → Keeping order with active lot {active_lot}: {full_sku}")
                        break
                elif full_sku == base_sku:
                    # SKU without lot number - check if it's the base SKU itself
                    logger.warning(f"  → SKU has no lot number: {full_sku}")
                    continue
                else:
                    logger.warning(f"  → Unexpected SKU format: {full_sku}")
                    continue
        
        # Fallback: Keep earliest order if no active lot match
        if not keep_item:
            keep_item = items_sorted[0]
            keep_item['keep_reason'] = 'Earliest created'
        
        plan['keep'].append(keep_item)
        
        # Mark others for deletion
        for item in items_sorted:
            if item['shipstation_order_id'] == keep_item['shipstation_order_id']:
                continue
            
            # Check if shipped (cannot delete)
            if item['order_status'] in ['shipped', 'cancelled']:
                item['cannot_delete_reason'] = f"Status: {item['order_status']}"
                plan['cannot_delete'].append(item)
            else:
                item['delete_reason'] = f"Duplicate of {keep_item['shipstation_order_id']}"
                plan['delete'].append(item)
    
    return plan


def print_cleanup_plan(plan):
    """Print cleanup plan summary"""
    
    print("\n" + "="*80)
    print("CLEANUP PLAN SUMMARY")
    print("="*80 + "\n")
    
    print(f"Orders to KEEP: {len(plan['keep'])}")
    print(f"Orders to DELETE: {len(plan['delete'])}")
    print(f"Orders CANNOT DELETE (shipped/cancelled): {len(plan['cannot_delete'])}\n")
    
    if plan['delete']:
        print("="*80)
        print("ORDERS TO DELETE:")
        print("="*80)
        
        for item in plan['delete'][:20]:  # Show first 20
            print(f"\n❌ DELETE: {item['order_number']} | {item['full_sku']}")
            print(f"   ShipStation ID: {item['shipstation_order_id']}")
            print(f"   Status: {item['order_status']}")
            print(f"   Created: {item['create_date']}")
            print(f"   Reason: {item['delete_reason']}")
        
        if len(plan['delete']) > 20:
            print(f"\n   ... and {len(plan['delete']) - 20} more")
    
    if plan['cannot_delete']:
        print("\n" + "="*80)
        print("ORDERS CANNOT DELETE (Manual Review Needed):")
        print("="*80)
        
        for item in plan['cannot_delete'][:10]:
            print(f"\n⚠️  SKIP: {item['order_number']} | {item['full_sku']}")
            print(f"   ShipStation ID: {item['shipstation_order_id']}")
            print(f"   Reason: {item['cannot_delete_reason']}")
        
        if len(plan['cannot_delete']) > 10:
            print(f"\n   ... and {len(plan['cannot_delete']) - 10} more")
    
    print("\n" + "="*80 + "\n")


def delete_shipstation_order(api_key, api_secret, order_id):
    """
    Delete an order from ShipStation
    
    Args:
        api_key: ShipStation API key
        api_secret: ShipStation API secret
        order_id: ShipStation order ID to delete
        
    Returns:
        Tuple (success: bool, error_message: str or None)
    """
    try:
        headers = get_shipstation_headers(api_key, api_secret)
        response = make_api_request(
            url=f"{settings.SHIPSTATION_ORDERS_ENDPOINT}/{order_id}",
            method='DELETE',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            return True, None
        else:
            error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            return False, error_msg
            
    except Exception as e:
        return False, str(e)


def execute_cleanup(plan, api_key, api_secret, batch_size=10, batch_delay=2, auto_confirm=False):
    """
    Execute the cleanup plan
    
    Args:
        plan: Cleanup plan from create_cleanup_plan()
        api_key: ShipStation API key
        api_secret: ShipStation API secret
        batch_size: Number of orders to process per batch
        batch_delay: Seconds to wait between batches
        auto_confirm: Skip manual confirmation prompts
    """
    orders_to_delete = plan['delete']
    total = len(orders_to_delete)
    
    if total == 0:
        logger.info("No orders to delete")
        return
    
    logger.info(f"Starting cleanup: {total} orders to delete")
    
    success_count = 0
    error_count = 0
    errors = []
    
    # Process in batches
    for i in range(0, total, batch_size):
        batch = orders_to_delete[i:i+batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (total + batch_size - 1) // batch_size
        
        print(f"\n{'='*80}")
        print(f"BATCH {batch_num}/{total_batches} ({len(batch)} orders)")
        print(f"{'='*80}\n")
        
        # Show batch details
        for item in batch:
            print(f"  - {item['order_number']} | {item['full_sku']} | ID: {item['shipstation_order_id']}")
        
        # Confirmation prompt
        if not auto_confirm:
            confirm = input(f"\nDelete this batch? [y/N]: ").strip().lower()
            if confirm != 'y':
                logger.info(f"Batch {batch_num} skipped by user")
                continue
        
        # Execute deletions
        for item in batch:
            order_id = item['shipstation_order_id']
            
            logger.info(f"Deleting order {item['order_number']} (ID: {order_id})...")
            success, error = delete_shipstation_order(api_key, api_secret, order_id)
            
            if success:
                success_count += 1
                print(f"  ✅ Deleted: {item['order_number']}")
            else:
                error_count += 1
                error_info = {
                    'order_number': item['order_number'],
                    'order_id': order_id,
                    'error': error
                }
                errors.append(error_info)
                print(f"  ❌ Failed: {item['order_number']} - {error}")
            
            # Small delay between individual deletes
            sleep(0.5)
        
        # Delay between batches
        if i + batch_size < total:
            logger.info(f"Batch complete. Waiting {batch_delay}s before next batch...")
            sleep(batch_delay)
    
    # Final summary
    print(f"\n{'='*80}")
    print("CLEANUP COMPLETE")
    print(f"{'='*80}\n")
    print(f"✅ Successfully deleted: {success_count}/{total}")
    print(f"❌ Failed: {error_count}/{total}\n")
    
    if errors:
        print("ERRORS:")
        for err in errors[:10]:
            print(f"  - Order {err['order_number']} (ID: {err['order_id']}): {err['error']}")
        
        # Save errors to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        error_file = Path('logs') / f'cleanup_errors_{timestamp}.log'
        error_file.parent.mkdir(exist_ok=True)
        
        with open(error_file, 'w') as f:
            json.dump(errors, f, indent=2)
        
        print(f"\nFull error log saved to: {error_file}")
    
    print(f"\n{'='*80}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Clean up duplicate orders in ShipStation'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show cleanup plan without executing (safe mode)'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Execute the cleanup (DESTRUCTIVE - deletes orders)'
    )
    parser.add_argument(
        '--confirm',
        action='store_true',
        help='Auto-confirm all batches (skip manual prompts)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=10,
        help='Number of orders to process per batch (default: 10)'
    )
    parser.add_argument(
        '--batch-delay',
        type=int,
        default=2,
        help='Seconds to wait between batches (default: 2)'
    )
    parser.add_argument(
        '--days-back',
        type=int,
        default=180,
        help='Number of days to look back (default: 180)'
    )
    
    args = parser.parse_args()
    
    # Validation
    if args.execute and args.dry_run:
        logger.error("Cannot use both --execute and --dry-run")
        return 1
    
    # Default to dry-run if neither specified
    if not args.execute and not args.dry_run:
        logger.info("No mode specified. Running in DRY-RUN mode (safe, no changes)")
        args.dry_run = True
    
    # Get credentials
    api_key, api_secret = get_shipstation_credentials()
    if not api_key or not api_secret:
        logger.error("ShipStation credentials not found")
        return 1
    
    # Get active lots
    active_lots = get_active_lot_map()
    
    # Fetch orders and identify duplicates
    logger.info("Fetching orders from ShipStation...")
    orders = fetch_all_shipstation_orders(api_key, api_secret, args.days_back)
    
    if not orders:
        logger.error("No orders found")
        return 1
    
    logger.info("Identifying duplicates...")
    duplicates = identify_duplicates(orders)
    
    if not duplicates:
        logger.info("✅ No duplicates found - nothing to clean up")
        return 0
    
    # Create cleanup plan
    logger.info("Creating cleanup plan...")
    plan = create_cleanup_plan(duplicates, active_lots)
    
    # Show plan
    print_cleanup_plan(plan)
    
    # Execute if requested
    if args.execute:
        print("\n" + "="*80)
        print("⚠️  WARNING: DESTRUCTIVE OPERATION")
        print("="*80)
        print("This will DELETE orders from ShipStation.")
        print("Make sure you have:")
        print("  1. Reviewed the cleanup plan above")
        print("  2. Created a backup")
        print("  3. Disabled upload workflows")
        print("="*80 + "\n")
        
        if not args.confirm:
            confirm = input("Type 'DELETE' to confirm: ").strip()
            if confirm != 'DELETE':
                logger.info("Cleanup cancelled by user")
                return 0
        
        execute_cleanup(
            plan,
            api_key,
            api_secret,
            batch_size=args.batch_size,
            batch_delay=args.batch_delay,
            auto_confirm=args.confirm
        )
    else:
        print("\n✅ DRY-RUN COMPLETE (no changes made)")
        print("To execute cleanup, run with --execute flag\n")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
