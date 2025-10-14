-- Migration: Add last_run_at column to workflow_controls table
-- This tracks when each workflow last executed successfully

ALTER TABLE workflow_controls ADD COLUMN last_run_at TIMESTAMP;

-- Update comment
-- This column will be updated by workflows when they start/complete execution
