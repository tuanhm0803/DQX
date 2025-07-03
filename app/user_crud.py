"""
User-related CRUD operations for the DQX application.
Adding these separate from the main crud.py to avoid disrupting the existing code.
"""

import psycopg2
from psycopg2.extensions import connection as PgConnection
from psycopg2 import sql
from datetime import datetime
from app.models import User
from app.auth import get_password_hash
from typing import Optional

# --- User Management Functions ---

def create_user(db: PgConnection, username: str, email: str, password: str, 
               full_name: Optional[str] = None, role: str = "inputter") -> User:
    """
    Create a new user in the database with the specified role.
    Valid roles are 'admin', 'creator', and 'inputter'.
    Returns the created User object.
    """
    # Validate the role
    if role not in ["admin", "creator", "inputter"]:
        raise ValueError(f"Invalid role: {role}. Must be 'admin', 'creator', or 'inputter'.")
        
    cursor = db.cursor()
    hashed_password = get_password_hash(password)
    now = datetime.now()
    
    try:
        cursor.execute(
            """
            INSERT INTO dq.users (username, email, full_name, hashed_password, role, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, username, email, full_name, hashed_password, is_active, role, created_at, updated_at
            """,
            (username, email, full_name, hashed_password, role, now, now)
        )
        
        user_data = cursor.fetchone()
        db.commit()
        
        # Create User object from returned data
        return User(
            id=user_data[0],
            username=user_data[1],
            email=user_data[2],
            full_name=user_data[3],
            hashed_password=user_data[4],
            is_active=user_data[5],
            role=user_data[6],
            created_at=user_data[7],
            updated_at=user_data[8]
        )
    
    except psycopg2.Error as e:
        db.rollback()
        if "duplicate key" in str(e).lower():
            if "users_username_key" in str(e):
                raise ValueError(f"Username '{username}' already exists")
            elif "users_email_key" in str(e):
                raise ValueError(f"Email '{email}' already exists")
        raise e
    finally:
        cursor.close()

def get_user_by_id(db: PgConnection, user_id: int) -> Optional[User]:
    """
    Retrieve a user by their ID.
    Returns User object if found, None otherwise.
    """
    cursor = db.cursor()
    try:
        cursor.execute(
            """
            SELECT id, username, email, full_name, hashed_password, is_active, role, created_at, updated_at
            FROM dq.users
            WHERE id = %s
            """,
            (user_id,)
        )
        
        user_data = cursor.fetchone()
        if not user_data:
            return None
            
        return User(
            id=user_data[0],
            username=user_data[1],
            email=user_data[2],
            full_name=user_data[3],
            hashed_password=user_data[4],
            is_active=user_data[5],
            role=user_data[6],
            created_at=user_data[7],
            updated_at=user_data[8]
        )
    finally:
        cursor.close()

def get_user_by_username(db: PgConnection, username: str) -> Optional[User]:
    """
    Retrieve a user by their username.
    Returns User object if found, None otherwise.
    """
    cursor = db.cursor()
    try:
        cursor.execute(
            """
            SELECT id, username, email, full_name, hashed_password, is_active, role, created_at, updated_at
            FROM dq.users
            WHERE username = %s
            """,
            (username,)
        )
        
        user_data = cursor.fetchone()
        if not user_data:
            return None
            
        return User(
            id=user_data[0],
            username=user_data[1],
            email=user_data[2],
            full_name=user_data[3],
            hashed_password=user_data[4],
            is_active=user_data[5],
            role=user_data[6],
            created_at=user_data[7],
            updated_at=user_data[8]
        )
    finally:
        cursor.close()

