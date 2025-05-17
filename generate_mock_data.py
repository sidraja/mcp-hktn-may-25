#!/usr/bin/env python3
"""
Generate synthetic data for Fraud Rule Copilot demo:
- PostgreSQL: payments table
- ClickHouse: user_velocity table
"""

import argparse
import random
import datetime
import psycopg2
import clickhouse_driver
from faker import Faker
import pandas as pd
import numpy as np
from tqdm import tqdm

# Initialize faker
fake = Faker()

# Constants
NUM_RECORDS = 50000
NUM_USERS = 5000
COUNTRIES = ['US', 'CA', 'UK', 'FR', 'DE', 'NG', 'ZA', 'IN', 'CN', 'JP', 'AU', 'BR', 'MX']
FRAUD_RATE = 0.05
HIGH_RISK_COUNTRIES = ['NG', 'ZA', 'IN']

def setup_postgres_table(conn_string):
    """Create payments table in PostgreSQL"""
    conn = psycopg2.connect(conn_string)
    cursor = conn.cursor()
    
    # Drop table if exists
    cursor.execute("DROP TABLE IF EXISTS payments")
    
    # Create table
    cursor.execute("""
    CREATE TABLE payments (
        order_id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        amount DECIMAL(10, 2) NOT NULL,
        country VARCHAR(2) NOT NULL,
        shipping_country VARCHAR(2) NOT NULL,
        ts TIMESTAMP NOT NULL,
        authorized BOOLEAN NOT NULL,
        fraud_label INTEGER NOT NULL
    )
    """)
    
    conn.commit()
    cursor.close()
    conn.close()
    print("PostgreSQL table 'payments' created.")

def setup_clickhouse_table(conn_params):
    """Create user_velocity table in ClickHouse"""
    client = clickhouse_driver.Client(**conn_params)
    
    # Drop table if exists
    client.execute("DROP TABLE IF EXISTS user_velocity")
    
    # Create table
    client.execute("""
    CREATE TABLE user_velocity (
        user_id UInt32,
        tx_last_24h UInt16,
        first_seen_days UInt16
    ) ENGINE = MergeTree() ORDER BY user_id
    """)
    
    print("ClickHouse table 'user_velocity' created.")

def generate_user_data(num_users):
    """Generate synthetic user data"""
    users = []
    
    # Create base user profiles
    for i in range(1, num_users + 1):
        # Determine if user account is new (1-30 days) or established
        is_new_account = random.random() < 0.3
        first_seen_days = random.randint(1, 30) if is_new_account else random.randint(31, 730)
        
        # Transaction velocity - newer accounts tend to have lower velocity
        if is_new_account:
            tx_last_24h = max(1, int(np.random.exponential(2)))
        else:
            tx_last_24h = max(1, int(np.random.exponential(5)))
        
        users.append({
            'user_id': i,
            'tx_last_24h': tx_last_24h,
            'first_seen_days': first_seen_days,
            'is_high_risk': random.random() < 0.2  # 20% of users flagged as high risk
        })
    
    return users

def generate_payments_data(users):
    """Generate payments data with fraud patterns embedded"""
    payments = []
    
    # Set a fixed date range ending today and going back 120 days
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=120)
    date_range = (end_date - start_date).days
    
    for i in tqdm(range(NUM_RECORDS), desc="Generating payment records"):
        # Select a user
        user = random.choice(users)
        user_id = user['user_id']
        is_high_risk = user['is_high_risk']
        is_new_account = user['first_seen_days'] < 30
        
        # Generate transaction timestamp
        days_ago = random.randint(0, date_range)
        hours_ago = random.randint(0, 23)
        minutes_ago = random.randint(0, 59)
        ts = end_date - datetime.timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)
        
        # Generate countries
        country = random.choice(HIGH_RISK_COUNTRIES) if is_high_risk and random.random() < 0.7 else random.choice(COUNTRIES)
        
        # Shipping country usually matches but sometimes doesn't
        country_mismatch = random.random() < 0.15
        shipping_country = random.choice(COUNTRIES) if country_mismatch else country
        
        # Generate transaction amount (log-normal distribution)
        # Fraud transactions tend to be larger
        if random.random() < 0.1:  # 10% high-value transactions
            amount = round(random.uniform(500, 2000), 2)
        else:
            amount = round(random.uniform(10, 500), 2)
        
        # Determine fraud label based on risk factors
        # Implement various fraud patterns:
        
        # Base fraud probability
        fraud_prob = FRAUD_RATE
        
        # Increase for high-risk factors
        if is_high_risk:
            fraud_prob *= 3
        
        if is_new_account and amount > 300:
            fraud_prob *= 2
            
        if country in HIGH_RISK_COUNTRIES and amount > 200:
            fraud_prob *= 2.5
            
        if country_mismatch and amount > 250:
            fraud_prob *= 3
            
        if user['tx_last_24h'] > 10:
            fraud_prob *= 2
            
        # Cap probability at 0.9 to avoid deterministic outcomes
        fraud_prob = min(fraud_prob, 0.9)
        
        # Determine fraud label
        fraud_label = 1 if random.random() < fraud_prob else 0
        
        # Authentication is usually successful unless fraud
        authorized = random.random() > (0.9 if fraud_label else 0.02)
        
        payments.append({
            'user_id': user_id,
            'amount': amount,
            'country': country,
            'shipping_country': shipping_country,
            'ts': ts,
            'authorized': authorized,
            'fraud_label': fraud_label
        })
    
    return payments

