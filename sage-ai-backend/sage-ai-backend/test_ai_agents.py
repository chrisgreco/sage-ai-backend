#!/usr/bin/env python3

"""
Test script for the Sage AI Multi-Agent Debate System
=====================================================

This script helps verify that all components are working correctly.
"""

import os
import sys
import requests
import json
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
BASE_URL = "http://localhost:8000"
TEST_ROOM = "test-debate-room"
TEST_TOPIC = "The impact of artificial intelligence on society"
TEST_PARTICIPANT = "TestUser"

def test_health_check():
    """Test the health check endpoint"""
    print("🔍 Testing health check...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data['status']}")
            print(f"   - LiveKit available: {data['livekit_available']}")
            print(f"   - Active agents: {data['active_agents']}")
            print(f"   - AI keys configured: {data['ai_keys_configured']}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_debate_creation():
    """Test creating a debate room"""
    print("🎯 Testing debate creation...")
    try:
        payload = {
            "topic": TEST_TOPIC,
            "room_name": TEST_ROOM,
            "participant_name": TEST_PARTICIPANT
        }
        response = requests.post(f"{BASE_URL}/debate", json=payload)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Debate creation passed")
            print(f"   - Room: {data['room_name']}")
            print(f"   - Topic: {data['topic']}")
            print(f"   - AI agents ready: {data.get('ai_agents_ready', False)}")
            return True
        else:
            print(f"❌ Debate creation failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Debate creation error: {e}")
        return False

def test_ai_agents_launch():
    """Test launching AI agents"""
    print("🚀 Testing AI agents launch...")
    try:
        payload = {
            "room_name": TEST_ROOM,
            "topic": TEST_TOPIC,
            "start_agents": True
        }
        response = requests.post(f"{BASE_URL}/launch-ai-agents", json=payload)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ AI agents launch passed")
            print(f"   - Room: {data['room_name']}")
            print(f"   - Topic: {data['topic']}")
            print(f"   - Agents launched: {len(data.get('agents_launched', []))}")
            for agent in data.get('agents_launched', []):
                print(f"     • {agent}")
            return True
        else:
            print(f"❌ AI agents launch failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ AI agents launch error: {e}")
        return False

def test_ai_agents_status():
    """Test checking AI agent status"""
    print("📊 Testing AI agents status...")
    try:
        response = requests.get(f"{BASE_URL}/ai-agents/status")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ AI agents status check passed")
            print(f"   - Active rooms: {data['active_agent_rooms']}")
            for room in data.get('rooms', []):
                print(f"     • Room: {room['room_name']}, PID: {room['process_id']}")
            return True
        else:
            print(f"❌ AI agents status failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ AI agents status error: {e}")
        return False

def test_ai_agents_stop():
    """Test stopping AI agents"""
    print("🛑 Testing AI agents stop...")
    try:
        payload = {"room_name": TEST_ROOM}
        response = requests.post(f"{BASE_URL}/ai-agents/stop", json=payload)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ AI agents stop passed")
            print(f"   - Message: {data['message']}")
            return True
        else:
            print(f"❌ AI agents stop failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ AI agents stop error: {e}")
        return False

def check_environment():
    """Check if all required environment variables are set"""
    print("🔧 Checking environment configuration...")
    
    required_vars = [
        "LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET",
        "OPENAI_API_KEY", "DEEPGRAM_API_KEY", "CARTESIA_API_KEY"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("   Please check your .env file")
        return False
    else:
        print("✅ All required environment variables are set")
        return True

def main():
    """Run all tests"""
    print("🎭 Sage AI Multi-Agent Debate System Test Suite")
    print("=" * 50)
    
    # Check environment first
    if not check_environment():
        print("\n❌ Environment check failed. Please configure your API keys.")
        sys.exit(1)
    
    print(f"\n🎯 Testing against: {BASE_URL}")
    print(f"🏛️ Test room: {TEST_ROOM}")
    print(f"💭 Test topic: {TEST_TOPIC}")
    print()
    
    tests = [
        test_health_check,
        test_debate_creation,
        test_ai_agents_launch,
        test_ai_agents_status,
        test_ai_agents_stop
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
        time.sleep(1)  # Brief pause between tests
    
    print("=" * 50)
    print(f"🏆 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your AI debate system is ready!")
        print()
        print("Next steps:")
        print("1. Deploy to Render or your preferred platform")
        print("2. Configure your frontend to call /launch-ai-agents")
        print("3. Join a debate room and watch the AI agents participate!")
    else:
        print("⚠️  Some tests failed. Please check the error messages above.")
        sys.exit(1)

if __name__ == "__main__":
    main() 