# Trino client implementation will go here
# This will handle communication with Trino's REST API 

import requests
import time
import logging
import re
import base64
from typing import Any, Dict, List, Optional, Tuple, Iterator, Set
from urllib.parse import urlparse
from .errors import (
    handle_trino_error,
    TrinoConnectionError,
    TrinoQueryError,
    TrinoTimeoutError,
    TrinoResourceError,
    TrinoAuthError
)

logger = logging.getLogger(__name__)

class TrinoClient:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 8080,
        user: str = "mcp-client",
        catalog: Optional[str] = None,
        schema: Optional[str] = None,
        password: Optional[str] = None,
        jwt_token: Optional[str] = None,
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
        self.password = password
        self.jwt_token = jwt_token
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
        
        # Add authentication headers if provided
        self._update_auth_headers()

    def _update_auth_headers(self):
        """Update authentication headers based on current credentials."""
        # Basic Auth
        if self.password:
            auth_str = f"{self.user}:{self.password}"
            auth_header = f"Basic {base64.b64encode(auth_str.encode()).decode()}"
            self.http_headers["Authorization"] = auth_header
        # JWT Token
        elif self.jwt_token:
            self.http_headers["Authorization"] = f"Bearer {self.jwt_token}"
        # Remove auth header if no credentials
        elif "Authorization" in self.http_headers:
            del self.http_headers["Authorization"]
    
    def set_credentials(self, user: Optional[str] = None, password: Optional[str] = None, jwt_token: Optional[str] = None):
        """
        Set authentication credentials.
        
        Args:
            user: Username for Trino connection
            password: Password for basic auth
            jwt_token: JWT token for bearer auth
        """
        if user:
            self.user = user
            self.http_headers["X-Trino-User"] = user
        
        self.password = password
        self.jwt_token = jwt_token
        
        # Update auth headers
        self._update_auth_headers()

    def list_catalogs(self) -> List[str]:
        """Execute SHOW CATALOGS query and return the list of available catalogs."""
        try:
            result = self.execute_query("SHOW CATALOGS")
            if not result or "rows" not in result:
                return []
            return [row[0] for row in result["rows"]]
        except Exception as e:
            raise handle_trino_error(e)
    
    def list_schemas(self, catalog: str) -> List[str]:
        """List all schemas in a catalog."""
        try:
            # We need to set the catalog in the headers for this query
            original_catalog = self.http_headers.get("X-Trino-Catalog")
            
            # Set the catalog for this request
            self.http_headers["X-Trino-Catalog"] = catalog
            
            try:
                result = self.execute_query("SHOW SCHEMAS")
                if not result or "rows" not in result:
                    return []
                return [row[0] for row in result["rows"]]
            finally:
                # Restore the original catalog
                if original_catalog:
                    self.http_headers["X-Trino-Catalog"] = original_catalog
                else:
                    self.http_headers.pop("X-Trino-Catalog", None)
        except Exception as e:
            raise handle_trino_error(e)
    
    def list_tables(self, catalog: str, schema: str) -> List[str]:
        """List all tables in a schema."""
        try:
            # We need to set the catalog and schema in the headers for this query
            original_catalog = self.http_headers.get("X-Trino-Catalog")
            original_schema = self.http_headers.get("X-Trino-Schema")
            
            # Set the catalog and schema for this request
            self.http_headers["X-Trino-Catalog"] = catalog
            self.http_headers["X-Trino-Schema"] = schema
            
            try:
                result = self.execute_query("SHOW TABLES")
                if not result or "rows" not in result:
                    return []
                return [row[0] for row in result["rows"]]
            finally:
                # Restore the original catalog and schema
                if original_catalog:
                    self.http_headers["X-Trino-Catalog"] = original_catalog
                else:
                    self.http_headers.pop("X-Trino-Catalog", None)
                    
                if original_schema:
                    self.http_headers["X-Trino-Schema"] = original_schema
                else:
                    self.http_headers.pop("X-Trino-Schema", None)
        except Exception as e:
            raise handle_trino_error(e)
    
    def get_table_schema(self, catalog: str, schema: str, table: str) -> List[Dict[str, Any]]:
        """Get the schema of a table."""
        try:
            query = f'DESCRIBE "{catalog}"."{schema}"."{table}"'
            result = self.execute_query(query)
            
            if not result or "rows" not in result:
                return []
            
            columns = []
            for row in result["rows"]:
                column_name = row[0]
                column_type = row[1]
                is_nullable = "not null" not in row[2].lower() if len(row) > 2 else True
                
                columns.append({
                    "name": column_name,
                    "type": column_type,
                    "nullable": is_nullable
                })
            
            return columns
        except Exception as e:
            raise handle_trino_error(e)
    
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
                
                # Check for auth-related status codes
                if response.status_code == 401:
                    raise TrinoAuthError("Authentication failed. Check your credentials.")
                elif response.status_code == 403:
                    raise TrinoAuthError("Permission denied. The user does not have sufficient privileges.")
                
                response.raise_for_status()
                return response
            except (requests.RequestException, ConnectionError) as e:
                last_exception = e
                if attempt < self.retry_attempts - 1:
                    wait_time = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Request failed, retrying in {wait_time:.2f}s: {str(e)}")
                    time.sleep(wait_time)
        
        # If we get here, all retries failed
        logger.error(f"Request failed after {self.retry_attempts} attempts: {str(last_exception)}")
        raise handle_trino_error(last_exception or RuntimeError("Request failed after multiple retries"))
    
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
            
            # Check for error in response
            if "error" in query_results:
                error_info = query_results["error"]
                error_message = error_info.get("message", "Unknown Trino error")
                error_type = error_info.get("errorType", "")
                error_name = error_info.get("errorName", "")
                
                if "SYNTAX_ERROR" in error_type:
                    raise handle_trino_error(Exception(f"Syntax error: {error_message}"))
                elif "RESOURCE_ERROR" in error_type:
                    raise handle_trino_error(Exception(f"Resource error: {error_message}"))
                elif "INSUFFICIENT_RESOURCES" in error_type:
                    raise handle_trino_error(Exception(f"Insufficient resources: {error_message}"))
                elif "PERMISSION_DENIED" in error_type:
                    raise handle_trino_error(Exception(f"Permission denied: {error_message}"))
                elif "ACCESS_DENIED" in error_type:
                    raise TrinoAuthError(f"Access denied: {error_message}")
                else:
                    raise handle_trino_error(Exception(f"{error_type} {error_name}: {error_message}"))
            
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
                
                # Check for error in follow-up responses too
                if "error" in query_results:
                    error_info = query_results["error"]
                    error_message = error_info.get("message", "Unknown Trino error")
                    error_type = error_info.get("errorType", "")
                    raise handle_trino_error(Exception(f"{error_type}: {error_message}"))
                
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
            raise handle_trino_error(e)
    
    def submit_query(self, sql: str) -> Dict[str, Any]:
        """
        Submit a query asynchronously and return the query ID.
        
        Returns:
            Dict containing the query ID
        """
        query_url = f"{self.base_url}/v1/statement"
        
        try:
            response = self._request_with_retry(
                'post',
                query_url,
                data=sql.encode("utf-8")
            )
            
            # Process response to get the query ID
            query_results = response.json()
            
            # Check for error in response
            if "error" in query_results:
                error_info = query_results["error"]
                error_message = error_info.get("message", "Unknown Trino error")
                error_type = error_info.get("errorType", "")
                raise handle_trino_error(Exception(f"{error_type}: {error_message}"))
            
            # Extract query ID from the response or the nextUri
            query_id = query_results.get("id")
            
            if not query_id and "nextUri" in query_results:
                # Try to extract query ID from nextUri
                match = re.search(r'/v1/query/([^/]+)/', query_results["nextUri"])
                if match:
                    query_id = match.group(1)
            
            if not query_id:
                raise TrinoQueryError("Failed to extract query ID from response")
            
            return {"queryId": query_id}
            
        except Exception as e:
            logger.error(f"Error submitting query: {str(e)}")
            raise handle_trino_error(e)
    
    def get_query_status(self, query_id: str) -> Dict[str, Any]:
        """
        Get the status of a query.
        
        Args:
            query_id: The query ID to get status for
            
        Returns:
            Dict containing the query state, ID, and other status information
        """
        try:
            query_url = f"{self.base_url}/v1/query/{query_id}"
            response = self._request_with_retry('get', query_url)
            query_info = response.json()
            
            # Transform to a more standardized format
            result = {
                "queryId": query_id,
                "state": query_info.get("state", "UNKNOWN"),
                "error": query_info.get("error"),
                "stats": query_info.get("statistics", {})
            }
            
            return result
        except Exception as e:
            logger.error(f"Error getting query status: {str(e)}")
            raise handle_trino_error(e)
    
    def get_query_results(self, query_id: str, max_rows: int = 100) -> Dict[str, Any]:
        """
        Get the results of a query.
        
        Args:
            query_id: The query ID to get results for
            max_rows: Maximum number of rows to return
            
        Returns:
            Dict containing columns, rows, and a nextToken if there are more results
        """
        try:
            # First check the query status
            status = self.get_query_status(query_id)
            
            if status["state"] not in ["FINISHED", "RUNNING"]:
                if status["state"] == "FAILED" and status["error"]:
                    raise handle_trino_error(Exception(f"Query failed: {status['error'].get('message', 'Unknown error')}"))
                elif status["state"] == "CANCELED":
                    raise TrinoQueryError(f"Query was canceled")
                else:
                    raise TrinoQueryError(f"Query is not ready yet. Current state: {status['state']}")
            
            # Get results URL
            # First try the info endpoint to get the results URL
            query_url = f"{self.base_url}/v1/query/{query_id}"
            response = self._request_with_retry('get', query_url)
            query_info = response.json()
            
            # Figure out where to get results from
            next_uri = None
            
            # If query is still running, we need to get the nextUri
            if status["state"] == "RUNNING":
                next_uri = query_info.get("nextUri")
            else:  # FINISHED state
                # For finished queries, we might have outputStage with a self link
                output_stage = query_info.get("outputStage", {})
                
                if "self" in output_stage:
                    # We can get results directly from this URL
                    next_uri = output_stage["self"] + "/results"
                elif "nextUri" in query_info:
                    # Fallback to the nextUri if available
                    next_uri = query_info["nextUri"]
            
            if not next_uri:
                # If no appropriate URI is found, try constructing a URL for the first page
                next_uri = f"{self.base_url}/v1/query/{query_id}/results"
            
            # Now fetch the results
            rows = []
            columns = []
            next_token = None
            
            # Get first page of results
            response = self._request_with_retry('get', next_uri)
            results = response.json()
            
            if "columns" in results:
                columns = [col["name"] for col in results["columns"]]
            
            if "data" in results:
                rows.extend(results["data"])
            
            # Save nextUri as the next token if available and we need more rows
            if "nextUri" in results and len(rows) < max_rows:
                next_token = results["nextUri"]
                
                # If we need more rows and have a next token, keep fetching
                while next_token and len(rows) < max_rows:
                    response = self._request_with_retry('get', next_token)
                    results = response.json()
                    
                    if "data" in results:
                        rows.extend(results["data"])
                        
                        # Trim to max_rows
                        if len(rows) > max_rows:
                            rows = rows[:max_rows]
                            break
                    
                    # Update next token
                    next_token = results.get("nextUri")
            
            return {
                "columns": columns,
                "rows": rows,
                "nextToken": next_token
            }
            
        except Exception as e:
            logger.error(f"Error getting query results: {str(e)}")
            raise handle_trino_error(e)
    
    def check_connection(self) -> bool:
        """Check if we can connect to Trino server."""
        try:
            # Try a simple query that should work on any Trino instance
            self.execute_query("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Connection check failed: {str(e)}")
            return False
    
    def cancel_query(self, query_id: str) -> bool:
        """
        Cancel a query.
        
        Args:
            query_id: The query ID to cancel
            
        Returns:
            True if the query was canceled, False otherwise
        """
        try:
            query_url = f"{self.base_url}/v1/query/{query_id}"
            self._request_with_retry('delete', query_url)
            return True
        except Exception as e:
            logger.error(f"Error canceling query: {str(e)}")
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