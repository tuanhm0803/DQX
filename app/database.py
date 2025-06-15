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

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Fallback or default if still not found, though this should ideally be caught by the check above
    print("Error: DATABASE_URL environment variable is not set even after attempting to load .env")
    raise ValueError("DATABASE_URL environment variable is not set")

# Dependency to get DB connection
def get_db():
    conn = None  # Initialize conn to None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        yield conn
    finally:
        if conn:
            conn.close()