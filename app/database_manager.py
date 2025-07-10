"""
Database Manager - Unified interface for PostgreSQL and Oracle databases
Handles timezone issues with Oracle thin mode connections
"""
import os
import re
from typing import Any, Optional, Union, List, Tuple
from datetime import datetime

# Database type configuration
DB_TYPE = os.getenv("DB_TYPE", "postgresql")  # "postgresql" or "oracle"

class DatabaseManager:
    """Unified database manager that works with both PostgreSQL and Oracle"""
    
    def __init__(self, db_type: Optional[str] = None):
        self.db_type = db_type or DB_TYPE
        self._connection_params = self._get_connection_params()
    
    def _get_connection_params(self) -> dict:
        """Get database connection parameters based on database type"""
        if self.db_type == "postgresql":
            return {
                "host": os.getenv("DB_HOST", "localhost"),
                "port": int(os.getenv("DB_PORT", "5432")),
                "database": os.getenv("DB_NAME", "dqx"),
                "user": os.getenv("DB_USER", "postgres"),
                "password": os.getenv("DB_PASSWORD", "password")
            }
        elif self.db_type == "oracle":
            return {
                "host": os.getenv("DB_HOST", "localhost"),
                "port": int(os.getenv("DB_PORT", "1521")),
                "service": os.getenv("DB_SERVICE", "XEPDB1"),
                "user": os.getenv("DB_USER", "dqx_user"),
                "password": os.getenv("DB_PASSWORD", "password")
            }
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")
    
    def get_connection(self):
        """Get database connection based on configured database type"""
        if self.db_type == "postgresql":
            import psycopg2
            return psycopg2.connect(**self._connection_params)
        elif self.db_type == "oracle":
            try:
                import oracledb
            except ImportError:
                raise ImportError(
                    "oracledb package is required for Oracle connections. "
                    "Install with: pip install oracledb>=1.4.0"
                )
            
            # Configure Oracle to avoid timezone issues in thin mode
            dsn = f"{self._connection_params['host']}:{self._connection_params['port']}/{self._connection_params['service']}"
            
            # Use thick mode or configure thin mode properly to avoid timezone issues
            try:
                # Try to initialize thick mode to avoid timezone issues
                oracledb.init_oracle_client()
            except Exception:
                # If thick mode initialization fails, continue with thin mode
                # but ensure we handle timestamps properly in queries
                pass
            
            return oracledb.connect(
                user=self._connection_params['user'],
                password=self._connection_params['password'],
                dsn=dsn
            )
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")
    
    def safe_get_connection(self):
        """Get database connection with error handling"""
        try:
            return self.get_connection()
        except Exception as e:
            print(f"Database connection error: {e}")
            return None
    
    def convert_query_for_oracle(self, query: str) -> str:
        """Convert PostgreSQL-style queries to Oracle-compatible format"""
        if self.db_type != "oracle":
            return query
        
        result = query
        
        # Convert PostgreSQL-specific functions to Oracle equivalents
        # NOW() -> SYSDATE (Oracle doesn't have timezone issues with SYSDATE)
        result = result.replace("NOW()", "SYSDATE")
        
        # Handle LIMIT/OFFSET for Oracle 12c+ using FETCH FIRST/OFFSET
        limit_pattern = r'\s+LIMIT\s+(\d+)(?:\s+OFFSET\s+(\d+))?\s*;?\s*$'
        match = re.search(limit_pattern, result, re.IGNORECASE)
        if match:
            limit = int(match.group(1))
            offset = int(match.group(2)) if match.group(2) else 0
            if offset > 0:
                replacement = f' OFFSET {offset} ROWS FETCH FIRST {limit} ROWS ONLY'
            else:
                replacement = f' FETCH FIRST {limit} ROWS ONLY'
            result = re.sub(limit_pattern, replacement, result, flags=re.IGNORECASE)
        
        # Convert information_schema queries to Oracle system views
        result = result.replace("information_schema.tables", "all_tables")
        result = result.replace("information_schema.columns", "all_tab_columns")
        result = result.replace("information_schema.schemata", "all_users")
        
        # Convert schema references
        result = result.replace("table_schema", "owner")
        result = result.replace("table_name", "table_name")
        result = result.replace("column_name", "column_name")
        
        return result
    
    def execute_query(self, query: str, params: Optional[Tuple] = None, fetch: bool = True):
        """Execute a query with unified interface for both databases"""
        conn = self.safe_get_connection()
        if not conn:
            return None
        
        try:
            cursor = conn.cursor()
            
            # Convert query for Oracle if needed
            converted_query = self.convert_query_for_oracle(query)
            
            if params:
                cursor.execute(converted_query, params)
            else:
                cursor.execute(converted_query)
            
            if fetch:
                # Both PostgreSQL and Oracle return results the same way
                result = cursor.fetchall()
                return result
            else:
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            print(f"Query execution error: {e}")
            conn.rollback()
            return None
        finally:
            try:
                cursor.close()
                conn.close()
            except Exception:
                pass
    
    def get_column_names(self, cursor) -> List[str]:
        """Get column names from cursor - unified for both databases"""
        # Both PostgreSQL and Oracle cursors have the same description structure
        return [desc[0] for desc in cursor.description]
    
    def format_placeholder(self, position: int) -> str:
        """Get database-specific parameter placeholder"""
        if self.db_type == "postgresql":
            return "%s"  # PostgreSQL uses %s for all parameters
        elif self.db_type == "oracle":
            return f":{position}"  # Oracle uses :1, :2, etc.
        else:
            return "%s"  # Default to PostgreSQL style


# Global database manager instance
db_manager = DatabaseManager()

# Convenience functions for backward compatibility
def get_db_connection():
    """Get database connection using global manager"""
    return db_manager.get_connection()

def safe_get_connection():
    """Get database connection with error handling using global manager"""
    return db_manager.safe_get_connection()
