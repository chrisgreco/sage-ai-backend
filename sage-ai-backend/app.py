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
import signal
from typing import Dict, Optional

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
CARTESIA_API_KEY = os.getenv("CARTESIA_API_KEY", "")
SERVICE_MODE = os.getenv("SERVICE_MODE", "web").lower()  # Default to web service mode

# Set LiveKit environment variables for the library to use automatically
if LIVEKIT_API_KEY and LIVEKIT_API_SECRET:
    os.environ["LIVEKIT_API_KEY"] = LIVEKIT_API_KEY
    os.environ["LIVEKIT_API_SECRET"] = LIVEKIT_API_SECRET
    logger.info(f"LiveKit environment variables set: API_KEY={LIVEKIT_API_KEY[:8]}...")
else:
    logger.warning("LiveKit API credentials not found in environment")

# Configure OpenAI
openai.api_key = OPENAI_API_KEY

# Create FastAPI instance
app = FastAPI()

# Global variable to track running AI agent processes
running_agents: Dict[str, subprocess.Popen] = {}

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
        # Lovable specific domains
        "https://lovable.dev",
        "https://sage-liquid-glow-design.lovable.app",
        "https://1e934c03-5a1a-4df1-9eed-2c278b3ec6a8.lovableproject.com",  # Previous domain
        "https://id-preview-1e934c03-5a1a-4df1-9eed-2c278b3ec6a8.lovable.app",  # CURRENT FRONTEND URL
        "https://lovableproject.com",  # Alternative Lovable domain
        # Local development
        "http://localhost:3000",  # Local development
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        # For production, we could use "*" but it's less secure
        # "*"  # Uncomment this line if you need to allow all origins (not recommended)
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

