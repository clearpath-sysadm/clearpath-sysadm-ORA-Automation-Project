"""
Centralized SKU-Lot Parsing Service

Handles all ShipStation SKU format variations and provides database lookup functions.
This eliminates scattered parsing logic across services and ensures consistency.

Supported Formats:
- "17612 - 250300" → base_sku=17612, lot=250300
- "17612-250300" → base_sku=17612, lot=250300  
- "18795" → base_sku=18795, lot=None

Author: ORA Automation Team
Date: October 2025
"""

import re
import logging
from typing import Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ParsedSKU:
    """Result of parsing a ShipStation SKU"""
    shipstation_raw: str
    base_sku: str
    lot_number: Optional[str]
    is_valid: bool
    error_msg: Optional[str] = None


def parse_shipstation_sku(raw_sku: str) -> ParsedSKU:
    """
    Parse ShipStation SKU into base_sku and lot_number.
    
    ShipStation stores "SKU - Lot" as the complete SKU value.
    This function separates them for normalized database storage.
    
    Args:
        raw_sku: Raw SKU from ShipStation (e.g., "17612 - 250300" or "18795")
        
    Returns:
        ParsedSKU object with parsed components and validation status
        
    Examples:
        >>> parse_shipstation_sku("17612 - 250300")
        ParsedSKU(shipstation_raw="17612 - 250300", base_sku="17612", lot_number="250300", is_valid=True)
        
        >>> parse_shipstation_sku("18795")
        ParsedSKU(shipstation_raw="18795", base_sku="18795", lot_number=None, is_valid=True)
    """
    if not raw_sku:
        return ParsedSKU(
            shipstation_raw="",
            base_sku="",
            lot_number=None,
            is_valid=False,
            error_msg="Empty SKU provided"
        )
    
    raw_sku = raw_sku.strip()
    
    # Pattern 1: SKU - LOT (with or without spaces around dash)
    # Matches: "17612 - 250300", "17612-250300", "17612  -  250300"
    match = re.match(r'^(\d+)\s*-\s*(\d+)$', raw_sku)
    
    if match:
        base = match.group(1)
        lot = match.group(2)
        logger.debug(f"Parsed SKU-Lot format: '{raw_sku}' → base={base}, lot={lot}")
        return ParsedSKU(
            shipstation_raw=raw_sku,
            base_sku=base,
            lot_number=lot,
            is_valid=True
        )
    
    # Pattern 2: SKU only (no lot)
    # Matches: "18795", "17612"
    if raw_sku.isdigit():
        logger.debug(f"Parsed SKU-only format: '{raw_sku}' → base={raw_sku}, lot=None")
        return ParsedSKU(
            shipstation_raw=raw_sku,
            base_sku=raw_sku,
            lot_number=None,
            is_valid=True
        )
    
    # Invalid format
    logger.warning(f"Cannot parse SKU format: '{raw_sku}'")
    return ParsedSKU(
        shipstation_raw=raw_sku,
        base_sku="",
        lot_number=None,
        is_valid=False,
        error_msg=f"Invalid SKU format: {raw_sku}"
    )


def lookup_sku_id(base_sku: str, conn) -> Optional[int]:
    """
    Get sku_id from skus table for a given SKU code.
    
    Args:
        base_sku: The base SKU code (e.g., "17612")
        conn: SQLite database connection
        
    Returns:
        sku_id if found, None otherwise
    """
    try:
        result = conn.execute(
            "SELECT sku_id FROM skus WHERE sku_code = ?", 
            (base_sku,)
        ).fetchone()
        
        if result:
            logger.debug(f"Found sku_id={result[0]} for base_sku={base_sku}")
            return result[0]
        else:
            logger.warning(f"No sku_id found for base_sku={base_sku}")
            return None
            
    except Exception as e:
        logger.error(f"Error looking up sku_id for {base_sku}: {e}")
        return None


