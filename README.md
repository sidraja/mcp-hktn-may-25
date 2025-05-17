# Trino MCP Client

A Model Context Protocol (MCP) client for Trino query engine.

## Setup

1. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Connecting to Trino on Docker

If you're running Trino in Docker, you can use the following configuration:

```bash
# Assuming Trino is running on the default port 8080 with Docker port mapping
export TRINO_HOST=localhost
export TRINO_PORT=8080
export TRINO_USER=admin
```

To start Trino using Docker:

```bash
# Pull the latest Trino image
docker pull trinodb/trino:latest

# Run Trino with port mapping
docker run -p 8080:8080 trinodb/trino:latest
```

The container will take a minute or two to start up completely. You can check if Trino is ready by running:

```bash
curl http://localhost:8080/v1/info
```

When Trino is ready, you should see a JSON response with server information.

## Starting the MCP Service

Once Trino is running, start the MCP service:

```bash
uvicorn app.main:app --reload
```

Then check if the service can connect to Trino:

```bash
curl http://localhost:8000/health
```

If the connection is successful, you'll see a JSON response with status "healthy".

## Configuration

The Trino client can be configured using environment variables:

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `TRINO_HOST` | Trino server hostname | localhost |
| `TRINO_PORT` | Trino server port | 8080 |
| `TRINO_USER` | Username to connect as | mcp-client |
| `TRINO_CATALOG` | Default catalog to use | None |
| `TRINO_SCHEMA` | Default schema to use | None |
| `TRINO_HTTP_SCHEME` | HTTP scheme (http/https) | http |
| `TRINO_VERIFY_SSL` | Whether to verify SSL certificates | true |

Example:

```bash
export TRINO_HOST=my-trino-server.example.com
export TRINO_PORT=443
export TRINO_HTTP_SCHEME=https
export TRINO_USER=admin
export TRINO_CATALOG=hive
export TRINO_SCHEMA=default
uvicorn app.main:app --reload
```

## Available Endpoints

- `GET /.well-known/mcp/manifest.json` - MCP manifest
- `POST /mcp` - JSON-RPC endpoint for MCP methods
- `GET /health` - Health check for Trino connectivity

## Available Methods

- `list_catalogs` - Returns a list of available Trino catalogs
- `run_query_sync` - Executes a SQL query and returns results (limited to 100 rows by default)

## Error Handling

The MCP client implements comprehensive error handling according to the JSON-RPC 2.0 specification. All errors are returned in the standard JSON-RPC error format:

```json
{
  "jsonrpc": "2.0",
  "id": "request-id",
  "error": {
    "code": -32000,
    "message": "Error message",
    "data": { "additional": "error details" }
  }
}
```

### Standard JSON-RPC Error Codes

| Code | Message | Meaning |
|------|---------|---------|
| -32700 | Parse error | Invalid JSON was received |
| -32600 | Invalid Request | The JSON sent is not a valid Request object |
| -32601 | Method not found | The method does not exist / is not available |
| -32602 | Invalid params | Invalid method parameter(s) |
| -32603 | Internal error | Internal JSON-RPC error |
| -32000 to -32099 | Server error | Implementation-defined server errors |

### Trino-Specific Error Codes

The MCP client defines additional error codes for Trino-specific errors:

| Code | Error Type | Description |
|------|------------|-------------|
| -33000 | TrinoConnectionError | Unable to connect to Trino server |
| -33001 | TrinoQueryError | Error executing a query on Trino |
| -33002 | TrinoAuthError | Authentication error with Trino |
| -33003 | TrinoResourceError | Resource not available (catalog, schema, table) |
| -33004 | TrinoTimeoutError | Query execution timeout |
| -33005 | TrinoSyntaxError | SQL syntax error |
| -33006 | TrinoStateError | Invalid state for the operation |

## Testing with curl

You can test the JSON-RPC endpoint using curl:

```bash
# List catalogs
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "list_catalogs", "params": {}}'

# Run a query
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 2, "method": "run_query_sync", "params": {"sql": "SELECT * FROM system.runtime.nodes", "maxRows": 10}}'

# Test error handling (invalid method)
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 3, "method": "non_existent_method", "params": {}}'

# Test error handling (invalid params)
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 4, "method": "run_query_sync", "params": {"not_sql": "SELECT 1"}}'
```

## Development

The current implementation includes a Trino client that communicates with Trino's REST API. You can extend this implementation by adding more methods or enhancing existing ones in `app/rpc.py`.