class AIAgentRequest(BaseModel):
    room_name: str
    topic: str = None
    start_agents: bool = True

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
        return JSONResponse(content={
            "status": "healthy", 
            "livekit_available": livekit_available,
            "active_agents": len(running_agents),
            "ai_keys_configured": {
                "openai": bool(OPENAI_API_KEY),
                "deepgram": bool(DEEPGRAM_API_KEY), 
                "cartesia": bool(CARTESIA_API_KEY)
            }
        })
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
            
        # Initialize LiveKit API client using environment variables
        token = AccessToken()
        token.with_identity("sage-ai-backend")
        jwt_token = token.to_jwt()
        
        logger.info("Generated connect token successfully")
        
        return {
            "status": "success", 
            "message": "Ready to connect to LiveKit",
            "livekit_url": LIVEKIT_URL,
            "token": jwt_token
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
            
        # Initialize LiveKit API client using environment variables
        token = AccessToken()
        token.with_identity("sage-ai-backend")
        jwt_token = token.to_jwt()
        
        logger.info("Generated connect token successfully")
        
        return {
            "status": "success", 
            "message": "Ready to connect to LiveKit",
            "livekit_url": LIVEKIT_URL,
            "token": jwt_token
        }
    except Exception as e:
        logger.error(f"Error connecting to LiveKit: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 🚀 NEW AI AGENTS LAUNCHER ENDPOINT
@app.post("/launch-ai-agents")
async def launch_ai_agents(request: AIAgentRequest):
    """
    🎯 MAIN AI AGENTS LAUNCHER
    
    This endpoint starts the multi-agent AI debate system for a specific room.
    It will launch 5 AI agents (moderator, expert, challenger, synthesizer, fact-checker)
    who will intelligently participate in the debate with unique voices and personalities.
    """
    try:
        logger.info(f"🚀 Launching AI agents for room: {request.room_name}")
        
        # Check if AI services are available
        missing_keys = []
        if not OPENAI_API_KEY:
            missing_keys.append("OPENAI_API_KEY")
        if not DEEPGRAM_API_KEY:
            missing_keys.append("DEEPGRAM_API_KEY")
        if not CARTESIA_API_KEY:
            missing_keys.append("CARTESIA_API_KEY")
        if not all([LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET]):
            missing_keys.extend(["LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET"])
            
        if missing_keys:
            return JSONResponse(
                content={
                    "status": "error", 
                    "message": f"Missing required API keys: {', '.join(missing_keys)}"
                }, 
                status_code=503
            )
        
        # Check if agents are already running for this room
        if request.room_name in running_agents:
            logger.info(f"AI agents already running for room: {request.room_name}")
            return {
                "status": "success",
                "message": f"AI agents already active in room: {request.room_name}",
                "room_name": request.room_name,
                "agents_running": True
            }
        
        if request.start_agents:
            # Launch the AI agents subprocess
            topic = request.topic or "General Discussion"
            
            # Set environment variables for the agent process
            agent_env = os.environ.copy()
            agent_env.update({
                "LIVEKIT_URL": LIVEKIT_URL,
                "LIVEKIT_API_KEY": LIVEKIT_API_KEY,
                "LIVEKIT_API_SECRET": LIVEKIT_API_SECRET,
                "OPENAI_API_KEY": OPENAI_API_KEY,
                "DEEPGRAM_API_KEY": DEEPGRAM_API_KEY,
                "CARTESIA_API_KEY": CARTESIA_API_KEY,
                "DEBATE_TOPIC": topic,
                "ROOM_NAME": request.room_name
            })
            
            # Launch AI agents process
            cmd = [sys.executable, "-u", "start_ai_agents.py"]
            
            logger.info(f"Starting AI agents with command: {' '.join(cmd)}")
            process = subprocess.Popen(
                cmd,
                env=agent_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            
            # Store the running process
            running_agents[request.room_name] = process
            
            logger.info(f"✅ AI agents launched successfully for room: {request.room_name}")
            logger.info(f"🎭 Active agents: Moderator, Expert, Challenger, Synthesizer, Fact-Checker")
            
            return {
                "status": "success",
                "message": f"Multi-agent AI debate system launched for room: {request.room_name}",
                "room_name": request.room_name,
                "topic": topic,
                "agents_launched": [
                    "Dr. Alexandra Wright (Moderator)",
                    "Professor James Chen (Expert)",
                    "Sarah Rodriguez (Challenger)", 
                    "Dr. Maya Patel (Synthesizer)",
                    "Dr. Robert Kim (Fact-Checker)"
                ],
                "agent_features": [
                    "Unique Cartesia voices for each agent",
                    "Real-time speech recognition via Deepgram",
                    "Intelligent conversation triggers",
                    "Contextual debate participation",
                    "Evidence-based fact checking"
                ]
            }
        else:
            return {
                "status": "success",
                "message": "AI agents configured but not started (start_agents=false)",
                "room_name": request.room_name
            }
            
    except Exception as e:
        logger.error(f"❌ Error launching AI agents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to launch AI agents: {str(e)}")

# AI Agent status endpoint
@app.get("/ai-agents/status")
async def get_ai_agents_status():
    """Check the status of running AI agent processes"""
    try:
        active_rooms = []
        
        # Clean up dead processes
        dead_processes = []
        for room_name, process in running_agents.items():
            if process.poll() is not None:  # Process has terminated
                dead_processes.append(room_name)
            else:
                active_rooms.append({
                    "room_name": room_name,
                    "process_id": process.pid,
                    "status": "running"
                })
        
        # Remove dead processes
        for room_name in dead_processes:
            del running_agents[room_name]
        
        return {
            "status": "success",
            "active_agent_rooms": len(active_rooms),
            "rooms": active_rooms,
            "total_processes_cleaned": len(dead_processes)
        }
    except Exception as e:
        logger.error(f"Error checking AI agent status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Stop AI agents endpoint
@app.post("/ai-agents/stop")
async def stop_ai_agents(request: AIAgentRequest):
    """Stop AI agents for a specific room"""
    try:
        if request.room_name not in running_agents:
            return {
                "status": "info",
                "message": f"No AI agents running for room: {request.room_name}",
                "room_name": request.room_name
            }
        
        process = running_agents[request.room_name]
        
        # Gracefully terminate the process
        process.terminate()
        
        # Wait a bit for graceful shutdown
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            # Force kill if it doesn't shut down gracefully
            process.kill()
            process.wait()
        
        del running_agents[request.room_name]
        
        logger.info(f"AI agents stopped for room: {request.room_name}")
        
        return {
            "status": "success",
            "message": f"AI agents stopped for room: {request.room_name}",
            "room_name": request.room_name
        }
    except Exception as e:
        logger.error(f"Error stopping AI agents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Debate creation endpoint
@app.post("/debate")
async def create_debate(request: DebateRequest):
    try:
        # === LOVABLE'S REQUESTED DEBUGGING ===
        logger.info('=== DEBATE REQUEST ===')
        logger.info(f'Request body received: {request}')
        logger.info(f'Request topic: {request.topic}')
        logger.info(f'Request room_name: {request.room_name}')
        logger.info(f'Request participant_name: {request.participant_name}')
        
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
        # Use automatic environment variable detection (LIVEKIT_API_KEY and LIVEKIT_API_SECRET)
        token = AccessToken()
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
        
        # === MORE LOVABLE DEBUGGING ===
        logger.info(f'Generated token participant identity: {participant_identity}')
        logger.info(f'LiveKit URL being returned: {LIVEKIT_URL}')
        logger.info(f'Room name being returned: {room_name}')
        logger.info(f'Token grants: room_join=True, can_publish=True, can_subscribe=True, can_publish_data=True, room_create=True')
        logger.info(f'Using environment variables: LIVEKIT_API_KEY={LIVEKIT_API_KEY[:8]}..., LIVEKIT_API_SECRET={("***" if LIVEKIT_API_SECRET else "MISSING")}')
        logger.info('========================')
        
        response_data = {
            "status": "success", 
            "message": f"Debate created on topic: {request.topic}",
            "room_name": room_name,
            "livekit_url": LIVEKIT_URL,
            "token": jwt_token,
            "participant_name": participant_display_name,
            "topic": request.topic,
            "ai_agents_ready": bool(OPENAI_API_KEY and DEEPGRAM_API_KEY and CARTESIA_API_KEY),
            "ai_agents_endpoint": "/launch-ai-agents"
        }
        
        logger.info(f'=== RESPONSE BEING SENT: {response_data} ===')
        return response_data
        
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
        
        # Create a token for the specific participant using environment variables
        token = AccessToken()
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
        logger.info(f"Participant token grants: room_join=True, can_publish=True, can_subscribe=True, can_publish_data=True")
        
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