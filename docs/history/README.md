# ShipStation Duplicate Remediation System

## Overview
This folder contains comprehensive documentation for identifying, cleaning up, and preventing duplicate orders in ShipStation. The system was implemented to address historical duplicates created before the duplicate detection fix (October 2025) and provides tools for ongoing maintenance.

## 📚 Documentation Index

### Quick Start
- **[Quick Reference Guide](QUICK_REFERENCE.md)** - TL;DR commands and troubleshooting (START HERE!)

### Comprehensive Guides
1. **[Remediation Plan](REMEDIATION_PLAN.md)** - Complete 6-phase cleanup process with safety controls
2. **[Duplicate Detection Fix](DUPLICATE_DETECTION_FIX.md)** - Prevention system implementation details
3. **[System Assumptions](ASSUMPTIONS.md)** - Requirements, limitations, and edge cases

## 🛠️ Utility Scripts

Located in `/utils/`:

| Script | Purpose | Safety |
|--------|---------|--------|
| `identify_shipstation_duplicates.py` | Scan & report duplicates | ✅ READ-ONLY |
| `backup_shipstation_data.py` | Create JSON backup | ✅ READ-ONLY |
| `cleanup_shipstation_duplicates.py` | Execute cleanup | ⚠️ DESTRUCTIVE |

## 🚀 Quick Workflow

```bash
# 1. Identify duplicates
python utils/identify_shipstation_duplicates.py --mode both

# 2. Create backup
python utils/backup_shipstation_data.py

# 3. Test cleanup plan (dry-run)
python utils/cleanup_shipstation_duplicates.py --dry-run

# 4. Execute cleanup (after disabling workflows)
python utils/cleanup_shipstation_duplicates.py --execute
```

## 📊 System Architecture

### Problem Statement
Before the duplicate detection fix, orders with the same order number but different lot numbers created multiple ShipStation orders:
- Order `689755` + SKU `17612-250237` → ShipStation Order A
- Order `689755` + SKU `17612-250300` → ShipStation Order B (duplicate!)

### Solution
**Two-Tier System:**

1. **Prevention** (Primary)
   - Modified upload logic to check `(order_number + base_SKU)` combination
   - Blocks duplicate uploads before they reach ShipStation
   - Active since October 2025

2. **Remediation** (Cleanup)
   - Utilities to identify and remove historical duplicates
   - Smart cleanup strategy prioritizing active lot numbers
   - Safety controls: dry-run, backups, batch processing

### Cleanup Strategy
- **Priority 1**: Keep orders with ACTIVE lot numbers (from `sku_lot` table)
- **Priority 2**: Keep EARLIEST uploaded order (lowest `createDate`)
- **Protection**: Cannot delete shipped/cancelled orders (API restriction)

## ✅ Validation Results

**Cleanup Execution (October 13, 2025):**
- Scanned: 4,155 orders (180 days)
- Found: 66 duplicate combinations (262 total orders)
- Actionable: 2 duplicate orders (awaiting_shipment status)
- Deleted: 2/2 successfully (100% success rate)
- Current State: **0 actionable duplicates remaining**

**Active Lot Matching Validated:**
- ✅ Kept: Orders with lot `250300` (active)
- ❌ Deleted: Orders with lot `250237` (inactive)

## 🔗 Related Documentation

- **[Workflow Controls Manual](../manuals/WORKFLOW_CONTROLS_USER_MANUAL.md)** - How to disable workflows during cleanup
- **[Database Schema](../DATABASE_SCHEMA.md)** - `sku_lot` table structure
- **[Main Project README](../../replit.md)** - Overall system architecture

## 🎯 Key Achievements

1. **Prevention System**: Active duplicate detection preventing new duplicates
2. **Remediation Tools**: Production-ready utilities with comprehensive safety controls
3. **Documentation**: Complete guides covering all scenarios and edge cases
4. **Validation**: Tested and verified with real production data
5. **Active Lot Priority**: Smart cleanup strategy preserving correct lot numbers

## 📞 Support

For questions or issues:
1. Check the [Quick Reference Guide](QUICK_REFERENCE.md) for common scenarios
2. Review the [Assumptions Document](ASSUMPTIONS.md) for system requirements
3. Consult the [Full Remediation Plan](REMEDIATION_PLAN.md) for detailed procedures

---

**Documentation Version**: 1.0  
**Last Updated**: October 13, 2025  
**Status**: Production-Ready ✅
