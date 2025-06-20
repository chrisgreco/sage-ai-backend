"""
Supabase Memory Manager for AI Debate Agents
Handles persistent conversation memory and context across debate sessions
"""

import os
import logging
import asyncio
import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class SupabaseMemoryManager:
    """Manages conversation memory in Supabase for AI debate rooms"""
    
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL", "https://zpfouxphwgtqhgalzyqk.supabase.co")
        self.supabase_key = os.getenv("SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpwZm91eHBod2d0cWhnYWx6eXFrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDk1OTc5MTYsImV4cCI6MjA2NTE3MzkxNn0.uzlPeumvFwJKdGR5rHyclBkc5ZMFH5NhJ41iROfRZmU")
        
        if not self.supabase_url or not self.supabase_key:
            logger.error("Supabase credentials not found in environment")
            self.client = None
        else:
            try:
                self.client: Client = create_client(self.supabase_url, self.supabase_key)
                logger.info("✅ Supabase client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")
                self.client = None
    
    def _hash_token(self, token: str) -> str:
        """Create a secure hash of the LiveKit token for room identification"""
        return hashlib.sha256(token.encode()).hexdigest()
    
    async def create_or_get_room(
        self, 
        room_name: str, 
        debate_topic: str, 
        livekit_token: str,
        participants: List[Dict] = None
    ) -> Optional[str]:
        """Create or retrieve a debate room record
        
        Returns:
            room_id (UUID) if successful, None if failed
        """
        if not self.client:
            logger.error("Supabase client not available")
            return None
            
        try:
            token_hash = self._hash_token(livekit_token)
            
            # Check if room already exists
            existing_room = self.client.table("debate_rooms").select("id").eq("room_name", room_name).execute()
            
            if existing_room.data:
                room_id = existing_room.data[0]["id"]
                logger.info(f"📍 Using existing room: {room_name} ({room_id})")
                
                # Update room with new token and participants
                self.client.table("debate_rooms").update({
                    "livekit_token_hash": token_hash,
                    "participants": participants or [],
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "status": "active"
                }).eq("id", room_id).execute()
                
                return room_id
            else:
                # Create new room
                new_room = self.client.table("debate_rooms").insert({
                    "room_name": room_name,
                    "debate_topic": debate_topic,
                    "livekit_token_hash": token_hash,
                    "participants": participants or [],
                    "status": "active"
                }).execute()
                
                if new_room.data:
                    room_id = new_room.data[0]["id"]
                    logger.info(f"🏗️ Created new room: {room_name} ({room_id})")
                    return room_id
                else:
                    logger.error(f"Failed to create room: {room_name}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error managing room {room_name}: {e}")
            return None
    
    async def store_conversation_segment(
        self,
        room_id: str,
        session_number: int,
        segment_number: int,
        speaker_role: str,  # 'human', 'socrates', 'aristotle', 'buddha', 'hermes', 'solon'
        speaker_name: str,
        content_text: str,
        key_points: List[str] = None,
        references_to: List[str] = None
    ) -> bool:
        """Store a conversation segment in Supabase
        
        Returns:
            True if successful, False if failed
        """
        if not self.client:
            return False
            
        try:
            segment_data = {
                "room_id": room_id,
                "session_number": session_number,
                "segment_number": segment_number,
                "speaker_role": speaker_role,
                "speaker_name": speaker_name,
                "content_text": content_text,
                "key_points": key_points or [],
                "references_to": references_to or [],
                "timestamp_start": datetime.now(timezone.utc).isoformat(),
                "token_count": len(content_text.split()) * 1.3  # Rough estimate
            }
            
            result = self.client.table("conversation_memory").insert(segment_data).execute()
            
            if result.data:
                logger.debug(f"💾 Stored segment {segment_number} for {speaker_role}: {speaker_name}")
                return True
            else:
                logger.error(f"Failed to store segment: {segment_data}")
                return False
                
        except Exception as e:
            logger.error(f"Error storing conversation segment: {e}")
            return False
    
    async def get_room_memory_context(
        self,
        room_name: str,
        session_number: int = None,
        max_segments: int = 10
    ) -> Dict:
        """Retrieve conversation context for a room
        
        Returns:
            Dictionary with recent_segments, session_summaries, and personality_memories
        """
        if not self.client:
            return {"recent_segments": [], "session_summaries": [], "personality_memories": {}}
            
        try:
            # Get room ID
            room_result = self.client.table("debate_rooms").select("id, session_count").eq("room_name", room_name).execute()
            if not room_result.data:
                logger.warning(f"Room not found: {room_name}")
                return {"recent_segments": [], "session_summaries": [], "personality_memories": {}}
            
            room_id = room_result.data[0]["id"]
            current_session = session_number or room_result.data[0]["session_count"]
            
            # Get recent conversation segments
            segments_query = self.client.table("conversation_memory").select(
                "segment_number, speaker_role, speaker_name, content_text, content_summary, key_points, timestamp_start, is_compressed"
            ).eq("room_id", room_id)
            
            if session_number:
                segments_query = segments_query.eq("session_number", session_number)
            else:
                # Get from current and previous session
                segments_query = segments_query.gte("session_number", max(1, current_session - 1))
            
            segments_result = segments_query.order("session_number", desc=False).order("segment_number", desc=False).limit(max_segments).execute()
            
            # Get session summaries
            summaries_result = self.client.table("debate_context").select(
                "context_type, content, session_number, importance_score"
            ).eq("room_id", room_id).order("importance_score", desc=True).limit(5).execute()
            
            # Get personality memories for each AI agent
            personalities = ["socrates", "aristotle", "buddha", "hermes", "solon"]
            personality_memories = {}
            
            for personality in personalities:
                memory_result = self.client.table("personality_memory").select(
                    "memory_type, content, session_number, relevance_score"
                ).eq("room_id", room_id).eq("personality", personality).order("relevance_score", desc=True).limit(3).execute()
                
                personality_memories[personality] = memory_result.data if memory_result.data else []
            
            return {
                "recent_segments": segments_result.data if segments_result.data else [],
                "session_summaries": summaries_result.data if summaries_result.data else [],
                "personality_memories": personality_memories,
                "room_id": room_id,
                "current_session": current_session
            }
            
        except Exception as e:
            logger.error(f"Error retrieving room memory context: {e}")
            return {"recent_segments": [], "session_summaries": [], "personality_memories": {}}
    
    async def store_personality_memory(
        self,
        room_id: str,
        personality: str,
        memory_type: str,  # 'key_question', 'stance_taken', 'insight_shared', 'moderation_action'
        content: str,
        session_number: int,
        relevance_score: int = 5
    ) -> bool:
        """Store a memory for a specific AI personality
        
        Returns:
            True if successful, False if failed
        """
        if not self.client:
            return False
            
        try:
            memory_data = {
                "room_id": room_id,
                "personality": personality,
                "memory_type": memory_type,
                "content": content,
                "session_number": session_number,
                "relevance_score": relevance_score
            }
            
            result = self.client.table("personality_memory").insert(memory_data).execute()
            
            if result.data:
                logger.debug(f"🧠 Stored {personality} memory: {memory_type}")
                return True
            else:
                logger.error(f"Failed to store personality memory: {memory_data}")
                return False
                
        except Exception as e:
            logger.error(f"Error storing personality memory: {e}")
            return False
    
    async def create_session_summary(
        self,
        room_id: str,
        session_number: int,
        summary_text: str,
        context_type: str = "session_summary",
        importance_score: int = 8
    ) -> bool:
        """Create a summary for a completed session
        
        Returns:
            True if successful, False if failed
        """
        if not self.client:
            return False
            
        try:
            summary_data = {
                "room_id": room_id,
                "session_number": session_number,
                "context_type": context_type,
                "content": summary_text,
                "importance_score": importance_score
            }
            
            result = self.client.table("debate_context").insert(summary_data).execute()
            
            if result.data:
                logger.info(f"📋 Created session {session_number} summary")
                return True
            else:
                logger.error(f"Failed to create session summary: {summary_data}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating session summary: {e}")
            return False
    
    async def increment_session(self, room_id: str) -> int:
        """Increment session count for a room (every 30 minutes)
        
        Returns:
            New session number
        """
        if not self.client:
            return 1
            
        try:
            # Get current session count
            room_result = self.client.table("debate_rooms").select("session_count").eq("id", room_id).execute()
            
            if room_result.data:
                current_session = room_result.data[0]["session_count"]
                new_session = current_session + 1
                
                # Update session count
                self.client.table("debate_rooms").update({
                    "session_count": new_session,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }).eq("id", room_id).execute()
                
                logger.info(f"🔄 Incremented to session {new_session} for room {room_id}")
                return new_session
            else:
                logger.error(f"Room not found for session increment: {room_id}")
                return 1
                
        except Exception as e:
            logger.error(f"Error incrementing session: {e}")
            return 1

