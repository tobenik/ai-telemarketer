#!/bin/bash

echo "Starting Twilio Voice Application..."

# Function to clean up processes on exit
cleanup() {
    echo -e "\nShutting down services..."
    if [ ! -z "$NGROK_PID" ]; then
        echo "Stopping ngrok (PID: $NGROK_PID)..."
        kill $NGROK_PID 2>/dev/null || true
    fi
    echo "Application stopped"
    exit 0
}

# Set up trap to catch Ctrl+C and other termination signals
trap cleanup SIGINT SIGTERM EXIT

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "Error: ngrok is not installed. Please install it first."
    exit 1
fi

# Kill any existing ngrok processes
pkill -f ngrok || true
echo "Starting ngrok..."
ngrok http 5001 > /dev/null 2>&1 &
NGROK_PID=$!

# Wait for ngrok to start
echo "Waiting for ngrok to initialize..."
sleep 3

# Get the ngrok URL
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | grep -o 'https://[^"]*\.ngrok-free\.app' | head -1)

if [ -z "$NGROK_URL" ]; then
    echo "Error: Could not get ngrok URL. Make sure ngrok is running properly."
    cleanup
fi

echo "ngrok URL: $NGROK_URL"

# Update .env file with ngrok URL
if grep -q "NGROK_URL=" .env; then
    # Update existing NGROK_URL
    sed -i '' "s|NGROK_URL=.*|NGROK_URL=$NGROK_URL|g" .env
else
    # Add NGROK_URL if it doesn't exist
    echo "NGROK_URL=$NGROK_URL" >> .env
fi

echo "Starting Flask server..."
echo "Application is running! Press Ctrl+C to stop all services."
echo "- ngrok URL: $NGROK_URL"
echo "- To make an outbound call, run in another terminal: python outbound_call.py"

# Run server in foreground
python server.py