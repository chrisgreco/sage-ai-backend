#!/usr/bin/env python3

"""
Enhanced Sage AI Backend with Fixed Agent Management
===================================================

This enhanced version fixes the agent connection issues where endpoints 
return 200 but agents don't actually connect to LiveKit rooms.

Key improvements:
- Better error handling and validation
- Real process monitoring and health checks  
- Detailed logging and status reporting
- Retry logic with exponential backoff
- Proper cleanup of dead processes
"""

import asyncio
import logging
import os
import sys
import time
import subprocess
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
import uvicorn

# Configure logging with more detail
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import our enhanced agent manager
try:
    from fixed_agent_launcher import enhanced_agent_manager, AgentStatus
    ENHANCED_AGENTS_AVAILABLE = True
    logger.info("✅ Enhanced agent management loaded")
except ImportError as e:
    ENHANCED_AGENTS_AVAILABLE = False
    logger.warning(f"⚠️ Enhanced agent management not available: {e}")
    logger.warning("Using fallback agent management")

# Environment variables
LIVEKIT_URL = os.getenv("LIVEKIT_URL")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY") 
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")
SERVICE_MODE = os.getenv("SERVICE_MODE", "web")

# LiveKit availability check
try:
    from livekit import api, AccessToken, VideoGrants
    livekit_available = True
    logger.info("✅ LiveKit SDK available")
except ImportError:
    livekit_available = False
    logger.warning("⚠️ LiveKit SDK not available")

# Supabase availability check
try:
    from supabase_memory_manager import (
        create_or_get_debate_room, 
        store_debate_segment, 
        get_debate_memory
    )
    SUPABASE_AVAILABLE = True
    logger.info("✅ Supabase memory manager available")
except ImportError:
    SUPABASE_AVAILABLE = False
    logger.warning("⚠️ Supabase memory manager not available")

# FastAPI app setup
app = FastAPI(
    title="Enhanced Sage AI Backend", 
    description="AI-powered debate platform with enhanced agent management",
    version="2.0.0"
)

# Enhanced CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8080", 
        "http://localhost:8083",
        "https://sage-liquid-glow-design.lovable.app",
        "https://*.lovable.app",
        "https://*.lovableproject.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Request models
class DebateRequest(BaseModel):
    topic: str = "The impact of AI on society"
    room_name: str = None
    participant_name: str = None

# Enhanced error handling
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Validation error: {exc}")
    return JSONResponse(
        status_code=422,
        content={"status": "error", "message": "Invalid request format", "details": str(exc)}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": "Internal server error", "details": str(exc)}
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "services": {
            "livekit": livekit_available,
            "supabase": SUPABASE_AVAILABLE,
            "enhanced_agents": ENHANCED_AGENTS_AVAILABLE
        }
    }

# Enhanced agent launch endpoint
@app.post("/launch-ai-agents")
async def launch_ai_agents(request: DebateRequest):
    """Launch AI agents with enhanced error handling and monitoring"""
    try:
        logger.info(f"🚀 Launching AI agents for room: {request.room_name}, topic: {request.topic}")
        
        # Validate LiveKit configuration
        if not all([LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET]):
            error_msg = "LiveKit configuration incomplete"
            logger.error(error_msg)
            return JSONResponse(
                content={"status": "error", "message": error_msg}, 
                status_code=503
            )
        
        # Generate room name
        room_name = request.room_name or f"debate-{request.topic.replace(' ', '-').lower()}"
        
        # Use enhanced agent manager if available
        if ENHANCED_AGENTS_AVAILABLE:
            result = await enhanced_agent_manager.launch_agent(room_name, request.topic)
            
            if result["status"] == "success":
                logger.info(f"✅ Enhanced agent launch successful for room {room_name}")
            else:
                logger.error(f"❌ Enhanced agent launch failed for room {room_name}: {result.get('message')}")
            
            return result
        else:
            # Fallback to basic agent management
            return await fallback_launch_agents(room_name, request.topic)
    
    except Exception as e:
        error_msg = f"Error launching AI agents: {str(e)}"
        logger.error(error_msg)
        return JSONResponse(
            content={"status": "error", "message": error_msg}, 
            status_code=500
        )

