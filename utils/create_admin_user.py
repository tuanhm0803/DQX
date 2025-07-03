"""
Script to create an admin user in the database
"""

import os
import psycopg2
from pathlib import Path
import sys
from passlib.context import CryptContext

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.database import DATABASE_URL

# Initialize password context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """Generate a password hash."""
    return pwd_context.hash(password)

def create_admin_user(username, email, password, full_name=None):
    """Create an admin user in the database"""
    print(f"Creating admin user '{username}'...")
    
    conn = None
    try:
        # Connect to the database
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Check if user already exists
        cursor.execute(
            "SELECT id FROM dq.users WHERE username = %s OR email = %s",
            (username, email)
        )
        if cursor.fetchone():
            print(f"User with username '{username}' or email '{email}' already exists")
            return False
            
        # Hash the password
        hashed_password = get_password_hash(password)
        
        # Insert admin user
        cursor.execute(
            """
            INSERT INTO dq.users 
                (username, email, full_name, hashed_password, is_active, role, created_at, updated_at)
            VALUES 
                (%s, %s, %s, %s, true, 'admin', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (username, email, full_name, hashed_password)
        )
        
        conn.commit()
        print(f"Admin user '{username}' created successfully!")
        return True
        
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    # Get user input for admin details
    username = input("Enter admin username: ")
    email = input("Enter admin email: ")
    password = input("Enter admin password: ")
    full_name = input("Enter admin's full name (optional, press Enter to skip): ")
    
    # If full_name is empty, set to None
    if not full_name.strip():
        full_name = None
        
    create_admin_user(username, email, password, full_name)