def insert_postgres_data(conn_string, payments):
    """Insert payments data into PostgreSQL"""
    conn = psycopg2.connect(conn_string)
    cursor = conn.cursor()
    
    # Insert data in batches
    batch_size = 1000
    for i in tqdm(range(0, len(payments), batch_size), desc="Inserting into PostgreSQL"):
        batch = payments[i:i+batch_size]
        
        args = []
        for payment in batch:
            args.append((
                payment['user_id'],
                payment['amount'],
                payment['country'],
                payment['shipping_country'],
                payment['ts'],
                payment['authorized'],
                payment['fraud_label']
            ))
        
        cursor.executemany(
            """
            INSERT INTO payments 
            (user_id, amount, country, shipping_country, ts, authorized, fraud_label) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, 
            args
        )
        conn.commit()
    
    cursor.close()
    conn.close()
    print(f"Inserted {len(payments)} records into PostgreSQL.")

def insert_clickhouse_data(conn_params, users):
    """Insert user velocity data into ClickHouse"""
    client = clickhouse_driver.Client(**conn_params)
    
    # Insert data in batches
    user_data = [
        (
            user['user_id'],
            user['tx_last_24h'],
            user['first_seen_days']
        )
        for user in users
    ]
    
    client.execute(
        "INSERT INTO user_velocity VALUES", 
        user_data
    )
    
    print(f"Inserted {len(users)} records into ClickHouse.")

def main():
    parser = argparse.ArgumentParser(description='Generate mock data for Fraud Rule Copilot demo')
    parser.add_argument('--postgres-host', default='localhost', help='PostgreSQL host')
    parser.add_argument('--postgres-port', default='5432', help='PostgreSQL port')
    parser.add_argument('--postgres-user', default='trino', help='PostgreSQL username')
    parser.add_argument('--postgres-password', default='trino', help='PostgreSQL password')
    parser.add_argument('--postgres-db', default='trino', help='PostgreSQL database name')
    parser.add_argument('--clickhouse-host', default='localhost', help='ClickHouse host')
    parser.add_argument('--clickhouse-port', default='9000', help='ClickHouse port')
    parser.add_argument('--clickhouse-user', default='default', help='ClickHouse username')
    parser.add_argument('--clickhouse-password', default='', help='ClickHouse password')
    parser.add_argument('--clickhouse-db', default='default', help='ClickHouse database name')
    parser.add_argument('--num-records', type=int, default=NUM_RECORDS, help='Number of payment records')
    parser.add_argument('--num-users', type=int, default=NUM_USERS, help='Number of users')
    
    args = parser.parse_args()
    
    # Update globals
    global NUM_RECORDS, NUM_USERS
    NUM_RECORDS = args.num_records
    NUM_USERS = args.num_users
    
    # Connection strings
    postgres_conn_string = f"dbname={args.postgres_db} user={args.postgres_user} password={args.postgres_password} host={args.postgres_host} port={args.postgres_port}"
    clickhouse_conn_params = {
        'host': args.clickhouse_host,
        'port': args.clickhouse_port,
        'user': args.clickhouse_user,
        'password': args.clickhouse_password,
        'database': args.clickhouse_db
    }
    
    # Setup tables
    try:
        setup_postgres_table(postgres_conn_string)
    except Exception as e:
        print(f"Error setting up PostgreSQL table: {e}")
        return
    
    try:
        setup_clickhouse_table(clickhouse_conn_params)
    except Exception as e:
        print(f"Error setting up ClickHouse table: {e}")
        return
    
    # Generate user data
    print(f"Generating data for {NUM_USERS} users and {NUM_RECORDS} payment transactions...")
    users = generate_user_data(NUM_USERS)
    
    # Generate payment data
    payments = generate_payments_data(users)
    
    # Insert data
    try:
        insert_postgres_data(postgres_conn_string, payments)
    except Exception as e:
        print(f"Error inserting into PostgreSQL: {e}")
        return
    
    try:
        insert_clickhouse_data(clickhouse_conn_params, users)
    except Exception as e:
        print(f"Error inserting into ClickHouse: {e}")
        return
    
    print("Data generation complete!")

if __name__ == '__main__':
    main()
