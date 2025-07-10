-- Migration script to add auto_publish column to dq_schedules table
-- Run this script if you have an existing dq_schedules table

-- Add the auto_publish column with default value FALSE
ALTER TABLE dq.dq_schedules 
ADD COLUMN IF NOT EXISTS auto_publish BOOLEAN NOT NULL DEFAULT FALSE;

-- Add comment for documentation
COMMENT ON COLUMN dq.dq_schedules.auto_publish IS 'Auto publish results to bad_detail table after script execution';