def get_user_by_email(db: PgConnection, email: str) -> Optional[User]:
    """
    Retrieve a user by their email.
    Returns User object if found, None otherwise.
    """
    cursor = db.cursor()
    try:
        cursor.execute(
            """
            SELECT id, username, email, full_name, hashed_password, is_active, role, created_at, updated_at
            FROM dq.users
            WHERE email = %s
            """,
            (email,)
        )
        
        user_data = cursor.fetchone()
        if not user_data:
            return None
            
        return User(
            id=user_data[0],
            username=user_data[1],
            email=user_data[2],
            full_name=user_data[3],
            hashed_password=user_data[4],
            is_active=user_data[5],
            role=user_data[6],
            created_at=user_data[7],
            updated_at=user_data[8]
        )
    finally:
        cursor.close()

def update_user(db: PgConnection, user_id: int, update_data: dict) -> Optional[User]:
    """
    Update a user's information.
    Returns the updated User object if successful, None if the user doesn't exist.
    """
    # Get current user data
    current_user = get_user_by_id(db, user_id)
    if not current_user:
        return None
        
    # Build update query dynamically based on provided fields
    cursor = db.cursor()
    try:
        update_fields = []
        params = []
        
        for field, value in update_data.items():
            if value is not None:  # Only update provided fields
                update_fields.append(f"{field} = %s")
                params.append(value)
        
        # Add updated_at timestamp
        update_fields.append("updated_at = %s")
        params.append(datetime.now())
        
        # Add user_id for WHERE clause
        params.append(user_id)
        
        query = f"""
            UPDATE dq.users
            SET {", ".join(update_fields)}
            WHERE id = %s
            RETURNING id, username, email, full_name, hashed_password, is_active, role, created_at, updated_at
        """
        
        cursor.execute(query, params)
        result = cursor.fetchone()
        db.commit()
        
        if not result:
            return None
            
        return User(
            id=result[0],
            username=result[1],
            email=result[2],
            full_name=result[3],
            hashed_password=result[4],
            is_active=result[5],
            role=result[6],
            created_at=result[7],
            updated_at=result[8]
        )
    
    except psycopg2.Error as e:
        db.rollback()
        raise e
    finally:
        cursor.close()

def deactivate_user(db: PgConnection, user_id: int) -> bool:
    """
    Deactivate a user (set is_active = False).
    Returns True if successful, False if the user doesn't exist.
    """
    cursor = db.cursor()
    try:
        cursor.execute(
            """
            UPDATE dq.users
            SET is_active = false, updated_at = %s
            WHERE id = %s
            """,
            (datetime.now(), user_id)
        )
        
        if cursor.rowcount == 0:
            return False
            
        db.commit()
        return True
    except psycopg2.Error as e:
        db.rollback()
        raise e
    finally:
        cursor.close()

def get_users(db: PgConnection):
    """
    Retrieve all users from the database.
    Returns a list of User objects.
    """
    cursor = db.cursor()
    try:
        cursor.execute(
            """
            SELECT id, username, email, full_name, hashed_password, is_active, role, created_at, updated_at
            FROM dq.users
            ORDER BY id ASC
            """
        )
        
        users_data = cursor.fetchall()
        users = []
        
        for user_data in users_data:
            users.append(User(
                id=user_data[0],
                username=user_data[1],
                email=user_data[2],
                full_name=user_data[3],
                hashed_password=user_data[4],
                is_active=user_data[5],
                role=user_data[6],
                created_at=user_data[7],
                updated_at=user_data[8]
            ))
            
        return users
    finally:
        cursor.close()

def get_user(db: PgConnection, user_id: int) -> Optional[User]:
    """
    Retrieve a user by their ID.
    This is an alias for get_user_by_id for consistency in function naming.
    Returns User object if found, None otherwise.
    """
    return get_user_by_id(db, user_id)

def delete_user(db: PgConnection, user_id: int) -> bool:
    """
    Delete a user from the database.
    Returns True if successful, False if the user doesn't exist.
    """
    cursor = db.cursor()
    try:
        cursor.execute(
            """
            DELETE FROM dq.users
            WHERE id = %s
            """,
            (user_id,)
        )
        
        if cursor.rowcount == 0:
            return False
            
        db.commit()
        return True
    except psycopg2.Error as e:
        db.rollback()
        raise e
    finally:
        cursor.close()
