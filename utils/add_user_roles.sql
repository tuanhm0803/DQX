-- Modify the users table to include user roles
ALTER TABLE dq.users ADD COLUMN IF NOT EXISTS role VARCHAR(20) NOT NULL DEFAULT 'inputter';

-- Create check constraint to ensure role is one of the allowed values
ALTER TABLE dq.users 
  DROP CONSTRAINT IF EXISTS users_role_check;

ALTER TABLE dq.users 
  ADD CONSTRAINT users_role_check 
  CHECK (role IN ('admin', 'creator', 'inputter'));

-- Update existing users to have admin role
UPDATE dq.users SET role = 'admin';

-- Add comments for clarity
COMMENT ON COLUMN dq.users.role IS 'User role: admin (full access), creator (all except user management), inputter (read-only, no create/insert)';
