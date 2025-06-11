#!/usr/bin/env python
# filepath: d:\Small_Projects\DQX\utils\create_tables.py
"""
Table Creation Utility for DQX

This script provides functionality to create tables from SELECT queries.
It can be used both as a command-line tool and imported as a module.

Usage:
    python utils/create_tables.py create_table --table_name <new_table_name> --query "<SELECT query>" [--schema <schema_name>] [--drop_if_exists]
    
    OR
    
    python utils/create_tables.py create_from_file --file <path_to_sql_file> --table_name <new_table_name> [--schema <schema_name>] [--drop_if_exists]

Example:
    python utils/create_tables.py create_table --table_name new_employees --query "SELECT id, name, department FROM employees WHERE hire_date > '2020-01-01'"
    
    OR
    
    python utils/create_tables.py create_from_file --file queries/employee_query.sql --table_name employee_report --schema HR --drop_if_exists
"""

import os
import sys
import argparse
import re
from sqlalchemy import text, Table, MetaData, inspect, Column, String, Integer, DateTime, Date, Float, Boolean
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import sqltypes
from typing import Dict, List, Optional, Tuple, Any, Union
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("create_tables")  # Updated logger name

# Add parent directory to path to ensure imports work when run from utils folder
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import database connection from app
try:
    from app.database import engine, get_db, SessionLocal
    from app.crud import execute_sql_script
except ImportError:
    # For standalone usage outside the DQX project
    load_dotenv()
    from sqlalchemy import create_engine
    
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost/postgres")
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    def get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    def execute_sql_script(db, script_content):
        """Execute a SQL script directly if not imported from crud.py"""
        result = db.execute(text(script_content))
        db.commit()
        return {"message": "Script executed successfully"}


def get_column_types_from_query(db, query: str) -> List[Tuple[str, Any]]:
    """
    Execute a query and determine the column names and their types.
    Returns a list of (column_name, column_type) tuples.
    """
    # Add LIMIT 0 to avoid retrieving large datasets just for metadata
    if not query.lower().strip().endswith('limit 0'):
        # Check if there's already a LIMIT clause
        if 'limit' not in query.lower():
            query = f"{query} LIMIT 0"
    
    # Execute the query to get column information
    result = db.execute(text(query))
    columns = result.keys()
    column_types = result.cursor.description
    
    # Map PostgreSQL types to SQLAlchemy types
    type_mapping = []
    for i, col in enumerate(columns):
        pg_type = column_types[i][1]
        
        # Basic mapping from PostgreSQL type codes to SQLAlchemy types
        # This is a simplified version and might need expansion
        if pg_type in (23, 20, 21):  # integer types
            sa_type = Integer
        elif pg_type in (700, 701):  # float, double
            sa_type = Float
        elif pg_type in (1043, 25):  # varchar, text
            sa_type = String
        elif pg_type in (1082,):  # date
            sa_type = Date
        elif pg_type in (1114, 1184):  # timestamp
            sa_type = DateTime
        elif pg_type in (16,):  # boolean
            sa_type = Boolean
        else:
            # Default to String for unknown types
            sa_type = String
            
        type_mapping.append((col, sa_type))
    
    return type_mapping


def create_table_from_query(db, table_name: str, query: str, schema: Optional[str] = None, drop_if_exists: bool = False) -> Dict[str, Any]:
    """
    Create a new table from a SELECT query.
    
    Args:
        db: Database session
        table_name: Name of the table to create
        query: SELECT query to use as source
        schema: Schema name (optional)
        drop_if_exists: Whether to drop the table if it already exists
    
    Returns:
        Dictionary with operation result
    """
    try:
        # Validate inputs
        if not table_name or not query:
            return {"success": False, "message": "Table name and query are required"}
        
        if not query.lower().strip().startswith('select'):
            return {"success": False, "message": "Only SELECT queries are supported"}
        
        # Fully qualified table name
        full_table_name = f"{schema}.{table_name}" if schema else table_name
        
        # Check if table exists
        inspector = inspect(engine)
        table_exists = False
        
        if schema:
            table_exists = table_name in inspector.get_table_names(schema=schema)
        else:
            table_exists = table_name in inspector.get_table_names()
        
        if table_exists and not drop_if_exists:
            return {"success": False, "message": f"Table {full_table_name} already exists. Use drop_if_exists=True to replace it."}
        
        # Create the CREATE TABLE statement
        create_table_sql = f"CREATE TABLE {full_table_name} AS {query}"
        
        # Execute the statement with transaction support
        if table_exists and drop_if_exists:
            drop_sql = f"DROP TABLE {full_table_name}"
            db.execute(text(drop_sql))
        
        db.execute(text(create_table_sql))
        db.commit()
        
        # Verify the table was created
        if schema:
            success = table_name in inspector.get_table_names(schema=schema)
        else:
            success = table_name in inspector.get_table_names()
        
        return {
            "success": success, 
            "message": f"Table {full_table_name} created successfully" if success else "Table creation failed",
            "table_name": full_table_name
        }
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating table: {str(e)}")
        return {"success": False, "message": f"Error: {str(e)}"}


