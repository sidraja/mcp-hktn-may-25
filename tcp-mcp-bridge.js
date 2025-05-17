#!/usr/bin/env node

const net = require('net');
const http = require('http');

// The port to listen on - this needs to be known in advance
const LISTEN_PORT = 50000;

// The MCP server URL
const MCP_SERVER_URL = 'http://localhost:8000/mcp';

// Create a server that listens for JSON-RPC messages
const server = net.createServer((socket) => {
  console.error('Client connected');
  
  let buffer = Buffer.alloc(0);
  
  socket.on('data', (data) => {
    buffer = Buffer.concat([buffer, data]);
    
    try {
      // Try to parse the message
      const message = JSON.parse(buffer.toString());
      buffer = Buffer.alloc(0); // Clear buffer after successful parse
      
      console.error(`Received message: ${JSON.stringify(message)}`);
      
      // Handle initialize message specially
      if (message.method === 'initialize') {
        const response = {
          jsonrpc: '2.0',
          id: message.id,
          result: {
            serverInfo: {
              name: 'trino-mcp-bridge',
              version: '1.0.0'
            },
            capabilities: {
              methodSupport: {
                "list_catalogs": true,
                "run_query_sync": true,
                "run_query_async": true,
                "get_query_status": true,
                "get_query_results": true,
                "list_schemas": true,
                "list_tables": true,
                "get_table_schema": true
              }
            }
          }
        };
        
        console.error(`Sending response: ${JSON.stringify(response)}`);
        socket.write(JSON.stringify(response) + '\n');
        return;
      }
      
      // For all other messages, forward to the MCP server
      const options = {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      };
      
      const req = http.request(MCP_SERVER_URL, options, (res) => {
        let responseData = '';
        
        res.on('data', (chunk) => {
          responseData += chunk;
        });
        
        res.on('end', () => {
          try {
            const response = JSON.parse(responseData);
            console.error(`Sending response: ${JSON.stringify(response)}`);
            socket.write(JSON.stringify(response) + '\n');
          } catch (err) {
            console.error(`Error parsing response: ${err.message}`);
            const errorResponse = {
              jsonrpc: '2.0',
              id: message.id,
              error: {
                code: -32603,
                message: `Internal error: ${err.message}`
              }
            };
            socket.write(JSON.stringify(errorResponse) + '\n');
          }
        });
      });
      
      req.on('error', (err) => {
        console.error(`Request error: ${err.message}`);
        const errorResponse = {
          jsonrpc: '2.0',
          id: message.id,
          error: {
            code: -32603,
            message: `Internal error: ${err.message}`
          }
        };
        socket.write(JSON.stringify(errorResponse) + '\n');
      });
      
      req.write(JSON.stringify(message));
      req.end();
    } catch (err) {
      // If we can't parse the message, it might be incomplete - just wait for more data
      if (!(err instanceof SyntaxError)) {
        console.error(`Error: ${err.message}`);
      }
    }
  });
  
  socket.on('error', (err) => {
    console.error(`Socket error: ${err.message}`);
  });
  
  socket.on('close', () => {
    console.error('Client disconnected');
  });
});

// Listen on a fixed port
server.listen(LISTEN_PORT, () => {
  console.error(`Server listening on port ${LISTEN_PORT}`);
  
  // Print the protocol/address message in a special format just for logging
  console.error('Protocol: jsonrpc');
  console.error(`Address: { port: ${LISTEN_PORT} }`);
}); 