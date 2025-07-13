"""
User-related CRUD operations for the DQX application.
"""

import psycopg2
from datetime import datetime
from typing import Optional, List, Dict, Any
from app.models import User
from app.auth import get_password_hash


# ========================================================================================
# HELPER FUNCTIONS
# ========================================================================================

def _create_user_from_row(row_data: tuple) -> User:
    """Create a User object from database row data."""
    return User(
        id=row_data[0],
        username=row_data[1],
        email=row_data[2],
        full_name=row_data[3],
        hashed_password=row_data[4],
        is_active=row_data[5],
        role=row_data[6],
        created_at=row_data[7],
        updated_at=row_data[8]
    )


def _get_single_user(db, query: str, params: tuple) -> Optional[User]:
    """Execute a query and return a single User object or None."""
    cursor = None
    try:
        cursor = db.cursor()
        cursor.execute(query, params)
        user_data = cursor.fetchone()
        return _create_user_from_row(user_data) if user_data else None
    finally:
        if cursor:
            cursor.close()


def _get_multiple_users(db, query: str, params: tuple = ()) -> List[User]:
    """Execute a query and return a list of User objects."""
    cursor = None
    try:
        cursor = db.cursor()
        cursor.execute(query, params)
        users_data = cursor.fetchall()
        return [_create_user_from_row(row) for row in users_data]
    finally:
        if cursor:
            cursor.close()


# ========================================================================================
# USER CRUD OPERATIONS
# ========================================================================================

def create_user(db, username: str, email: str, password: str, 
               full_name: Optional[str] = None, role: str = "inputter") -> User:
    """Create a new user with the specified role."""
    if role not in ["admin", "creator", "inputter"]:
        raise ValueError(f"Invalid role: {role}. Must be 'admin', 'creator', or 'inputter'.")
        
    cursor = None
    try:
        cursor = db.cursor()
        hashed_password = get_password_hash(password)
        now = datetime.now()
        
        cursor.execute("""
            INSERT INTO dq.users (username, email, full_name, hashed_password, role, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, username, email, full_name, hashed_password, is_active, role, created_at, updated_at
        """, (username, email, full_name, hashed_password, role, now, now))
        
        user_data = cursor.fetchone()
        db.commit()
        return _create_user_from_row(user_data)
        
    except psycopg2.Error as e:
        db.rollback()
        error_msg = str(e).lower()
        if "duplicate key" in error_msg:
            if "users_username_key" in error_msg:
                raise ValueError(f"Username '{username}' already exists")
            elif "users_email_key" in error_msg:
                raise ValueError(f"Email '{email}' already exists")
        raise e
    finally:
        if cursor:
            cursor.close()


def get_user_by_id(db, user_id: int) -> Optional[User]:
    """Retrieve a user by their ID."""
    query = """
        SELECT id, username, email, full_name, hashed_password, is_active, role, created_at, updated_at
        FROM dq.users WHERE id = %s
    """
    return _get_single_user(db, query, (user_id,))


def get_user_by_username(db, username: str) -> Optional[User]:
    """Retrieve a user by their username."""
    query = """
        SELECT id, username, email, full_name, hashed_password, is_active, role, created_at, updated_at
        FROM dq.users WHERE username = %s
    """
    return _get_single_user(db, query, (username,))


def get_user_by_email(db, email: str) -> Optional[User]:
    """Retrieve a user by their email."""
    query = """
        SELECT id, username, email, full_name, hashed_password, is_active, role, created_at, updated_at
        FROM dq.users WHERE email = %s
    """
    return _get_single_user(db, query, (email,))


def get_users(db) -> List[User]:
    """Retrieve all users from the database."""
    query = """
        SELECT id, username, email, full_name, hashed_password, is_active, role, created_at, updated_at
        FROM dq.users ORDER BY id ASC
    """
    return _get_multiple_users(db, query)


def update_user(db, user_id: int, update_data: Dict[str, Any]) -> Optional[User]:
    """Update a user's information."""
    if not get_user_by_id(db, user_id):
        return None
        
    cursor = None
    try:
        cursor = db.cursor()
        
        # Build dynamic update query
        update_fields = []
        params = []
        
        for field, value in update_data.items():
            if value is not None:
                update_fields.append(f"{field} = %s")
                params.append(value)
        
        if not update_fields:
            return get_user_by_id(db, user_id)
        
        # Add updated_at timestamp and user_id
        update_fields.append("updated_at = %s")
        params.extend([datetime.now(), user_id])
        
        query = f"""
            UPDATE dq.users SET {", ".join(update_fields)}
            WHERE id = %s
            RETURNING id, username, email, full_name, hashed_password, is_active, role, created_at, updated_at
        """
        
        cursor.execute(query, params)
        result = cursor.fetchone()
        db.commit()
        
        return _create_user_from_row(result) if result else None
        
    except psycopg2.Error as e:
        db.rollback()
        raise e
    finally:
        if cursor:
            cursor.close()


def deactivate_user(db, user_id: int) -> bool:
    """Deactivate a user (set is_active = False)."""
    cursor = None
    try:
        cursor = db.cursor()
        cursor.execute("""
            UPDATE dq.users SET is_active = false, updated_at = %s WHERE id = %s
        """, (datetime.now(), user_id))
        
        success = cursor.rowcount > 0
        if success:
            db.commit()
        return success
        
    except psycopg2.Error as e:
        db.rollback()
        raise e
    finally:
        if cursor:
            cursor.close()


def delete_user(db, user_id: int) -> bool:
    """Delete a user from the database."""
    cursor = None
    try:
        cursor = db.cursor()
        cursor.execute("DELETE FROM dq.users WHERE id = %s", (user_id,))
        
        success = cursor.rowcount > 0
        if success:
            db.commit()
        return success
        
    except psycopg2.Error as e:
        db.rollback()
        raise e
    finally:
        if cursor:
            cursor.close()


# Alias for consistency
def get_user(db, user_id: int) -> Optional[User]:
    """Alias for get_user_by_id for consistency in function naming."""
    return get_user_by_id(db, user_id)
