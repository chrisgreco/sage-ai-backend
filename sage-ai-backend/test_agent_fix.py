#!/usr/bin/env python3

"""
Quick Agent Connection Fix Test
=============================

Based on the network logs showing 200 responses but no actual agent connections,
this script tests and fixes the agent launching process.
"""

import os
import sys
import subprocess
import time
import requests
import json
from dotenv import load_dotenv

# Load environment
load_dotenv()

def test_agent_launch_endpoint():
    """Test the /launch-ai-agents endpoint directly"""
    print("🧪 Testing /launch-ai-agents endpoint...")
    
    # Test with your production URL
    url = "https://sage-ai-backend-l0en.onrender.com/launch-ai-agents"
    
    payload = {
        "topic": "Test Connection Issue",
        "room_name": "debug-test-room-" + str(int(time.time()))
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("✅ Endpoint returns 200 - but are agents actually connecting?")
            return response.json()
        else:
            print(f"❌ Endpoint failed with status {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return None

def test_agent_status_endpoint():
    """Check the status endpoint for detailed information"""
    print("\n🔍 Checking agent status...")
    
    url = "https://sage-ai-backend-l0en.onrender.com/ai-agents/status"
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Active Rooms: {data.get('active_rooms', 0)}")
            
            if 'rooms' in data:
                for room_name, room_info in data['rooms'].items():
                    print(f"Room: {room_name}")
                    print(f"  - Running: {room_info.get('running', False)}")
                    print(f"  - Topic: {room_info.get('topic', 'Unknown')}")
                    print(f"  - Started: {room_info.get('started_at', 'Unknown')}")
            
            return data
        else:
            print(f"❌ Status endpoint failed: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Status check failed: {e}")
        return None

def check_local_agent():
    """Test running the agent locally to see what happens"""
    print("\n🔧 Testing local agent startup...")
    
    # Check if we have the required environment variables
    required_vars = ["LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "OPENAI_API_KEY"]
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        print(f"❌ Missing environment variables: {missing}")
        print("Cannot test local agent without proper credentials")
        return False
    
    # Try to run the agent locally
    try:
        env = os.environ.copy()
        env.update({
            "ROOM_NAME": "local-debug-test",
            "DEBATE_TOPIC": "Local Debug Test Topic"
        })
        
        print("Starting agent process locally...")
        process = subprocess.Popen([
            sys.executable, "multi_personality_agent.py"
        ], 
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
        )
        
        print(f"Process started with PID: {process.pid}")
        
        # Wait a few seconds to see what happens
        time.sleep(5)
        
        if process.poll() is None:
            print("✅ Process is still running")
            process.terminate()
            process.wait()
            return True
        else:
            stdout, stderr = process.communicate()
            print(f"❌ Process terminated with code: {process.returncode}")
            print(f"STDOUT: {stdout[:500]}")
            print(f"STDERR: {stderr[:500]}")
            return False
            
    except Exception as e:
        print(f"❌ Local agent test failed: {e}")
        return False

def identify_issue():
    """Analyze the results and identify the likely issue"""
    print("\n🔍 ISSUE ANALYSIS")
    print("=" * 40)
    
    # Test the endpoints
    launch_result = test_agent_launch_endpoint()
    status_result = test_agent_status_endpoint()
    
    # Analyze results
    if launch_result and launch_result.get('status') == 'success':
        print("✅ Launch endpoint works and returns success")
        
        if status_result and status_result.get('active_rooms', 0) > 0:
            print("✅ Status shows active rooms")
            
            # Check if processes are actually running
            rooms = status_result.get('rooms', {})
            running_count = sum(1 for room in rooms.values() if room.get('running', False))
            
            if running_count > 0:
                print(f"✅ {running_count} agent processes are running")
                print("\n🤔 LIKELY ISSUE: Agents start but don't connect to LiveKit room")
                print("SOLUTIONS:")
                print("1. Check LiveKit credentials in production environment")
                print("2. Verify LiveKit URL is accessible from Render")
                print("3. Check agent logs for connection errors")
                print("4. Verify room name generation is consistent")
            else:
                print("❌ No agent processes are actually running")
                print("\n🤔 LIKELY ISSUE: Subprocess launch fails silently")
                print("SOLUTIONS:")
                print("1. Check if multi_personality_agent.py exists on Render")
                print("2. Verify Python environment and dependencies")
                print("3. Check file permissions")
        else:
            print("❌ No active rooms found")
            print("\n🤔 LIKELY ISSUE: Agent processes terminate immediately")
            print("SOLUTIONS:")
            print("1. Check agent startup errors in Render logs")
            print("2. Verify all required environment variables are set")
            print("3. Check for missing dependencies")
    else:
        print("❌ Launch endpoint is failing")
        print("\n🤔 LIKELY ISSUE: Backend configuration problem")
        print("SOLUTIONS:")
        print("1. Check Render deployment logs")
        print("2. Verify environment variables are set correctly")
        print("3. Check if the endpoint code is deployed properly")

if __name__ == "__main__":
    print("🔧 SAGE AI AGENT CONNECTION DIAGNOSTIC")
    print("=" * 45)
    print("Based on network logs showing 200 responses but no agent connections\n")
    
    identify_issue()
    
    print(f"\n💡 NEXT STEPS:")
    print("1. Check Render logs for detailed error messages")
    print("2. Run the debug script on the production environment")
    print("3. Verify LiveKit credentials and connectivity")
    print("4. Add more detailed logging to the agent startup process") 