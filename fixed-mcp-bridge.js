#!/usr/bin/env node
const net = require('net');
const http = require('http');

const MCP_SERVER_URL = 'http://localhost:8000/mcp';

// ---- handshake (stdout once) ----------------------------------------------
const server = net.createServer();       // create early so we know the port
server.listen(0, '127.0.0.1', () => {
  const { port } = server.address();
  // KEY FIX #1: Use 'tcp' protocol, not 'jsonrpc'
  console.log(JSON.stringify({ protocol: 'tcp', address: { host: '127.0.0.1', port } }));
  console.error(`MCP bridge running on port ${port}, forwarding to ${MCP_SERVER_URL}`);
});

// ---- per-connection handler -----------------------------------------------
server.on('connection', (socket) => {
  console.error('Client connected');
  
  // KEY FIX #2: Use proper line-delimited message parsing
  let partial = '';

  socket.on('data', (chunk) => {
    partial += chunk.toString();
    let nl;
    while ((nl = partial.indexOf('\n')) !== -1) {
      const raw = partial.slice(0, nl).trim();
      partial = partial.slice(nl + 1);
      if (!raw) continue; // skip blank lines
      
      try {
        const message = JSON.parse(raw);
        console.error(`Received message: ${JSON.stringify(message)}`);
        dispatch(message);
      } catch (err) {
        console.error(`Error parsing message: ${err.message}`);
      }
    }
  });

  async function dispatch(msg) {
    // Handle initialize message specially
    if (msg.method === 'initialize') {
      const response = {
        jsonrpc: '2.0',
        id: msg.id,
        result: {
          serverInfo: {
            name: 'trino-mcp-bridge',
            version: '1.0.0'
          },
          capabilities: {
            methodSupport: {
              list_catalogs: true,
              list_schemas: true,
              list_tables: true,
              get_table_schema: true,
              run_query_sync: true,
              run_query_async: true,
              get_query_status: true,
              get_query_results: true
            }
          }
        }
      };
      
      console.error(`Sending response: ${JSON.stringify(response)}`);
      // KEY FIX #3: Always include newline
      socket.write(JSON.stringify(response) + '\n');
      return;
    }
    
    const response = await forwardToMcp(msg);
    console.error(`Sending response: ${JSON.stringify(response)}`);
    socket.write(JSON.stringify(response) + '\n');
  }

  function forwardToMcp(message) {
    return new Promise((resolve) => {
      const req = http.request(
        MCP_SERVER_URL,
        { method: 'POST', headers: { 'Content-Type': 'application/json' } },
        (res) => {
          let body = '';
          res.on('data', (chunk) => { body += chunk; });
          res.on('end', () => {
            try {
              // KEY FIX #4: Ensure we parse and forward the response correctly
              resolve(JSON.parse(body));
            } catch (err) {
              console.error(`Error parsing response: ${err.message}`);
              resolve({
                jsonrpc: '2.0',
                id: message.id,
                error: {
                  code: -32603,
                  message: `Internal error: ${err.message}`
                }
              });
            }
          });
        }
      );
      
      req.on('error', (err) => {
        console.error(`Request error: ${err.message}`);
        resolve({
          jsonrpc: '2.0',
          id: message.id,
          error: {
            code: -32603,
            message: `Internal error: ${err.message}`
          }
        });
      });
      
      req.write(JSON.stringify(message));
      req.end();
    });
  }
  
  socket.on('error', (err) => {
    console.error(`Socket error: ${err.message}`);
  });
  
  socket.on('close', () => {
    console.error('Client disconnected');
  });
});

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