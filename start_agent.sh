#!/bin/bash

# Sage AI Agent Startup Script
# This script helps debug agent startup issues

echo "🚀 Starting Sage AI Agent..."
echo "Environment Check:"
echo "  LIVEKIT_URL: ${LIVEKIT_URL:-'NOT SET'}"
echo "  LIVEKIT_TOKEN: ${LIVEKIT_TOKEN:+'SET'}"
echo "  DEBATE_TOPIC: ${DEBATE_TOPIC:-'NOT SET'}"
echo "  MODERATOR_PERSONA: ${MODERATOR_PERSONA:-'NOT SET'}"
echo "  ROOM_NAME: ${ROOM_NAME:-'NOT SET'}"
echo "  OPENAI_API_KEY: ${OPENAI_API_KEY:+'SET'}"
echo "  PERPLEXITY_API_KEY: ${PERPLEXITY_API_KEY:+'SET'}"

# Check if required environment variables are set
if [ -z "$LIVEKIT_URL" ] || [ -z "$LIVEKIT_TOKEN" ] || [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ Missing required environment variables"
    exit 1
fi

echo "✅ Environment variables OK"

# Pre-download models to avoid startup delays
echo "📦 Pre-downloading models..."
python debate_moderator_agent.py download-files

# Start the agent
echo "🎯 Starting agent process..."
exec python debate_moderator_agent.py 