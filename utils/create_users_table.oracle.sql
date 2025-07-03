-- PostgreSQL to Oracle Migration

-- Create users table in Oracle format

-- First create the sequence for auto-increment
CREATE SEQUENCE dq.users_seq START WITH 1 INCREMENT BY 1;

-- Create the users table
CREATE TABLE dq.users (
    id NUMBER(10) PRIMARY KEY,
    username VARCHAR2(50) NOT NULL,
    email VARCHAR2(100) NOT NULL,
    full_name VARCHAR2(100),
    hashed_password VARCHAR2(255) NOT NULL,
    is_active NUMBER(1) DEFAULT 1 NOT NULL,
    role VARCHAR2(20) DEFAULT 'inputter' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    -- Add constraints
    CONSTRAINT users_username_uk UNIQUE (username),
    CONSTRAINT users_email_uk UNIQUE (email),
    CONSTRAINT users_role_chk CHECK (role IN ('admin', 'creator', 'inputter'))
);

-- Create trigger for auto-increment
CREATE OR REPLACE TRIGGER dq.users_bir
BEFORE INSERT ON dq.users
FOR EACH ROW
WHEN (new.id IS NULL)
BEGIN
    SELECT users_seq.NEXTVAL INTO :new.id FROM dual;
END;
/

-- Create indexes (Oracle doesn't have IF NOT EXISTS)
CREATE INDEX idx_user_username ON dq.users(username);
CREATE INDEX idx_user_email ON dq.users(email);

-- Add comment
COMMENT ON TABLE dq.users IS 'User accounts for authentication and authorization';
COMMENT ON COLUMN dq.users.role IS 'User role: admin (full access), creator (all except user management), inputter (read-only, no create/insert)';
