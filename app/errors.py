"""
Error handling module for Trino MCP client.

This module defines error classes and utilities according to the JSON-RPC 2.0 specification:
https://www.jsonrpc.org/specification#error_object
"""
from typing import Any, Dict, Optional


# Standard JSON-RPC error codes
class ErrorCode:
    # JSON-RPC 2.0 standard error codes
    PARSE_ERROR = -32700  # Invalid JSON was received
    INVALID_REQUEST = -32600  # The JSON sent is not a valid Request object
    METHOD_NOT_FOUND = -32601  # The method does not exist / is not available
    INVALID_PARAMS = -32602  # Invalid method parameter(s)
    INTERNAL_ERROR = -32603  # Internal JSON-RPC error
    
    # Server error range (-32000 to -32099)
    # Implementation-defined server errors
    SERVER_ERROR_START = -32000
    SERVER_ERROR_END = -32099
    
    # Trino MCP specific error codes (starting from -33000)
    TRINO_CONNECTION_ERROR = -33000  # Unable to connect to Trino server
    TRINO_QUERY_ERROR = -33001  # Error executing a query on Trino
    TRINO_AUTH_ERROR = -33002  # Authentication error with Trino
    TRINO_RESOURCE_ERROR = -33003  # Resource not available (catalog, schema, table)
    TRINO_TIMEOUT_ERROR = -33004  # Query execution timeout
    TRINO_SYNTAX_ERROR = -33005  # SQL syntax error
    TRINO_STATE_ERROR = -33006  # Invalid state for the operation


class MCPError(Exception):
    """Base exception class for MCP errors."""
    
    def __init__(
        self,
        code: int,
        message: str,
        data: Optional[Any] = None
    ):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the error to a JSON-RPC error object."""
        error = {
            "code": self.code,
            "message": self.message
        }
        if self.data is not None:
            error["data"] = self.data
        return error


# JSON-RPC standard errors
class ParseError(MCPError):
    """Invalid JSON was received."""
    def __init__(self, message: str = "Parse error", data: Optional[Any] = None):
        super().__init__(ErrorCode.PARSE_ERROR, message, data)


class InvalidRequest(MCPError):
    """The JSON sent is not a valid Request object."""
    def __init__(self, message: str = "Invalid Request", data: Optional[Any] = None):
        super().__init__(ErrorCode.INVALID_REQUEST, message, data)


class MethodNotFound(MCPError):
    """The method does not exist / is not available."""
    def __init__(self, message: str = "Method not found", data: Optional[Any] = None):
        super().__init__(ErrorCode.METHOD_NOT_FOUND, message, data)


class InvalidParams(MCPError):
    """Invalid method parameter(s)."""
    def __init__(self, message: str = "Invalid params", data: Optional[Any] = None):
        super().__init__(ErrorCode.INVALID_PARAMS, message, data)


class InternalError(MCPError):
    """Internal JSON-RPC error."""
    def __init__(self, message: str = "Internal error", data: Optional[Any] = None):
        super().__init__(ErrorCode.INTERNAL_ERROR, message, data)


# Trino MCP specific errors
class TrinoConnectionError(MCPError):
    """Unable to connect to Trino server."""
    def __init__(self, message: str = "Trino connection error", data: Optional[Any] = None):
        super().__init__(ErrorCode.TRINO_CONNECTION_ERROR, message, data)


class TrinoQueryError(MCPError):
    """Error executing a query on Trino."""
    def __init__(self, message: str = "Trino query error", data: Optional[Any] = None):
        super().__init__(ErrorCode.TRINO_QUERY_ERROR, message, data)


class TrinoAuthError(MCPError):
    """Authentication error with Trino."""
    def __init__(self, message: str = "Trino authentication error", data: Optional[Any] = None):
        super().__init__(ErrorCode.TRINO_AUTH_ERROR, message, data)


class TrinoResourceError(MCPError):
    """Resource not available (catalog, schema, table)."""
    def __init__(self, message: str = "Trino resource not available", data: Optional[Any] = None):
        super().__init__(ErrorCode.TRINO_RESOURCE_ERROR, message, data)


class TrinoTimeoutError(MCPError):
    """Query execution timeout."""
    def __init__(self, message: str = "Trino query timeout", data: Optional[Any] = None):
        super().__init__(ErrorCode.TRINO_TIMEOUT_ERROR, message, data)


class TrinoSyntaxError(MCPError):
    """SQL syntax error."""
    def __init__(self, message: str = "Trino SQL syntax error", data: Optional[Any] = None):
        super().__init__(ErrorCode.TRINO_SYNTAX_ERROR, message, data)


class TrinoStateError(MCPError):
    """Invalid state for the operation."""
    def __init__(self, message: str = "Trino invalid state", data: Optional[Any] = None):
        super().__init__(ErrorCode.TRINO_STATE_ERROR, message, data)


def handle_trino_error(error: Exception) -> MCPError:
    """
    Convert a Trino-related exception to the appropriate MCPError.
    
    This function analyzes the error message and type to determine
    the most appropriate MCPError subclass.
    """
    error_msg = str(error)
    error_data = {"original_error": error_msg}
    
    if "Connection refused" in error_msg or "Failed to establish a new connection" in error_msg:
        return TrinoConnectionError(
            "Failed to connect to Trino server. Please check that the server is running and accessible.",
            error_data
        )
    
    if "Invalid credentials" in error_msg or "Authentication failed" in error_msg:
        return TrinoAuthError(
            "Authentication failed. Please check your credentials.",
            error_data
        )
    
    if "does not exist" in error_msg:
        if "catalog" in error_msg:
            return TrinoResourceError(f"Catalog not found: {error_msg}", error_data)
        if "schema" in error_msg:
            return TrinoResourceError(f"Schema not found: {error_msg}", error_data)
        if "table" in error_msg:
            return TrinoResourceError(f"Table not found: {error_msg}", error_data)
        return TrinoResourceError(f"Resource not found: {error_msg}", error_data)
    
    if "syntax error" in error_msg.lower() or "line" in error_msg and "position" in error_msg:
        return TrinoSyntaxError(f"SQL syntax error: {error_msg}", error_data)
    
    if "exceeded the query timeout" in error_msg or "execution time exceeded" in error_msg:
        return TrinoTimeoutError(f"Query execution timed out: {error_msg}", error_data)
    
    # Default to the generic query error
    return TrinoQueryError(f"Error executing Trino query: {error_msg}", error_data) 