import os
import logging
import uvicorn
import asyncio
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv
# Note: OpenAI import removed - this backend only handles LiveKit tokens and agent launching
# OpenAI API calls are handled by the LiveKit agent subprocess
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import subprocess
import sys
import time
import json
import threading

# Load environment variables
load_dotenv()

# Import enhanced logging configuration
try:
    from app.logging_config import setup_global_logging, agent_logger, performance_logger
    from app.routers.log_webhook import router as log_router
    setup_global_logging(os.getenv("LOG_LEVEL", "INFO"))
    logger = agent_logger.logger
    ENHANCED_LOGGING = True
except ImportError as e:
    # Fallback to basic logging if enhanced logging is not available
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    ENHANCED_LOGGING = False
    logger.warning(f"Enhanced logging not available: {e}")

# Logging middleware for request/response monitoring
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start_time = time.time()
        
        # Log request
        if ENHANCED_LOGGING:
            agent_logger.info("Incoming request", 
                            method=request.method,
                            url=str(request.url),
                            client_ip=request.client.host if request.client else None)
        
        response = await call_next(request)
        
        # Log response
        process_time = time.time() - start_time
        if ENHANCED_LOGGING:
            performance_logger.log_api_call(
                api_name=f"{request.method} {request.url.path}",
                duration=process_time,
                status_code=response.status_code
            )
        else:
            logger.info(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")
        
        return response

# LiveKit imports - conditional import with error handling
try:
    from livekit import api
    livekit_available = True
    logger.info("✅ LiveKit API imported successfully")
except ImportError as e:
    logger.error(f"Error importing LiveKit API: {str(e)}")
    logger.warning("LiveKit functionality will be limited. Please install with: pip install livekit-api")
    livekit_available = False

# Supabase memory manager imports - conditional import
try:
    from supabase_memory_manager import (
        create_or_get_debate_room, 
        store_debate_segment, 
        get_debate_memory,
        SUPABASE_AVAILABLE
    )
    logger.info("✅ Supabase memory manager imported successfully")
except ImportError as e:
    logger.error(f"Error importing Supabase memory manager: {str(e)}")
    logger.warning("Memory functionality will be limited.")
    SUPABASE_AVAILABLE = False
    
    # Create dummy functions to prevent runtime errors
    async def create_or_get_debate_room(*args, **kwargs):
        return None
    async def store_debate_segment(*args, **kwargs):
        return False
    async def get_debate_memory(*args, **kwargs):
        return {"recent_segments": [], "session_summaries": [], "personality_memories": {}}

# Force redeploy to pick up LiveKit API fixes - 2025-01-19

# Force redeploy to pick up LiveKit API fixes - 2025-01-19

# Supabase memory integration for persistent conversation storage
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
    logger.info("✅ Supabase client library available")
except ImportError:
    SUPABASE_AVAILABLE = False
    logger.warning("⚠️ Supabase client library not available")

# Get environment variables
LIVEKIT_URL = os.getenv("LIVEKIT_URL")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Only used to pass to agent subprocess
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")
SERVICE_MODE = os.getenv("SERVICE_MODE", "web").lower()  # Default to web service mode

# Note: OpenAI API key is only used to pass to the agent subprocess
# The main backend app only handles LiveKit tokens and agent launching

# Create FastAPI instance
app = FastAPI(
    title="Sage AI Backend - LiveKit Agent System",
    description="Dual Agent Debate System with Enhanced Logging and Monitoring",
    version="1.0.0"
)

# Add logging middleware
app.add_middleware(LoggingMiddleware)

# Include log webhook router if enhanced logging is available
if ENHANCED_LOGGING:
    app.include_router(log_router)
    logger.info("Enhanced logging and webhook endpoints enabled")

# Add global exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    try:
        body = await request.body()
        body_str = body.decode('utf-8') if body else "Empty body"
    except Exception as e:
        body_str = "Could not read body"
    
    if ENHANCED_LOGGING:
        agent_logger.error("Request validation error",
                         method=request.method,
                         url=str(request.url),
                         errors=exc.errors(),
                         request_body=body_str[:500])  # Limit body size in logs
    else:
        logger.error(f"Validation error on {request.method} {request.url}: {exc.errors()}")
    
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors(),
            "body": body_str,
            "url": str(request.url),
            "method": request.method
        }
    )

