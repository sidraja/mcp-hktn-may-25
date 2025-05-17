from pathlib import Path
import os
import logging
import json
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError
from .rpc import dispatch_rpc
from . import trino_client
from .errors import (
    MCPError, ParseError, InvalidRequest, MethodNotFound,
    InvalidParams, InternalError, ErrorCode
)
from .auth import (
    get_current_user, get_current_user_optional, is_auth_enabled,
    get_auth_mode, create_jwt_token, AUTH_ENABLED, AUTH_MODE,
    TokenData
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Get configuration from environment variables
TRINO_HOST = os.environ.get("TRINO_HOST", "localhost")
TRINO_PORT = int(os.environ.get("TRINO_PORT", "8080"))
TRINO_USER = os.environ.get("TRINO_USER", "mcp-client")
TRINO_CATALOG = os.environ.get("TRINO_CATALOG", None)
TRINO_SCHEMA = os.environ.get("TRINO_SCHEMA", None)
TRINO_HTTP_SCHEME = os.environ.get("TRINO_HTTP_SCHEME", "http")
TRINO_VERIFY_SSL = os.environ.get("TRINO_VERIFY_SSL", "true").lower() == "true"

# Configure the Trino client
try:
    trino_client.configure_client(
        host=TRINO_HOST,
        port=TRINO_PORT,
        user=TRINO_USER,
        catalog=TRINO_CATALOG,
        schema=TRINO_SCHEMA,
        http_scheme=TRINO_HTTP_SCHEME,
        verify=TRINO_VERIFY_SSL,
    )
    logger.info(f"Trino client configured to connect to {TRINO_HTTP_SCHEME}://{TRINO_HOST}:{TRINO_PORT}")
except Exception as e:
    logger.error(f"Failed to configure Trino client: {str(e)}")

app = FastAPI(title="Trino MCP Gateway")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

MANIFEST_PATH = Path(__file__).parent.parent / ".well-known" / "mcp" / "manifest.json"


@app.get("/.well-known/mcp/manifest.json")
def manifest():
    return FileResponse(MANIFEST_PATH)


@app.get("/health")
async def health_check():
    """Health check endpoint that verifies Trino connectivity."""
    client = trino_client.get_client()
    
    if not client.check_connection():
        raise HTTPException(
            status_code=503,
            detail=f"Cannot connect to Trino server at {client.http_scheme}://{client.host}:{client.port}"
        )
        
    # Return information about the Trino server
    return {
        "status": "healthy",
        "trino_connection": {
            "host": client.host,
            "port": client.port,
            "user": client.user,
            "catalog": client.catalog,
            "schema": client.schema,
        }
    }


@app.get("/auth/status")
async def auth_status(username: str = Depends(get_current_user_optional)):
    """
    Get authentication status.
    
    Returns the authentication status and the current user if authenticated.
    """
    return {
        "auth_enabled": AUTH_ENABLED,
        "auth_mode": AUTH_MODE,
        "authenticated": username is not None,
        "username": username
    }


class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/auth/token")
async def login_for_token(request: LoginRequest):
    """
    Authenticate user and provide JWT token.
    
    This endpoint allows users to get a JWT token by providing
    username/password credentials. The token can then be used
    for subsequent API calls.
    """
    from .auth import authenticate_user
    
    if not is_auth_enabled() or get_auth_mode() not in ["bearer", "all"]:
        raise HTTPException(
            status_code=400,
            detail="Token authentication is not enabled"
        )
    
    # Authenticate the user
    if not authenticate_user(request.username, request.password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    token_data = {
        "sub": request.username,
        "scopes": []  # Add scopes if needed
    }
    access_token = create_jwt_token(token_data)
    
    return {"access_token": access_token, "token_type": "bearer"}


class RPCEnvelope(BaseModel):
    jsonrpc: str
    id: str | int | None
    method: str
    params: dict | None = None


@app.post("/mcp")
async def mcp_endpoint(req: Request, username: str = Depends(get_current_user_optional)):
    # Handle authentication
    if is_auth_enabled() and username is None:
        return JSONResponse(
            status_code=401,
            content={
                "jsonrpc": "2.0",
                "error": {
                    "code": ErrorCode.TRINO_AUTH_ERROR,
                    "message": "Authentication required"
                },
                "id": None
            },
            headers={"WWW-Authenticate": 'Basic realm="MCP API", Bearer'}
        )
    
    # Set the Trino user based on the authenticated user or default
    trino_user = username or "anonymous"
    
    # Parse JSON and handle JSON parsing errors
    try:
        payload = await req.json()
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in request: {str(e)}")
        return JSONResponse(
            status_code=400,
            content={
                "jsonrpc": "2.0",
                "error": ParseError(f"Invalid JSON: {str(e)}").to_dict(),
                "id": None
            }
        )
    
    # Validate against JSON-RPC envelope schema
    try:
        env = RPCEnvelope.model_validate(payload)
    except ValidationError as e:
        logger.error(f"Invalid RPC request format: {str(e)}")
        return JSONResponse(
            status_code=400,
            content={
                "jsonrpc": "2.0",
                "error": InvalidRequest(f"Invalid RPC request format: {str(e)}").to_dict(),
                "id": payload.get("id")
            }
        )
    
    # Check JSON-RPC version
    if env.jsonrpc != "2.0":
        logger.error(f"Unsupported JSON-RPC version: {env.jsonrpc}")
        return JSONResponse(
            status_code=400,
            content={
                "jsonrpc": "2.0",
                "error": InvalidRequest(f"Unsupported JSON-RPC version: {env.jsonrpc}").to_dict(),
                "id": env.id
            }
        )
    
    # Configure the Trino client with the user from authentication
    trino_client.get_client().user = trino_user
    
    # Dispatch the method call
    try:
        result = await dispatch_rpc(env.method, env.params or {})
        return {"jsonrpc": "2.0", "id": env.id, "result": result}
    except MCPError as exc:
        # This is already a proper MCPError, use it directly
        logger.error(f"RPC error in method {env.method}: {exc.message}")
        return {
            "jsonrpc": "2.0",
            "id": env.id,
            "error": exc.to_dict(),
        }
    except KeyError as exc:
        # Method not found
        logger.error(f"Method not found: {env.method}")
        return {
            "jsonrpc": "2.0",
            "id": env.id,
            "error": MethodNotFound(f"Method '{env.method}' not found").to_dict(),
        }
    except Exception as exc:
        # Unexpected error
        logger.error(f"Internal error in method {env.method}: {str(exc)}", exc_info=True)
        return {
            "jsonrpc": "2.0",
            "id": env.id,
            "error": InternalError(f"Internal server error: {str(exc)}").to_dict(),
        } 