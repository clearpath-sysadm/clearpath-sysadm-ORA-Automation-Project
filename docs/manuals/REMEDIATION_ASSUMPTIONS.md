# ShipStation Duplicate Remediation - Assumptions & Limitations

## System Assumptions

### SKU Format Requirements
The duplicate remediation utilities are designed for the following SKU format:

1. **Base SKU**: 5-digit numeric (e.g., `17612`)
2. **Lot Number**: Variable length numeric (e.g., `250300`)
3. **Combined Format**: `XXXXX-YYYYYY` or `XXXXX - YYYYYY`
   - Examples: `17612-250300`, `17612 - 250237`

### Critical Assumptions
✅ **All base SKUs are exactly 5 digits** (confirmed by user)
✅ **SKU format is consistent**: `<5-digit-base>-<lot-number>`
✅ **Lot numbers are unique identifiers** for inventory batches

### How Duplicate Detection Works

#### Step 1: Group by (Order Number + Base SKU)
```python
# Extract first 5 characters as base SKU
base_sku = sku[:5]  # "17612-250300" → "17612"

# Group duplicates by (order_number, base_sku)
key = (order_number, base_sku)  # ("689755", "17612")
```

#### Step 2: Identify Lot Variants
For Order `689755` + SKU `17612`:
- `17612-250300` (Active lot)
- `17612-250237` (Old lot)

These are **correctly identified as duplicates** of the same product.

#### Step 3: Cleanup Strategy
1. **Priority 1**: Keep order with **active lot** from `sku_lot` table
   - Query: `SELECT lot FROM sku_lot WHERE sku = '17612' AND active = 1`
   - Returns: `250300`
   - Action: Keep `17612-250300`, delete `17612-250237`

2. **Priority 2**: If no active lot match, keep **earliest created** order
   - Sorted by `createDate` ascending
   - Keep first, delete rest

3. **Protection**: **Cannot delete shipped/cancelled** orders
   - API restriction
   - These are skipped and logged for manual review

## Edge Cases & Limitations

### ⚠️ Limitation 1: 5-Character Base SKU Assumption
**What it means**: The system assumes all product SKUs have 5-digit bases.

**Risk**: If you have SKUs with:
- Less than 5 digits (e.g., `1234-250300`)
- More than 5 meaningful digits (e.g., `176123-250300`)

The grouping may not work as expected.

**Your case**: ✅ SAFE - All SKUs are 5 digits (confirmed)

### ⚠️ Limitation 2: Hyphen Separator Required
**What it means**: SKUs must use hyphen (`-`) to separate base from lot.

**Risk**: SKUs with different formats (underscores, slashes, etc.) won't parse correctly.

**Your case**: ✅ SAFE - SKU format is `XXXXX-YYYYYY` or `XXXXX - YYYYYY`

### ⚠️ Limitation 3: Lot Numbers Must Be Unique
**What it means**: Each lot number should represent a unique inventory batch.

**Risk**: If same lot number is reused for different batches, cleanup may incorrectly identify as duplicates.

**Your case**: ✅ SAFE - Lot numbers are date-based and unique (e.g., `250300` = 2025-03-00)

## Verification Checklist

Before running cleanup on YOUR data, verify:

- [ ] All SKUs have 5-digit base numbers
- [ ] SKU format is `XXXXX-YYYYYY` (hyphen-separated)
- [ ] Lot numbers in `sku_lot` table are current and accurate
- [ ] Active lots in `sku_lot` table have `active = 1`
- [ ] You have created a backup

## Testing Recommendations

### 1. Start with Dry-Run
```bash
python utils/cleanup_shipstation_duplicates.py --dry-run
```

Review output carefully:
- Check "Orders to KEEP" - verify active lot numbers are correct
- Check "Orders to DELETE" - ensure they have old/inactive lot numbers
- Look for "Unexpected SKU format" warnings

### 2. Test with Small Batch
```bash
python utils/cleanup_shipstation_duplicates.py --execute --batch-size 5
```

- Process only 5 orders first
- Verify results in ShipStation UI
- Confirm correct orders were kept/deleted

### 3. Full Cleanup
Once confident, run full cleanup:
```bash
python utils/cleanup_shipstation_duplicates.py --execute --confirm
```

## Troubleshooting Edge Cases

### Issue: "Unexpected SKU format" warnings
**Cause**: SKU doesn't match `XXXXX-YYYYYY` pattern

**Solution**: 
1. Check the warning messages in output
2. Manually review those SKUs in ShipStation
3. Fix format if needed, or skip those orders

### Issue: Wrong order being kept
**Cause**: Active lot in `sku_lot` table might be incorrect

**Solution**:
1. Check `sku_lot` table: `SELECT * FROM sku_lot WHERE active = 1`
2. Update active lot if needed
3. Re-run cleanup

### Issue: "Cannot delete" messages for non-shipped orders
**Cause**: Order might be locked or in special status

**Solution**: Manually review in ShipStation UI

## Production Readiness

### ✅ Safe for YOUR Use Case If:
- All SKUs are 5 digits (confirmed ✓)
- SKU format is consistent (confirmed ✓)
- Active lots in `sku_lot` table are accurate
- You run dry-run first and review results

### ⚠️ Not Suitable If:
- SKUs have variable-length base numbers
- SKU format is inconsistent or uses different separators
- Lot numbers are not reliable identifiers

---

**Recommendation for Your Case**: The system is **production-ready** for your specific use case. Follow the testing workflow above to verify results before full cleanup.

**Document Version**: 1.0  
**Last Updated**: October 13, 2025
