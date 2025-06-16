import os
import logging
import uvicorn
import asyncio
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ValidationError
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

# Add global exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Validation error on {request.method} {request.url}: {exc.errors()}")
    try:
        body = await request.body()
        logger.error(f"Request body: {body}")
        body_str = body.decode('utf-8') if body else "Empty body"
    except Exception as e:
        logger.error(f"Could not read request body: {e}")
        body_str = "Could not read body"
    
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors(),
            "body": body_str,
            "url": str(request.url),
            "method": request.method
        }
    )

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://lovable.dev",
        "https://sage-liquid-glow-design.lovable.app",
        "https://1e934c03-5a1a-4df1-9eed-2c278b3ec6a8.lovableproject.com",  # Previous domain
        "https://id-preview-1e934c03-5a1a-4df1-9eed-2c278b3ec6a8.lovable.app",  # ACTUAL FRONTEND URL
        "https://lovableproject.com",  # Alternative Lovable domain
        "http://localhost:3000",  # Local development
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define request models
class DebateRequest(BaseModel):
    topic: str = None  # Make topic optional with default
    room_name: str = None
    participant_name: str = None

# Add a more flexible model for debugging
class FlexibleDebateRequest(BaseModel):
    topic: str = None
    room_name: str = None
    participant_name: str = None
    # Allow any additional fields for debugging
    class Config:
        extra = "allow"

# Health check endpoint
@app.get("/health")
async def health_check():
    logger.info("Health check endpoint called")
    try:
        return JSONResponse(content={"status": "healthy", "livekit_available": livekit_available})
    except Exception as e:
        logger.error(f"Error in health check endpoint: {str(e)}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

# Debug endpoint to see what the frontend is sending
@app.post("/debug")
async def debug_request(request: FlexibleDebateRequest):
    logger.info(f"Debug endpoint received: {request}")
    return {"received": request.dict(), "status": "debug"}

# LiveKit connection endpoint
@app.get("/connect")
async def connect_to_livekit():
    try:
        logger.info("Connect endpoint called via GET")
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

# Also add POST version of connect endpoint
@app.post("/connect")
async def connect_to_livekit_post(request: FlexibleDebateRequest = None):
    try:
        logger.info(f"Connect endpoint called via POST with data: {request}")
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
        logger.info(f"Creating debate with request: {request}")
        logger.info(f"Request topic: {request.topic}")
        logger.info(f"Request room_name: {request.room_name}")
        logger.info(f"Request participant_name: {request.participant_name}")
        
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
        
        # Handle missing topic by deriving it from room_name or providing default
        if not request.topic:
            if request.room_name:
                # Extract topic from room name (remove timestamp if present)
                topic_parts = request.room_name.split('-')
                if topic_parts[-1].isdigit():  # Remove timestamp
                    topic_parts = topic_parts[:-1]
                request.topic = ' '.join(topic_parts).replace('-', ' ').title()
            else:
                request.topic = "General Debate"
        
        # Generate a room name if not provided
        room_name = request.room_name or f"debate-{request.topic.replace(' ', '-').lower()}"
        
        # Use participant name if provided, otherwise default to "participant"
        participant_identity = request.participant_name or "participant"
        participant_display_name = request.participant_name or "Participant"
        
        # Create a token for the participant with proper LiveKit grants
        token = AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        token.with_identity(participant_identity)
        token.with_name(participant_display_name)
        
        # Set up proper video grants following LiveKit best practices
        video_grants = VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=True,
            can_subscribe=True,
            can_publish_data=True,
            # Add room creation permission
            room_create=True
        )
        token.with_grants(video_grants)
        
        jwt_token = token.to_jwt()
        
        logger.info(f"Generated token for room: {room_name}, participant: {participant_identity}")
        
        return {
            "status": "success", 
            "message": f"Debate created on topic: {request.topic}",
            "room_name": room_name,
            "livekit_url": LIVEKIT_URL,
            "token": jwt_token,
            "participant_name": participant_display_name,
            "topic": request.topic
        }
    except Exception as e:
        logger.error(f"Error creating debate: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Participant token endpoint
@app.post("/participant-token")
async def get_participant_token(request: DebateRequest):
    try:
        logger.info(f"Generating participant token for: {request.participant_name}")
        
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
        
        # Require room_name and participant_name for this endpoint
        if not request.room_name or not request.participant_name:
            return JSONResponse(
                content={"status": "error", "message": "room_name and participant_name are required"}, 
                status_code=400
            )
        
        # Create a token for the specific participant using improved pattern
        token = AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        token.with_identity(request.participant_name)
        token.with_name(request.participant_name)
        
        # Set up proper video grants following LiveKit best practices
        video_grants = VideoGrants(
            room_join=True,
            room=request.room_name,
            can_publish=True,
            can_subscribe=True,
            can_publish_data=True
        )
        token.with_grants(video_grants)
        
        jwt_token = token.to_jwt()
        
        logger.info(f"Generated participant token for room: {request.room_name}, participant: {request.participant_name}")
        
        return {
            "status": "success", 
            "message": f"Token generated for participant: {request.participant_name}",
            "room_name": request.room_name,
            "livekit_url": LIVEKIT_URL,
            "token": jwt_token,
            "participant_name": request.participant_name
        }
    except Exception as e:
        logger.error(f"Error generating participant token: {str(e)}")
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