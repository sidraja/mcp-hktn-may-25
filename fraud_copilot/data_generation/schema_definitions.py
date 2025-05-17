"""
Schema definitions for the Fraud Rule Copilot project.

This module defines the database schemas for:
1. PostgreSQL: payments table
2. ClickHouse: user_velocity table

These tables are designed to work together for fraud detection analytics using Trino
to execute cross-database queries.
"""

# PostgreSQL schema definitions
POSTGRES_SCHEMA = {
    "database_name": "trino",
    "schema_name": "public",
    "tables": {
        "payments": {
            "description": "Stores transaction payment records with fraud labels",
            "columns": [
                {
                    "name": "order_id",
                    "type": "SERIAL PRIMARY KEY",
                    "description": "Unique identifier for each transaction"
                },
                {
                    "name": "user_id",
                    "type": "INTEGER NOT NULL",
                    "description": "Identifier of the customer making the purchase"
                },
                {
                    "name": "amount",
                    "type": "DECIMAL(10, 2) NOT NULL",
                    "description": "Transaction amount in USD"
                },
                {
                    "name": "country",
                    "type": "VARCHAR(2) NOT NULL",
                    "description": "Two-letter country code of the card/payment method"
                },
                {
                    "name": "shipping_country",
                    "type": "VARCHAR(2) NOT NULL",
                    "description": "Two-letter country code for the shipping address"
                },
                {
                    "name": "ts",
                    "type": "TIMESTAMP NOT NULL",
                    "description": "Timestamp when the transaction occurred"
                },
                {
                    "name": "authorized",
                    "type": "BOOLEAN NOT NULL",
                    "description": "Whether the transaction was authorized"
                },
                {
                    "name": "fraud_label",
                    "type": "INTEGER NOT NULL",
                    "description": "Fraud label: 1 if transaction was fraudulent, 0 if legitimate"
                }
            ],
            "create_sql": """
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
            """
        }
    }
}

# ClickHouse schema definitions
CLICKHOUSE_SCHEMA = {
    "database_name": "default",
    "tables": {
        "user_velocity": {
            "description": "Stores user transaction velocity metrics",
            "columns": [
                {
                    "name": "user_id",
                    "type": "UInt32",
                    "description": "Identifier of the customer, can be joined with payments.user_id"
                },
                {
                    "name": "tx_last_24h",
                    "type": "UInt16",
                    "description": "Number of transactions by this user in the last 24 hours"
                },
                {
                    "name": "first_seen_days",
                    "type": "UInt16",
                    "description": "Number of days since the user was first seen on the platform"
                }
            ],
            "create_sql": """
            CREATE TABLE user_velocity (
                user_id UInt32,
                tx_last_24h UInt16,
                first_seen_days UInt16
            ) ENGINE = MergeTree() ORDER BY user_id
            """
        }
    }
}

# Cross-database join examples using Trino
TRINO_CROSS_DB_QUERY_TEMPLATE = """
WITH candidates AS (
  SELECT 
    p.order_id,
    p.user_id,
    p.amount,
    p.country,
    p.shipping_country,
    p.ts,
    p.authorized,
    p.fraud_label,
    v.tx_last_24h,
    v.first_seen_days
  FROM 
    postgresql.{pg_schema}.payments p
  JOIN 
    clickhouse.{ch_schema}.user_velocity v 
  ON 
    p.user_id = v.user_id
  WHERE 
    {where_clause}
    AND p.ts BETWEEN date_add('day', -90, now()) AND now()
)
SELECT
  count(*)                                  AS blocked,
  sum(amount)                               AS blocked_value,
  sum(CASE WHEN fraud_label=0 THEN 1 END)   AS false_positives,
  sum(CASE WHEN fraud_label=1 THEN 1 END)   AS fraud_caught,
  sum(CASE WHEN fraud_label=1 THEN amount ELSE 0 END) AS fraud_value_caught,
  sum(CASE WHEN fraud_label=0 THEN amount ELSE 0 END) AS false_positive_value
FROM 
  candidates
"""

# Examples of fraud rules converted to SQL WHERE clauses
EXAMPLE_FRAUD_RULES = {
    "Block transactions above $500 from new accounts in Nigeria": 
        "amount > 500 AND country = 'NG' AND first_seen_days < 7",
    
    "If card country doesn't match shipping country AND amount > $300, block": 
        "country != shipping_country AND amount > 300",
    
    "Block users with more than 15 transactions in 24 hours": 
        "tx_last_24h > 15",
    
    "Block transactions over $1000 from accounts less than 30 days old": 
        "amount > 1000 AND first_seen_days < 30",
    
    "High-risk countries (Nigeria, South Africa, India) with transactions above $200": 
        "country IN ('NG', 'ZA', 'IN') AND amount > 200"
}
