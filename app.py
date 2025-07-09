#!/usr/bin/env python3

"""
SAGE AI Backend - LiveKit Agent Management API

This FastAPI application manages debate rooms and AI agents for the SAGE platform.
Features:
- Room creation with metadata
- AI agent launching and management  
- Participant token generation
- Health monitoring

Updated: 2025-07-06 - Added /debate endpoint for frontend compatibility
"""

import os
import asyncio
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# LiveKit imports for token generation
from livekit import api

# Environment variables are managed by Render directly - no need for dotenv
# load_dotenv() removed since Render sets environment variables

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Sage AI Backend", version="1.0.0")

# CORS middleware for frontend integration - Updated for Lovable domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",  # Allow all origins for development
        "https://lovable.dev",
        "https://lovable.app", 
        "https://*.lovable.app",
        "https://*.lovableproject.com",
        "https://1e934c03-5a1a-4df1-9eed-2c278b3ec6a8.lovable.app",  # Specific domain from error
        "http://localhost:8080",  # Local development
        "http://localhost:3000",  # Local development
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "*",
        "Authorization",
        "Content-Type", 
        "X-Requested-With",
        "Accept",
        "Origin",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers",
    ],
    expose_headers=["*"],
)

# Request/Response models
class DebateRequest(BaseModel):
    topic: str
    persona: Optional[str] = None  # No default - frontend must specify
    participant_name: Optional[str] = "User"

class TokenRequest(BaseModel):
    room_name: str
    participant_name: str
    topic: Optional[str] = None
    persona: Optional[str] = None

class AgentLaunchRequest(BaseModel):
    room_name: str
    topic: str
    persona: Optional[str] = None  # No default - frontend must specify

class AgentStopRequest(BaseModel):
    room_name: str

# LiveKit configuration
LIVEKIT_URL = os.getenv("LIVEKIT_URL")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")

# Ensure LIVEKIT_URL is in the correct format (wss:// for WebSocket connections)
if LIVEKIT_URL and LIVEKIT_URL.startswith("https://"):
    LIVEKIT_URL = LIVEKIT_URL.replace("https://", "wss://")

if not all([LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET]):
    raise ValueError("LiveKit configuration missing. Check LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET")

# Global state for active agents
active_agents: Dict[str, Dict[str, Any]] = {}

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Sage AI Backend is running", "status": "healthy"}

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "livekit_configured": bool(LIVEKIT_URL and LIVEKIT_API_KEY and LIVEKIT_API_SECRET),
        "active_agents": len(active_agents)
    }

@app.options("/{full_path:path}")
async def options_handler(full_path: str):
    """Handle CORS preflight requests"""
    return {"message": "OK"}

@app.post("/debate")
async def create_debate(request: DebateRequest):
    """Create a new debate room"""
    try:
        # Validate required fields
        if not request.persona:
            raise HTTPException(status_code=400, detail="Persona is required. Choose from: Aristotle, Socrates, Buddha")
        
        # Generate unique room name based on topic
        import hashlib
        import time
        
        topic_hash = hashlib.md5(request.topic.encode()).hexdigest()[:8]
        timestamp = int(time.time())
        room_name = f"debate-{topic_hash}-{timestamp}"
        
        logger.info(f"Created debate room {room_name} for topic: {request.topic}")
        
        return {
            "room_name": room_name,
            "topic": request.topic,
            "persona": request.persona,
            "livekit_url": LIVEKIT_URL,
            "created_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to create debate: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/participant-token")
async def generate_participant_token(request: TokenRequest):
    """Generate LiveKit token for participant with topic context"""
    try:
        # 🔍 DEBUG: Log what parameters we received from frontend
        logger.info(f"🔍 /participant-token received parameters:")
        logger.info(f"   - room_name: '{request.room_name}'")
        logger.info(f"   - participant_name: '{request.participant_name}'")
        logger.info(f"   - topic: '{request.topic}'")
        logger.info(f"   - persona: '{request.persona}'")
        
        # Create token with participant permissions
        # Ensure all required parameters are present
        if not all([LIVEKIT_API_KEY, LIVEKIT_API_SECRET, request.room_name, request.participant_name]):
            raise ValueError("Missing required parameters for token generation")
            
        # Environment variables are already set by Render - no need to set manually
        
        # Generate standard LiveKit participant token (no metadata in JWT)
        # LiveKit agents get metadata from room metadata, not participant metadata
        token_builder = api.AccessToken() \
            .with_identity(request.participant_name) \
            .with_name(request.participant_name) \
            .with_grants(api.VideoGrants(
                room_join=True,
                room=request.room_name,
            ))
            
        token = token_builder.to_jwt()
        
        # Validate token was generated successfully
        if not token:
            raise ValueError("Failed to generate JWT token")
        
        logger.info(f"✅ Generated token for {request.participant_name} in room {request.room_name}")
        
        return {
            "token": token,
            "livekit_url": LIVEKIT_URL,
            "participant_name": request.participant_name,
            "room_name": request.room_name,
            "topic": request.topic
        }
        
    except Exception as e:
        logger.error(f"Failed to generate token: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/launch-ai-agents")
