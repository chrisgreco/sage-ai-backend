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
SERVICE_MODE = os.getenv("SERVICE_MODE", "web").lower()

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
        "https://1e934c03-5a1a-4df1-9eed-2c278b3ec6a8.lovableproject.com",
        "https://id-preview-1e934c03-5a1a-4df1-9eed-2c278b3ec6a8.lovable.app",
        "https://lovableproject.com",
        # Local development
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
        "http://localhost:8081",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:8081",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define request models
class DebateRequest(BaseModel):
    topic: str = None
    room_name: str = None
    participant_name: str = None

class AIAgentRequest(BaseModel):
    room_name: str
    topic: str = None
    start_agents: bool = True

class FlexibleDebateRequest(BaseModel):
    topic: str = None
    room_name: str = None
    participant_name: str = None
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
            "livekit_agents_available": True,  # New agent system available
            "ai_keys_configured": {
                "openai": bool(OPENAI_API_KEY),
                "deepgram": bool(DEEPGRAM_API_KEY), 
                "cartesia": bool(CARTESIA_API_KEY)
            }
        })
    except Exception as e:
        logger.error(f"Error in health check endpoint: {str(e)}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@app.options("/health")
async def health_check_options():
    logger.info("Health check OPTIONS endpoint called")
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Max-Age": "86400"
    }
    return JSONResponse(content={"status": "ok"}, headers=headers)

# General OPTIONS handler for all endpoints
@app.options("/{path:path}")
async def options_handler(path: str):
    logger.info(f"OPTIONS request for path: /{path}")
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Max-Age": "86400"
    }
    return JSONResponse(content={"status": "ok"}, headers=headers)

@app.post("/debug")
async def debug_request(request: FlexibleDebateRequest):
    logger.info(f"Debug endpoint called with: {request}")
    return JSONResponse(content={"received": request.dict(), "status": "debug successful"})

@app.get("/connect")
async def connect_to_livekit():
    logger.info("Connect endpoint called (GET)")
    if not livekit_available:
        raise HTTPException(status_code=503, detail="LiveKit not available")
    
    if not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET:
        raise HTTPException(status_code=500, detail="LiveKit credentials not configured")
    
    try:
        token = AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        token.with_identity("test-participant")
        token.with_name("Test Participant")
        
        grants = VideoGrants(
            room_join=True,
            room="default-room"
        )
        token.with_grants(grants)
        
        jwt_token = token.to_jwt()
        
        return JSONResponse(content={
            "token": jwt_token,
            "url": LIVEKIT_URL,
            "room": "default-room",
            "identity": "test-participant"
        })
    except Exception as e:
        logger.error(f"Error generating token: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating token: {str(e)}")

@app.post("/connect")
async def connect_to_livekit_post(request: FlexibleDebateRequest = None):
    logger.info(f"Connect endpoint called (POST) with request: {request}")
    
    if not livekit_available:
        raise HTTPException(status_code=503, detail="LiveKit not available")
    
    if not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET:
        raise HTTPException(status_code=500, detail="LiveKit credentials not configured")
    
    # Use request data if provided, otherwise use defaults
    room_name = request.room_name if request and request.room_name else "default-room"
    participant_name = request.participant_name if request and request.participant_name else "participant"
    
    try:
        token = AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        token.with_identity(participant_name)
        token.with_name(participant_name)
        
        grants = VideoGrants(
            room_join=True,
            room=room_name
        )
        token.with_grants(grants)
        
        jwt_token = token.to_jwt()
        
        return JSONResponse(content={
            "token": jwt_token,
            "url": LIVEKIT_URL,
            "room": room_name,
            "identity": participant_name
        })
    except Exception as e:
        logger.error(f"Error generating token: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating token: {str(e)}")

