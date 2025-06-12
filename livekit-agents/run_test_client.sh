#!/bin/bash

# Default parameters
LIVEKIT_URL="wss://sage-2kpu4z1y.livekit.cloud"
LIVEKIT_API_KEY="APIWQtUQUijqXVp"
LIVEKIT_API_SECRET="LDs7r35vqLLwR5vBPFg99hlPqE5y2EZ4sq7M90fAfEI"
ROOM_NAME="test-debate-room"
IDENTITY="test-user"

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --livekit-url)
      LIVEKIT_URL="$2"
      shift 2
      ;;
    --livekit-api-key)
      LIVEKIT_API_KEY="$2"
      shift 2
      ;;
    --livekit-api-secret)
      LIVEKIT_API_SECRET="$2"
      shift 2
      ;;
    --room-name)
      ROOM_NAME="$2"
      shift 2
      ;;
    --identity)
      IDENTITY="$2"
      shift 2
      ;;
    --help)
      echo "Usage: $0 [options]"
      echo "Options:"
      echo "  --livekit-url VALUE      LiveKit URL"
      echo "  --livekit-api-key VALUE  LiveKit API key"
      echo "  --livekit-api-secret VALUE LiveKit API secret"
      echo "  --room-name VALUE        Room name"
      echo "  --identity VALUE         User identity"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Export environment variables
export LIVEKIT_URL="$LIVEKIT_URL"
export LIVEKIT_API_KEY="$LIVEKIT_API_KEY"
export LIVEKIT_API_SECRET="$LIVEKIT_API_SECRET"
export ROOM_NAME="$ROOM_NAME"
export IDENTITY="$IDENTITY"

# Display configuration
echo "Using configuration:"
echo "  LIVEKIT_URL: $LIVEKIT_URL"
echo "  LIVEKIT_API_KEY: $LIVEKIT_API_KEY"
echo "  LIVEKIT_API_SECRET: ${LIVEKIT_API_SECRET:0:5}..."
echo "  ROOM_NAME: $ROOM_NAME"
echo "  IDENTITY: $IDENTITY"

# Run the test client
echo "Starting LiveKit test client..."
python test_client.py 