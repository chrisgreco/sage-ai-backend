#!/usr/bin/env python3

"""
Sage AI Backend - FastAPI Web Service
Handles debate room creation, LiveKit tokens, and AI agent management
"""

import os
import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# LiveKit imports for token generation
from livekit import api

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Sage AI Backend", version="1.0.0")

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class DebateRequest(BaseModel):
    topic: str
    persona: Optional[str] = "Aristotle"

class TokenRequest(BaseModel):
    room_name: str
    participant_name: str
    topic: Optional[str] = None

class AgentLaunchRequest(BaseModel):
    room_name: str
    topic: str
    persona: Optional[str] = "Aristotle"

class AgentStopRequest(BaseModel):
    room_name: str

# LiveKit configuration
LIVEKIT_URL = os.getenv("LIVEKIT_URL")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")

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

@app.post("/create-debate")
async def create_debate(request: DebateRequest):
    """Create a new debate room with topic and persona"""
    try:
        # Generate unique room name based on topic
        import hashlib
        import time
        
        topic_hash = hashlib.md5(request.topic.encode()).hexdigest()[:8]
        timestamp = int(time.time())
        room_name = f"debate-{topic_hash}-{timestamp}"
        
        logger.info(f"Creating debate room: {room_name} with topic: {request.topic}")
        
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
        # Create token with participant permissions
        token = api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET) \
            .with_identity(request.participant_name) \
            .with_name(request.participant_name) \
            .with_grants(api.VideoGrants(
                room_join=True,
                room=request.room_name,
                can_publish=True,
                can_subscribe=True,
            )) \
            .with_metadata({
                "topic": request.topic or "General Discussion",
                "participant_type": "human"
            })
        
        jwt_token = token.to_jwt()
        
        logger.info(f"Generated token for {request.participant_name} in room {request.room_name}")
        
        return {
            "token": jwt_token,
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
        return active_agents[room_name]
    else:
        return {"status": "inactive", "room_name": room_name}

async def start_agent_process(room_name: str, topic: str, persona: str):
    """Start the LiveKit agent process with topic and persona context"""
    try:
        # Generate agent token
        agent_token = api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET) \
            .with_identity(f"sage-ai-{persona.lower()}") \
            .with_name(f"Sage AI - {persona}") \
            .with_grants(api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
            )) \
            .with_metadata({
                "topic": topic,
                "persona": persona,
                "participant_type": "agent"
            })
        
        jwt_token = agent_token.to_jwt()
        
        # Set environment variables for the agent process
        env = os.environ.copy()
        env.update({
            "LIVEKIT_URL": LIVEKIT_URL,
            "LIVEKIT_TOKEN": jwt_token,
            "DEBATE_TOPIC": topic,
            "MODERATOR_PERSONA": persona,
            "ROOM_NAME": room_name
        })
        
        # Start the agent process
        import subprocess
        process = subprocess.Popen(
            ["python", "debate_moderator_agent.py", "start"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Update status
        if room_name in active_agents:
            active_agents[room_name]["status"] = "active"
            active_agents[room_name]["process_id"] = process.pid
        
        logger.info(f"Started agent process {process.pid} for room {room_name}")
        
    except Exception as e:
        logger.error(f"Failed to start agent process: {e}")
        if room_name in active_agents:
            active_agents[room_name]["status"] = "failed"
            active_agents[room_name]["error"] = str(e)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port) 