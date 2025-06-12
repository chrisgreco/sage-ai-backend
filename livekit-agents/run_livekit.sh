#!/bin/bash

# Default parameters
LIVEKIT_URL="wss://sage-2kpu4z1y.livekit.cloud"
LIVEKIT_API_KEY="APIWQtUQUijqXVp"
LIVEKIT_API_SECRET="LDs7r35vqLLwR5vBPFg99hlPqE5y2EZ4sq7M90fAfEI"
DEBATE_TOPIC="The impact of artificial intelligence on society"
MODE="dev"

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
    --openai-api-key)
      OPENAI_API_KEY="$2"
      shift 2
      ;;
    --debate-topic)
      DEBATE_TOPIC="$2"
      shift 2
      ;;
    --mode)
      MODE="$2"
      shift 2
      ;;
    --help)
      echo "Usage: $0 [options]"
      echo "Options:"
      echo "  --livekit-url VALUE      LiveKit URL"
      echo "  --livekit-api-key VALUE  LiveKit API key"
      echo "  --livekit-api-secret VALUE LiveKit API secret"
      echo "  --openai-api-key VALUE   OpenAI API key"
      echo "  --debate-topic VALUE     Debate topic"
      echo "  --mode VALUE             Mode: dev, start, or console"
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
export DEBATE_TOPIC="$DEBATE_TOPIC"

# Display configuration
echo "Using configuration:"
echo "  LIVEKIT_URL: $LIVEKIT_URL"
echo "  LIVEKIT_API_KEY: $LIVEKIT_API_KEY"
echo "  LIVEKIT_API_SECRET: ${LIVEKIT_API_SECRET:0:5}..."
echo "  DEBATE_TOPIC: $DEBATE_TOPIC"
if [ -n "$OPENAI_API_KEY" ]; then
  echo "  OPENAI_API_KEY: ${OPENAI_API_KEY:0:5}..."
  export OPENAI_API_KEY="$OPENAI_API_KEY"
else
  echo "  OPENAI_API_KEY: not set (required for agent to work properly)"
fi

# Run the agent
echo "Starting LiveKit debate moderator agent in $MODE mode..."
python run_agent.py $MODE 