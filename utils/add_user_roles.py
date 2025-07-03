"""
Script to add user roles to the users table
"""

import os
import psycopg2
from pathlib import Path
import sys

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.database import DATABASE_URL

def add_user_roles():
    """Add role column to the users table if it doesn't exist"""
    print("Adding user roles to users table...")
    
    conn = None
    try:
        # Connect to the database
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Read SQL file
        sql_path = os.path.join(os.path.dirname(__file__), 'add_user_roles.sql')
        with open(sql_path, 'r') as sql_file:
            sql = sql_file.read()
        
        # Execute SQL
        cursor.execute(sql)
        conn.commit()
        print("User roles added successfully")
        
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    add_user_roles()
