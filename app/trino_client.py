# Trino client implementation will go here
# This will handle communication with Trino's REST API 

import requests
import time
import logging
from typing import Any, Dict, List, Optional, Tuple, Iterator
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class TrinoClient:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 8080,
        user: str = "mcp-client",
        catalog: Optional[str] = None,
        schema: Optional[str] = None,
        session_properties: Optional[Dict[str, str]] = None,
        http_headers: Optional[Dict[str, str]] = None,
        http_scheme: str = "http",
        verify: bool = True,
        retry_attempts: int = 3,
        retry_delay: float = 1.0,
    ):
        self.host = host
        self.port = port
        self.user = user
        self.catalog = catalog
        self.schema = schema
        self.session_properties = session_properties or {}
        self.http_headers = http_headers or {}
        self.http_scheme = http_scheme
        self.verify = verify
        self.base_url = f"{http_scheme}://{host}:{port}"
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        
        # Add default headers
        self.http_headers.update({
            "User-Agent": "trino-mcp-client",
            "X-Trino-User": user,
        })
        
        if catalog:
            self.http_headers["X-Trino-Catalog"] = catalog
        if schema:
            self.http_headers["X-Trino-Schema"] = schema
        
        # Add session properties if provided
        for key, value in self.session_properties.items():
            self.http_headers[f"X-Trino-Session"] = f"{key}={value}"

    def list_catalogs(self) -> List[str]:
        """Execute SHOW CATALOGS query and return the list of available catalogs."""
        result = self.execute_query("SHOW CATALOGS")
        if not result or "rows" not in result:
            return []
        return [row[0] for row in result["rows"]]
    
    def _request_with_retry(self, method: str, url: str, **kwargs) -> requests.Response:
        """Perform an HTTP request with retry logic."""
        last_exception = None
        
        for attempt in range(self.retry_attempts):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=self.http_headers,
                    verify=self.verify,
                    **kwargs
                )
                response.raise_for_status()
                return response
            except (requests.RequestException, ConnectionError) as e:
                last_exception = e
                if attempt < self.retry_attempts - 1:
                    wait_time = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Request failed, retrying in {wait_time:.2f}s: {str(e)}")
                    time.sleep(wait_time)
        
        # If we get here, all retries failed
        raise last_exception or RuntimeError("Request failed after multiple retries")
    
    def execute_query(self, sql: str, max_rows: int = 100) -> Dict[str, Any]:
        """Execute a SQL query and return results with columns and rows."""
        # Initial request to submit the query
        query_url = f"{self.base_url}/v1/statement"
        
        try:
            response = self._request_with_retry(
                'post',
                query_url,
                data=sql.encode("utf-8"),
            )
            
            # Process response
            query_results = response.json()
            
            # Handle nextUri for pagination until we get all results or hit max_rows
            rows = []
            columns = []
            
            if "columns" in query_results:
                columns = [col["name"] for col in query_results["columns"]]
            
            # Collect rows from initial response
            if "data" in query_results:
                rows.extend(query_results["data"])
            
            # Follow nextUri if it exists
            while "nextUri" in query_results and len(rows) < max_rows:
                response = self._request_with_retry('get', query_results["nextUri"])
                query_results = response.json()
                
                if "columns" in query_results and not columns:
                    columns = [col["name"] for col in query_results["columns"]]
                    
                if "data" in query_results:
                    rows.extend(query_results["data"])
                    if len(rows) >= max_rows:
                        rows = rows[:max_rows]
                        break
                
                # Check if query is finished
                if "nextUri" not in query_results:
                    break
                
                # Add a small delay to avoid hammering the server
                time.sleep(0.1)
            
            return {
                "columns": columns,
                "rows": rows
            }
            
        except Exception as e:
            logger.error(f"Error executing query: {str(e)}")
            # Provide more context in the error message
            error_msg = f"Failed to execute query: {str(e)}"
            if "Connection refused" in str(e):
                error_msg += ". Check if Trino server is running and accessible."
            raise RuntimeError(error_msg)
    
    def get_query_info(self, query_id: str) -> Dict[str, Any]:
        """Get information about a specific query."""
        query_url = f"{self.base_url}/v1/query/{query_id}"
        response = self._request_with_retry('get', query_url)
        return response.json()
    
    def check_connection(self) -> bool:
        """Check if we can connect to Trino server."""
        try:
            # Try a simple query that should work on any Trino instance
            self.execute_query("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Connection check failed: {str(e)}")
            return False


# Singleton instance of the Trino client for easy import elsewhere
default_client = None

def get_client(**kwargs) -> TrinoClient:
    """Get a configured Trino client, creating it if needed."""
    global default_client
    if default_client is None:
        default_client = TrinoClient(**kwargs)
    return default_client

def configure_client(**kwargs) -> None:
    """Configure the default client with the given parameters."""
    global default_client
    default_client = TrinoClient(**kwargs) 