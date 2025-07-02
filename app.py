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
import time
import json

# Load environment variables
load_dotenv()

# Import enhanced logging configuration
try:
    from backend_modules.logging_config import setup_global_logging, agent_logger, performance_logger
    from backend_modules.routers.log_webhook import router as log_router
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

# Supabase availability is already handled by the memory manager import above

# Get environment variables
LIVEKIT_URL = os.getenv("LIVEKIT_URL")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Only used to pass to agent subprocess
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")
# SERVICE_MODE removed - only web service mode is supported now

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

# AI Agents Management - Store active agent processes with detailed status
active_agents = {}
agent_status_cache = {}

# Enhanced Launch AI Agents endpoint with room cleanup to prevent 409 conflicts
@app.post("/launch-ai-agents")
async def launch_ai_agents(request: DebateRequest):
    room_name = None
    try:
        logger.info(f"🚀 LAUNCH REQUEST - Topic: {request.topic}, Moderator: {request.moderator}, Room: {request.room_name}")
        
        # Check LiveKit configuration
        if not all([LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET]):
            logger.error("❌ CRITICAL: LiveKit configuration missing")
            logger.error(f"LIVEKIT_URL: {'SET' if LIVEKIT_URL else 'MISSING'}")
            logger.error(f"LIVEKIT_API_KEY: {'SET' if LIVEKIT_API_KEY else 'MISSING'}")
            logger.error(f"LIVEKIT_API_SECRET: {'SET' if LIVEKIT_API_SECRET else 'MISSING'}")
            return JSONResponse(
                content={
                    "status": "error", 
                    "message": "LiveKit configuration missing",
                    "details": {
                        "url": bool(LIVEKIT_URL),
                        "api_key": bool(LIVEKIT_API_KEY),
                        "api_secret": bool(LIVEKIT_API_SECRET)
                    }
                }, 
                status_code=503
            )
        
        # Generate room name
        room_name = request.room_name or f"debate-{request.topic.replace(' ', '-').lower()}"
        logger.info(f"📍 Using room name: {room_name}")
        
        # Validate moderator selection
        valid_moderators = ["Socrates", "Aristotle", "Buddha"]
        moderator = request.moderator if request.moderator in valid_moderators else "Aristotle"
        if moderator != request.moderator:
            logger.warning(f"⚠️  Invalid moderator '{request.moderator}', defaulting to '{moderator}'")
        
        logger.info(f"🎭 Selected moderator: {moderator}")
        
        # CRITICAL FIX: Remove existing room from cache to prevent 409 conflicts
        if room_name in active_agents:
            logger.warning(f"⚠️  Room {room_name} already in cache - removing to allow fresh dispatch")
            del active_agents[room_name]
            logger.info(f"🗑️  Removed {room_name} from active_agents cache")
        
        # Create LiveKit room and dispatch single agent with moderator persona
        try:
            logger.info("🔌 Initializing LiveKit API client...")
            
            # Initialize LiveKit API client with async context manager for proper cleanup
            livekit_api = api.LiveKitAPI(
                url=LIVEKIT_URL,
                api_key=LIVEKIT_API_KEY,
                api_secret=LIVEKIT_API_SECRET
            )
            logger.info("✅ LiveKit API client initialized successfully")
            
            # Import the agent dispatch protocol classes
            logger.info("📦 Importing agent dispatch modules...")
            from livekit.protocol import agent_dispatch
            logger.info("✅ Agent dispatch modules imported")
            
            # Prepare metadata for job dispatch (Context7 compliant approach)
            job_metadata = {
                "moderator_persona": moderator,
                "debate_topic": request.topic
            }
            logger.info(f"📋 Job metadata prepared: {job_metadata}")
            
            # Dispatch single agent with job metadata (Context7 compliant approach)
            logger.info(f"🚀 Creating agent dispatch request for room: {room_name}")
            
            # Convert metadata to proper format for LiveKit (Context7 requirement)
            metadata_json = json.dumps(job_metadata) if job_metadata else "{}"
            logger.info(f"📋 Serialized metadata: {metadata_json}")
            
            agent_dispatch_req = agent_dispatch.CreateAgentDispatchRequest(
                room=room_name,
                agent_name="moderator",
                metadata=metadata_json  # Must be JSON string, not dict
            )
            logger.info("✅ Agent dispatch request created")
            
            logger.info("🎯 Dispatching agent to LiveKit...")
            agent_job = await livekit_api.agent_dispatch.create_dispatch(agent_dispatch_req)
            logger.info(f"🎉 Agent successfully dispatched! Job ID: {agent_job.id}")
            
            # Store room info for tracking
            room_info = {
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
            
            active_agents[room_name] = room_info
            logger.info(f"📊 Room info stored in active_agents cache")
            
            logger.info(f"🎉 SUCCESS: Debate room ready: {room_name}")
            logger.info(f"📢 {moderator} moderator dispatched and ready")
            
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
            
        except Exception as dispatch_error:
            logger.error(f"❌ AGENT DISPATCH FAILED: {type(dispatch_error).__name__}: {str(dispatch_error)}")
            logger.error(f"📍 Room: {room_name}, Moderator: {moderator}")
            
            # Log detailed error information
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"🔍 Full error traceback:\n{error_details}")
            
            # Check specific error types
            if "connection" in str(dispatch_error).lower():
                logger.error("🔌 CONNECTION ERROR: Cannot reach LiveKit server")
            elif "authentication" in str(dispatch_error).lower() or "unauthorized" in str(dispatch_error).lower():
                logger.error("🔐 AUTHENTICATION ERROR: Invalid LiveKit credentials")
            elif "timeout" in str(dispatch_error).lower():
                logger.error("⏱️  TIMEOUT ERROR: LiveKit request timed out")
            else:
                logger.error(f"🔍 UNKNOWN ERROR TYPE: {type(dispatch_error).__name__}")
            
            return JSONResponse(
                content={
                    "status": "error", 
                    "message": f"Failed to dispatch agents: {str(dispatch_error)}",
                    "error_type": type(dispatch_error).__name__,
                    "room_name": room_name,
                    "topic": request.topic,
                    "moderator": moderator,
                    "note": "Background workers only mode - ensure LiveKit service is accessible and background workers are running",
                    "debug_info": {
                        "livekit_url": LIVEKIT_URL,
                        "has_api_key": bool(LIVEKIT_API_KEY),
                        "has_api_secret": bool(LIVEKIT_API_SECRET)
                    }
                }, 
                status_code=503
            )
    
    except Exception as general_error:
        logger.error(f"❌ GENERAL ERROR in launch_ai_agents: {type(general_error).__name__}: {str(general_error)}")
        logger.error(f"📍 Room: {room_name}")
        
        # Log full traceback for debugging
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"🔍 Full error traceback:\n{error_details}")
        
        raise HTTPException(
            status_code=500, 
            detail={
                "error": str(general_error),
                "error_type": type(general_error).__name__,
                "room_name": room_name
            }
        )

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
            
            # For agent dispatch method, terminate agents by deleting the room
            if agent_info.get("method") == "single_agent_dispatch":
                logger.info(f"Terminating dispatched agent by deleting room {room_name}")
                try:
                    # Initialize LiveKit API client for room deletion
                    livekit_api = api.LiveKitAPI(
                        url=LIVEKIT_URL,
                        api_key=LIVEKIT_API_KEY,
                        api_secret=LIVEKIT_API_SECRET
                    )
                    # Delete the LiveKit room to force agent cleanup
                    await livekit_api.room.delete_room(room_name)
                    logger.info(f"✅ Room {room_name} deleted - agent should terminate")
                except Exception as e:
                    logger.warning(f"Could not delete room for agent cleanup: {e}")
                    # Continue with local cleanup even if room deletion fails
            
            # Remove from active agents
            del active_agents[room_name]
            
            logger.info(f"AI agent stopped successfully for room {room_name}")
            return {
                "status": "success",
                "message": f"AI agent stopped for room: {room_name}",
                "room_name": room_name,
                "agents_active": False
            }
            
        except Exception as e:
            logger.error(f"Failed to stop AI agent: {str(e)}")
            # Clean up the entry even if stopping failed
            if room_name in active_agents:
                del active_agents[room_name]
            
            return JSONResponse(
                content={"status": "error", "message": f"Failed to stop AI agent: {str(e)}"}, 
                status_code=500
            )
    
    except Exception as e:
        logger.error(f"Error stopping AI agents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Enhanced AI Agents Status endpoint with detailed monitoring
@app.get("/ai-agents/status")
async def get_ai_agents_status():
    try:
        detailed_status = {}
        current_time = time.time()
        
        for room_name, agent_info in active_agents.items():
            start_time = agent_info.get("created_at", current_time)
            
            room_status = {
                "topic": agent_info["topic"],
                "moderator": agent_info.get("moderator", "Aristotle"),
                "started_at": start_time,
                "uptime_seconds": round(current_time - start_time, 2),
                "uptime_minutes": round((current_time - start_time) / 60, 2),
                "status": agent_info.get("status", "unknown"),
                "method": agent_info.get("method", "single_agent_dispatch"),
                "agent_dispatched": agent_info.get("agent_dispatched", {})
            }
            
            detailed_status[room_name] = room_status
        
        return {
            "status": "success",
            "timestamp": current_time,
            "summary": {
                "total_rooms": len(detailed_status),
                "method": "single_agent_dispatch"
            },
            "rooms": detailed_status
        }
    except Exception as e:
        logger.error(f"Error getting AI agents status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Agent health monitoring endpoint
@app.get("/ai-agents/health/{room_name}")
async def get_agent_health(room_name: str):
    """Get detailed health information for a specific room's agent"""
    try:
        if room_name not in active_agents:
            return JSONResponse(
                content={"status": "error", "message": f"No agent found for room: {room_name}"}, 
                status_code=404
            )
        
        agent_info = active_agents[room_name]
        current_time = time.time()
        start_time = agent_info.get("created_at", current_time)
        uptime = current_time - start_time
        
        health_data = {
            "room_name": room_name,
            "healthy": agent_info.get("status") == "agent_dispatched",
            "status": agent_info.get("status", "unknown"),
            "method": agent_info.get("method", "single_agent_dispatch"),
            "uptime_seconds": round(uptime, 2),
            "topic": agent_info["topic"],
            "moderator": agent_info.get("moderator", "Aristotle"),
            "started_at": start_time,
            "last_check": current_time,
            "agent_dispatched": agent_info.get("agent_dispatched", {})
        }
        
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
    logger.info("Running in web service mode")
    uvicorn.run(app, host="0.0.0.0", port=8000) 
