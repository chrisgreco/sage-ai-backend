import os
import sys
import asyncio
import logging
import argparse
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

# Function to parse command line arguments
def parse_args():
    parser = argparse.ArgumentParser(description='LiveKit Test Client')
    parser.add_argument('--livekit-url', default=os.environ.get('LIVEKIT_URL', 'wss://sage-2kpu4z1y.livekit.cloud'),
                        help='LiveKit server URL')
    parser.add_argument('--livekit-api-key', default=os.environ.get('LIVEKIT_API_KEY', 'APIWQtUQUijqXVp'),
                        help='LiveKit API key')
    parser.add_argument('--livekit-api-secret', default=os.environ.get('LIVEKIT_API_SECRET', 'LDs7r35vqLLwR5vBPFg99hlPqE5y2EZ4sq7M90fAfEI'),
                        help='LiveKit API secret')
    parser.add_argument('--room-name', default=os.environ.get('ROOM_NAME', 'test-debate-room'),
                        help='Room name to join')
    parser.add_argument('--identity', default=os.environ.get('IDENTITY', 'test-user'),
                        help='User identity')
    return parser.parse_args()

# Parse arguments
args = parse_args()

# Get LiveKit credentials from arguments
livekit_url = args.livekit_url
livekit_api_key = args.livekit_api_key
livekit_api_secret = args.livekit_api_secret

# Room info
room_name = args.room_name
identity = args.identity

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
    url = f"https://sage-2kpu4z1y.livekit.cloud/twirp/livekit.RoomService/CreateRoom"
    
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
    
    # List participants
    participants = room.participants
    logger.info(f"Participants in room: {[p.name for p in participants.values()]}")
    
    # Wait for agent to connect
    logger.info("Waiting for agent to connect...")
    
    # Keep the connection open for a while to give the agent time to connect
    try:
        for _ in range(60):  # Wait up to 60 seconds
            await asyncio.sleep(1)
            
            # Check for new participants
            current_participants = [p.name for p in room.participants.values()]
            logger.info(f"Current participants: {current_participants}")
            
            # Check if an agent has connected
            agent_connected = any(p.name.startswith("agent") or "bot" in p.name.lower() or "ai" in p.name.lower() for p in room.participants.values())
            if agent_connected:
                logger.info("Agent has connected!")
                # Wait a bit longer to let the agent fully initialize
                await asyncio.sleep(10)
                break
    
    finally:
        # Disconnect from the room
        await room.disconnect()
        logger.info("Disconnected from room")

async def main():
    """Main function to run the test"""
    logger.info("Starting LiveKit agent test")
    
    # Create the room if it doesn't exist
    if create_room():
        # Join the room
        await join_room()
    
    logger.info("Test completed")

if __name__ == "__main__":
    # Install PyJWT if not already installed
    try:
        import jwt
    except ImportError:
        logger.info("Installing PyJWT for token generation...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "PyJWT", "requests"])
        import jwt
        import requests
    
    # Run the test
    asyncio.run(main()) 