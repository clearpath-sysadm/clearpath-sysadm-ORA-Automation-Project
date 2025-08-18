# Action Plan: ORA_Weekly_Shipped_History Requirements Compliance

## Modules Involved
- `src/daily_shipment_processor.py`
- `src/services/data_processing/shipment_processor.py`

---

## Action Steps

### 1. `src/daily_shipment_processor.py`

1. **Deduplication**
	- After updating or appending weekly data, deduplicate the DataFrame by `Start Date` and `Stop Date`, keeping only the most recent entry for each week.

2. **Enforce 52 Weeks**
	- After deduplication, trim the DataFrame to the most recent 52 weeks (by `Start Date`). If fewer than 52, consider padding if required by business logic.

3. **Ensure Current Week**
	- After all updates, check that the most recent week matches the current week’s start date. If not, update or append as needed.

4. **Validation**
	- Add a final validation step to ensure all requirements are met before writing to the sheet.

---

### 2. `src/services/data_processing/shipment_processor.py`

1. **Aggregation Uniqueness**
	- Ensure that the aggregation logic always produces unique weeks by `Start Date` and `Stop Date`.
	- Optionally, add a deduplication step after aggregation as a safeguard.

2. **Documentation**
	- Add comments to clarify that this function does not enforce the 52-week limit or current week logic, which is handled by the processor.

---

## Summary
- The main enforcement and validation logic should reside in `daily_shipment_processor.py`.
- `shipment_processor.py` should guarantee unique week aggregation but not business rule enforcement.
- This plan ensures the ORA_Weekly_Shipped_History tab always meets all requirements, including edge cases and exceptions.
Action Plan
For daily_shipment_processor.py
Deduplication:

After updating or appending weekly data, deduplicate the DataFrame by Start Date and Stop Date, keeping only the most recent entry for each week.
Enforce 52 Weeks:

After deduplication, trim the DataFrame to the most recent 52 weeks (by Start Date), or pad if fewer (if padding is required by business logic).
Ensure Current Week:

After all updates, check that the most recent week matches the current week’s start date. If not, update or append as needed.
Validation:

Add a final validation step to ensure all requirements are met before writing to the sheet.
For shipment_processor.py
Aggregation Uniqueness:

Ensure that the aggregation logic always produces unique weeks by Start Date and Stop Date.
Optionally, add a deduplication step after aggregation as a safeguard.
Documentation:

Add comments to clarify that this function does not enforce the 52-week limit or current week logic, which is handled by the processor.