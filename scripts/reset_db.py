#!/usr/bin/env python3
"""
Database initialization script for kbsearch-mcp-server.
Runs all SQL init scripts in order to set up both rag_service and cicd_service databases.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

try:
    import psycopg2
except ImportError:
    print("Error: psycopg2 not installed. Install it with:")
    print("  pip install psycopg2-binary")
    sys.exit(1)


def load_config():
    """Load database configuration from environment."""
    # Load from .env file if it exists
    env_file = Path(__file__).parent.parent / '.env'
    if env_file.exists():
        load_dotenv(env_file)
        print(f"✓ Loaded configuration from {env_file}")
    else:
        print(f"⚠ No .env file found at {env_file}, using defaults")
    
    # Use localhost for direct connection (not Docker internal)
    config = {
        'host': os.getenv('POSTGRES_SCRIPT_HOST', 'localhost'),
        'port': int(os.getenv('POSTGRES_SCRIPT_PORT', '5432')),
        'user': os.getenv('POSTGRES_USER', 'testuser'),
        'password': os.getenv('POSTGRES_PASSWORD', 'testpass'),
        'dbname': 'postgres'  # Connect to default postgres database first
    }
    
    return config


def execute_sql_file(conn, sql_file):
    """Execute a SQL file."""
    print(f"\n{'='*60}")
    print(f"Executing: {sql_file.name}")
    print(f"{'='*60}")
    
    with open(sql_file, 'r') as f:
        sql_content = f.read()
    
    # Split by commands, handling \c (connect) commands specially
    commands = []
    current_db = None
    current_command = []
    
    for line in sql_content.split('\n'):
        line = line.strip()
        
        # Handle database connection commands
        if line.startswith('\\c '):
            if current_command:
                commands.append(('execute', current_db, '\n'.join(current_command)))
                current_command = []
            
            current_db = line.split()[1]
            commands.append(('connect', current_db, None))
            continue
        
        # Skip empty lines and comments
        if not line or line.startswith('--'):
            continue
        
        current_command.append(line)
    
    # Add remaining command
    if current_command:
        commands.append(('execute', current_db, '\n'.join(current_command)))
    
    # Execute commands
    cursor = conn.cursor()
    current_connection = conn
    
    for cmd_type, target, sql in commands:
        if cmd_type == 'connect':
            print(f"\n→ Connecting to database: {target}")
            # Close existing connection and create new one
            if current_connection != conn:
                current_connection.close()
            
            config = load_config()
            config['dbname'] = target
            current_connection = psycopg2.connect(**config)
            current_connection.autocommit = True
            cursor = current_connection.cursor()
            
        elif cmd_type == 'execute':
            # Split by semicolons for individual statements
            statements = [s.strip() for s in sql.split(';') if s.strip()]
            
            for stmt in statements:
                try:
                    cursor.execute(stmt)
                    # Print feedback for major operations
                    if any(keyword in stmt.upper() for keyword in ['CREATE TABLE', 'CREATE DATABASE', 'INSERT INTO']):
                        operation = stmt.split()[0:2]
                        print(f"  ✓ {' '.join(operation)}")
                except Exception as e:
                    print(f"  ✗ Error: {e}")
                    # Continue with other statements
    
    # Close additional connections
    if current_connection != conn:
        current_connection.close()
    
    cursor.close()
    print(f"✓ Completed: {sql_file.name}")


def main():
    """Main execution function."""
    print("\n" + "="*60)
    print("KBSEARCH-MCP Database Initialization")
    print("="*60)
    
    # Get configuration
    config = load_config()
    print(f"\nConnecting to PostgreSQL at {config['host']}:{config['port']}")
    
    try:
        # Connect to default postgres database
        conn = psycopg2.connect(**config)
        conn.autocommit = True
        print("✓ Connected to PostgreSQL")
        
        # Get init scripts directory
        script_dir = Path(__file__).parent.parent / 'sql'
        if not script_dir.exists():
            print(f"\n✗ Error: Init scripts directory not found: {script_dir}")
            sys.exit(1)
        
        # Get all SQL files in order
        sql_files = sorted(script_dir.glob('*.sql'))
        if not sql_files:
            print(f"\n✗ Error: No SQL files found in {script_dir}")
            sys.exit(1)
        
        print(f"\nFound {len(sql_files)} SQL files to execute:")
        for sql_file in sql_files:
            print(f"  - {sql_file.name}")
        
        # Execute each SQL file in order
        for sql_file in sql_files:
            try:
                execute_sql_file(conn, sql_file)
            except Exception as e:
                print(f"\n✗ Error executing {sql_file.name}: {e}")
                sys.exit(1)
        
        # Verify databases were created
        print(f"\n{'='*60}")
        print("Verifying database setup...")
        print(f"{'='*60}")
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT datname FROM pg_database 
            WHERE datname IN ('rag_service', 'cicd_service')
            ORDER BY datname
        """)
        databases = cursor.fetchall()
        cursor.close()
        
        if len(databases) == 2:
            print(f"✓ Both databases created successfully:")
            for db in databases:
                print(f"  - {db[0]}")
        else:
            print(f"⚠ Warning: Expected 2 databases, found {len(databases)}")
        
        conn.close()
        
        print(f"\n{'='*60}")
        print("✓ Database initialization completed successfully!")
        print(f"{'='*60}\n")
        
    except psycopg2.Error as e:
        print(f"\n✗ Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
