#!/bin/bash

# Set the PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$(pwd)/..:$(pwd)/../src

# Set the working directory to the script's location
cd "$(dirname "$0")"

kill_existing_processes() {
    echo "Checking for existing Python processes..."
    ps ax | grep "peerjs-py-server.py\|py-client/client.py\|js-client" | grep -v grep | awk '{print $1}' | xargs -r kill
    sleep 2
}

kill_existing_processes

# Start the Python PeerJS server, 
# python3 peerjs-py-server.py --port 5000 &
# SERVER_PID=$!

# Wait for the server to start
# sleep 5

# Start the Python client start with compatibility.test
# python3 py-client/client.py > compatibility.test.log &
# PY_CLIENT_PID=$!

# Wait for the Python client to initialize
# sleep 5

# Start a simple HTTP server for the JavaScript client
python3 -m http.server 8000 --directory js-client &
HTTP_SERVER_PID=$!

# Wait for the HTTP server to start
sleep 5

echo "Current working directory: $(pwd)"

# Check if npx command exists
if ! command -v npx &> /dev/null
then
    echo "Error: npx command not found. Please install Node.js and npm. and install packages.  npm install "
    exit 1
fi

echo "Current working directory: $(pwd)"
TS_NODE_PROJECT=./tsconfig.json npx wdio run ./wdio.local.conf.ts
# Run the WDIO tests
# npx wdio run --autoCompileOpts.tsNodeOpts.project=./tsconfig.json ./wdio.local.conf.ts

# Kill the Python server, Python client, and HTTP server
# kill $SERVER_PID
# kill $PY_CLIENT_PID
kill $HTTP_SERVER_PID

echo "E2E tests completed."
