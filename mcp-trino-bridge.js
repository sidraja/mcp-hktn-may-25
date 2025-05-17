#!/usr/bin/env node

const net = require('net');
const http = require('http');

// MCP server URL - this is where your FastAPI server is running
const MCP_SERVER_URL = 'http://localhost:8000/mcp';

// Create a JSON-RPC client that connects to the MCP server
const server = net.createServer((socket) => {
  console.error('Client connected');
  
  let buffer = Buffer.alloc(0);
  
  // Handle data from the client (Claude Desktop)
  socket.on('data', async (data) => {
    buffer = Buffer.concat([buffer, data]);
    
    try {
      // Try to parse the message as JSON
      const message = JSON.parse(buffer.toString());
      buffer = Buffer.alloc(0); // Clear the buffer
      
      console.error(`Received message from client: ${JSON.stringify(message)}`);
      
      // Special handling for initialize method
      if (message.method === 'initialize') {
        console.error('Handling initialize method');
        // Directly respond to initialize without forwarding to the server
        const response = {
          jsonrpc: '2.0',
          id: message.id,
          result: {
            capabilities: {
              // Add capabilities here that match what the Trino MCP server supports
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
            },
            serverInfo: {
              name: "trino-mcp-bridge",
              version: "1.0.0"
            }
          }
        };
        
        console.error(`Sending initialize response: ${JSON.stringify(response)}`);
        socket.write(JSON.stringify(response) + '\n');
        return;
      }
      
      // All other messages forwarded to the MCP server
      const response = await sendToMcpServer(message);
      
      console.error(`Sending response to client: ${JSON.stringify(response)}`);
      socket.write(JSON.stringify(response) + '\n');
    } catch (err) {
      // If we can't parse the message, it might be incomplete
      // Just wait for more data
      if (!(err instanceof SyntaxError)) {
        console.error(`Error processing message: ${err.message}`);
        if (err.stack) {
          console.error(err.stack);
        }
        
        // Try to send an error response if we have a message ID
        try {
          const message = JSON.parse(buffer.toString());
          const errorResponse = {
            jsonrpc: '2.0',
            id: message.id || null,
            error: {
              code: -32603,
              message: `Internal error: ${err.message}`
            }
          };
          socket.write(JSON.stringify(errorResponse) + '\n');
        } catch (e) {
          // Can't get message ID, just log
          console.error('Could not send error response: ' + e.message);
        }
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

async function sendToMcpServer(message) {
  return new Promise((resolve, reject) => {
    // Prepare the request
    const options = {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    };
    
    const req = http.request(MCP_SERVER_URL, options, (res) => {
      let data = '';
      
      res.on('data', (chunk) => {
        data += chunk;
      });
      
      res.on('end', () => {
        try {
          const response = JSON.parse(data);
          resolve(response);
        } catch (err) {
          console.error(`Error parsing MCP server response: ${err.message}`);
          // Return an error response in JSON-RPC format
          resolve({
            jsonrpc: '2.0',
            id: message.id || null,
            error: {
              code: -32603,
              message: `Internal error: Error parsing server response: ${err.message}`
            }
          });
        }
      });
    });
    
    req.on('error', (err) => {
      console.error(`Error sending to MCP server: ${err.message}`);
      
      // Return an error response in JSON-RPC format
      resolve({
        jsonrpc: '2.0',
        id: message.id || null,
        error: {
          code: -32603,
          message: `Internal error: ${err.message}`
        }
      });
    });
    
    // Send the request
    req.write(JSON.stringify(message));
    req.end();
  });
}

// Handle process signals
process.on('SIGINT', () => {
  console.error('SIGINT received, shutting down');
  server.close();
  process.exit(0);
});

process.on('SIGTERM', () => {
  console.error('SIGTERM received, shutting down');
  server.close();
  process.exit(0);
});

// Start the server on a random port
const listenPort = process.env.PORT || 0;
server.listen(listenPort, () => {
  const address = server.address();
  
  // Just log the port, but don't output the protocol/address message that Claude Desktop misinterpreted
  console.error(`MCP bridge running on port ${address.port}, forwarding to ${MCP_SERVER_URL}`);
  
  // For Claude Desktop to connect
  console.log(JSON.stringify({
    protocol: 'jsonrpc',
    address: { port: address.port }
  }));
}); 