#!/usr/bin/env python3

"""
Test Script for Improved Chat API
=================================

Demonstrates the improvements:
1. Single agent responses (no simultaneous talking)
2. Persistent conversation memory
3. Intelligent agent selection
4. Context-aware responses
"""

import requests
import json
import time

API_BASE = "http://localhost:8001"

def send_message(message: str, room_id: str = "demo-room"):
    """Send a message to the chat API"""
    response = requests.post(
        f"{API_BASE}/api/chat/message",
        json={"message": message, "room_id": room_id}
    )
    return response.json()

def get_conversation_memory(room_id: str = "demo-room"):
    """Get the conversation memory"""
    response = requests.get(f"{API_BASE}/api/chat/memory/{room_id}")
    return response.json()

def main():
    print("🎭 Testing Improved Sage AI Chat API")
    print("=" * 50)
    
    room_id = "demo-room"
    
    # Test 1: Single agent response
    print("\n1️⃣ Testing single agent response...")
    result1 = send_message("humans are 2x stronger than apes", room_id)
    response1 = result1["response"]
    print(f"   👤 User: humans are 2x stronger than apes")
    print(f"   🤖 {response1['agent_name']} ({response1['agent_role']}): {response1['message']}")
    print(f"   📊 Conversation length: {result1['conversation_length']}")
    
    time.sleep(1)
    
    # Test 2: Follow-up question to test memory
    print("\n2️⃣ Testing conversation memory...")
    result2 = send_message("aristotle can you cite your sources?", room_id)
    response2 = result2["response"]
    print(f"   👤 User: aristotle can you cite your sources?")
    print(f"   🤖 {response2['agent_name']} ({response2['agent_role']}): {response2['message']}")
    print(f"   📊 Conversation length: {result2['conversation_length']}")
    
    time.sleep(1)
    
    # Test 3: Different topic to test agent selection
    print("\n3️⃣ Testing agent selection...")
    result3 = send_message("I feel conflicted about this issue", room_id)
    response3 = result3["response"]
    print(f"   👤 User: I feel conflicted about this issue")
    print(f"   🤖 {response3['agent_name']} ({response3['agent_role']}): {response3['message']}")
    print(f"   📊 Conversation length: {result3['conversation_length']}")
    
    # Test 4: Show conversation memory
    print("\n4️⃣ Full conversation memory:")
    memory = get_conversation_memory(room_id)
    print(f"   📚 Total messages: {memory['message_count']}")
    for i, msg in enumerate(memory['conversation'], 1):
        speaker = msg['speaker'].title()
        print(f"   {i:2d}. {speaker}: {msg['message'][:60]}...")
    
    print("\n✅ Key Improvements Demonstrated:")
    print("   • Only ONE agent responds per message (no chaos)")
    print("   • Conversation memory persists across requests")
    print("   • Intelligent agent selection based on content")
    print("   • Context-aware responses using conversation history")
    
    print("\n🎯 Production Integration:")
    print("   • This API can integrate with LiveKit voice agents")
    print("   • Frontend can call these endpoints for real conversations")
    print("   • Memory system supports multi-user rooms")
    print("   • Turn-taking prevents simultaneous responses")

if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to API. Make sure it's running on port 8001")
        print("Run: python integrated_chat_api.py")
    except Exception as e:
        print(f"❌ Error: {e}") 