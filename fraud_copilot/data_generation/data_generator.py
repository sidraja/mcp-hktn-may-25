"""
Data generator module for the Fraud Rule Copilot project.

This module handles:
1. Generating synthetic user data for the user_velocity table in ClickHouse
2. Generating synthetic transaction data for the payments table in PostgreSQL
3. Inserting the generated data into the respective databases

The generated data follows patterns that make it suitable for fraud rule analysis.
"""

import random
import datetime
from faker import Faker
import numpy as np
from tqdm import tqdm

from .db_setup import get_postgres_connection, get_clickhouse_client

# Initialize faker
fake = Faker()

# Constants
DEFAULT_NUM_USERS = 5000
DEFAULT_NUM_RECORDS = 50000
COUNTRIES = ['US', 'CA', 'UK', 'FR', 'DE', 'NG', 'ZA', 'IN', 'CN', 'JP', 'AU', 'BR', 'MX']
HIGH_RISK_COUNTRIES = ['NG', 'ZA', 'IN']
FRAUD_RATE = 0.05

class FraudDataGenerator:
    """
    Generator for synthetic fraud detection data.
    
    This class handles the generation of:
    - User velocity data for ClickHouse
    - Payment transaction data with fraud signals for PostgreSQL
    """
    
    def __init__(self, num_users=DEFAULT_NUM_USERS, num_records=DEFAULT_NUM_RECORDS):
        """
        Initialize the data generator.
        
        Args:
            num_users (int): Number of unique users to generate
            num_records (int): Number of payment records to generate
        """
        self.num_users = num_users
        self.num_records = num_records
        self.users = []
        self.payments = []
    
    def generate_user_data(self):
        """
        Generate synthetic user data for the user_velocity table.
        
        The data includes:
        - user_id: Unique identifier for each user
        - tx_last_24h: Number of transactions in the last 24 hours
        - first_seen_days: Number of days since the user first appeared
        
        Also adds a 'is_high_risk' flag for internal use during payment generation.
        
        Returns:
            list: List of user data dictionaries
        """
        self.users = []
        
        # Create base user profiles
        for i in range(1, self.num_users + 1):
            # Determine if user account is new (1-30 days) or established
            is_new_account = random.random() < 0.3
            first_seen_days = random.randint(1, 30) if is_new_account else random.randint(31, 730)
            
            # Transaction velocity - newer accounts tend to have lower velocity
            if is_new_account:
                tx_last_24h = max(1, int(np.random.exponential(2)))
            else:
                tx_last_24h = max(1, int(np.random.exponential(5)))
            
            self.users.append({
                'user_id': i,
                'tx_last_24h': tx_last_24h,
                'first_seen_days': first_seen_days,
                'is_high_risk': random.random() < 0.2  # 20% of users flagged as high risk
            })
        
        print(f"Generated data for {len(self.users)} users.")
        return self.users
    
    def generate_payment_data(self):
        """
        Generate synthetic payment data for the payments table.
        
        The data includes various fraud patterns:
        - Higher fraud rates for high-risk countries
        - Higher fraud rates for large transactions
        - Higher fraud rates for new accounts
        - Higher fraud rates when countries don't match
        - Higher fraud rates for users with many transactions in 24h
        
        Returns:
            list: List of payment data dictionaries
        """
        if not self.users:
            self.generate_user_data()
        
        self.payments = []
        
        # Set a fixed date range ending today and going back 120 days
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=120)
        date_range = (end_date - start_date).days
        
        for i in tqdm(range(self.num_records), desc="Generating payment records"):
            # Select a user
            user = random.choice(self.users)
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
            
            self.payments.append({
                'user_id': user_id,
                'amount': amount,
                'country': country,
                'shipping_country': shipping_country,
                'ts': ts,
                'authorized': authorized,
                'fraud_label': fraud_label
            })
        
        print(f"Generated {len(self.payments)} payment records.")
        return self.payments
    
    def insert_postgres_data(self, postgres_config):
        """
        Insert payment data into PostgreSQL.
        
        Args:
            postgres_config (dict): PostgreSQL connection configuration
        
        Returns:
            bool: True if insertion was successful, False otherwise
        """
        if not self.payments:
            self.generate_payment_data()
        
        try:
            conn, cursor = get_postgres_connection(postgres_config)
            
            # Insert data in batches
            batch_size = 1000
            for i in tqdm(range(0, len(self.payments), batch_size), desc="Inserting into PostgreSQL"):
                batch = self.payments[i:i+batch_size]
                
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
            print(f"Inserted {len(self.payments)} records into PostgreSQL.")
            return True
        
        except Exception as e:
            print(f"Error inserting into PostgreSQL: {e}")
            return False
    
    def insert_clickhouse_data(self, clickhouse_config):
        """
        Insert user velocity data into ClickHouse.
        
        Args:
            clickhouse_config (dict): ClickHouse connection configuration
        
        Returns:
            bool: True if insertion was successful, False otherwise
        """
        if not self.users:
            self.generate_user_data()
        
        try:
            client = get_clickhouse_client(clickhouse_config)
            
            # Prepare data for insertion
            user_data = [
                (
                    user['user_id'],
                    user['tx_last_24h'],
                    user['first_seen_days']
                )
                for user in self.users
            ]
            
            # Insert all data at once (ClickHouse is optimized for bulk inserts)
            client.execute(
                "INSERT INTO user_velocity VALUES", 
                user_data
            )
            
            print(f"Inserted {len(self.users)} records into ClickHouse.")
            return True
        
        except Exception as e:
            print(f"Error inserting into ClickHouse: {e}")
            return False
            
    def generate_and_insert_data(self, postgres_config, clickhouse_config):
        """
        Generate and insert data into both PostgreSQL and ClickHouse.
        
        Args:
            postgres_config (dict): PostgreSQL connection configuration
            clickhouse_config (dict): ClickHouse connection configuration
        
        Returns:
            tuple: (postgres_success, clickhouse_success)
        """
        # Generate data
        self.generate_user_data()
        self.generate_payment_data()
        
        # Insert data
        pg_success = self.insert_postgres_data(postgres_config)
        ch_success = self.insert_clickhouse_data(clickhouse_config)
        
        if pg_success and ch_success:
            print("Data generation and insertion completed successfully for all databases.")
        else:
            print("Data generation and insertion had some errors. Check the logs above.")
        
        return (pg_success, ch_success)
