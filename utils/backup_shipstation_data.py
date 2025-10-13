#!/usr/bin/env python3
"""
ShipStation Data Backup Utility
Creates a backup of ShipStation orders before cleanup operations

Usage:
    python utils/backup_shipstation_data.py
    python utils/backup_shipstation_data.py --days-back 90
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.shipstation.api_client import get_shipstation_credentials
from utils.identify_shipstation_duplicates import fetch_all_shipstation_orders

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_backup(orders, output_dir='backups'):
    """
    Create JSON backup of ShipStation orders
    
    Args:
        orders: List of order dictionaries
        output_dir: Directory to save backup (default: backups/)
        
    Returns:
        Path to backup file
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = output_dir / f'shipstation_backup_{timestamp}.json'
    
    backup_data = {
        'created_at': datetime.now().isoformat(),
        'total_orders': len(orders),
        'orders': orders
    }
    
    with open(backup_path, 'w') as f:
        json.dump(backup_data, f, indent=2)
    
    logger.info(f"Backup saved to: {backup_path}")
    logger.info(f"Backup size: {backup_path.stat().st_size / 1024 / 1024:.2f} MB")
    
    return backup_path


def main():
    parser = argparse.ArgumentParser(
        description='Backup ShipStation orders before cleanup'
    )
    parser.add_argument(
        '--days-back',
        type=int,
        default=180,
        help='Number of days to backup (default: 180)'
    )
    parser.add_argument(
        '--output-dir',
        default='backups',
        help='Directory to save backup (default: backups/)'
    )
    
    args = parser.parse_args()
    
    # Get credentials
    api_key, api_secret = get_shipstation_credentials()
    if not api_key or not api_secret:
        logger.error("ShipStation credentials not found")
        return 1
    
    # Fetch orders
    logger.info(f"Fetching orders from last {args.days_back} days...")
    orders = fetch_all_shipstation_orders(api_key, api_secret, args.days_back)
    
    if not orders:
        logger.error("No orders found to backup")
        return 1
    
    # Create backup
    logger.info(f"Creating backup of {len(orders)} orders...")
    backup_path = create_backup(orders, args.output_dir)
    
    print(f"\n{'='*80}")
    print("BACKUP COMPLETE")
    print(f"{'='*80}")
    print(f"File: {backup_path}")
    print(f"Orders: {len(orders)}")
    print(f"Size: {backup_path.stat().st_size / 1024 / 1024:.2f} MB")
    print(f"{'='*80}\n")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
