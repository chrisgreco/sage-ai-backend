import os
import logging
import uvicorn
import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import openai
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import subprocess
import sys

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import LiveKit API with proper error handling
try:
    logger.info("Importing LiveKit API...")
    from livekit.api import AccessToken, VideoGrants
    logger.info("Successfully imported LiveKit API!")
    livekit_available = True
except ImportError as e:
    logger.error(f"Error importing LiveKit API: {str(e)}")
    logger.warning("LiveKit functionality will be limited. Please install with: pip install livekit-api")
    livekit_available = False

# Load environment variables
load_dotenv()

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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://lovable.dev",  # Production frontend
        "http://localhost:3000"  # Local development only; remove in production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define request models
class DebateRequest(BaseModel):
    topic: str
    room_name: str = None

# Health check endpoint
@app.get("/health")
async def health_check():
    logger.info("Health check endpoint called")
    try:
        return JSONResponse(content={"status": "healthy", "livekit_available": livekit_available})
    except Exception as e:
        logger.error(f"Error in health check endpoint: {str(e)}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

# LiveKit connection endpoint
@app.get("/connect")
async def connect_to_livekit():
    try:
        if not livekit_available:
            return JSONResponse(
                content={"status": "error", "message": "LiveKit SDK not available"}, 
                status_code=503
            )
            
        if not all([LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET]):
            return JSONResponse(
                content={"status": "error", "message": "LiveKit configuration missing"}, 
                status_code=503
            )
            
        # Initialize LiveKit API client
        token = AccessToken(
            api_key=LIVEKIT_API_KEY,
            api_secret=LIVEKIT_API_SECRET
        ).with_identity("sage-ai-backend").to_jwt()
        
        return {
            "status": "success", 
            "message": "Ready to connect to LiveKit",
            "livekit_url": LIVEKIT_URL,
            "token": token
        }
    except Exception as e:
        logger.error(f"Error connecting to LiveKit: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Debate creation endpoint
@app.post("/debate")
async def create_debate(request: DebateRequest):
    try:
        logger.info(f"Creating debate on topic: {request.topic}")
        
        if not livekit_available:
            return JSONResponse(
                content={"status": "error", "message": "LiveKit SDK not available"}, 
                status_code=503
            )
            
        if not all([LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET]):
            return JSONResponse(
                content={"status": "error", "message": "LiveKit configuration missing"}, 
                status_code=503
            )
        
        # Generate a room name if not provided
        room_name = request.room_name or f"debate-{request.topic.replace(' ', '-').lower()}"
        
        # Create a token with room creation permissions
        token = AccessToken(
            api_key=LIVEKIT_API_KEY,
            api_secret=LIVEKIT_API_SECRET
        ).with_identity("ai-moderator").with_name("AI Moderator").with_grants(
            VideoGrants(
                room_join=True,
                room_create=True,
                room=room_name
            )
        ).to_jwt()
        
        return {
            "status": "success", 
            "message": f"Debate created on topic: {request.topic}",
            "room_name": room_name,
            "livekit_url": LIVEKIT_URL,
            "token": token
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
        logger.info("Running in background worker mode (launching LiveKit agent)")
        # Launch the real agent (main.py) as a subprocess
        subprocess.run([sys.executable, "-u", "livekit-agents/main.py"])
    else:
        logger.info("Running in web service mode")
        uvicorn.run(app, host="0.0.0.0", port=8000) 