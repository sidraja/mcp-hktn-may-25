#!/bin/bash
# Script to test MCP client with Trino in Docker

set -e

echo "=== Testing Trino MCP Client with Docker ==="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
  echo "Error: Docker is not running or not installed"
  exit 1
fi

# Check if Trino container is already running
if docker ps | grep -q trinodb/trino; then
  echo "Trino container is already running"
else
  echo "Starting Trino container..."
  docker pull trinodb/trino:latest
  docker run -d --name trino-test -p 8080:8080 trinodb/trino:latest
  
  echo "Waiting for Trino to start up (this may take a minute)..."
  # Wait for Trino to be ready
  for i in {1..30}; do
    if curl -s http://localhost:8080/v1/info > /dev/null 2>&1; then
      echo "Trino is up and running!"
      break
    fi
    echo -n "."
    sleep 2
    if [ $i -eq 30 ]; then
      echo "Failed to start Trino within the timeout period"
      docker stop trino-test
      docker rm trino-test
      exit 1
    fi
  done
fi

echo "=== Setting up Python environment ==="
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python -m venv .venv
fi

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt

echo "=== Starting MCP service ==="
echo "Setting environment variables..."
export TRINO_HOST=localhost
export TRINO_PORT=8080
export TRINO_USER=test-user

echo "Starting MCP service in the background..."
uvicorn app.main:app --reload &
MCP_PID=$!

# Wait for service to start
sleep 3

echo "=== Testing API endpoints ==="
echo "1. Testing health endpoint..."
curl -s http://localhost:8000/health | jq .

echo "2. Testing manifest endpoint..."
curl -s http://localhost:8000/.well-known/mcp/manifest.json | jq .

echo "3. Testing list_catalogs method..."
curl -s -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "list_catalogs", "params": {}}' | jq .

echo "4. Testing run_query_sync method with SELECT 1..."
curl -s -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 2, "method": "run_query_sync", "params": {"sql": "SELECT 1"}}' | jq .

# Clean up
kill $MCP_PID

echo "=== Test completed ==="
echo "To stop the Trino container, run: docker stop trino-test && docker rm trino-test" 