def create_table_ddl_from_query(db, query: str) -> str:
    """
    Generate CREATE TABLE DDL statement from a SELECT query without executing it.
    This is useful for previewing the table structure that would be created.
    
    Args:
        db: Database session
        query: SELECT query to analyze
    
    Returns:
        DDL statement as a string
    """
    try:
        # Get column types from query
        columns = get_column_types_from_query(db, query)
        
        # Build DDL statement
        column_definitions = []
        for col_name, col_type in columns:
            type_name = col_type.__name__.upper()
            if type_name == 'STRING':
                type_name = 'VARCHAR(255)'
            column_definitions.append(f'    "{col_name}" {type_name}')
        
        ddl = "CREATE TABLE table_name (\n"
        ddl += ",\n".join(column_definitions)
        ddl += "\n);"
        
        return ddl
    
    except Exception as e:
        logger.error(f"Error generating DDL: {str(e)}")
        return f"-- Error generating DDL: {str(e)}"


def read_query_from_file(file_path: str) -> str:
    """Read a SQL query from a file."""
    try:
        with open(file_path, 'r') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {str(e)}")
        raise


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Create tables from SELECT queries')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Command: create_table
    create_parser = subparsers.add_parser('create_table', help='Create a table from a SELECT query')
    create_parser.add_argument('--table_name', required=True, help='Name of the table to create')
    create_parser.add_argument('--query', required=True, help='SELECT query to use as source')
    create_parser.add_argument('--schema', help='Schema name (optional)')
    create_parser.add_argument('--drop_if_exists', action='store_true', help='Drop table if it exists')
    
    # Command: create_from_file
    file_parser = subparsers.add_parser('create_from_file', help='Create a table from a SQL file')
    file_parser.add_argument('--file', required=True, help='Path to SQL file')
    file_parser.add_argument('--table_name', required=True, help='Name of the table to create')
    file_parser.add_argument('--schema', help='Schema name (optional)')
    file_parser.add_argument('--drop_if_exists', action='store_true', help='Drop table if it exists')
    
    # Command: preview_ddl
    preview_parser = subparsers.add_parser('preview_ddl', help='Preview the CREATE TABLE DDL without executing it')
    preview_parser.add_argument('--query', help='SELECT query to analyze')
    preview_parser.add_argument('--file', help='Path to SQL file with SELECT query')
    
    return parser.parse_args()


def main():
    """Main entry point for the script."""
    args = parse_arguments()
    
    # Initialize DB session
    db = next(get_db())
    
    try:
        if args.command == 'create_table':
            result = create_table_from_query(
                db=db,
                table_name=args.table_name,
                query=args.query,
                schema=args.schema,
                drop_if_exists=args.drop_if_exists
            )
            print(result["message"])
            
        elif args.command == 'create_from_file':
            query = read_query_from_file(args.file)
            result = create_table_from_query(
                db=db,
                table_name=args.table_name,
                query=query,
                schema=args.schema,
                drop_if_exists=args.drop_if_exists
            )
            print(result["message"])
            
        elif args.command == 'preview_ddl':
            if args.query:
                query = args.query
            elif args.file:
                query = read_query_from_file(args.file)
            else:
                print("Error: Either --query or --file must be specified")
                return
                
            ddl = create_table_ddl_from_query(db, query)
            print("Generated DDL:")
            print(ddl)
            
        else:
            print("No valid command specified. Use --help for usage information.")
    
    except Exception as e:
        print(f"Error: {str(e)}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
