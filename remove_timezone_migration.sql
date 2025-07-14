-- Remove timezone from existing log tables for Oracle DB compatibility

-- Update user_actions_log table
ALTER TABLE dq.user_actions_log 
ALTER COLUMN created_at TYPE TIMESTAMP USING created_at::TIMESTAMP;

-- Update schedule_run_log table  
ALTER TABLE dq.schedule_run_log 
ALTER COLUMN started_at TYPE TIMESTAMP USING started_at::TIMESTAMP,
ALTER COLUMN completed_at TYPE TIMESTAMP USING completed_at::TIMESTAMP;
