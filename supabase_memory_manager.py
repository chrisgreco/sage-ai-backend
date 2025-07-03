#!/usr/bin/env python3

"""
Supabase Memory Manager for Sage AI Debate Moderator
Handles persistent storage of debate context, participant memory, and conversation history
"""

import os
import asyncio
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
import json

from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class SupabaseMemoryManager:
    """Manages debate memory and context using Supabase"""
    
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            logger.warning("Supabase credentials not found. Memory features will be disabled.")
            self.client = None
            return
            
        try:
            self.client: Client = create_client(self.supabase_url, self.supabase_key)
            logger.info("Supabase memory manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            self.client = None

    async def store_debate_session(self, room_name: str, topic: str, persona: str, participants: List[str]) -> Optional[str]:
        """Store a new debate session"""
        if not self.client:
            return None
            
        try:
            data = {
                "room_name": room_name,
                "topic": topic,
                "moderator_persona": persona,
                "participants": participants,
                "created_at": datetime.utcnow().isoformat(),
                "status": "active"
            }
            
            result = self.client.table("debate_sessions").insert(data).execute()
            session_id = result.data[0]["id"] if result.data else None
            
            logger.info(f"Stored debate session {session_id} for room {room_name}")
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to store debate session: {e}")
            return None

    async def get_debate_session(self, room_name: str) -> Optional[Dict[str, Any]]:
        """Get debate session by room name"""
        if not self.client:
            return None
            
        try:
            result = self.client.table("debate_sessions") \
                .select("*") \
                .eq("room_name", room_name) \
                .eq("status", "active") \
                .execute()
            
            return result.data[0] if result.data else None
            
        except Exception as e:
            logger.error(f"Failed to get debate session: {e}")
            return None

    async def store_conversation_turn(self, session_id: str, speaker: str, content: str, turn_type: str = "speech") -> bool:
        """Store a conversation turn"""
        if not self.client:
            return False
            
        try:
            data = {
                "session_id": session_id,
                "speaker": speaker,
                "content": content,
                "turn_type": turn_type,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self.client.table("conversation_turns").insert(data).execute()
            logger.debug(f"Stored conversation turn from {speaker}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store conversation turn: {e}")
            return False

    async def get_recent_conversation(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent conversation turns"""
        if not self.client:
            return []
            
        try:
            result = self.client.table("conversation_turns") \
                .select("*") \
                .eq("session_id", session_id) \
                .order("timestamp", desc=True) \
                .limit(limit) \
                .execute()
            
            # Reverse to get chronological order
            return list(reversed(result.data)) if result.data else []
            
        except Exception as e:
            logger.error(f"Failed to get recent conversation: {e}")
            return []

    async def store_participant_memory(self, session_id: str, participant: str, memory_type: str, content: str) -> bool:
        """Store participant-specific memory"""
        if not self.client:
            return False
            
        try:
            data = {
                "session_id": session_id,
                "participant": participant,
                "memory_type": memory_type,
                "content": content,
                "created_at": datetime.utcnow().isoformat()
            }
            
            self.client.table("participant_memory").insert(data).execute()
            logger.debug(f"Stored {memory_type} memory for {participant}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store participant memory: {e}")
            return False

    async def get_participant_memory(self, session_id: str, participant: str, memory_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get participant memory"""
        if not self.client:
            return []
            
        try:
            query = self.client.table("participant_memory") \
                .select("*") \
                .eq("session_id", session_id) \
                .eq("participant", participant)
            
            if memory_type:
                query = query.eq("memory_type", memory_type)
            
            result = query.order("created_at", desc=True).execute()
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Failed to get participant memory: {e}")
            return []

    async def store_moderation_action(self, session_id: str, action_type: str, details: Dict[str, Any]) -> bool:
        """Store AI moderation action"""
        if not self.client:
            return False
            
        try:
            data = {
                "session_id": session_id,
                "action_type": action_type,
                "details": json.dumps(details),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self.client.table("moderation_actions").insert(data).execute()
            logger.debug(f"Stored moderation action: {action_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store moderation action: {e}")
            return False

    async def get_debate_context(self, session_id: str) -> Dict[str, Any]:
        """Get comprehensive debate context for AI agents"""
        if not self.client:
            return {}
            
        try:
            # Get session info
            session = await self.get_debate_session_by_id(session_id)
            if not session:
                return {}
            
            # Get recent conversation
            recent_conversation = await self.get_recent_conversation(session_id, limit=20)
            
            # Get all participant memories
            participants = session.get("participants", [])
            participant_memories = {}
            for participant in participants:
                memories = await self.get_participant_memory(session_id, participant)
                participant_memories[participant] = memories
            
            # Get recent moderation actions
            moderation_actions = await self.get_recent_moderation_actions(session_id, limit=10)
            
            return {
                "session": session,
                "recent_conversation": recent_conversation,
                "participant_memories": participant_memories,
                "moderation_actions": moderation_actions,
                "context_retrieved_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get debate context: {e}")
            return {}

    async def get_debate_session_by_id(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get debate session by ID"""
        if not self.client:
            return None
            
        try:
            result = self.client.table("debate_sessions") \
                .select("*") \
                .eq("id", session_id) \
                .execute()
            
            return result.data[0] if result.data else None
            
        except Exception as e:
            logger.error(f"Failed to get debate session by ID: {e}")
            return None

    async def get_recent_moderation_actions(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent moderation actions"""
        if not self.client:
            return []
            
        try:
            result = self.client.table("moderation_actions") \
                .select("*") \
                .eq("session_id", session_id) \
                .order("timestamp", desc=True) \
                .limit(limit) \
                .execute()
            
            # Parse JSON details
            actions = []
            for action in result.data or []:
                try:
                    action["details"] = json.loads(action["details"])
                except:
                    pass
                actions.append(action)
            
            return actions
            
        except Exception as e:
            logger.error(f"Failed to get recent moderation actions: {e}")
            return []

    async def end_debate_session(self, session_id: str) -> bool:
        """Mark debate session as ended"""
        if not self.client:
            return False
            
        try:
            self.client.table("debate_sessions") \
                .update({"status": "ended", "ended_at": datetime.utcnow().isoformat()}) \
                .eq("id", session_id) \
                .execute()
            
            logger.info(f"Ended debate session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to end debate session: {e}")
            return False

    async def cleanup_old_sessions(self, days_old: int = 7) -> int:
        """Clean up old debate sessions"""
        if not self.client:
            return 0
            
        try:
            cutoff_date = (datetime.utcnow() - timedelta(days=days_old)).isoformat()
            
            # Get old sessions
            result = self.client.table("debate_sessions") \
                .select("id") \
                .lt("created_at", cutoff_date) \
                .execute()
            
            old_session_ids = [session["id"] for session in result.data or []]
            
            if not old_session_ids:
                return 0
            
            # Delete related data
            for session_id in old_session_ids:
                # Delete conversation turns
                self.client.table("conversation_turns").delete().eq("session_id", session_id).execute()
                # Delete participant memory
                self.client.table("participant_memory").delete().eq("session_id", session_id).execute()
                # Delete moderation actions
                self.client.table("moderation_actions").delete().eq("session_id", session_id).execute()
            
            # Delete sessions
            self.client.table("debate_sessions").delete().in_("id", old_session_ids).execute()
            
            logger.info(f"Cleaned up {len(old_session_ids)} old debate sessions")
            return len(old_session_ids)
            
        except Exception as e:
            logger.error(f"Failed to cleanup old sessions: {e}")
            return 0

# Global instance
memory_manager = SupabaseMemoryManager() 