from pathlib import Path
import os
import logging
import json
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, ValidationError
from .rpc import dispatch_rpc
from . import trino_client
from .errors import (
    MCPError, ParseError, InvalidRequest, MethodNotFound,
    InvalidParams, InternalError, ErrorCode
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


class RPCEnvelope(BaseModel):
    jsonrpc: str
    id: str | int | None
    method: str
    params: dict | None = None


@app.post("/mcp")
async def mcp_endpoint(req: Request):
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