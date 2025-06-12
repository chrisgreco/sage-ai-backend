import os
import sys
import asyncio
import logging
from dotenv import load_dotenv
import jwt
import time
import requests
from livekit import rtc

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables from .env file (if available)
load_dotenv()

# Get LiveKit credentials
livekit_url = os.environ.get("LIVEKIT_URL", "wss://sage-2kpu4z1y.livekit.cloud")
livekit_api_key = os.environ.get("LIVEKIT_API_KEY", "APIWQtUQUijqXVp")
livekit_api_secret = os.environ.get("LIVEKIT_API_SECRET", "LDs7r35vqLLwR5vBPFg99hlPqE5y2EZ4sq7M90fAfEI")

# Room info
room_name = os.environ.get("ROOM_NAME", "test-debate-room")
identity = os.environ.get("IDENTITY", "test-user")

def create_token():
    """Create a LiveKit token for joining a room"""
    now = int(time.time())
    exp = now + 3600  # 1 hour expiration
    
    # Define permissions
    payload = {
        "exp": exp,
        "iss": livekit_api_key,
        "sub": identity,
        "nbf": now,
        "video": {
            "room": room_name,
            "roomJoin": True,
            "roomCreate": True,
            "canPublish": True,
            "canSubscribe": True,
            "canPublishData": True
        }
    }
    
    # Create the token
    token = jwt.encode(payload, livekit_api_secret, algorithm="HS256")
    logger.info(f"Generated JWT token: {token[:20]}...")
    return token

def create_room():
    """Create a room using the LiveKit API"""
    # LiveKit API endpoint for creating a room
    api_base = livekit_url.replace("wss://", "https://").replace("ws://", "http://")
    url = f"{api_base}/twirp/livekit.RoomService/CreateRoom"
    
    # Request data
    data = {
        "name": room_name,
        "empty_timeout": 300,  # 5 minutes
        "max_participants": 5
    }
    
    # Set up auth header
    access_token = create_token()
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    try:
        # Make the API request
        logger.info(f"Creating room with URL: {url}")
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        logger.info(f"Room created: {response.json()}")
        return True
    except Exception as e:
        logger.error(f"Error creating room: {e}")
        return False

async def join_room():
    """Join a room and wait for the agent to connect"""
    logger.info(f"Joining room: {room_name}")
    
    # Create a token
    token = create_token()
    
    # Create a room client
    room = rtc.Room()
    
    # Connect to the room
    logger.info(f"Connecting to room: {room_name}")
    await room.connect(livekit_url, token)
    logger.info(f"Connected to room: {room_name}")
    
    # Wait for agent to connect
    logger.info("Waiting for agent to connect...")
    
    # Keep the connection open for a while to give the agent time to connect
    try:
        for _ in range(60):  # Wait up to 60 seconds
            await asyncio.sleep(1)
            
            # Check for new participants - participants structure may differ in newer versions
            participants = []
            try:
                if hasattr(room, 'participants'):
                    participants = list(room.participants.values())
                elif hasattr(room, 'get_participants'):
                    participants = await room.get_participants()
                else:
                    # Try to see what's available in the room object
                    logger.info(f"Room attributes: {dir(room)}")
            except Exception as e:
                logger.error(f"Error getting participants: {e}")
            
            # Log whatever information we can get
            try:
                if participants:
                    logger.info(f"Current participants: {len(participants)} found")
                    for p in participants:
                        logger.info(f"Participant: {p}")
                else:
                    logger.info("No participants found yet")
            except Exception as e:
                logger.error(f"Error processing participants: {e}")
            
            # Check if we can detect an agent has connected
            try:
                agent_connected = False
                for p in participants:
                    p_name = str(p)
                    if "agent" in p_name.lower() or "bot" in p_name.lower() or "ai" in p_name.lower():
                        agent_connected = True
                        logger.info(f"Agent detected: {p}")
                        break
                
                if agent_connected:
                    logger.info("Agent has connected!")
                    # Wait a bit longer to let the agent fully initialize
                    await asyncio.sleep(10)
                    break
            except Exception as e:
                logger.error(f"Error checking for agent: {e}")
    
    finally:
        # Disconnect from the room
        await room.disconnect()
        logger.info("Disconnected from room")

async def main():
    """Main function to run the test"""
    logger.info(f"Starting LiveKit test client with URL: {livekit_url}")
    logger.info(f"Room name: {room_name}")
    
    # Create the room if it doesn't exist
    if create_room():
        # Join the room
        await join_room()
    
    logger.info("Test completed")

if __name__ == "__main__":
    # Run the test
    asyncio.run(main()) 