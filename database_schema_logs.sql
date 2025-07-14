-- User Actions Log Table
CREATE TABLE IF NOT EXISTS dq.user_actions_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES dq.users(id),
    username VARCHAR(100) NOT NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id INTEGER,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Scheduled Jobs Running Log Table
CREATE TABLE IF NOT EXISTS dq.schedule_run_log (
    id SERIAL PRIMARY KEY,
    schedule_id INTEGER REFERENCES dq.dq_schedules(id),
    job_name VARCHAR(255) NOT NULL,
    script_id INTEGER REFERENCES dq.dq_sql_scripts(id),
    script_name VARCHAR(255),
    status VARCHAR(50) NOT NULL, -- 'running', 'completed', 'failed'
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,
    rows_affected INTEGER,
    error_message TEXT,
    auto_published BOOLEAN DEFAULT FALSE,
    created_by_user_id INTEGER REFERENCES dq.users(id)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_user_actions_log_user_id ON dq.user_actions_log(user_id);
CREATE INDEX IF NOT EXISTS idx_user_actions_log_created_at ON dq.user_actions_log(created_at);
CREATE INDEX IF NOT EXISTS idx_user_actions_log_action ON dq.user_actions_log(action);

CREATE INDEX IF NOT EXISTS idx_schedule_run_log_schedule_id ON dq.schedule_run_log(schedule_id);
CREATE INDEX IF NOT EXISTS idx_schedule_run_log_started_at ON dq.schedule_run_log(started_at);
CREATE INDEX IF NOT EXISTS idx_schedule_run_log_status ON dq.schedule_run_log(status);