# Updated launch endpoint for new agent system
@app.post("/launch-ai-agents")
async def launch_ai_agents(request: AIAgentRequest):
    global running_agents
    
    logger.info(f"🚀 Launching AI agents for room: {request.room_name}")
    
    if not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET or not LIVEKIT_URL:
        raise HTTPException(status_code=500, detail="LiveKit credentials not configured")
    
    # Stop existing agents for this room if any
    if request.room_name in running_agents:
        try:
            process = running_agents[request.room_name]
            process.terminate()
            del running_agents[request.room_name]
            logger.info(f"Stopped existing agents for room: {request.room_name}")
        except Exception as e:
            logger.warning(f"Error stopping existing agents: {e}")
    
    # Set environment variables for the agent
    env = os.environ.copy()
    env.update({
        "LIVEKIT_API_KEY": LIVEKIT_API_KEY,
        "LIVEKIT_API_SECRET": LIVEKIT_API_SECRET,
        "LIVEKIT_URL": LIVEKIT_URL,
        "OPENAI_API_KEY": OPENAI_API_KEY,
        "ROOM_NAME": request.room_name,
        "DEBATE_TOPIC": request.topic or "The impact of AI on society"
    })
    
    try:
        # Use the new multi-personality agent
        command = [sys.executable, "-u", "multi_personality_agent.py", "start"]
        logger.info(f"Starting multi-personality agent with command: {' '.join(command)}")
        
        process = subprocess.Popen(
            command,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        running_agents[request.room_name] = process
        
        logger.info("✅ Multi-personality agent launched successfully")
        
        return JSONResponse(content={
            "status": "success",
            "message": f"Multi-personality debate agent launched for room {request.room_name}",
            "room_name": request.room_name,
            "topic": request.topic or "The impact of AI on society",
            "personalities": ["Solon (Moderator)", "Socrates (Questioner)", "Aristotle (Analyst)", "Buddha (Peacekeeper)", "Hermes (Synthesizer)"],
            "agent_type": "multi_personality",
            "process_id": process.pid
        })
        
    except Exception as e:
        logger.error(f"Error launching multi-personality agent: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to launch agent: {str(e)}")

@app.get("/ai-agents/status")
async def get_ai_agents_status():
    global running_agents
    
    active_agents = {}
    for room_name, process in running_agents.items():
        try:
            # Check if process is still running
            if process.poll() is None:
                active_agents[room_name] = {
                    "status": "running",
                    "pid": process.pid,
                    "agent_type": "multi_personality",
                    "personalities": ["Solon", "Socrates", "Aristotle", "Buddha", "Hermes"]
                }
            else:
                # Process has terminated, remove it
                del running_agents[room_name]
        except Exception as e:
            logger.warning(f"Error checking agent status for room {room_name}: {e}")
            del running_agents[room_name]
    
    return JSONResponse(content={
        "active_agents": active_agents,
        "total_active": len(active_agents)
    })

@app.post("/ai-agents/stop")
async def stop_ai_agents(request: AIAgentRequest):
    global running_agents
    
    logger.info(f"🛑 Stopping AI agents for room: {request.room_name}")
    
    if request.room_name not in running_agents:
        raise HTTPException(status_code=404, detail=f"No agents running for room {request.room_name}")
    
    try:
        process = running_agents[request.room_name]
        process.terminate()
        
        # Wait for graceful shutdown
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            logger.warning("Agent process didn't terminate gracefully, forcing kill")
            process.kill()
            process.wait()
        
        del running_agents[request.room_name]
        
        return JSONResponse(content={
            "status": "success",
            "message": f"AI agents stopped for room {request.room_name}"
        })
        
    except Exception as e:
        logger.error(f"Error stopping AI agents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to stop agents: {str(e)}")

# Keep existing participant token endpoint
@app.post("/participant-token")
async def get_participant_token(request: DebateRequest):
    logger.info(f"Participant token endpoint called with: {request}")
    
    if not livekit_available:
        raise HTTPException(status_code=503, detail="LiveKit not available")
    
    if not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET:
        raise HTTPException(status_code=500, detail="LiveKit credentials not configured")
    
    # Use request data or defaults
    room_name = request.room_name if request.room_name else "default-room"
    participant_name = request.participant_name if request.participant_name else "participant"
    
    try:
        token = AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        token.with_identity(participant_name)
        token.with_name(participant_name)
        
        grants = VideoGrants(
            room_join=True,
            room=room_name,
            room_record=False,
            room_admin=False
        )
        token.with_grants(grants)
        
        jwt_token = token.to_jwt()
        
        response_data = {
            "token": jwt_token,
            "url": LIVEKIT_URL,
            "room": room_name,
            "identity": participant_name
        }
        
        logger.info(f"Generated participant token for {participant_name} in room {room_name}")
        return JSONResponse(content=response_data)
        
    except Exception as e:
        logger.error(f"Error generating participant token: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating token: {str(e)}")

# Main execution
if __name__ == "__main__":
    # Register signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal, stopping all agents...")
        for room_name, process in running_agents.items():
            try:
                process.terminate()
                process.wait(timeout=5)
            except Exception as e:
                logger.warning(f"Error stopping agent for room {room_name}: {e}")
                process.kill()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    if SERVICE_MODE == "web":
        logger.info("Running in web service mode")
        uvicorn.run(app, host="0.0.0.0", port=8000)
    else:
        logger.info("Running in background worker mode")
        asyncio.run(run_background_worker())

async def run_background_worker():
    logger.info("Background worker started - monitoring for requests...")
    try:
        while True:
            await asyncio.sleep(10)
            logger.debug("Background worker heartbeat")
    except KeyboardInterrupt:
        logger.info("Background worker stopped")
    except Exception as e:
        logger.error(f"Background worker error: {e}")
        raise 