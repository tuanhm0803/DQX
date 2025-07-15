"""
Multi-Database Connection Manager
Handles connections to multiple PostgreSQL databases for source data management
"""
import os
import psycopg2
from dotenv import load_dotenv
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

@dataclass
class DatabaseConnection:
    """Data class to represent a database connection configuration"""
    id: str
    name: str
    host: str
    port: int
    database: str
    username: str
    password: str
    description: Optional[str] = None
    
    def get_connection_string(self) -> str:
        """Generate PostgreSQL connection string"""
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "username": self.username,
            "description": self.description
        }

class MultiDatabaseManager:
    """Manager for multiple database connections"""
    
    def __init__(self):
        self._connections: Dict[str, DatabaseConnection] = {}
        # Ensure environment variables are loaded
        load_dotenv()
        self._load_connections_from_env()
    
    def _load_connections_from_env(self):
        """Load database connections from environment variables"""
        self._load_default_connection()
        self._load_target_connection()
        self._load_source_connections()
    
    def _build_connection_url(self, db_type: str, user: str, password: str, host: str, port: str, db_name: str) -> str:
        """Build connection URL based on database type"""
        if db_type.lower() == "postgresql":
            return f"postgresql://{user}:{password}@{host}:{port}/{db_name}"
        elif db_type.lower() == "oracle":
            return f"oracle+cx_oracle://{user}:{password}@{host}:{port}/{db_name}"
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
    
    def _load_default_connection(self):
        """Load the primary/default connection (for app operations)"""
        db_type = os.getenv("DB_TYPE", "postgresql")
        
        # Try individual parameters first
        db_host = os.getenv("DB_HOST")
        db_port = os.getenv("DB_PORT")
        db_name = os.getenv("DB_NAME")
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")
        
        if all([db_host, db_port, db_name, db_user, db_password]):
            default_url = self._build_connection_url(db_type, db_user, db_password, db_host, db_port, db_name)  # type: ignore
            self.add_connection_from_url("default", "Default Database", default_url, "Primary application database")
        else:
            # Fallback to legacy DATABASE_URL
            default_url = os.getenv("DATABASE_URL")
            if default_url:
                self.add_connection_from_url("default", "Default Database", default_url, "Primary application database")
    
    def _load_target_connection(self):
        """Load the target database (where tables will be created)"""
        db_type = os.getenv("DB_TYPE", "postgresql")
        
        # Try individual parameters first
        target_host = os.getenv("TARGET_DB_HOST")
        target_port = os.getenv("TARGET_DB_PORT") 
        target_db_name = os.getenv("TARGET_DB_NAME_DB")
        target_user = os.getenv("TARGET_DB_USER")
        target_password = os.getenv("TARGET_DB_PASSWORD")
        
        if all([target_host, target_port, target_db_name, target_user, target_password]):
            target_url = self._build_connection_url(db_type, target_user, target_password, target_host, target_port, target_db_name)  # type: ignore
            target_name = os.getenv("TARGET_DB_NAME", "Target Database")
            target_desc = os.getenv("TARGET_DB_DESC", "Target database for table creation")
            self.add_connection_from_url("target", target_name, target_url, target_desc)
        else:
            # Fallback to legacy TARGET_DB_URL
            target_url = os.getenv("TARGET_DB_URL")
            if target_url:
                target_name = os.getenv("TARGET_DB_NAME", "Target Database")
                target_desc = os.getenv("TARGET_DB_DESC", "Target database for table creation")
                self.add_connection_from_url("target", target_name, target_url, target_desc)
    
    def _load_source_connections(self):
        """Load source database connections (where data will be queried from)"""
        source_ids = self._discover_source_connection_ids()
        
        for format_type, source_id in source_ids:
            self._load_single_source_connection(format_type, source_id)
    
    def _discover_source_connection_ids(self) -> set:
        """Discover all source connection IDs from environment variables"""
        source_ids = set()
        
        # Check for new DB_SOURCE_<ID>_HOST format (individual parameters)
        for key in os.environ.keys():
            if key.startswith("DB_SOURCE_") and key.endswith("_HOST"):
                source_id = key.replace("DB_SOURCE_", "").replace("_HOST", "").lower()
                source_ids.add(("source_params", source_id))
        
        # Check for legacy DB_SOURCE_<ID>_URL format
        for key in os.environ.keys():
            if key.startswith("DB_SOURCE_") and key.endswith("_URL"):
                source_id = key.replace("DB_SOURCE_", "").replace("_URL", "").lower()
                if ("source_params", source_id) not in source_ids:  # Only add if not already added via params
                    source_ids.add(("source_url", source_id))
        
        # Check for legacy DB_CONN_ format  
        for key in os.environ.keys():
            if key.startswith("DB_CONN_") and key.endswith("_URL"):
                conn_id = key.replace("DB_CONN_", "").replace("_URL", "").lower()
                source_ids.add(("conn", conn_id))
                
        return source_ids
    
    def _load_single_source_connection(self, format_type: str, source_id: str):
        """Load a single source connection based on format type"""
        if format_type == "source_params":
            self._load_source_from_params(source_id)
        elif format_type == "source_url":
            self._load_source_from_url(source_id)
        else:  # format_type == "conn"
            self._load_legacy_connection(source_id)
    
    def _load_source_from_params(self, source_id: str):
        """Load source connection from individual parameters"""
        db_type = os.getenv("DB_TYPE", "postgresql")
        host = os.getenv(f"DB_SOURCE_{source_id.upper()}_HOST")
        port = os.getenv(f"DB_SOURCE_{source_id.upper()}_PORT")
        db_name = os.getenv(f"DB_SOURCE_{source_id.upper()}_NAME_DB")
        user = os.getenv(f"DB_SOURCE_{source_id.upper()}_USER")
        password = os.getenv(f"DB_SOURCE_{source_id.upper()}_PASSWORD")
        
        if all([host, port, db_name, user, password]):
            url = self._build_connection_url(db_type, user, password, host, port, db_name)  # type: ignore
            name = os.getenv(f"DB_SOURCE_{source_id.upper()}_NAME", f"Source {source_id}")
            description = os.getenv(f"DB_SOURCE_{source_id.upper()}_DESC", "Source database")
            connection_id = f"source_{source_id}"
            self.add_connection_from_url(connection_id, name, url, description)
    
    def _load_source_from_url(self, source_id: str):
        """Load source connection from URL"""
        name = os.getenv(f"DB_SOURCE_{source_id.upper()}_NAME", f"Source {source_id}")
        url = os.getenv(f"DB_SOURCE_{source_id.upper()}_URL")
        description = os.getenv(f"DB_SOURCE_{source_id.upper()}_DESC", "Source database")
        connection_id = f"source_{source_id}"
        if url:
            self.add_connection_from_url(connection_id, name, url, description)
    
    def _load_legacy_connection(self, source_id: str):
        """Load legacy DB_CONN connection"""
        name = os.getenv(f"DB_CONN_{source_id.upper()}_NAME", f"Database {source_id}")
        url = os.getenv(f"DB_CONN_{source_id.upper()}_URL")
        description = os.getenv(f"DB_CONN_{source_id.upper()}_DESC", "Legacy connection")
        if url:
            self.add_connection_from_url(source_id, name, url, description)
    
    def add_connection_from_url(self, conn_id: str, name: str, url: str, description: str = ""):
        """Add a database connection from a PostgreSQL URL"""
        try:
            # Parse PostgreSQL URL: postgresql://user:password@host:port/database
            if not url.startswith("postgresql://"):
                raise ValueError("URL must start with postgresql://")
            
            # Remove the protocol part
            url_parts = url.replace("postgresql://", "")
            
            # Split user:password@host:port/database
            if "@" not in url_parts:
                raise ValueError("Invalid URL format")
            
            auth_part, host_db_part = url_parts.split("@", 1)
            username, password = auth_part.split(":", 1)
            
            # Split host:port/database
            if "/" not in host_db_part:
                raise ValueError("Invalid URL format")
            
            host_port, database = host_db_part.split("/", 1)
            
            if ":" in host_port:
                host, port_str = host_port.split(":", 1)
                port = int(port_str)
            else:
                host = host_port
                port = 5432
            
            connection = DatabaseConnection(
                id=conn_id,
                name=name,
                host=host,
                port=port,
                database=database,
                username=username,
                password=password,
                description=description
            )
            
            self._connections[conn_id] = connection
            
        except Exception as e:
            print(f"Error parsing database URL for {conn_id}: {e}")
    
    def get_connection(self, conn_id: str) -> Optional[psycopg2.extensions.connection]:
        """Get a database connection by ID"""
        if conn_id not in self._connections:
            return None
        
        try:
            db_config = self._connections[conn_id]
            conn = psycopg2.connect(db_config.get_connection_string())
            return conn
        except Exception as e:
            print(f"Error connecting to database {conn_id}: {e}")
            return None
    
    def get_all_connections(self) -> List[Dict[str, Any]]:
        """Get all available database connections (without passwords)"""
        return [conn.to_dict() for conn in self._connections.values()]
    
    def test_connection(self, conn_id: str) -> Dict[str, Any]:
        """Test a database connection and return status"""
        try:
            conn = self.get_connection(conn_id)
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()  # Just to verify the query works
                cursor.close()
                conn.close()
                
                return {
                    "success": True,
                    "message": "Connection successful",
                    "connection_id": conn_id
                }
            else:
                return {
                    "success": False,
                    "message": "Failed to establish connection",
                    "connection_id": conn_id
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Connection error: {str(e)}",
                "connection_id": conn_id
            }
    
    def get_schemas(self, conn_id: str) -> List[str]:
        """Get all schemas from a specific database connection"""
        conn = self.get_connection(conn_id)
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
                ORDER BY schema_name
            """)
            schemas = [row[0] for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            return schemas
        except Exception as e:
            print(f"Error fetching schemas from {conn_id}: {e}")
            if conn:
                conn.close()
            return []
    
    def get_tables(self, conn_id: str, schema: str = 'stg') -> List[str]:
        """Get all tables from a specific schema in a database connection"""
        conn = self.get_connection(conn_id)
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = %s
                ORDER BY table_name
            """, (schema,))
            tables = [row[0] for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            return tables
        except Exception as e:
            print(f"Error fetching tables from {conn_id}.{schema}: {e}")
            if conn:
                conn.close()
            return []
    
    def get_target_connection(self) -> Optional[psycopg2.extensions.connection]:
        """Get the target database connection (where tables will be created)"""
        # Try target database first, fallback to default
        return self.get_connection("target") or self.get_connection("default")
    
    def get_source_connections(self) -> List[Dict[str, Any]]:
        """Get all source database connections (where data will be queried from)"""
        source_connections = []
        for conn in self._connections.values():
            if conn.id.startswith("source_") or conn.id not in ["default", "target"]:
                source_connections.append(conn.to_dict())
        return source_connections
    
    def get_target_connection_info(self) -> Optional[Dict[str, Any]]:
        """Get target database connection info"""
        if "target" in self._connections:
            return self._connections["target"].to_dict()
        elif "default" in self._connections:
            return self._connections["default"].to_dict()
        return None
    
    def is_target_connection(self, conn_id: str) -> bool:
        """Check if a connection ID is the target database"""
        return conn_id in ["target", "default"]

# Global instance
db_manager = MultiDatabaseManager()

def get_db_connection(conn_id: str = "default"):
    """Dependency to get a specific database connection"""
    conn = db_manager.get_connection(conn_id)
    if not conn:
        raise ValueError(f"Could not connect to database: {conn_id}")
    
    try:
        yield conn
    finally:
        if conn:
            conn.close()
