#!/usr/bin/env python3
"""
Quick migration script to add auto_publish column to dq_schedules table
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database connection from .env
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found in .env file")
    sys.exit(1)

# Migration SQL
migration_sql = """
-- Add the auto_publish column with default value FALSE
ALTER TABLE dq.dq_schedules 
ADD COLUMN IF NOT EXISTS auto_publish BOOLEAN NOT NULL DEFAULT FALSE;

-- Add comment for documentation
COMMENT ON COLUMN dq.dq_schedules.auto_publish IS 'Auto publish results to bad_detail table after script execution';
"""

def run_migration():
    conn = None
    cursor = None
    try:
        print(f"Connecting to database...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        print("Running migration to add auto_publish column...")
        cursor.execute(migration_sql)
        conn.commit()
        
        print("✅ Migration completed successfully!")
        print("The auto_publish column has been added to dq.dq_schedules table.")
        
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        if conn:
            conn.rollback()
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    run_migration()
