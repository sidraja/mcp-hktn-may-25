#!/bin/bash
# Script to test MCP client with Trino in Docker Compose

set -e

echo "=== Testing Trino MCP Client with Docker Compose ==="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
  echo "Error: Docker is not running or not installed"
  exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
  echo "Error: Docker Compose is not installed"
  exit 1
fi

# Start the Docker Compose environment
echo "Starting Docker Compose environment..."
docker-compose up -d

# Wait for all services to be ready
echo "Waiting for services to start up (this may take a few minutes)..."

echo "Waiting for Trino to be ready..."
for i in {1..30}; do
  if curl -s http://localhost:8080/v1/info > /dev/null 2>&1; then
    echo "Trino is up and running!"
    break
  fi
  echo -n "."
  sleep 2
  if [ $i -eq 30 ]; then
    echo "Failed to start Trino within the timeout period"
    docker-compose down
    exit 1
  fi
done

echo "Waiting for MCP server to be ready..."
for i in {1..15}; do
  if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "MCP server is up and running!"
    break
  fi
  echo -n "."
  sleep 2
  if [ $i -eq 15 ]; then
    echo "Failed to start MCP server within the timeout period"
    docker-compose down
    exit 1
  fi
done

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

echo "=== Test completed ==="
echo "To stop all containers, run: docker-compose down"
echo "To view logs, run: docker-compose logs -f [service_name]" 