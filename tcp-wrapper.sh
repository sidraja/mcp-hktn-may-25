#!/bin/bash

# This script reads from stdin, forwards to port 50000, and relays responses back
# It uses socat if available, otherwise falls back to nc

if command -v socat > /dev/null 2>&1; then
    echo "Using socat to connect to port 50000" >&2
    # socat maintains a bidirectional connection
    socat STDIO TCP:localhost:50000
elif command -v nc > /dev/null 2>&1; then
    echo "Using netcat to connect to port 50000" >&2
    # Use nc -N to close the socket after EOF on stdin (which shouldn't happen in this case)
    # but still listen for responses from the server
    if nc -h 2>&1 | grep -q '\-N'; then
        # GNU netcat supports -N option
        nc -N localhost 50000
    else
        # BSD netcat (macOS) - keep the connection open
        exec 3<>/dev/tcp/localhost/50000
        cat <&3 &
        cat >&3
    fi
else
    echo "Error: Neither socat nor nc (netcat) is available" >&2
    exit 1
fi 