
Here are the requirements for the weekly data on the ORA_Weekly_Shipped_History tab:

1. No duplicate weeks: Each week should be unique by start/stop date. After any update, the data must be deduplicated, keeping only the most recent entry for any duplicate week.
2. Exactly 52 weeks: The tab should always contain exactly 52 weeks of data (no more, no less). After deduplication, the data must be trimmed or padded to ensure exactly 52 weeks are present, even if the source data is corrupted or incomplete.
3. Most recent week is current week: The most recent week in the data must always correspond to the current week (based on the defined week start). If the current week is missing, it should be appended; if it exists, it should be updated.
4. If the sheet already contains duplicate weeks, these must be removed as part of the update process.
5. If the sheet contains more or fewer than 52 weeks, the data must be corrected to exactly 52 weeks after every update.
6. If the current week is not present or is incorrect, the data must be updated to ensure the current week is always represented accurately.
7. All validation and correction steps should be performed after any update to the weekly history tab to guarantee data integrity.

    please review the relevant modules in the codebase to ensure that they are working towards the above requirements.

    the ORA_Weekly_Shipped_History tab is currently not receiving the correct data when the daily_shipment_processor is running