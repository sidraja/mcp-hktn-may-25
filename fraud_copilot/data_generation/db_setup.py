"""
Database setup module for the Fraud Rule Copilot project.

This module handles:
1. Creating necessary tables in PostgreSQL and ClickHouse
2. Setting up any required indexes or optimizations
3. Helper functions for connecting to both databases

Usage:
    from fraud_copilot.data_generation.db_setup import setup_databases
    setup_databases(postgres_config, clickhouse_config)
"""

import psycopg2
import clickhouse_driver
from .schema_definitions import POSTGRES_SCHEMA, CLICKHOUSE_SCHEMA

def setup_postgres(config):
    """
    Set up PostgreSQL database with the payments table.
    
    Args:
        config (dict): PostgreSQL connection configuration
            - host: PostgreSQL host
            - port: PostgreSQL port
            - user: PostgreSQL username
            - password: PostgreSQL password
            - dbname: PostgreSQL database name
    
    Returns:
        bool: True if setup was successful, False otherwise
    """
    try:
        # Create connection string
        conn_string = f"dbname={config['dbname']} user={config['user']} " \
                      f"password={config['password']} host={config['host']} " \
                      f"port={config['port']}"
        
        # Connect to PostgreSQL
        conn = psycopg2.connect(conn_string)
        cursor = conn.cursor()
        
        # Get table info
        payments_table = POSTGRES_SCHEMA['tables']['payments']
        
        # Drop table if it exists
        cursor.execute("DROP TABLE IF EXISTS payments")
        
        # Create table
        cursor.execute(payments_table['create_sql'])
        
        # Create any required indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_country ON payments(country)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_ts ON payments(ts)")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("PostgreSQL setup completed successfully.")
        return True
    
    except Exception as e:
        print(f"Error setting up PostgreSQL: {e}")
        return False

def setup_clickhouse(config):
    """
    Set up ClickHouse database with the user_velocity table.
    
    Args:
        config (dict): ClickHouse connection configuration
            - host: ClickHouse host
            - port: ClickHouse port
            - user: ClickHouse username
            - password: ClickHouse password
            - database: ClickHouse database name
    
    Returns:
        bool: True if setup was successful, False otherwise
    """
    try:
        # Connect to ClickHouse
        client = clickhouse_driver.Client(
            host=config['host'],
            port=config['port'],
            user=config['user'],
            password=config['password'],
            database=config['database']
        )
        
        # Get table info
        user_velocity_table = CLICKHOUSE_SCHEMA['tables']['user_velocity']
        
        # Drop table if it exists
        client.execute("DROP TABLE IF EXISTS user_velocity")
        
        # Create table
        client.execute(user_velocity_table['create_sql'])
        
        print("ClickHouse setup completed successfully.")
        return True
    
    except Exception as e:
        print(f"Error setting up ClickHouse: {e}")
        return False

def setup_databases(postgres_config, clickhouse_config):
    """
    Set up both PostgreSQL and ClickHouse databases.
    
    Args:
        postgres_config (dict): PostgreSQL connection configuration
        clickhouse_config (dict): ClickHouse connection configuration
    
    Returns:
        tuple: (postgres_success, clickhouse_success)
    """
    pg_success = setup_postgres(postgres_config)
    ch_success = setup_clickhouse(clickhouse_config)
    
    if pg_success and ch_success:
        print("Database setup completed successfully for all databases.")
    else:
        print("Database setup had some errors. Check the logs above.")
    
    return (pg_success, ch_success)

def get_postgres_connection(config):
    """
    Get a connection to PostgreSQL.
    
    Args:
        config (dict): PostgreSQL connection configuration
    
    Returns:
        tuple: (connection, cursor)
    """
    conn_string = f"dbname={config['dbname']} user={config['user']} " \
                  f"password={config['password']} host={config['host']} " \
                  f"port={config['port']}"
    
    conn = psycopg2.connect(conn_string)
    cursor = conn.cursor()
    
    return conn, cursor

def get_clickhouse_client(config):
    """
    Get a ClickHouse client.
    
    Args:
        config (dict): ClickHouse connection configuration
    
    Returns:
        clickhouse_driver.Client: ClickHouse client
    """
    client = clickhouse_driver.Client(
        host=config['host'],
        port=config['port'],
        user=config['user'],
        password=config['password'],
        database=config['database']
    )
    
    return client
