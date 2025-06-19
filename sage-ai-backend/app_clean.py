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
import subprocess
import sys
import time
import json
import threading

# Load environment variables first
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    from livekit.api import AccessToken, VideoGrants, RoomServiceClient, CreateRoomRequest
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
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # Only used to pass to agent subprocess
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")
SERVICE_MODE = os.getenv("SERVICE_MODE", "web").lower()  # Default to web service mode

# Note: OpenAI API key is only used to pass to the agent subprocess
# The main backend app only handles LiveKit tokens and agent launching

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