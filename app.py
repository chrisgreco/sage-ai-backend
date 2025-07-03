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
        agent_info = active_agents[room_name].copy()
        
        # Check if process is still running
        if "process_id" in agent_info:
            try:
                import psutil
                process = psutil.Process(agent_info["process_id"])
                agent_info["process_running"] = process.is_running()
                agent_info["process_status"] = process.status()
            except (psutil.NoSuchProcess, ImportError):
                agent_info["process_running"] = False
                agent_info["process_status"] = "not_found"
        
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
    """Start the LiveKit agent process with topic and persona context"""
    try:
        # Generate agent token with proper identity matching frontend expectations
        agent_identity = f"sage-ai-{persona.lower()}"  # Use consistent naming
        agent_token = api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET) \
            .with_identity(agent_identity) \
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
                "participant_type": "agent",
                "agent_state": "initializing"
            })
        
        jwt_token = agent_token.to_jwt()
        
        # Set environment variables for the agent process
        env = os.environ.copy()
        env.update({
            "LIVEKIT_URL": LIVEKIT_URL,
            "LIVEKIT_TOKEN": jwt_token,
            "DEBATE_TOPIC": topic,
            "MODERATOR_PERSONA": persona,
            "ROOM_NAME": room_name,
            # Ensure all required API keys are passed
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
            "PERPLEXITY_API_KEY": os.getenv("PERPLEXITY_API_KEY", ""),
            "CARTESIA_API_KEY": os.getenv("CARTESIA_API_KEY", ""),
            "DEEPGRAM_API_KEY": os.getenv("DEEPGRAM_API_KEY", ""),
            "SUPABASE_URL": os.getenv("SUPABASE_URL", ""),
            "SUPABASE_KEY": os.getenv("SUPABASE_KEY", ""),
        })
        
        # Start the agent process with proper error handling
        import subprocess
        import sys
        
        # Use the proper command for LiveKit agents
        # On Windows, use the batch file for better debugging
        if os.name == 'nt':  # Windows
            cmd = ["start_agent.bat"]
        else:  # Unix/Linux
            cmd = ["./start_agent.sh"]
        
        logger.info(f"Starting agent with command: {' '.join(cmd)}")
        logger.info(f"Environment variables set: LIVEKIT_URL, DEBATE_TOPIC={topic}, MODERATOR_PERSONA={persona}")
        
        process = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Combine stderr with stdout
            universal_newlines=True,
            bufsize=1,  # Line buffered
            shell=True  # Required for batch files on Windows
        )
        
        # Update status
        if room_name in active_agents:
            active_agents[room_name]["status"] = "active"
            active_agents[room_name]["process_id"] = process.pid
            active_agents[room_name]["agent_identity"] = agent_identity
        
        logger.info(f"✅ Started agent process {process.pid} for room {room_name}")
        
        # Monitor process in background (non-blocking)
        asyncio.create_task(monitor_agent_process(room_name, process))
        
    except Exception as e:
        logger.error(f"❌ Failed to start agent process: {e}")
        if room_name in active_agents:
            active_agents[room_name]["status"] = "failed"
            active_agents[room_name]["error"] = str(e)

async def monitor_agent_process(room_name: str, process):
    """Monitor the agent process and handle failures"""
    try:
        # Wait for process to complete (or crash)
        await asyncio.get_event_loop().run_in_executor(None, process.wait)
        
        # Process has ended
        return_code = process.returncode
        
        if return_code == 0:
            logger.info(f"✅ Agent process for room {room_name} completed successfully")
        else:
            logger.error(f"❌ Agent process for room {room_name} exited with code {return_code}")
            
            # Get the last output for debugging
            try:
                stdout, stderr = process.communicate(timeout=1)
                if stdout:
                    logger.error(f"Agent stdout: {stdout}")
                if stderr:
                    logger.error(f"Agent stderr: {stderr}")
            except Exception as e:
                logger.warning(f"Could not get process output: {e}")
        
        # Update status
        if room_name in active_agents:
            active_agents[room_name]["status"] = "completed" if return_code == 0 else "failed"
            active_agents[room_name]["exit_code"] = return_code
            active_agents[room_name]["ended_at"] = datetime.utcnow().isoformat()
            
    except Exception as e:
        logger.error(f"❌ Error monitoring agent process for room {room_name}: {e}")
        if room_name in active_agents:
            active_agents[room_name]["status"] = "error"
            active_agents[room_name]["error"] = str(e)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port) 