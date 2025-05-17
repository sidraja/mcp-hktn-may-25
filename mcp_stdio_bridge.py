#!/usr/bin/env python3
"""Simple MCP stdio bridge for Claude Desktop.

This program:
1. Prints a single handshake line   {"protocol": "jsonrpc"}
2. Reads newline-delimited JSON-RPC envelopes from STDIN.
3. For the "initialize" method it responds locally with server info / capabilities.
4. For every other request it POSTs the envelope to the FastAPI MCP server
   running at http://localhost:8000/mcp and writes back the response.

All logs are written to STDERR; every line written to STDOUT is a valid
JSON document terminated by a single newline so Claude can parse it
reliably.
"""

import sys
import json
import logging
import requests
from typing import Dict, Any

MCP_SERVER_URL = "http://localhost:8000/mcp"

logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(message)s")
logger = logging.getLogger("mcp-stdio-bridge")

# -------------------------------------------------------------
# helper for sending error back
# -------------------------------------------------------------

def _error(id_: Any, code: int, msg: str) -> None:
    resp = {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": msg}}
    print(json.dumps(resp), flush=True)

# -------------------------------------------------------------
# read ‑ process ‑ write loop (newline-delimited JSON-RPC)
# -------------------------------------------------------------

for raw_line in sys.stdin:
    line = raw_line.strip()
    if not line:
        continue  # skip blanks / keep-alive newlines

    try:
        envelope: Dict[str, Any] = json.loads(line)
    except json.JSONDecodeError as exc:
        logger.error(f"Invalid JSON from Claude: {exc}\n> {line}")
        _error(None, -32700, "Parse error: invalid JSON")
        continue

    logger.info(f"← {envelope}")
    msg_id = envelope.get("id")
    method = envelope.get("method")

    # ---------------------------------------------------------
    # handle initialize locally
    # ---------------------------------------------------------
    if method == "initialize":
        init_resp = {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "serverInfo": {"name": "trino-mcp-bridge", "version": "1.0.0"},
                "capabilities": {
                    "methodSupport": {
                        "list_catalogs": True,
                        "list_schemas": True,
                        "list_tables": True,
                        "get_table_schema": True,
                        "run_query_sync": True,
                        "run_query_async": True,
                        "get_query_status": True,
                        "get_query_results": True,
                    }
                },
            },
        }
        print(json.dumps(init_resp), flush=True)
        # Send required initialized notification so client knows server is ready
        notify = {"jsonrpc": "2.0", "method": "initialized"}
        print(json.dumps(notify), flush=True)
        logger.info("→ initialize response + initialized notification sent")
        continue

    # ---------------------------------------------------------
    # forward everything else to FastAPI MCP server
    # ---------------------------------------------------------
    try:
        resp = requests.post(MCP_SERVER_URL, json=envelope, timeout=60)
    except requests.RequestException as exc:
        logger.error(f"Error contacting MCP server: {exc}")
        _error(msg_id, -32000, f"Transport error: {exc}")
        continue

    try:
        data = resp.json()
    except ValueError as exc:
        logger.error(f"MCP server returned non-JSON: {exc}\n{resp.text[:500]}")
        _error(msg_id, -32603, "Invalid JSON from MCP server")
        continue

    # Ensure newline terminated
    print(json.dumps(data), flush=True)
    logger.info(f"→ response forwarded (id={msg_id})") 