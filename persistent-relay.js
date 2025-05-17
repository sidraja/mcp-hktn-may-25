#!/usr/bin/env node

const net = require('net');

// The port to connect to
const PORT = 50000;
const HOST = 'localhost';

// Connect to the TCP server
const socket = net.createConnection({ port: PORT, host: HOST }, () => {
  console.error(`Connected to TCP server on ${HOST}:${PORT}`);
});

// Forward data from process stdin to the socket
process.stdin.pipe(socket);

// Forward data from the socket to process stdout
socket.pipe(process.stdout);

// Error handling
socket.on('error', (err) => {
  console.error(`Socket error: ${err.message}`);
  process.exit(1);
});

// Handle process exit
process.on('SIGINT', () => {
  console.error('SIGINT received, shutting down');
  socket.end();
  process.exit(0);
});

process.on('SIGTERM', () => {
  console.error('SIGTERM received, shutting down');
  socket.end();
  process.exit(0);
}); 