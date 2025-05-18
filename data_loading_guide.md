# Data Loading Guide for Fraud Rule Copilot

This guide explains how to load mock data into PostgreSQL and ClickHouse databases for the Fraud Rule Copilot project. The data model includes payment transactions in PostgreSQL and user velocity metrics in ClickHouse.

## Prerequisites

- Docker containers up and running (PostgreSQL, ClickHouse, Trino)
- Python with necessary libraries (pandas, numpy, sqlalchemy, clickhouse_driver)

## PostgreSQL Data Loading

### Data Model

PostgreSQL will store the `payments` table with transaction data:

```
payments(order_id, user_id, amount, country, ts, authorized, fraud_label)
```

### Steps

1. **Connect to the PostgreSQL container**:
   ```bash
   docker exec -it mcp-trino-postgres psql -U trino -d trino
   ```

2. **Create the table**:
   ```sql
   CREATE TABLE payments (
     order_id VARCHAR(36) PRIMARY KEY,
     user_id VARCHAR(36) NOT NULL,
     amount DECIMAL(10,2) NOT NULL,
     country VARCHAR(2) NOT NULL,
     ts TIMESTAMP NOT NULL,
     authorized BOOLEAN NOT NULL,
     fraud_label BOOLEAN
   );
   ```

3. **Create a Python script (`load_postgres_data.py`) to generate and load mock data**:

```python
import pandas as pd
import numpy as np
import uuid
from sqlalchemy import create_engine
from datetime import datetime, timedelta

# Generate mock data
n_rows = 50000
data = {
    'order_id': [str(uuid.uuid4()) for _ in range(n_rows)],
    'user_id': [str(uuid.uuid4()) for _ in range(n_rows)],
    'amount': np.random.exponential(100, n_rows),
    'country': np.random.choice(['US', 'CA', 'UK', 'DE', 'FR', 'AU', 'JP', 'CN', 'BR', 'MX'], n_rows),
    'ts': [(datetime.now() - timedelta(days=np.random.randint(0, 90))) for _ in range(n_rows)],
    'authorized': np.random.choice([True, False], n_rows, p=[0.95, 0.05]),
    'fraud_label': np.random.choice([True, False, None], n_rows, p=[0.03, 0.92, 0.05])
}

df = pd.DataFrame(data)

# Connect to PostgreSQL
engine = create_engine('postgresql://trino:trino@localhost:5432/trino')
df.to_sql('payments', engine, if_exists='replace', index=False)

print(f"Successfully loaded {n_rows} rows into PostgreSQL payments table")
print(f"Fraud rate: {df['fraud_label'].mean():.2%}")

# Save user_ids to file for ClickHouse data generation
np.save('user_ids.npy', df['user_id'].unique())
```

4. **Run the script**:
   ```bash
   python load_postgres_data.py
   ```

## ClickHouse Data Loading

### Data Model

ClickHouse will store the `user_velocity` table with user behavior metrics:

```
user_velocity(user_id, tx_last_24h, first_seen_days)
```

### Steps

1. **Connect to the ClickHouse container**:
   ```bash
   docker exec -it mcp-trino-clickhouse clickhouse-client --user default --password ""
   ```

2. **Create the database and table**:
   ```sql
   CREATE DATABASE IF NOT EXISTS fraud;
   
   USE fraud;
   
   CREATE TABLE user_velocity (
     user_id String,
     tx_last_24h UInt16,
     first_seen_days UInt16
   ) ENGINE = MergeTree()
   ORDER BY user_id;
   ```

3. **Create a Python script (`load_clickhouse_data.py`) to generate and load mock data**:

```python
import pandas as pd
import numpy as np
from clickhouse_driver import Client

# Load user_ids generated in the PostgreSQL step
user_ids = np.load('user_ids.npy')

# Generate mock velocity data
velocity_data = {
    'user_id': user_ids,
    'tx_last_24h': np.random.poisson(lam=2, size=len(user_ids)),
    'first_seen_days': np.random.randint(1, 365, size=len(user_ids))
}

velocity_df = pd.DataFrame(velocity_data)

# Connect to ClickHouse
client = Client(
    host='localhost',
    port=9000,
    database='fraud'
)

# Insert data
client.execute(
    'INSERT INTO user_velocity VALUES',
    velocity_df.to_dict('records')
)

print(f"Successfully loaded {len(user_ids)} rows into ClickHouse user_velocity table")
print(f"Average transactions in last 24h: {velocity_df['tx_last_24h'].mean():.2f}")
print(f"Average user age in days: {velocity_df['first_seen_days'].mean():.2f}")
```

4. **Run the script**:
   ```bash
   python load_clickhouse_data.py
   ```

## Verification via Trino MCP Server

Once data is loaded, verify it through your Trino MCP server:

```bash
# Verify PostgreSQL data
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "run_query_sync", "params": {"sql": "SELECT COUNT(*) FROM postgres.public.payments", "maxRows": 10}}'

# Verify ClickHouse data
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 2, "method": "run_query_sync", "params": {"sql": "SELECT COUNT(*) FROM clickhouse.fraud.user_velocity", "maxRows": 10}}'
```

## Sample Cross-Database Query

To test a cross-database fraud rule:

```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0", 
    "id": 3, 
    "method": "run_query_sync", 
    "params": {
      "sql": "SELECT p.order_id, p.amount, p.country, v.tx_last_24h, v.first_seen_days FROM postgres.public.payments p JOIN clickhouse.fraud.user_velocity v ON p.user_id = v.user_id WHERE p.amount > 500 AND v.tx_last_24h > 5 AND v.first_seen_days < 7 LIMIT 10", 
      "maxRows": 10
    }
  }'
```

This query identifies potentially fraudulent transactions with high amounts from new users with suspicious transaction velocity.
