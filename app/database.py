from dotenv import load_dotenv
import os
from app.database_manager import db_manager

# Determine the project root directory
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
DOTENV_PATH = os.path.join(PROJECT_ROOT, '.env')

# Load environment variables from .env file in the project root
if os.path.exists(DOTENV_PATH):
    load_dotenv(DOTENV_PATH)
else:
    print(f"Warning: .env file not found at {DOTENV_PATH}")

# Database connection using unified manager
# For backward compatibility, still support DATABASE_URL if set
DATABASE_URL = os.getenv("DATABASE_URL")

# Dependency to get DB connection
def get_db():
    conn = None
    try:
        if DATABASE_URL:
            # Use legacy DATABASE_URL if provided
            if db_manager.db_type == "postgresql":
                import psycopg2
                conn = psycopg2.connect(DATABASE_URL)
            else:
                # For Oracle, fall back to environment variables
                conn = db_manager.get_connection()
        else:
            # Use the unified database manager
            conn = db_manager.get_connection()
        yield conn
    except Exception as e:
        print(f"Database connection error in get_db: {e}")
        if conn:
            conn.close()
        raise
    finally:
        if conn:
            conn.close()