#!/bin/bash
echo "Starting Sage AI Multi-Personality Agent..."
echo "Current directory: $(pwd)"
echo "Files in current directory:"
ls -la
echo "Looking for multi_personality_agent.py..."
if [ -f "multi_personality_agent.py" ]; then
    echo "Found multi_personality_agent.py, starting agent..."
    python multi_personality_agent.py start
else
    echo "multi_personality_agent.py not found!"
    exit 1
fi 