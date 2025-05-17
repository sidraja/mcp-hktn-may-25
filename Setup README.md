# MCP-Themed Trino Hackathon Project

This project sets up an MCP server for Apache Trino connected to PostgreSQL and ClickHouse databases, allowing you to write queries across multiple databases using natural language prompts.

## Quick Setup Guide

### Starting the Environment

```bash
# Navigate to the project directory
cd /path/to/mcp-hktn-may-25

# Start all services
docker-compose up -d
```

### Checking Service Status

```bash
# Check all running containers
docker ps

# Check logs for specific services
docker logs mcp-trino-coordinator
docker logs mcp-trino-postgres
docker logs mcp-trino-clickhouse
docker logs mcp-trino-metabase

# Check Trino server status
curl http://localhost:8080/v1/info
```

### Accessing Services

| Service | URL | Description |
|---------|-----|-------------|
| Trino Web UI | http://localhost:8080 | Query interface and management |
| Metabase | http://localhost:3000 | Data visualization dashboard |
| PostgreSQL | localhost:5432 | PostgreSQL database |
| ClickHouse HTTP | http://localhost:8123 | ClickHouse HTTP interface |
| ClickHouse Native | localhost:9000 | ClickHouse native interface |

### Service Credentials

#### PostgreSQL
- **Database**: trino
- **Username**: trino
- **Password**: trino

#### ClickHouse
- **Username**: default
- **Password**: (empty)

## Using Trino

### CLI Access

To use the Trino CLI:

```bash
# Connect to Trino using Docker
docker exec -it mcp-trino-coordinator trino
```

### Example Queries

#### List Available Catalogs

```sql
SHOW CATALOGS;
```

#### List Schemas in PostgreSQL

```sql
SHOW SCHEMAS FROM postgresql;
```

#### List Tables in PostgreSQL Public Schema

```sql
SHOW TABLES FROM postgresql.public;
```

#### List Schemas in ClickHouse

```sql
SHOW SCHEMAS FROM clickhouse;
```

#### Query Across Databases

```sql
-- Example joining data from PostgreSQL and ClickHouse
SELECT 
  p.column1, 
  c.column2 
FROM 
  postgresql.schema1.table1 p 
JOIN 
  clickhouse.schema2.table2 c 
ON 
  p.id = c.id;
```

## Troubleshooting

### Container Issues

```bash
# Restart all services
docker-compose restart

# Completely rebuild the environment
docker-compose down
docker-compose up -d
```

### Checking Container Health

```bash
# View details about container health
docker inspect mcp-trino-coordinator | grep -A 10 "Health"
```

### Trino Connectivity Issues

If you can't connect to Trino, check the logs:

```bash
docker logs mcp-trino-coordinator
```

## Adding Test Data

### PostgreSQL

```bash
# Connect to PostgreSQL
docker exec -it mcp-trino-postgres psql -U trino -d trino

# Create a test table and add data
CREATE TABLE users (id SERIAL PRIMARY KEY, name VARCHAR(100), email VARCHAR(100));
INSERT INTO users (name, email) VALUES ('John Doe', 'john@example.com'), ('Jane Smith', 'jane@example.com');
```

### ClickHouse

```bash
# Connect to ClickHouse
docker exec -it mcp-trino-clickhouse clickhouse-client

# Create a test table and add data
CREATE TABLE default.events (id UInt32, event_type String, timestamp DateTime) ENGINE = MergeTree() ORDER BY id;
INSERT INTO default.events VALUES (1, 'login', now()), (2, 'purchase', now());
```

## Shutting Down

```bash
# Stop all services while preserving data
docker-compose stop

# Stop and remove all containers, networks, and volumes
docker-compose down -v
```