# Fraud Rule Copilot - MCP Hackathon Project

This document provides detailed instructions for setting up and working with the Fraud Rule Copilot MCP project.

## Project Overview

The Fraud Rule Copilot allows users to type natural language fraud rules, which are then:
1. Translated to SQL
2. Executed across PostgreSQL and ClickHouse databases via Trino
3. Analyzed for effectiveness (hit-rate, false-positive rate, etc.)
4. Auto-tuned to optimize thresholds

## 1. Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.9+ 
- Pip (Python package manager)

### Clone the Repository

```bash
git clone <repository-url>
cd mcp-hktn-may-25
```

### Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Start the Docker Environment

```bash
docker-compose up -d
```

This will start:
- PostgreSQL (port 5432)
- ClickHouse (ports 8123, 9000)
- Trino (port 8080)
- Metabase (port 3000)

## 2. Database Schema

The project uses two databases with the following schemas:

### PostgreSQL: payments table

Stores transaction data and fraud labels.

| Column | Type | Description |
|--------|------|-------------|
| order_id | SERIAL PRIMARY KEY | Unique transaction ID |
| user_id | INTEGER | Customer ID (joins with ClickHouse) |
| amount | DECIMAL(10,2) | Transaction amount in USD |
| country | VARCHAR(2) | Two-letter country code of card |
| shipping_country | VARCHAR(2) | Two-letter country code for shipping |
| ts | TIMESTAMP | When the transaction occurred |
| authorized | BOOLEAN | Whether transaction was authorized |
| fraud_label | INTEGER | 1 if fraudulent, 0 if legitimate |

### ClickHouse: user_velocity table

Stores user behavior metrics.

| Column | Type | Description |
|--------|------|-------------|
| user_id | UInt32 | Customer ID (joins with PostgreSQL) |
| tx_last_24h | UInt16 | Number of transactions in last 24 hours |
| first_seen_days | UInt16 | Days since user first appeared |

## 3. Generating Mock Data

Use the `generate_data.py` script to create and load synthetic data with fraud patterns:

```bash
# For small test dataset
python generate_data.py --num-users 100 --num-records 1000

# For full dataset (5k users, 50k transactions)
python generate_data.py

# If containers are using different host names
python generate_data.py --postgres-host <postgres-host> --clickhouse-host <clickhouse-host>
```

The data generator creates accounts and transactions with realistic fraud patterns:
- Higher fraud rates for transactions from high-risk countries (NG, ZA, IN)
- Higher fraud rates for large transactions (especially above $300-500)
- Higher fraud rates for new accounts (less than 30 days old)
- Higher fraud rates when billing/shipping countries don't match
- Higher fraud rates for users with high transaction velocity

## 4. Directory Structure

```
mcp-hktn-may-25/
├── docker-compose.yml          # Docker environment configuration
├── requirements.txt            # Python dependencies
├── trino/                      # Trino configuration files
│   └── etc/
│       ├── catalog/            # Database connectors
│       │   ├── clickhouse.properties
│       │   └── postgresql.properties
│       ├── config.properties   # Trino config
│       ├── jvm.config          # JVM settings
│       └── node.properties     # Node settings
├── generate_data.py            # Script to generate and load test data
├── fraud_copilot/              # Main project code
│   ├── data_generation/        # Data generation modules
│   │   ├── schema_definitions.py
│   │   ├── db_setup.py
│   │   └── data_generator.py
```

## 5. Using Trino for Cross-Database Queries

### Connect to Trino

- **Web UI**: http://localhost:8080/
- **CLI**: `docker exec -it mcp-trino-coordinator trino`

### Example Query Joining Both Databases

```sql
SELECT 
  p.order_id, 
  p.amount, 
  p.country, 
  p.shipping_country, 
  p.fraud_label, 
  v.tx_last_24h, 
  v.first_seen_days
FROM 
  postgresql.public.payments p
JOIN 
  clickhouse.default.user_velocity v 
ON 
  p.user_id = v.user_id
LIMIT 10;
```

## 6. Visualizing Data with Metabase

Connect to Metabase at http://localhost:3000/ and:

1. Create a new database connection to Trino
   - Host: mcp-trino-coordinator
   - Port: 8080
   - Database name: Leave empty
   - Username: trino (or your configured username)

2. Use Metabase to create dashboards with the fraud data

## 7. Troubleshooting

### Docker Issues

```bash
# Check container status
docker ps

# View logs
docker logs mcp-trino-coordinator
docker logs mcp-trino-postgres
docker logs mcp-trino-clickhouse

# Restart all containers
docker-compose restart

# Rebuild from scratch
docker-compose down
docker-compose up -d
```

### Database Connection Issues

- **PostgreSQL**: Try connecting directly with `docker exec -it mcp-trino-postgres psql -U trino -d trino`
- **ClickHouse**: Try connecting with `docker exec -it mcp-trino-clickhouse clickhouse-client`
- **Trino**: Check connector status at http://localhost:8080/ui/catalog

## 8. Next Steps

After setting up the environment and generating data:

1. Implement the natural language to SQL conversion
2. Create the fraud rule evaluation logic
3. Develop the threshold auto-tuning mechanism
4. Build a simple UI for rule input and results display
