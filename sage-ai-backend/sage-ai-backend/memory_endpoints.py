'# Memory Management API Endpoints for Supabase Integration' 

import logging
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Import memory manager with fallback
try:
    from supabase_memory_manager import (
        create_or_get_debate_room,
        store_debate_segment,
        get_debate_memory,
        store_ai_memory,
        memory_manager
    )
    SUPABASE_AVAILABLE = True
except ImportError as e:
    SUPABASE_AVAILABLE = False
    # Create dummy functions to prevent errors
    async def create_or_get_debate_room(*args, **kwargs): return None
    async def store_debate_segment(*args, **kwargs): return False
    async def get_debate_memory(*args, **kwargs): return {"recent_segments": [], "session_summaries": [], "personality_memories": {}}
    async def store_ai_memory(*args, **kwargs): return False

logger = logging.getLogger(__name__)

class MemoryRequest(BaseModel):
    room_token: str
    content: str = None
    speaker_name: str = None
    speaker_type: str = "human"  # or "ai"
    segment_type: str = "conversation"

def setup_memory_endpoints(app):
    """Add memory management endpoints to FastAPI app"""
    
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
    
    logger.info("✅ Memory management endpoints registered") 
