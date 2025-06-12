import os
import logging
import uvicorn
import asyncio
import secrets
import string
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import openai
from livekit.jwt import AccessToken, VideoGrant

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get environment variables
LIVEKIT_URL = os.getenv("LIVEKIT_URL")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")
SERVICE_MODE = os.getenv("SERVICE_MODE", "web").lower()  # Default to web service mode

# Configure OpenAI
openai.api_key = OPENAI_API_KEY

# Create FastAPI instance
app = FastAPI()

# Define request models
class DebateRequest(BaseModel):
    topic: str
    room_name: str = None

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Generate a random room name if needed
def generate_room_name(topic=None):
    if topic:
        base = f"debate-{topic.replace(' ', '-').lower()}"
        # Add some randomness to avoid collisions
        random_suffix = ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(6))
        return f"{base}-{random_suffix}"
    else:
        random_chars = ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(12))
        return f"debate-{random_chars}"

# LiveKit connection endpoint
@app.get("/connect")
async def connect_to_livekit():
    try:
        # Initialize LiveKit token
        token = AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        token.add_identity("sage-ai-backend")
        
        return {
            "status": "success", 
            "message": "Ready to connect to LiveKit",
            "livekit_url": LIVEKIT_URL,
            "token": token.to_jwt()
        }
    except Exception as e:
        logger.error(f"Error connecting to LiveKit: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Debate creation endpoint
@app.post("/debate")
async def create_debate(request: DebateRequest):
    try:
        logger.info(f"Creating debate on topic: {request.topic}")
        
        # Generate a room name if not provided
        room_name = request.room_name or generate_room_name(request.topic)
        
        # Create a token with room creation permissions
        token = AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        token.add_identity("ai-moderator")
        token.name = "AI Moderator"
        
        # Set permissions
        grant = VideoGrant(
            room_join=True,
            room_create=True,
            room=room_name
        )
        token.with_grants(grant)
        
        return {
            "status": "success", 
            "message": f"Debate created on topic: {request.topic}",
            "room_name": room_name,
            "livekit_url": LIVEKIT_URL,
            "token": token.to_jwt()
        }
    except Exception as e:
        logger.error(f"Error creating debate: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Background worker mode function
async def run_background_worker():
    logger.info("Starting background worker mode")
    
    try:
        logger.info("Worker mode doesn't yet implement real-time connections")
        logger.info("In a future version, this will connect to LiveKit rooms and provide AI moderation")
        
        # Keep the worker running
        while True:
            await asyncio.sleep(60)
            logger.info("Background worker heartbeat")
            
    except Exception as e:
        logger.error(f"Background worker error: {str(e)}")
        # Wait before reconnecting
        await asyncio.sleep(5)
        return await run_background_worker()  # Reconnect

if __name__ == "__main__":
    if SERVICE_MODE == "worker":
        logger.info("Running in background worker mode")
        asyncio.run(run_background_worker())
    else:
        logger.info("Running in web service mode")
        uvicorn.run(app, host="0.0.0.0", port=8000) 