#!/usr/bin/env python3
"""
Diagnostic script to check import issues
"""

print("🔍 Starting import diagnosis...")

# Test basic imports
try:
    import os
    import sys
    print("✅ Standard library imports OK")
except ImportError as e:
    print(f"❌ Standard library import error: {e}")

# Test dotenv
try:
    from dotenv import load_dotenv
    print("✅ python-dotenv import OK")
except ImportError as e:
    print(f"❌ python-dotenv import error: {e}")

# Test LiveKit imports
try:
    from livekit import agents
    print("✅ livekit.agents import OK")
except ImportError as e:
    print(f"❌ livekit.agents import error: {e}")

try:
    from livekit.agents import Agent, AgentSession, JobContext, RunContext, WorkerOptions, cli, function_tool
    print("✅ LiveKit agent classes import OK")
except ImportError as e:
    print(f"❌ LiveKit agent classes import error: {e}")

try:
    from livekit.plugins import openai
    print("✅ LiveKit OpenAI plugin import OK")
except ImportError as e:
    print(f"❌ LiveKit OpenAI plugin import error: {e}")

try:
    from livekit.plugins.turn_detector.english import EnglishModel
    print("✅ LiveKit turn detector import OK")
except ImportError as e:
    print(f"❌ LiveKit turn detector import error: {e}")

# Check environment variables
print("\n🔧 Environment Variables:")
required_vars = ["LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "LIVEKIT_URL", "OPENAI_API_KEY"]
for var in required_vars:
    value = os.getenv(var)
    if value:
        print(f"✅ {var}: {'*' * 8}...{value[-4:]}")
    else:
        print(f"❌ {var}: NOT SET")

print("\n🎯 Diagnosis complete!")

# Try to import the actual agent file
try:
    print("\n📁 Testing multi_personality_agent.py import...")
    import multi_personality_agent
    print("✅ multi_personality_agent.py imports successfully")
except ImportError as e:
    print(f"❌ multi_personality_agent.py import error: {e}")
except Exception as e:
    print(f"❌ multi_personality_agent.py execution error: {e}") 