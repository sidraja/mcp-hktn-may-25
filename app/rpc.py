import asyncio
from typing import Any, Dict, List
from . import trino_client

# Note: Trino client configuration is now handled in main.py

async def list_catalogs(_: dict) -> List[str]:
    """Return all available Trino catalogs."""
    # Run in a thread pool to avoid blocking the event loop
    client = trino_client.get_client()
    return await asyncio.to_thread(client.list_catalogs)

async def run_query_sync(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a SQL statement and return up to max_rows rows."""
    sql = params["sql"]
    max_rows = params.get("maxRows", 100)
    
    # Run in a thread pool to avoid blocking the event loop
    client = trino_client.get_client()
    try:
        result = await asyncio.to_thread(client.execute_query, sql, max_rows)
        return result
    except Exception as e:
        # Add useful error information
        error_msg = f"Error executing query: {str(e)}"
        raise ValueError(error_msg)

# Map JSON‑RPC method → Python coroutine
METHOD_TABLE = {
    "list_catalogs": list_catalogs,
    "run_query_sync": run_query_sync,
}

async def dispatch_rpc(method: str, params: dict):
    if method not in METHOD_TABLE:
        raise KeyError(f"Unknown method: {method}")
    return await METHOD_TABLE[method](params) 