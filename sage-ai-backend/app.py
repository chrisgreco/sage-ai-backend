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
import time

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Force redeploy to pick up Supabase environment variables - 2025-01-17

# Force redeploy to pick up Supabase environment variables - 2025-01-17

# Supabase memory integration for persistent conversation storage
try:
    from supabase_memory_manager import (
        create_or_get_debate_room,
        store_debate_segment,
        get_debate_memory,
        store_ai_memory,
        memory_manager
    )
    SUPABASE_AVAILABLE = True
    logger.info("✅ Supabase memory manager available for API endpoints")
except ImportError as e:
    SUPABASE_AVAILABLE = False
    logger.warning(f"⚠️ Supabase memory manager not available: {e}")
    # Create dummy functions to prevent errors
    async def create_or_get_debate_room(*args, **kwargs): return None
    async def store_debate_segment(*args, **kwargs): return False
    async def get_debate_memory(*args, **kwargs): return {"recent_segments": [], "session_summaries": [], "personality_memories": {}}
    async def store_ai_memory(*args, **kwargs): return False

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
    topic: str = "The impact of AI on society"  # Make optional with default
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

# Health check endpoint - Updated for voice agent deployment
@app.get("/health")
async def health_check():
    logger.info("Health check endpoint called")
    try:
        return JSONResponse(content={"status": "healthy", "livekit_available": livekit_available, "voice_agents": "ready"})
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
        
        # Generate a room name if not provided
        room_name = request.room_name or f"debate-{request.topic.replace(' ', '-').lower()}"
        
        # Use participant name if provided, otherwise default to "participant"
        participant_identity = request.participant_name or "participant"
        participant_display_name = request.participant_name or "Participant"
        
        # Create a token for the participant with room join permissions
        token = AccessToken(
            api_key=LIVEKIT_API_KEY,
            api_secret=LIVEKIT_API_SECRET
        ).with_identity(participant_identity).with_name(participant_display_name).with_grants(
            VideoGrants(
                room_join=True,
                room_create=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True
            )
        ).to_jwt()
        
        return {
            "status": "success", 
            "message": f"Debate created on topic: {request.topic}",
            "room_name": room_name,
            "livekit_url": LIVEKIT_URL,
            "token": token,
            "participant_name": participant_display_name
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
        
        # Create a token for the specific participant
        token = AccessToken(
            api_key=LIVEKIT_API_KEY,
            api_secret=LIVEKIT_API_SECRET
        ).with_identity(request.participant_name).with_name(request.participant_name).with_grants(
            VideoGrants(
                room_join=True,
                room=request.room_name,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True
            )
        ).to_jwt()
        
        return {
            "status": "success", 
            "message": f"Token generated for participant: {request.participant_name}",
            "room_name": request.room_name,
            "livekit_url": LIVEKIT_URL,
            "token": token,
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

# AI Agents Management - Store active agent processes with detailed status
active_agents = {}
agent_status_cache = {}

# Agent status monitoring
async def monitor_agent_connection(room_name: str, process_id: int, max_wait_time: int = 30):
    """Monitor if agents successfully connect to LiveKit room"""
    logger.info(f"Starting agent connection monitoring for room {room_name}, PID {process_id}")
    
    start_time = time.time()
    connection_confirmed = False
    
    # Wait for agent to connect and send status updates
    while time.time() - start_time < max_wait_time:
        # Check if process is still running
        if room_name in active_agents:
            process = active_agents[room_name]["process"]
            if process.poll() is not None:
                # Process has terminated
                return_code = process.returncode
                logger.error(f"Agent process {process_id} terminated early with code {return_code}")
                return {"connected": False, "error": f"Process terminated with code {return_code}"}
        
        # Check for status updates (implement actual LiveKit room monitoring here)
        await asyncio.sleep(1)
        
        # For now, we'll assume connection after a short delay
        # In production, you'd check LiveKit API for participant presence
        if time.time() - start_time > 5:  # Give 5 seconds for connection
            connection_confirmed = True
            break
    
    if connection_confirmed:
        logger.info(f"Agent connection confirmed for room {room_name}")
        return {"connected": True, "connection_time": time.time() - start_time}
    else:
        logger.warning(f"Agent connection timeout for room {room_name}")
        return {"connected": False, "error": "Connection timeout"}

# Enhanced Launch AI Agents endpoint with monitoring
@app.post("/launch-ai-agents")
async def launch_ai_agents(request: DebateRequest):
    try:
        logger.info(f"Launching AI agents for room: {request.room_name}, topic: {request.topic}")
        
        if not all([LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET]):
            return JSONResponse(
                content={"status": "error", "message": "LiveKit configuration missing"}, 
                status_code=503
            )
        
        room_name = request.room_name or f"debate-{request.topic.replace(' ', '-').lower()}"
        
        # Check if agents are already running for this room
        if room_name in active_agents:
            agent_info = active_agents[room_name]
            process = agent_info["process"]
            
            # Check if process is still alive
            if process.poll() is None:
                return {
                    "status": "success",
                    "message": f"AI agents already running for room: {room_name}",
                    "room_name": room_name,
                    "agents_active": True,
                    "process_id": process.pid,
                    "started_at": agent_info["started_at"]
                }
            else:
                # Process died, clean it up
                logger.warning(f"Found dead agent process for room {room_name}, cleaning up")
                del active_agents[room_name]
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                logger.info(f"Attempt {retry_count + 1}/{max_retries} to launch agents for room {room_name}")
                
                # Set environment variables for the agent - ENSURE ALL ARE SET
                env = os.environ.copy()
                
                # Ensure LiveKit variables are explicitly set from current environment
                livekit_url = os.getenv("LIVEKIT_URL") or LIVEKIT_URL
                livekit_api_key = os.getenv("LIVEKIT_API_KEY") or LIVEKIT_API_KEY  
                livekit_api_secret = os.getenv("LIVEKIT_API_SECRET") or LIVEKIT_API_SECRET
                
                if not all([livekit_url, livekit_api_key, livekit_api_secret]):
                    error_msg = f"Missing LiveKit configuration - URL: {'✓' if livekit_url else '✗'}, Key: {'✓' if livekit_api_key else '✗'}, Secret: {'✓' if livekit_api_secret else '✗'}"
                    logger.error(error_msg)
                    return JSONResponse(
                        content={"status": "error", "message": error_msg}, 
                        status_code=503
                    )
                
                env.update({
                    "LIVEKIT_URL": livekit_url,
                    "LIVEKIT_API_KEY": livekit_api_key,
                    "LIVEKIT_API_SECRET": livekit_api_secret,
                    "ROOM_NAME": room_name,
                    "DEBATE_TOPIC": request.topic,
                    "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
                    "DEEPGRAM_API_KEY": os.getenv("DEEPGRAM_API_KEY", ""),
                    "CARTESIA_API_KEY": os.getenv("CARTESIA_API_KEY", "")
                })
                
                logger.info(f"Environment prepared - LiveKit URL: {livekit_url[:20]}...")
                logger.info(f"Starting agent for room: {room_name}")
                
                # CORRECT WAY: Use LiveKit agents CLI with 'start' command
                process = subprocess.Popen([
                    sys.executable, "-u", "multi_personality_agent.py", "start"
                ], 
                env=env, 
                cwd=os.path.dirname(os.path.abspath(__file__)),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
                )
                
                # Store the process with detailed info
                agent_info = {
                    "process": process,
                    "topic": request.topic,
                    "started_at": time.time(),
                    "retry_count": retry_count,
                    "status": "starting",
                    "room_name": room_name
                }
                active_agents[room_name] = agent_info
                
                logger.info(f"Agent process launched with PID {process.pid} for room {room_name}")
                
                # Start background monitoring
                async def background_monitor():
                    try:
                        monitor_result = await monitor_agent_connection(room_name, process.pid, max_wait_time=30)
                        
                        if room_name in active_agents:
                            active_agents[room_name]["status"] = "connected" if monitor_result["connected"] else "failed"
                            active_agents[room_name]["connection_result"] = monitor_result
                            
                            if monitor_result["connected"]:
                                logger.info(f"✅ Agents successfully connected for room {room_name}")
                            else:
                                logger.error(f"❌ Agent connection failed for room {room_name}: {monitor_result.get('error', 'Unknown error')}")
                                
                    except Exception as e:
                        logger.error(f"Background monitoring error for room {room_name}: {e}")
                        if room_name in active_agents:
                            active_agents[room_name]["status"] = "error"
                            active_agents[room_name]["connection_error"] = str(e)
                
                # Start monitoring in background
                asyncio.create_task(background_monitor())
                
                # Return immediate success with process info
                return {
                    "status": "success",
                    "message": f"AI agents launched for room: {room_name}",
                    "room_name": room_name,
                    "topic": request.topic,
                    "agents_active": True,
                    "process_id": process.pid,
                    "retry_count": retry_count,
                    "monitoring": "Agent connection monitoring started - check status endpoint for updates",
                    "launch_method": "livekit_agents_cli"
                }
                
            except FileNotFoundError:
                error_msg = "multi_personality_agent.py not found"
                logger.error(f"Retry {retry_count + 1} failed: {error_msg}")
                if retry_count == max_retries - 1:
                    return JSONResponse(
                        content={"status": "error", "message": error_msg}, 
                        status_code=500
                    )
                    
            except Exception as e:
                error_msg = f"Failed to start AI agents: {str(e)}"
                logger.error(f"Retry {retry_count + 1} failed: {error_msg}")
                if retry_count == max_retries - 1:
                    return JSONResponse(
                        content={"status": "error", "message": error_msg}, 
                        status_code=500
                    )
            
            retry_count += 1
            if retry_count < max_retries:
                logger.info(f"Waiting 2 seconds before retry {retry_count + 1}")
                await asyncio.sleep(2)
        
        # If we get here, all retries failed
        return JSONResponse(
            content={"status": "error", "message": f"Failed to launch agents after {max_retries} attempts"}, 
            status_code=500
        )
    
    except Exception as e:
        logger.error(f"Error launching AI agents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Stop AI Agents endpoint
@app.post("/ai-agents/stop")
async def stop_ai_agents(request: DebateRequest):
    try:
        logger.info(f"Stopping AI agents for room: {request.room_name}")
        
        room_name = request.room_name
        if not room_name:
            return JSONResponse(
                content={"status": "error", "message": "room_name is required"}, 
                status_code=400
            )
        
        if room_name not in active_agents:
            return {
                "status": "success",
                "message": f"No AI agents running for room: {room_name}",
                "room_name": room_name,
                "agents_active": False
            }
        
        try:
            # Get the process
            agent_info = active_agents[room_name]
            process = agent_info["process"]
            
            # Terminate the process
            process.terminate()
            
            # Wait for it to finish (with timeout)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                # Force kill if it doesn't terminate gracefully
                process.kill()
                process.wait()
            
            # Remove from active agents
            del active_agents[room_name]
            
            logger.info(f"AI agents stopped successfully for room {room_name}")
            
            return {
                "status": "success",
                "message": f"AI agents stopped for room: {room_name}",
                "room_name": room_name,
                "agents_active": False
            }
            
        except Exception as e:
            logger.error(f"Failed to stop AI agents: {str(e)}")
            # Clean up the entry even if stopping failed
            if room_name in active_agents:
                del active_agents[room_name]
            
            return JSONResponse(
                content={"status": "error", "message": f"Failed to stop AI agents: {str(e)}"}, 
                status_code=500
            )
    
    except Exception as e:
        logger.error(f"Error stopping AI agents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Enhanced AI Agents Status endpoint with detailed monitoring
@app.get("/ai-agents/status")
async def get_ai_agents_status():
    try:
        # Clean up any dead processes and collect detailed status
        dead_rooms = []
        detailed_status = {}
        
        for room_name, agent_info in active_agents.items():
            process = agent_info["process"]
            is_running = process.poll() is None
            
            if not is_running:
                dead_rooms.append(room_name)
            
            # Collect detailed status information
            current_time = time.time()
            uptime = current_time - agent_info["started_at"]
            
            detailed_status[room_name] = {
                "topic": agent_info["topic"],
                "started_at": agent_info["started_at"],
                "uptime_seconds": round(uptime, 2),
                "uptime_minutes": round(uptime / 60, 2),
                "process_id": process.pid,
                "running": is_running,
                "retry_count": agent_info.get("retry_count", 0),
                "status": agent_info.get("status", "unknown"),
                "connection_result": agent_info.get("connection_result", {}),
                "connection_error": agent_info.get("connection_error"),
                "return_code": process.returncode if not is_running else None
            }
        
        # Clean up dead processes
        for room_name in dead_rooms:
            logger.info(f"Cleaning up dead agent process for room {room_name}")
            del active_agents[room_name]
        
        # Summary statistics
        running_count = sum(1 for info in detailed_status.values() if info["running"])
        failed_count = sum(1 for info in detailed_status.values() if info["status"] == "failed")
        connected_count = sum(1 for info in detailed_status.values() if info["status"] == "connected")
        
        return {
            "status": "success",
            "timestamp": current_time,
            "summary": {
                "total_rooms": len(detailed_status),
                "running_agents": running_count,
                "connected_agents": connected_count,
                "failed_agents": failed_count,
                "dead_processes_cleaned": len(dead_rooms)
            },
            "rooms": detailed_status,
            "monitoring_info": {
                "agent_connection_timeout": 30,
                "max_retries": 3,
                "retry_delay": 2
            }
        }
    except Exception as e:
        logger.error(f"Error getting AI agents status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# New endpoint for real-time agent health monitoring
@app.get("/ai-agents/health/{room_name}")
async def get_agent_health(room_name: str):
    """Get detailed health information for a specific room's agents"""
    try:
        if room_name not in active_agents:
            return JSONResponse(
                content={"status": "error", "message": f"No agents found for room: {room_name}"}, 
                status_code=404
            )
        
        agent_info = active_agents[room_name]
        process = agent_info["process"]
        is_running = process.poll() is None
        current_time = time.time()
        uptime = current_time - agent_info["started_at"]
        
        health_data = {
            "room_name": room_name,
            "healthy": is_running and agent_info.get("status") == "connected",
            "process_running": is_running,
            "connection_status": agent_info.get("status", "unknown"),
            "uptime_seconds": round(uptime, 2),
            "process_id": process.pid,
            "topic": agent_info["topic"],
            "started_at": agent_info["started_at"],
            "retry_count": agent_info.get("retry_count", 0),
            "connection_result": agent_info.get("connection_result", {}),
            "last_check": current_time
        }
        
        if not is_running:
            health_data["return_code"] = process.returncode
            health_data["termination_reason"] = "Process terminated"
        
        if agent_info.get("connection_error"):
            health_data["connection_error"] = agent_info["connection_error"]
        
        return {"status": "success", "health": health_data}
        
    except Exception as e:
        logger.error(f"Error getting agent health for room {room_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Memory Management Endpoints for Supabase Integration
class MemoryRequest(BaseModel):
    room_token: str
    content: str = None
    speaker_name: str = None
    speaker_type: str = "human"  # or "ai"
    segment_type: str = "conversation"

@app.post("/memory/room")
async def create_memory_room(request: MemoryRequest):
    """Create or get a debate room for memory storage"""
    if not SUPABASE_AVAILABLE:
        return JSONResponse(
            content={"status": "error", "message": "Memory storage not available"}, 
            status_code=503
        )
    
    try:
        room_id = await create_or_get_debate_room(
            room_token=request.room_token,
            topic="AI Debate",
            max_duration_hours=24
        )
        return {"status": "success", "room_id": room_id}
    except Exception as e:
        logger.error(f"Error creating memory room: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/memory/store")
async def store_memory_segment(request: MemoryRequest):
    """Store a conversation segment in memory"""
    if not SUPABASE_AVAILABLE:
        return JSONResponse(
            content={"status": "error", "message": "Memory storage not available"}, 
            status_code=503
        )
    
    try:
        # First ensure room exists
        room_id = await create_or_get_debate_room(
            room_token=request.room_token,
            topic="AI Debate",
            max_duration_hours=24
        )
        
        # Store the segment
        success = await store_debate_segment(
            room_id=room_id,
            speaker_name=request.speaker_name or "Anonymous",
            speaker_type=request.speaker_type,
            content=request.content or "",
            segment_type=request.segment_type
        )
        
        return {"status": "success" if success else "failed", "stored": success}
    except Exception as e:
        logger.error(f"Error storing memory segment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/memory/{room_token}")
async def get_memory_data(room_token: str):
    """Retrieve conversation memory for a room"""
    if not SUPABASE_AVAILABLE:
        return JSONResponse(
            content={"status": "error", "message": "Memory storage not available"}, 
            status_code=503
        )
    
    try:
        # Get room ID from token
        room_id = await create_or_get_debate_room(
            room_token=room_token,
            topic="AI Debate",
            max_duration_hours=24
        )
        
        # Retrieve memory data
        memory_data = await get_debate_memory(room_id)
        return {
            "status": "success", 
            "memory": memory_data,
            "segments_count": len(memory_data.get("recent_segments", [])),
            "summaries_count": len(memory_data.get("session_summaries", []))
        }
    except Exception as e:
        logger.error(f"Error retrieving memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/memory/health")
async def memory_health_check():
    """Check if memory storage is available"""
    return {
        "supabase_available": SUPABASE_AVAILABLE,
        "status": "healthy" if SUPABASE_AVAILABLE else "memory_unavailable"
    }

if __name__ == "__main__":
    if SERVICE_MODE == "worker":
        logger.info("Running in background worker mode (launching LiveKit agent)")
        # Launch the real agent (multi_personality_agent.py) as a subprocess
        subprocess.run([sys.executable, "-u", "multi_personality_agent.py", "start"])
    else:
        logger.info("Running in web service mode")
        uvicorn.run(app, host="0.0.0.0", port=8000) 