def lookup_lot_id(sku_id: int, lot_number: str, conn) -> Optional[int]:
    """
    Get lot_id from lots table for a given SKU and lot number.
    
    Args:
        sku_id: The SKU foreign key
        lot_number: The lot number (e.g., "250300")
        conn: SQLite database connection
        
    Returns:
        lot_id if found, None otherwise
    """
    try:
        result = conn.execute(
            "SELECT lot_id FROM lots WHERE sku_id = ? AND lot_number = ?",
            (sku_id, lot_number)
        ).fetchone()
        
        if result:
            logger.debug(f"Found lot_id={result[0]} for sku_id={sku_id}, lot={lot_number}")
            return result[0]
        else:
            logger.warning(f"No lot_id found for sku_id={sku_id}, lot={lot_number}")
            return None
            
    except Exception as e:
        logger.error(f"Error looking up lot_id for sku_id={sku_id}, lot={lot_number}: {e}")
        return None


def create_lot_if_missing(sku_id: int, lot_number: str, conn) -> Optional[int]:
    """
    Create a new lot entry if it doesn't exist.
    Useful for handling lots that appear in ShipStation but aren't in our database yet.
    
    Args:
        sku_id: The SKU foreign key
        lot_number: The lot number to create
        conn: SQLite database connection
        
    Returns:
        lot_id of created (or existing) lot, None on error
    """
    try:
        # First check if it exists
        existing = lookup_lot_id(sku_id, lot_number, conn)
        if existing:
            return existing
        
        # Create new lot
        cursor = conn.execute("""
            INSERT INTO lots (sku_id, lot_number, status)
            VALUES (?, ?, 'active')
        """, (sku_id, lot_number))
        
        new_lot_id = cursor.lastrowid
        logger.info(f"Created new lot: lot_id={new_lot_id}, sku_id={sku_id}, lot={lot_number}")
        
        return new_lot_id
        
    except Exception as e:
        logger.error(f"Error creating lot for sku_id={sku_id}, lot={lot_number}: {e}")
        return None


def parse_and_lookup(raw_sku: str, conn, create_missing_lots: bool = True) -> Tuple[Optional[int], Optional[int], str]:
    """
    Complete parsing and database lookup in one call.
    
    This is the main function services should use. It:
    1. Parses the raw ShipStation SKU
    2. Looks up sku_id in database
    3. Looks up lot_id in database (creates if missing and flag is True)
    
    Args:
        raw_sku: Raw SKU from ShipStation
        conn: SQLite database connection
        create_missing_lots: If True, create lot entries that don't exist yet
        
    Returns:
        Tuple of (sku_id, lot_id, shipstation_raw)
        Returns (None, None, raw_sku) if parsing fails or SKU not found
        
    Example:
        >>> sku_id, lot_id, raw = parse_and_lookup("17612 - 250300", conn)
        >>> # Use sku_id and lot_id in INSERT statement
    """
    # Parse the raw SKU
    parsed = parse_shipstation_sku(raw_sku)
    
    if not parsed.is_valid:
        logger.error(f"Cannot parse SKU: {parsed.error_msg}")
        return (None, None, raw_sku)
    
    # Lookup sku_id
    sku_id = lookup_sku_id(parsed.base_sku, conn)
    if not sku_id:
        logger.error(f"SKU not found in database: {parsed.base_sku}")
        return (None, None, raw_sku)
    
    # Lookup or create lot_id (if lot exists in raw SKU)
    lot_id = None
    if parsed.lot_number:
        lot_id = lookup_lot_id(sku_id, parsed.lot_number, conn)
        
        # Create missing lot if requested
        if not lot_id and create_missing_lots:
            lot_id = create_lot_if_missing(sku_id, parsed.lot_number, conn)
        
        if not lot_id:
            logger.warning(f"Lot not found (and not created): sku_id={sku_id}, lot={parsed.lot_number}")
    
    return (sku_id, lot_id, parsed.shipstation_raw)


# Convenience function for testing
def test_parser():
    """Test the parser with various inputs"""
    test_cases = [
        "17612 - 250300",
        "17612-250300",
        "17612  -  250300",
        "18795",
        "17612",
        "",
        "INVALID-SKU",
        "123-ABC",
    ]
    
    print("Testing SKU Parser:")
    print("=" * 60)
    for test in test_cases:
        result = parse_shipstation_sku(test)
        status = "✅" if result.is_valid else "❌"
        print(f"{status} Input: '{test}'")
        print(f"   → base_sku: {result.base_sku}, lot: {result.lot_number}")
        if result.error_msg:
            print(f"   → Error: {result.error_msg}")
        print()


if __name__ == "__main__":
    # Run tests if executed directly
    test_parser()
