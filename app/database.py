from dotenv import load_dotenv
import os
import psycopg2

# Determine the project root directory
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
DOTENV_PATH = os.path.join(PROJECT_ROOT, '.env')

# Load environment variables from .env file in the project root
if os.path.exists(DOTENV_PATH):
    load_dotenv(DOTENV_PATH)
else:
    print(f"Warning: .env file not found at {DOTENV_PATH}")

# Database connection configuration
DB_TYPE = os.getenv("DB_TYPE", "postgresql")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "dqx")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")

# Build connection string based on database type
if DB_TYPE.lower() == "postgresql":
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
elif DB_TYPE.lower() == "oracle":
    # For Oracle, you might use cx_Oracle or oracledb
    DATABASE_URL = f"oracle+cx_oracle://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
else:
    raise ValueError(f"Unsupported database type: {DB_TYPE}")

# Fallback to legacy DATABASE_URL if individual parameters are not set
if not all([DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD]):
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("Error: Database configuration is incomplete. Please set either individual DB_* variables or DATABASE_URL")
        raise ValueError("Database configuration is incomplete")

# Dependency to get DB connection
def get_db():
    conn = None  # Initialize conn to None
    try:
        if DB_TYPE.lower() == "postgresql":
            conn = psycopg2.connect(DATABASE_URL)
        elif DB_TYPE.lower() == "oracle":
            # For future Oracle support
            # import cx_Oracle or oracledb
            # conn = cx_Oracle.connect(f"{DB_USER}/{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
            raise NotImplementedError("Oracle support not yet implemented")
        else:
            raise ValueError(f"Unsupported database type: {DB_TYPE}")
        yield conn
    finally:
        if conn:
            conn.close()