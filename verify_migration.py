#!/usr/bin/env python3
"""
Verify that the auto_publish column was added successfully
"""

import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def verify_column():
    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Check if auto_publish column exists
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default 
            FROM information_schema.columns 
            WHERE table_schema = 'dq' 
            AND table_name = 'dq_schedules' 
            AND column_name = 'auto_publish';
        """)
        
        result = cursor.fetchone()
        if result:
            column_name, data_type, is_nullable, column_default = result
            print("✅ Column verification successful!")
            print(f"Column: {column_name}")
            print(f"Type: {data_type}")
            print(f"Nullable: {is_nullable}")
            print(f"Default: {column_default}")
        else:
            print("❌ auto_publish column not found!")
            
        # Also check all columns in the table
        print("\n📋 All columns in dq.dq_schedules:")
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default 
            FROM information_schema.columns 
            WHERE table_schema = 'dq' 
            AND table_name = 'dq_schedules'
            ORDER BY ordinal_position;
        """)
        
        columns = cursor.fetchall()
        for col in columns:
            print(f"  - {col[0]} ({col[1]}) {'NULL' if col[2] == 'YES' else 'NOT NULL'} {col[3] or ''}")
        
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    verify_column()