async def launch_ai_agents(request: AgentLaunchRequest, background_tasks: BackgroundTasks):
    """Launch AI agents for a debate room with topic and persona context"""
    try:
        # Validate required fields
        if not request.persona:
            raise HTTPException(status_code=400, detail="Persona is required. Choose from: Aristotle, Socrates, Buddha")
            
        if request.room_name in active_agents:
            return {"message": "AI agents already active for this room", "room_name": request.room_name}
        
        # Store agent configuration
        active_agents[request.room_name] = {
            "topic": request.topic,
            "persona": request.persona,
            "launched_at": datetime.utcnow().isoformat(),
            "status": "launching"
        }
        
        # Launch agent process in background
        background_tasks.add_task(start_agent_process, request.room_name, request.topic, request.persona)
        
        logger.info(f"Launching AI agents for room {request.room_name} with topic: {request.topic}, persona: {request.persona}")
        
        return {
            "message": "AI agents launching",
            "room_name": request.room_name,
            "topic": request.topic,
            "persona": request.persona
        }
        
    except Exception as e:
        logger.error(f"Failed to launch AI agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ai-agents/stop")
async def stop_ai_agents(request: AgentStopRequest):
    """Stop AI agents for a room"""
    try:
        if request.room_name in active_agents:
            del active_agents[request.room_name]
            logger.info(f"Stopped AI agents for room {request.room_name}")
            return {"message": "AI agents stopped", "room_name": request.room_name}
        else:
            return {"message": "No active agents found for this room", "room_name": request.room_name}
            
    except Exception as e:
        logger.error(f"Failed to stop AI agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ai-agents/status/{room_name}")
async def get_agent_status(room_name: str):
    """Get status of AI agents for a room"""
    if room_name in active_agents:
        agent_info = active_agents[room_name].copy()
        return agent_info
    else:
        return {"status": "inactive", "room_name": room_name}

@app.get("/ai-agents/status")
async def get_all_agent_status():
    """Get status of all active agents"""
    return {
        "active_agents": active_agents,
        "total_agents": len(active_agents)
    }


async def start_agent_process(room_name: str, topic: str, persona: str):
    """Use official LiveKit agent dispatch with job metadata"""
    try:
        logger.info(f"🚀 Dispatching agent using official LiveKit agent dispatch for room {room_name}")
        
        # Add small delay to ensure background worker is fully registered (LiveKit best practice)
        import asyncio
        await asyncio.sleep(2)  # 2-second delay to ensure worker registration
        logger.info(f"⏰ Delay complete, proceeding with agent dispatch...")
        
        # Use official LiveKit agent dispatch API as documented
        lkapi = api.LiveKitAPI()
        try:
            # Create job metadata with topic and persona (JSON string as per docs)
            job_metadata = json.dumps({
                "topic": topic,
                "persona": persona,
                "room_name": room_name,
                "agent_type": "debate_moderator",
                "created_at": datetime.now().isoformat()
            })
            
            logger.info(f"🎯 Creating agent dispatch with job metadata: {job_metadata}")
            
            # Use official agent dispatch API as documented
            dispatch = await lkapi.agent_dispatch.create_dispatch(
                api.CreateAgentDispatchRequest(
                    agent_name="sage-debate-moderator",  # Must match agent registration name
                    room=room_name,
                    metadata=job_metadata  # Job metadata passed as JSON string
                )
            )
            
            logger.info(f"✅ Agent dispatched successfully:")
            logger.info(f"   Dispatch object: {dispatch}")
            logger.info(f"   Dispatch type: {type(dispatch)}")
            
            # Check if dispatch has expected attributes
            if hasattr(dispatch, 'dispatch_id'):
                logger.info(f"   Dispatch ID: {dispatch.dispatch_id}")
            elif hasattr(dispatch, 'id'):
                logger.info(f"   Dispatch ID: {dispatch.id}")
            else:
                logger.warning(f"   No dispatch_id or id attribute found")
                
            if hasattr(dispatch, 'agent_name'):
                logger.info(f"   Agent Name: {dispatch.agent_name}")
            else:
                logger.warning(f"   No agent_name attribute found")
                
            if hasattr(dispatch, 'room'):
                logger.info(f"   Room: {dispatch.room}")
            else:
                logger.warning(f"   No room attribute found")
            
            # Update status with dispatch information
            if room_name in active_agents:
                active_agents[room_name]["status"] = "dispatched"
                if hasattr(dispatch, 'dispatch_id'):
                    active_agents[room_name]["dispatch_id"] = dispatch.dispatch_id
                elif hasattr(dispatch, 'id'):
                    active_agents[room_name]["dispatch_id"] = dispatch.id
                if hasattr(dispatch, 'agent_name'):
                    active_agents[room_name]["agent_name"] = dispatch.agent_name
                active_agents[room_name]["job_metadata"] = job_metadata
            
        finally:
            await lkapi.aclose()
        
    except Exception as e:
        logger.error(f"❌ Failed to dispatch agent: {e}")
        if room_name in active_agents:
            active_agents[room_name]["status"] = "failed"
            active_agents[room_name]["error"] = str(e)
        # Don't raise in background task - just log the error



if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port) 