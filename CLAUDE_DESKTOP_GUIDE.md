# Using Trino MCP with Claude Desktop

This guide explains how to connect Claude Desktop to your Trino MCP server.

## Prerequisites

1. A running Trino server and related databases (using Docker Compose)
2. The FastAPI MCP server running locally

## Configuration

1. Create or update the Claude Desktop configuration file located at:

```
/Users/a42/Library/Application Support/Claude/claude_desktop_config.json
```

2. Use the following configuration:

```json
{
  "mcpServers": {
    "trino": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

## Starting the Services

1. Start the database services:

```bash
docker-compose up -d
```

2. Start the MCP server:

```bash
source .venv/bin/activate
export TRINO_HOST=localhost 
export TRINO_PORT=8080
export TRINO_USER=mcp-client
uvicorn app.main:app --reload
```

## Using with Claude Desktop

1. Restart Claude Desktop for the configuration changes to take effect
2. Create a new chat
3. Click on the "Trino" option in the context panel
4. You can now run SQL queries against your Trino server

### Example Queries

Here are some example queries you can try:

1. List available catalogs:
```sql
SHOW CATALOGS
```

2. List schemas in the clickhouse catalog:
```sql
SHOW SCHEMAS FROM clickhouse
```

3. List tables in a schema:
```sql
SHOW TABLES FROM clickhouse.system
```

4. Query system information:
```sql
SELECT * FROM system.runtime.nodes
```

## Troubleshooting

If you encounter issues, check:

1. The FastAPI server is running on port 8000
2. The Trino server is running and accessible
3. The Claude Desktop configuration is correct
4. Server logs for more detailed error information

You can check the server's health with:

```bash
curl http://localhost:8000/health
```

And test the MCP endpoint with:

```bash
curl -X POST http://localhost:8000/mcp -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","id":1,"method":"list_catalogs","params":{}}'
``` 