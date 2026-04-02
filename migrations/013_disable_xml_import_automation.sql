-- Migration 013: Disable xml-import automation
-- The XML pipeline (X-Cart / xcart orders with 10xxxx order numbers) is retired.
-- xml-import may still be triggered manually via the dashboard, but it must NOT
-- poll automatically on a schedule.
--
-- This migration is safe to re-run; it is idempotent.

UPDATE workflow_controls
SET enabled = false
WHERE workflow_name = 'xml-import'
  AND enabled = true;