# Add global exception handler for unhandled exceptions
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if ENHANCED_LOGGING:
        agent_logger.error("Unhandled exception",
                         method=request.method,
                         url=str(request.url),
                         error_type=type(exc).__name__,
                         error_message=str(exc),
                         exc_info=True)
    else:
        logger.error(f"Unhandled exception in {request.method} {request.url}: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error_type": type(exc).__name__,
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
        "https://id-preview--1e934c03-5a1a-4df1-9eed-2c278b3ec6a8.lovable.app",  # CURRENT FRONTEND URL (double hyphens!)
        "https://lovableproject.com",  # Alternative Lovable domain
        "http://localhost:3000",  # Local development
        "http://localhost:5173",  # Vite dev server
        "http://localhost:8080",  # For local development testing
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom CORS middleware to handle Lovable's dynamic domains
@app.middleware("http")
async def cors_handler(request: Request, call_next):
    origin = request.headers.get("origin")
    
    # Check if it's a Lovable domain
    if origin and (
        origin.endswith(".lovable.app") or 
        origin.endswith(".lovable.dev") or 
        origin.endswith(".lovableproject.com") or
        "lovable" in origin
    ):
        response = await call_next(request)
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response
    
    return await call_next(request)

# Define request models
class DebateRequest(BaseModel):
    topic: str = "The impact of AI on society"  # Make optional with default
    room_name: str = None
    participant_name: str = None
    moderator: str = "Aristotle"  # Default moderator persona

# Add a more flexible model for debugging
class FlexibleDebateRequest(BaseModel):
    topic: str = None
    room_name: str = None
    participant_name: str = None
    moderator: str = None
    # Allow any additional fields for debugging
    class Config:
        extra = "allow"

# Root endpoint for health monitoring and basic info
@app.get("/")
async def root():
    logger.info("Root endpoint called")
    try:
        return JSONResponse(content={
            "message": "Sage AI Backend - Dual Agent Debate System",
            "status": "healthy",
            "livekit_available": livekit_available,
            "voice_agents": "ready",
            "endpoints": ["/health", "/connect", "/launch-ai-agents", "/participant-token"]
        })
    except Exception as e:
        logger.error(f"Error in root endpoint: {str(e)}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

# Also handle HEAD requests to root (common for health checks)
@app.head("/")
async def root_head():
    return JSONResponse(content={})

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
        token = api.AccessToken(
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
        token = api.AccessToken(
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
        logger.info(f"Request moderator: {request.moderator}")
        
        # Debug logging for troubleshooting
        logger.info(f"DEBUG - livekit_available: {livekit_available}")
        logger.info(f"DEBUG - LIVEKIT_URL present: {bool(LIVEKIT_URL)}")
        logger.info(f"DEBUG - LIVEKIT_API_KEY present: {bool(LIVEKIT_API_KEY)}")
        logger.info(f"DEBUG - LIVEKIT_API_SECRET present: {bool(LIVEKIT_API_SECRET)}")
        
        if not livekit_available:
            logger.error("LiveKit SDK not available - check package installation")
            return JSONResponse(
                content={"status": "error", "message": "LiveKit SDK not available"}, 
                status_code=503
            )
            
        if not all([LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET]):
            logger.error(f"LiveKit configuration missing - URL: {bool(LIVEKIT_URL)}, KEY: {bool(LIVEKIT_API_KEY)}, SECRET: {bool(LIVEKIT_API_SECRET)}")
            return JSONResponse(
                content={"status": "error", "message": "LiveKit configuration missing"}, 
                status_code=503
            )
        
        # Generate a room name if not provided
        room_name = request.room_name or f"debate-{request.topic.replace(' ', '-').lower()}"
        
        # Use participant name if provided, otherwise default to "participant"
        participant_identity = request.participant_name or "participant"
        participant_display_name = request.participant_name or "Participant"
        
        # Validate moderator selection
        valid_moderators = ["Socrates", "Aristotle", "Buddha"]
        moderator = request.moderator if request.moderator in valid_moderators else "Aristotle"
        
        # Include moderator and topic in token metadata
        metadata = json.dumps({
            "moderator": moderator,
            "topic": request.topic
        })
        
        # Create a token for the participant with room join permissions and metadata
        token = api.AccessToken(
            api_key=LIVEKIT_API_KEY,
            api_secret=LIVEKIT_API_SECRET
        ).with_identity(participant_identity).with_name(participant_display_name).with_metadata(metadata).with_grants(
            api.VideoGrants(
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
            "participant_name": participant_display_name,
            "moderator": moderator
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
        token = api.AccessToken(
            api_key=LIVEKIT_API_KEY,
            api_secret=LIVEKIT_API_SECRET
        ).with_identity(request.participant_name).with_name(request.participant_name).with_grants(
            api.VideoGrants(
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

# Enhanced Launch AI Agents endpoint using room metadata for background workers
@app.post("/launch-ai-agents")
async def launch_ai_agents(request: DebateRequest):
    try:
        logger.info(f"Creating LiveKit room for debate: {request.room_name}, topic: {request.topic}, moderator: {request.moderator}")
        
        if not all([LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET]):
            return JSONResponse(
                content={"status": "error", "message": "LiveKit configuration missing"}, 
                status_code=503
            )
        
        room_name = request.room_name or f"debate-{request.topic.replace(' ', '-').lower()}"
        
        # Validate moderator selection
        valid_moderators = ["Socrates", "Aristotle", "Buddha"]
        moderator = request.moderator if request.moderator in valid_moderators else "Aristotle"
        
        # Create LiveKit room and dispatch single agent with moderator persona
        try:
            # Initialize LiveKit API client
            livekit_api = api.LiveKitAPI(
                url=LIVEKIT_URL,
                api_key=LIVEKIT_API_KEY,
                api_secret=LIVEKIT_API_SECRET
            )
            
            # Room should already exist from /debate endpoint, just dispatch single agent
            logger.info(f"🔍 Dispatching single agent with {moderator} persona to room: {room_name}")
            
            # Import the agent dispatch protocol classes
            from livekit.protocol import agent_dispatch
            
            # Dispatch single agent (using Aristotle codebase) with moderator persona
            agent_dispatch_req = agent_dispatch.CreateAgentDispatchRequest(
                room=room_name,
                agent_name="moderator",  # Single agent name
                metadata=json.dumps({
                    "moderator": moderator,
                    "debate_topic": request.topic,
                    "agent_type": "moderator"
                })
            )
            
            agent_job = await livekit_api.agent_dispatch.create_dispatch(agent_dispatch_req)
            logger.info(f"✅ {moderator} moderator explicitly dispatched to room {room_name}, dispatch ID: {agent_job.id}")
            
            # Store room info for tracking
            active_agents[room_name] = {
                "room_name": room_name,
                "topic": request.topic,
                "moderator": moderator,
                "created_at": time.time(),
                "status": "agent_dispatched",
                "method": "single_agent_dispatch",
                "agent_dispatched": {
                    "moderator": {
                        "dispatch_id": agent_job.id,
                        "status": "dispatched",
                        "persona": moderator
                    }
                }
            }
            
            logger.info(f"🎉 Debate room ready: {room_name}")
            logger.info(f"📢 {moderator} moderator dispatched to room")
            
            return {
                "status": "success",
                "message": f"{moderator} moderator dispatched to room: {room_name}",
                "room_name": room_name,
                "topic": request.topic,
                "moderator": moderator,
                "method": "single_agent_dispatch",
                "agent_dispatched": {
                    "moderator": {
                        "dispatch_id": agent_job.id,
                        "status": "dispatched",
                        "persona": moderator
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to dispatch agents: {e}")
            logger.error("Background workers only mode - no fallback spawning available")
            
            # Return error instead of falling back to direct spawning
            return JSONResponse(
                content={
                    "status": "error", 
                    "message": f"Failed to dispatch agents: {str(e)}",
                    "room_name": room_name,
                    "topic": request.topic,
                    "note": "Background workers only mode - ensure LiveKit service is accessible and background workers are running"
                }, 
                status_code=503
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
            # Get the agent info
            agent_info = active_agents[room_name]
            stopped_agents = []
            errors = []
            
            # Stop Aristotle agent if it exists
            if "aristotle_process" in agent_info:
                try:
                    aristotle_process = agent_info["aristotle_process"]
                    aristotle_process.terminate()
                    
                    # Wait for it to finish (with timeout)
                    try:
                        aristotle_process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        # Force kill if it doesn't terminate gracefully
                        aristotle_process.kill()
                        aristotle_process.wait()
                    
                    stopped_agents.append("aristotle")
                    logger.info(f"Aristotle agent stopped for room {room_name}")
                    
                except Exception as e:
                    errors.append(f"Failed to stop Aristotle: {str(e)}")
                    logger.error(f"Failed to stop Aristotle agent: {e}")
            
            # Stop Socrates agent if it exists
            if "socrates_process" in agent_info:
                try:
                    socrates_process = agent_info["socrates_process"]
                    socrates_process.terminate()
                    
                    # Wait for it to finish (with timeout)
                    try:
                        socrates_process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        # Force kill if it doesn't terminate gracefully
                        socrates_process.kill()
                        socrates_process.wait()
                    
                    stopped_agents.append("socrates")
                    logger.info(f"Socrates agent stopped for room {room_name}")
                    
                except Exception as e:
                    errors.append(f"Failed to stop Socrates: {str(e)}")
                    logger.error(f"Failed to stop Socrates agent: {e}")
            
            # Stop legacy single process if it exists (for backwards compatibility)
            if "process" in agent_info:
                try:
                    process = agent_info["process"]
                    process.terminate()
                    
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                    
                    stopped_agents.append("legacy")
                    logger.info(f"Legacy agent stopped for room {room_name}")
                    
                except Exception as e:
                    errors.append(f"Failed to stop legacy agent: {str(e)}")
                    logger.error(f"Failed to stop legacy agent: {e}")
            
            # For new agent dispatch method, terminate agents by deleting the room
            if agent_info.get("method") == "explicit_agent_dispatch" and "agents_dispatched" in agent_info:
                logger.info(f"Terminating dispatched agents by deleting room {room_name}")
                try:
                    # Initialize LiveKit API client for room deletion
                    livekit_api = api.LiveKitAPI(
                        url=LIVEKIT_URL,
                        api_key=LIVEKIT_API_KEY,
                        api_secret=LIVEKIT_API_SECRET
                    )
                    # Delete the LiveKit room to force agent cleanup
                    await livekit_api.room.delete_room(room_name)
                    logger.info(f"✅ Room {room_name} deleted - agents should terminate")
                except Exception as e:
                    logger.warning(f"Could not delete room for agent cleanup: {e}")
                    # Continue with local cleanup even if room deletion fails
            
            # Remove from active agents
            del active_agents[room_name]
            
            if errors:
                logger.warning(f"Some agents failed to stop cleanly: {errors}")
                return {
                    "status": "partial_success",
                    "message": f"Some agents stopped with errors for room: {room_name}",
                    "room_name": room_name,
                    "agents_active": False,
                    "stopped_agents": stopped_agents,
                    "errors": errors
                }
            else:
                logger.info(f"All AI agents stopped successfully for room {room_name}")
                return {
                    "status": "success",
                    "message": f"All AI agents stopped for room: {room_name}",
                    "room_name": room_name,
                    "agents_active": False,
                    "stopped_agents": stopped_agents
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
        current_time = time.time()
        
        for room_name, agent_info in active_agents.items():
            # Handle both new dual-agent and legacy single-agent structures
            # Use "created_at" for new agent dispatch, "started_at" for legacy
            start_time = agent_info.get("created_at", agent_info.get("started_at", current_time))
            
            room_status = {
                "topic": agent_info["topic"],
                "started_at": start_time,
                "uptime_seconds": round(current_time - start_time, 2),
                "uptime_minutes": round((current_time - start_time) / 60, 2),
                "retry_count": agent_info.get("retry_count", 0),
                "status": agent_info.get("status", "unknown"),
                "connection_result": agent_info.get("connection_result", {}),
                "connection_error": agent_info.get("connection_error"),
                "method": agent_info.get("method", "legacy"),
                "agents": {}
            }
            
            room_is_dead = True
            
            # Handle new agent dispatch structure
            if agent_info.get("method") == "explicit_agent_dispatch" and "agents_dispatched" in agent_info:
                agents_dispatched = agent_info["agents_dispatched"]
                for agent_name, agent_data in agents_dispatched.items():
                    room_status["agents"][agent_name] = {
                        "dispatch_id": agent_data.get("dispatch_id", "unknown"),
                        "role": agent_data.get("role", "unknown"),
                        "status": agent_data.get("status", "unknown"),
                        "method": "agent_dispatch",
                        "running": agent_data.get("status") == "dispatched"
                    }
                    if agent_data.get("status") == "dispatched":
                        room_is_dead = False
            
            # Check Aristotle agent process if it exists (legacy subprocess method)
            elif "aristotle_process" in agent_info:
                aristotle_process = agent_info["aristotle_process"]
                aristotle_running = aristotle_process.poll() is None
                room_status["agents"]["aristotle"] = {
                    "process_id": aristotle_process.pid,
                    "role": "logical moderator with reason + structure",
                    "running": aristotle_running,
                    "method": "subprocess",
                    "return_code": aristotle_process.returncode if not aristotle_running else None
                }
                if aristotle_running:
                    room_is_dead = False
            
            # Check Socrates agent process if it exists (legacy subprocess method)
            if "socrates_process" in agent_info:
                socrates_process = agent_info["socrates_process"]
                socrates_running = socrates_process.poll() is None
                room_status["agents"]["socrates"] = {
                    "process_id": socrates_process.pid,
                    "role": "inquisitive challenger with questioning + truth-seeking",
                    "running": socrates_running,
                    "method": "subprocess",
                    "return_code": socrates_process.returncode if not socrates_running else None
                }
                if socrates_running:
                    room_is_dead = False
            
            # Check legacy single process if it exists (backwards compatibility)
            elif "process" in agent_info:
                process = agent_info["process"]
                legacy_running = process.poll() is None
                room_status["agents"]["legacy"] = {
                    "process_id": process.pid,
                    "role": "multi-personality agent",
                    "running": legacy_running,
                    "method": "subprocess",
                    "return_code": process.returncode if not legacy_running else None
                }
                if legacy_running:
                    room_is_dead = False
            
            if room_is_dead:
                dead_rooms.append(room_name)
            
            detailed_status[room_name] = room_status
        
        # Clean up dead processes
        for room_name in dead_rooms:
            logger.info(f"Cleaning up dead agent processes for room {room_name}")
            del active_agents[room_name]
        
        # Summary statistics
        total_agents = 0
        running_agents = 0
        failed_agents = 0
        connected_agents = 0
        
        for room_status in detailed_status.values():
            for agent_name, agent_data in room_status["agents"].items():
                total_agents += 1
                if agent_data["running"]:
                    running_agents += 1
                else:
                    failed_agents += 1
            
            if room_status["status"] == "connected":
                connected_agents += 1
        
        return {
            "status": "success",
            "timestamp": current_time,
            "summary": {
                "total_rooms": len(detailed_status),
                "total_agents": total_agents,
                "running_agents": running_agents,
                "connected_agents": connected_agents,
                "failed_agents": failed_agents,
                "dead_rooms_cleaned": len(dead_rooms)
            },
            "rooms": detailed_status,
            "monitoring_info": {
                "agent_connection_timeout": 30,
                "max_retries": 3,
                "retry_delay": 2,
                "agent_types": ["aristotle", "socrates"]
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
        start_time = agent_info.get("created_at", agent_info.get("started_at", current_time))
        uptime = current_time - start_time
        
        health_data = {
            "room_name": room_name,
            "healthy": is_running and agent_info.get("status") == "connected",
            "process_running": is_running,
            "connection_status": agent_info.get("status", "unknown"),
            "uptime_seconds": round(uptime, 2),
            "process_id": process.pid,
            "topic": agent_info["topic"],
            "started_at": start_time,
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
            room_name=request.room_token,
            debate_topic="AI Debate",
            livekit_token=request.room_token,  # Using token as a placeholder
            participants=[]
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
            room_name=request.room_token,
            debate_topic="AI Debate",
            livekit_token=request.room_token,
            participants=[]
        )
        
        # Store the segment - note: this function needs more parameters
        # For now, using defaults since the API doesn't provide all required fields
        success = await store_debate_segment(
            room_id=room_id,
            session_number=1,  # Default session
            segment_number=1,  # Would need to track this
            speaker_role=request.speaker_type,
            speaker_name=request.speaker_name or "Anonymous",
            content_text=request.content or "",
            key_points=[]
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
        # Retrieve memory data using room name (token as room identifier)
        memory_data = await get_debate_memory(
            room_name=room_token,
            session_number=None,  # Get all sessions
            max_segments=10
        )
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
        # Worker mode is deprecated - use render.yaml background workers instead
        logger.error("Worker mode deprecated - use render.yaml background workers instead")
        sys.exit(1)
    else:
        logger.info("Running in web service mode")
        uvicorn.run(app, host="0.0.0.0", port=8000) 
