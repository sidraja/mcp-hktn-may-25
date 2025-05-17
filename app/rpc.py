import asyncio
from typing import Any, Dict, List
from . import trino_client
from .errors import (
    InvalidParams, MethodNotFound, MCPError,
    TrinoConnectionError, TrinoQueryError, handle_trino_error
)

# Note: Trino client configuration is now handled in main.py

async def list_catalogs(params: dict) -> List[str]:
    """Return all available Trino catalogs."""
    # Validate parameters (though none expected for this method)
    if params and not isinstance(params, dict):
        raise InvalidParams("Parameters must be a dictionary or null")
    
    # Run in a thread pool to avoid blocking the event loop
    client = trino_client.get_client()
    try:
        return await asyncio.to_thread(client.list_catalogs)
    except Exception as e:
        # Convert to appropriate MCPError
        raise handle_trino_error(e)

async def run_query_sync(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a SQL statement and return up to max_rows rows."""
    # Validate required parameters
    if not isinstance(params, dict):
        raise InvalidParams("Parameters must be a dictionary")
    
    if "sql" not in params:
        raise InvalidParams("Missing required parameter: 'sql'")
    
    sql = params["sql"]
    if not isinstance(sql, str) or not sql.strip():
        raise InvalidParams("'sql' parameter must be a non-empty string")
    
    # Validate optional parameters
    max_rows = params.get("maxRows", 100)
    if not isinstance(max_rows, int) or max_rows <= 0:
        raise InvalidParams("'maxRows' must be a positive integer")
    
    # Run in a thread pool to avoid blocking the event loop
    client = trino_client.get_client()
    try:
        result = await asyncio.to_thread(client.execute_query, sql, max_rows)
        return result
    except Exception as e:
        # Convert to appropriate MCPError
        raise handle_trino_error(e)

async def run_query_async(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a SQL statement asynchronously and return a query ID."""
    # Validate required parameters
    if not isinstance(params, dict):
        raise InvalidParams("Parameters must be a dictionary")
    
    if "sql" not in params:
        raise InvalidParams("Missing required parameter: 'sql'")
    
    sql = params["sql"]
    if not isinstance(sql, str) or not sql.strip():
        raise InvalidParams("'sql' parameter must be a non-empty string")
    
    # Run in a thread pool to avoid blocking the event loop
    client = trino_client.get_client()
    try:
        result = await asyncio.to_thread(client.submit_query, sql)
        return result
    except Exception as e:
        # Convert to appropriate MCPError
        raise handle_trino_error(e)

async def get_query_status(params: Dict[str, Any]) -> Dict[str, Any]:
    """Get the status of an asynchronous query."""
    # Validate required parameters
    if not isinstance(params, dict):
        raise InvalidParams("Parameters must be a dictionary")
    
    if "queryId" not in params:
        raise InvalidParams("Missing required parameter: 'queryId'")
    
    query_id = params["queryId"]
    if not isinstance(query_id, str) or not query_id.strip():
        raise InvalidParams("'queryId' parameter must be a non-empty string")
    
    # Run in a thread pool to avoid blocking the event loop
    client = trino_client.get_client()
    try:
        result = await asyncio.to_thread(client.get_query_status, query_id)
        return result
    except Exception as e:
        # Convert to appropriate MCPError
        raise handle_trino_error(e)

async def get_query_results(params: Dict[str, Any]) -> Dict[str, Any]:
    """Get results from an asynchronous query."""
    # Validate required parameters
    if not isinstance(params, dict):
        raise InvalidParams("Parameters must be a dictionary")
    
    if "queryId" not in params:
        raise InvalidParams("Missing required parameter: 'queryId'")
    
    query_id = params["queryId"]
    if not isinstance(query_id, str) or not query_id.strip():
        raise InvalidParams("'queryId' parameter must be a non-empty string")
    
    # Validate optional parameters
    max_rows = params.get("maxRows", 100)
    if not isinstance(max_rows, int) or max_rows <= 0:
        raise InvalidParams("'maxRows' must be a positive integer")
    
    # Run in a thread pool to avoid blocking the event loop
    client = trino_client.get_client()
    try:
        result = await asyncio.to_thread(client.get_query_results, query_id, max_rows)
        return result
    except Exception as e:
        # Convert to appropriate MCPError
        raise handle_trino_error(e)

async def list_schemas(params: Dict[str, Any]) -> List[str]:
    """List all schemas in a catalog."""
    # Validate required parameters
    if not isinstance(params, dict):
        raise InvalidParams("Parameters must be a dictionary")
    
    if "catalog" not in params:
        raise InvalidParams("Missing required parameter: 'catalog'")
    
    catalog = params["catalog"]
    if not isinstance(catalog, str) or not catalog.strip():
        raise InvalidParams("'catalog' parameter must be a non-empty string")
    
    # Run in a thread pool to avoid blocking the event loop
    client = trino_client.get_client()
    try:
        result = await asyncio.to_thread(client.list_schemas, catalog)
        return result
    except Exception as e:
        # Convert to appropriate MCPError
        raise handle_trino_error(e)

async def list_tables(params: Dict[str, Any]) -> List[str]:
    """List all tables in a schema."""
    # Validate required parameters
    if not isinstance(params, dict):
        raise InvalidParams("Parameters must be a dictionary")
    
    if "catalog" not in params:
        raise InvalidParams("Missing required parameter: 'catalog'")
    
    catalog = params["catalog"]
    if not isinstance(catalog, str) or not catalog.strip():
        raise InvalidParams("'catalog' parameter must be a non-empty string")
    
    if "schema" not in params:
        raise InvalidParams("Missing required parameter: 'schema'")
    
    schema = params["schema"]
    if not isinstance(schema, str) or not schema.strip():
        raise InvalidParams("'schema' parameter must be a non-empty string")
    
    # Run in a thread pool to avoid blocking the event loop
    client = trino_client.get_client()
    try:
        result = await asyncio.to_thread(client.list_tables, catalog, schema)
        return result
    except Exception as e:
        # Convert to appropriate MCPError
        raise handle_trino_error(e)

async def get_table_schema(params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get the schema of a table."""
    # Validate required parameters
    if not isinstance(params, dict):
        raise InvalidParams("Parameters must be a dictionary")
    
    if "catalog" not in params:
        raise InvalidParams("Missing required parameter: 'catalog'")
    
    catalog = params["catalog"]
    if not isinstance(catalog, str) or not catalog.strip():
        raise InvalidParams("'catalog' parameter must be a non-empty string")
    
    if "schema" not in params:
        raise InvalidParams("Missing required parameter: 'schema'")
    
    schema = params["schema"]
    if not isinstance(schema, str) or not schema.strip():
        raise InvalidParams("'schema' parameter must be a non-empty string")
    
    if "table" not in params:
        raise InvalidParams("Missing required parameter: 'table'")
    
    table = params["table"]
    if not isinstance(table, str) or not table.strip():
        raise InvalidParams("'table' parameter must be a non-empty string")
    
    # Run in a thread pool to avoid blocking the event loop
    client = trino_client.get_client()
    try:
        result = await asyncio.to_thread(client.get_table_schema, catalog, schema, table)
        return result
    except Exception as e:
        # Convert to appropriate MCPError
        raise handle_trino_error(e)

# Map JSON‑RPC method → Python coroutine
METHOD_TABLE = {
    "list_catalogs": list_catalogs,
    "run_query_sync": run_query_sync,
    "run_query_async": run_query_async,
    "get_query_status": get_query_status,
    "get_query_results": get_query_results,
    "list_schemas": list_schemas,
    "list_tables": list_tables,
    "get_table_schema": get_table_schema,
}

async def dispatch_rpc(method: str, params: dict):
    """
    Dispatch a JSON-RPC method call to the appropriate handler.
    
    Args:
        method: The method name to dispatch
        params: Parameters for the method
        
    Returns:
        The result of the method call
        
    Raises:
        MethodNotFound: If the method is not found
        InvalidParams: If the parameters are invalid
        Various MCPError subclasses: For other errors
    """
    if method not in METHOD_TABLE:
        raise MethodNotFound(f"Method '{method}' not found")
    
    handler = METHOD_TABLE[method]
    return await handler(params) 