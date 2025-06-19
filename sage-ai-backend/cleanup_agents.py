import requests
import json
import time

def cleanup_all_agents():
    """Clean up all active agents and their sessions"""
    
    base_url = "https://sage-ai-backend-l0en.onrender.com"
    
    print("🧹 Starting agent cleanup process...")
    
    # Step 1: Get current agent status
    print("\n1️⃣ Checking current agent status...")
    status_response = requests.get(f"{base_url}/ai-agents/status")
    
    if status_response.status_code != 200:
        print(f"❌ Failed to get agent status: {status_response.status_code}")
        return
    
    status_data = status_response.json()
    rooms = status_data.get('rooms', {})
    
    print(f"📊 Found {len(rooms)} active rooms with agents")
    
    # Step 2: Stop agents for each room
    for room_name, room_data in rooms.items():
        print(f"\n🛑 Stopping agents for room: {room_name}")
        print(f"   📅 Uptime: {room_data.get('uptime_minutes', 0):.1f} minutes")
        print(f"   🤖 Agents: {len(room_data.get('agents', {}))}")
        
        # Call stop endpoint for this room
        stop_payload = {
            "room_name": room_name
        }
        
        stop_response = requests.post(f"{base_url}/ai-agents/stop", json=stop_payload)
        
        if stop_response.status_code == 200:
            stop_data = stop_response.json()
            print(f"   ✅ Stop request successful: {stop_data.get('message', 'No message')}")
        else:
            print(f"   ⚠️  Stop request failed: {stop_response.status_code} - {stop_response.text}")
    
    # Step 3: Wait for cleanup
    print(f"\n⏳ Waiting 5 seconds for cleanup to complete...")
    time.sleep(5)
    
    # Step 4: Verify cleanup
    print(f"\n4️⃣ Verifying cleanup...")
    final_status_response = requests.get(f"{base_url}/ai-agents/status")
    
    if final_status_response.status_code == 200:
        final_status_data = final_status_response.json()
        final_summary = final_status_data.get('summary', {})
        
        print(f"📊 Final status:")
        print(f"   🏠 Total rooms: {final_summary.get('total_rooms', 0)}")
        print(f"   🤖 Total agents: {final_summary.get('total_agents', 0)}")
        print(f"   ✅ Running agents: {final_summary.get('running_agents', 0)}")
        print(f"   🧹 Dead rooms cleaned: {final_summary.get('dead_rooms_cleaned', 0)}")
        
        if final_summary.get('total_agents', 0) == 0:
            print(f"🎉 All agents successfully cleaned up!")
        else:
            print(f"⚠️  Some agents may still be running")
            remaining_rooms = final_status_data.get('rooms', {})
            for room_name, room_data in remaining_rooms.items():
                print(f"   🏠 {room_name}: {len(room_data.get('agents', {}))} agents")
    else:
        print(f"❌ Failed to verify cleanup: {final_status_response.status_code}")
    
    print(f"\n💡 Check LiveKit dashboard to confirm sessions are terminated")
    print(f"💡 If sessions persist, they may need manual termination in LiveKit Cloud")

if __name__ == "__main__":
    cleanup_all_agents() 