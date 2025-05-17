#!/usr/bin/env node

const http = require('http');
const https = require('https');
const net = require('net');

// Get the target URL from command line arguments
const targetUrl = process.argv[2];
if (!targetUrl) {
  console.error('Please provide a target URL as an argument');
  process.exit(1);
}

// Parse the target URL
const url = new URL(targetUrl);
const isHttps = url.protocol === 'https:';

// Create a server that handles JSON-RPC 2.0
const server = net.createServer((socket) => {
  console.error(`Client connected`);
  
  const client = isHttps ? https : http;
  
  let bufferedData = '';
  
  // Handle data from Claude Desktop
  socket.on('data', (data) => {
    const stringData = data.toString();
    bufferedData += stringData;
    
    try {
      // Try to parse as JSON (could be partial)
      const message = JSON.parse(bufferedData);
      bufferedData = '';
      console.error(`Received message: ${JSON.stringify(message)}`);
      
      // Forward to the target URL
      const options = {
        hostname: url.hostname,
        port: url.port || (isHttps ? 443 : 80),
        path: url.pathname + (url.search || ''),
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      };
      
      const req = client.request(options, (res) => {
        let responseData = '';
        
        res.on('data', (chunk) => {
          responseData += chunk;
        });
        
        res.on('end', () => {
          try {
            console.error(`Server response: ${responseData}`);
            // Send response back to Claude Desktop
            socket.write(responseData);
          } catch (e) {
            console.error(`Error processing response: ${e.message}`);
            // Format error as JSON-RPC 2.0 error
            const errorResponse = {
              jsonrpc: "2.0",
              error: {
                code: -32603,
                message: `Internal error: ${e.message}`
              },
              id: message.id || null
            };
            socket.write(JSON.stringify(errorResponse));
          }
        });
      });
      
      req.on('error', (error) => {
        console.error(`Request error: ${error.message}`);
        // Format error as JSON-RPC 2.0 error
        const errorResponse = {
          jsonrpc: "2.0",
          error: {
            code: -32603,
            message: `Internal error: ${error.message}`
          },
          id: message.id || null
        };
        socket.write(JSON.stringify(errorResponse));
      });
      
      // Send the message to the server
      req.write(JSON.stringify(message));
      req.end();
    } catch (e) {
      // Not valid JSON yet, likely partial message
      // Just continue buffering
    }
  });
  
  socket.on('error', (error) => {
    console.error(`Socket error: ${error.message}`);
  });
  
  socket.on('close', () => {
    console.error('Client disconnected');
  });
});

// Start the server on a random port
server.listen(0, () => {
  const address = server.address();
  console.log(JSON.stringify({
    protocol: "jsonrpc",
    address: { port: address.port }
  }));
  console.error(`Proxy server running on port ${address.port}, forwarding to ${targetUrl}`);
});

// Handle server errors
server.on('error', (error) => {
  console.error(`Server error: ${error.message}`);
  process.exit(1);
});

// Log unhandled errors
process.on('uncaughtException', (error) => {
  console.error('Uncaught exception:', error);
});

// Gracefully close when the parent process disconnects
process.on('disconnect', () => {
  server.close();
  process.exit(0);
}); 