# Global memory manager instance
memory_manager = SupabaseMemoryManager()

# Export availability flag for easy import
SUPABASE_AVAILABLE = memory_manager.client is not None

# Convenience functions for easy import
async def create_or_get_debate_room(room_name: str, debate_topic: str, livekit_token: str, participants: List[Dict] = None) -> Optional[str]:
    """Convenience function to create or get a debate room"""
    return await memory_manager.create_or_get_room(room_name, debate_topic, livekit_token, participants)

async def store_debate_segment(room_id: str, session_number: int, segment_number: int, speaker_role: str, speaker_name: str, content_text: str, key_points: List[str] = None) -> bool:
    """Convenience function to store a conversation segment"""
    return await memory_manager.store_conversation_segment(room_id, session_number, segment_number, speaker_role, speaker_name, content_text, key_points)

async def get_debate_memory(room_id: str, session_number: int = None, max_segments: int = 10) -> Dict:
    """Convenience function to get room memory context by room_id"""
    if not memory_manager.client:
        return {"recent_segments": [], "session_summaries": [], "personality_memories": {}}
        
    try:
        # Get room name from room_id first
        room_result = memory_manager.client.table("debate_rooms").select("room_name").eq("id", room_id).execute()
        if not room_result.data:
            logger.warning(f"Room not found for ID: {room_id}")
            return {"recent_segments": [], "session_summaries": [], "personality_memories": {}}
        
        room_name = room_result.data[0]["room_name"]
        return await memory_manager.get_room_memory_context(room_name, session_number, max_segments)
    except Exception as e:
        logger.error(f"Error in get_debate_memory: {e}")
        return {"recent_segments": [], "session_summaries": [], "personality_memories": {}}

async def store_ai_memory(room_id: str, personality: str, memory_type: str, content: str, session_number: int, relevance_score: int = 5) -> bool:
    """Convenience function to store AI personality memory"""
    return await memory_manager.store_personality_memory(room_id, personality, memory_type, content, session_number, relevance_score) 