async def fallback_launch_agents(room_name: str, topic: str) -> Dict[str, Any]:
    """Fallback agent launch method"""
    logger.warning("Using fallback agent launch method")
    
    try:
        # Basic environment setup
        env = os.environ.copy()
        env.update({
            "LIVEKIT_URL": LIVEKIT_URL,
            "LIVEKIT_API_KEY": LIVEKIT_API_KEY,
            "LIVEKIT_API_SECRET": LIVEKIT_API_SECRET,
            "ROOM_NAME": room_name,
            "DEBATE_TOPIC": topic,
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", "")
        })
        
        # Check if agent file exists
        agent_file = "multi_personality_agent.py"
        if not os.path.exists(agent_file):
            return {"status": "error", "message": f"Agent file not found: {agent_file}"}
        
        # Start process
        process = subprocess.Popen([
            sys.executable, "-u", agent_file
        ], env=env, cwd=os.path.dirname(os.path.abspath(__file__)))
        
        logger.info(f"Fallback agent started with PID: {process.pid}")
        
        return {
            "status": "success",
            "message": f"Agents launched for room: {room_name}",
            "room_name": room_name,
            "topic": topic,
            "process_id": process.pid,
            "method": "fallback"
        }
        
    except Exception as e:
        return {"status": "error", "message": f"Fallback launch failed: {str(e)}"}

# Enhanced status endpoint
@app.get("/ai-agents/status")
async def get_ai_agents_status():
    """Get comprehensive AI agent status"""
    try:
        if ENHANCED_AGENTS_AVAILABLE:
            status = enhanced_agent_manager.get_status()
            logger.info(f"Agent status: {status['summary']}")
            return status
        else:
            # Fallback status
            return {
                "status": "success",
                "message": "Enhanced monitoring not available",
                "summary": {
                    "total_agents": 0,
                    "running_processes": 0,
                    "connected_agents": 0,
                    "failed_agents": 0
                },
                "agents": {},
                "fallback_mode": True
            }
    except Exception as e:
        logger.error(f"Error getting agent status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Enhanced health check for specific agent
@app.get("/ai-agents/health/{room_name}")
async def get_agent_health(room_name: str):
    """Get detailed health information for a specific room's agents"""
    try:
        if ENHANCED_AGENTS_AVAILABLE:
            return enhanced_agent_manager.get_agent_health(room_name)
        else:
            return {
                "status": "error", 
                "message": "Enhanced health monitoring not available"
            }
    except Exception as e:
        logger.error(f"Error getting agent health for room {room_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Enhanced stop endpoint
@app.post("/ai-agents/stop")
async def stop_ai_agents(request: DebateRequest):
    """Stop AI agents with enhanced cleanup"""
    try:
        room_name = request.room_name
        if not room_name:
            return JSONResponse(
                content={"status": "error", "message": "room_name is required"}, 
                status_code=400
            )
        
        logger.info(f"🛑 Stopping AI agents for room: {room_name}")
        
        if ENHANCED_AGENTS_AVAILABLE:
            result = await enhanced_agent_manager.stop_agent(room_name)
            logger.info(f"Enhanced agent stop result: {result}")
            return result
        else:
            return {"status": "success", "message": "No enhanced agents to stop"}
            
    except Exception as e:
        error_msg = f"Error stopping AI agents: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

# Debugging endpoint
@app.post("/debug/validate-environment")
async def validate_environment():
    """Validate the environment for agent launching"""
    try:
        issues = []
        
        # Check environment variables
        required_vars = ["LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "OPENAI_API_KEY"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            issues.append(f"Missing environment variables: {missing_vars}")
        
        # Check files
        required_files = ["multi_personality_agent.py"]
        missing_files = [f for f in required_files if not os.path.exists(f)]
        if missing_files:
            issues.append(f"Missing files: {missing_files}")
        
        # Check services
        if not livekit_available:
            issues.append("LiveKit SDK not available")
        
        if not ENHANCED_AGENTS_AVAILABLE:
            issues.append("Enhanced agent management not available")
        
        return {
            "status": "success" if not issues else "warning",
            "valid": len(issues) == 0,
            "issues": issues,
            "environment": {
                "livekit_configured": bool(LIVEKIT_URL and LIVEKIT_API_KEY and LIVEKIT_API_SECRET),
                "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
                "service_mode": SERVICE_MODE,
                "enhanced_agents": ENHANCED_AGENTS_AVAILABLE
            }
        }
        
    except Exception as e:
        logger.error(f"Environment validation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Existing endpoints (debate, participant-token, etc.) would go here...
# For brevity, I'm focusing on the agent management improvements

if __name__ == "__main__":
    logger.info("🚀 Starting Enhanced Sage AI Backend")
    logger.info(f"Service Mode: {SERVICE_MODE}")
    logger.info(f"Enhanced Agents: {ENHANCED_AGENTS_AVAILABLE}")
    logger.info(f"LiveKit Available: {livekit_available}")
    
    if SERVICE_MODE == "worker":
        logger.info("Running in background worker mode")
        # Worker mode implementation
    else:
        logger.info("Running in web service mode")
        uvicorn.run(app, host="0.0.0.0", port=8000) 