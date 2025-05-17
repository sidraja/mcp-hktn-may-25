#!/usr/bin/env python3
"""
Main script for generating synthetic data for the Fraud Rule Copilot project.

This script:
1. Sets up the necessary database tables in PostgreSQL and ClickHouse
2. Generates synthetic data following fraud patterns
3. Inserts the data into both databases

Usage:
    python generate_data.py --postgres-host localhost --clickhouse-host localhost [other options]
"""

import argparse
import sys
from fraud_copilot.data_generation.db_setup import setup_databases
from fraud_copilot.data_generation.data_generator import FraudDataGenerator

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Generate mock data for Fraud Rule Copilot demo')
    
    # PostgreSQL connection options
    pg_group = parser.add_argument_group('PostgreSQL options')
    pg_group.add_argument('--postgres-host', default='localhost', help='PostgreSQL host')
    pg_group.add_argument('--postgres-port', default='5432', help='PostgreSQL port')
    pg_group.add_argument('--postgres-user', default='trino', help='PostgreSQL username')
    pg_group.add_argument('--postgres-password', default='trino', help='PostgreSQL password')
    pg_group.add_argument('--postgres-dbname', default='trino', help='PostgreSQL database name')
    
    # ClickHouse connection options
    ch_group = parser.add_argument_group('ClickHouse options')
    ch_group.add_argument('--clickhouse-host', default='localhost', help='ClickHouse host')
    ch_group.add_argument('--clickhouse-port', default='9000', help='ClickHouse port')
    ch_group.add_argument('--clickhouse-user', default='default', help='ClickHouse username')
    ch_group.add_argument('--clickhouse-password', default='', help='ClickHouse password')
    ch_group.add_argument('--clickhouse-database', default='default', help='ClickHouse database name')
    
    # Data generation options
    data_group = parser.add_argument_group('Data generation options')
    data_group.add_argument('--num-users', type=int, default=5000, help='Number of users to generate')
    data_group.add_argument('--num-records', type=int, default=50000, help='Number of payment records to generate')
    data_group.add_argument('--skip-db-setup', action='store_true', help='Skip database setup (table creation)')
    
    return parser.parse_args()

def main():
    """Main function to run the data generation process."""
    args = parse_args()
    
    # Create configuration dictionaries
    postgres_config = {
        'host': args.postgres_host,
        'port': args.postgres_port,
        'user': args.postgres_user,
        'password': args.postgres_password,
        'dbname': args.postgres_dbname
    }
    
    clickhouse_config = {
        'host': args.clickhouse_host,
        'port': args.clickhouse_port,
        'user': args.clickhouse_user,
        'password': args.clickhouse_password,
        'database': args.clickhouse_database
    }
    
    print("Fraud Rule Copilot - Data Generation")
    print("===================================")
    
    # Setup databases if not skipped
    if not args.skip_db_setup:
        print("\nSetting up database tables...")
        pg_success, ch_success = setup_databases(postgres_config, clickhouse_config)
        
        if not (pg_success and ch_success):
            print("Database setup failed. Exiting.")
            sys.exit(1)
    
    # Generate and insert data
    print("\nGenerating and inserting synthetic data...")
    data_generator = FraudDataGenerator(num_users=args.num_users, num_records=args.num_records)
    pg_success, ch_success = data_generator.generate_and_insert_data(postgres_config, clickhouse_config)
    
    if pg_success and ch_success:
        print("\nData generation completed successfully!")
        print(f"Generated {args.num_users} users and {args.num_records} payment records.")
        print("\nYou can now query this data using Trino with SQL like:")
        print("""
        SELECT 
          p.order_id, p.user_id, p.amount, p.country, p.shipping_country, 
          p.fraud_label, v.tx_last_24h, v.first_seen_days
        FROM 
          postgresql.public.payments p
        JOIN 
          clickhouse.default.user_velocity v 
        ON 
          p.user_id = v.user_id
        LIMIT 10;
        """)
    else:
        print("\nData generation process had errors. Please check the logs above.")
        sys.exit(1)

if __name__ == '__main__':
    main()
