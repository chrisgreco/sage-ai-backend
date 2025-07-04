#!/usr/bin/env python3

"""
Supabase Memory Manager - Enhanced Memory System for LiveKit Agents
Provides conversation memory, participant memory, and session management with Supabase
Backward compatible with existing schema and supports new optimized schema
"""

import os
import json
import logging
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timezone
from supabase import create_client, Client

# Configure logging
logger = logging.getLogger(__name__)

class SupabaseMemoryManager:
    """
    Enhanced memory manager using Supabase for persistent storage.
    Supports both legacy schema (debate_rooms, conversation_memory, personality_memory)
    and new optimized schema (debate_sessions, conversation_turns, participant_memory)
    """
    
    def __init__(self):
        """Initialize Supabase client with environment variables."""
        self.client: Optional[Client] = None
        self.schema_type: Optional[str] = None  # 'legacy' or 'new'
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the Supabase client and detect schema type."""
        try:
            # Get Supabase credentials from environment variables
            # Render sets these automatically - no need for dotenv
            supabase_url = os.getenv('SUPABASE_URL')
            
            # Support both service role key and regular key
            supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
            
            if not supabase_url or not supabase_key:
                logger.warning("Supabase credentials not found. Required: SUPABASE_URL and either SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY")
                logger.info("Memory features will be disabled. Agent will continue without persistent memory.")
                return
            
            # Create Supabase client
            self.client = create_client(supabase_url, supabase_key)
            
            # Test connection and detect schema type
            self._test_connection_and_detect_schema()
            
            logger.info(f"✅ Supabase Memory Manager initialized successfully with {self.schema_type} schema")
            
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            logger.info("Memory features will be disabled. Agent will continue without persistent memory.")
            self.client = None
    
    def _test_connection_and_detect_schema(self):
        """Test connection and detect which schema is available."""
        if not self.client:
            return
            
        try:
            # Try to query new schema first
            try:
                result = self.client.table('debate_sessions').select('id').limit(1).execute()
                self.schema_type = 'new'
                logger.info("Detected new optimized database schema")
                return
            except Exception:
                pass
                
            # Fall back to legacy schema
            try:
                result = self.client.table('debate_rooms').select('id').limit(1).execute()
                self.schema_type = 'legacy'
                logger.info("Detected legacy database schema")
                return
            except Exception:
                pass
                
            # If neither works, throw error
            raise Exception("No compatible database schema found")
            
        except Exception as e:
            raise Exception(f"Database connection test failed: {e}")
    
    def is_available(self) -> bool:
        """Check if memory manager is available."""
        return self.client is not None and self.schema_type is not None
    
    async def create_session(self, room_name: str, topic: str, persona: str) -> Optional[str]:
        """Create a new debate session and return session ID."""
        if not self.is_available():
            logger.warning("Memory manager not available - session will not be persisted")
            return None
            
        try:
            if self.schema_type == 'new':
                # Use new schema
                response = self.client.table('debate_sessions').insert({
                    'room_name': room_name,
                    'topic': topic,
                    'persona': persona,
                    'participants': [],
                    'status': 'active'
                }).execute()
                
                session_id = response.data[0]['id']
                logger.info(f"Created new debate session: {session_id}")
                return session_id
                
            else:  # legacy schema
                # Use legacy schema
                response = self.client.table('debate_rooms').insert({
                    'room_name': room_name,
                    'debate_topic': topic,
                    'livekit_token_hash': f"persona_{persona}",  # Use persona as token hash
                    'status': 'active',
                    'participants': []
                }).execute()
                
                session_id = response.data[0]['id']
                logger.info(f"Created new debate room (legacy): {session_id}")
                return session_id
                
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            return None
    
    async def add_conversation_turn(self, session_id: str, speaker: str, content: str, turn_type: str = "speech") -> bool:
        """Add a conversation turn to the session."""
        if not self.is_available() or not session_id:
            return False
            
        try:
            if self.schema_type == 'new':
                # Use new schema
                self.client.table('conversation_turns').insert({
                    'session_id': session_id,
                    'speaker': speaker,
                    'content': content,
                    'turn_type': turn_type
                }).execute()
                
            else:  # legacy schema
                # Use legacy schema
                self.client.table('conversation_memory').insert({
                    'room_id': session_id,
                    'speaker_role': 'ai' if speaker.startswith('AI-') else 'human',
                    'speaker_name': speaker,
                    'content_text': content,
                    'content_summary': content[:200],  # Truncate for summary
                    'timestamp_start': datetime.now(timezone.utc).isoformat()
                }).execute()
            
            logger.debug(f"Added conversation turn for {speaker}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add conversation turn: {e}")
            return False
    
    async def add_participant_memory(self, session_id: str, participant: str, memory_type: str, content: str) -> bool:
        """Add participant-specific memory."""
        if not self.is_available() or not session_id:
            return False
            
        try:
            if self.schema_type == 'new':
                # Use new schema
                self.client.table('participant_memory').insert({
                    'session_id': session_id,
                    'participant': participant,
                    'memory_type': memory_type,
                    'content': content
                }).execute()
                
            else:  # legacy schema
                # Use legacy schema - map to personality_memory
                personality_map = {
                    'socrates': 'socrates',
                    'aristotle': 'aristotle', 
                    'buddha': 'buddha',
                    'hermes': 'hermes',
                    'solon': 'solon'
                }
                
                personality = personality_map.get(participant.lower(), 'socrates')
                
                self.client.table('personality_memory').insert({
                    'room_id': session_id,
                    'personality': personality,
                    'memory_type': memory_type,
                    'content': content,
                    'session_number': 1
                }).execute()
            
            logger.debug(f"Added participant memory for {participant}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add participant memory: {e}")
            return False
    
    async def add_moderation_action(self, session_id: str, action_type: str, details: Dict[str, Any]) -> bool:
        """Add a moderation action record."""
        if not self.is_available() or not session_id:
            return False
            
        try:
            if self.schema_type == 'new':
                # Use new schema
                self.client.table('moderation_actions').insert({
                    'session_id': session_id,
                    'action_type': action_type,
                    'details': json.dumps(details)
                }).execute()
                
            else:  # legacy schema
                # For legacy schema, store in debate_context
                self.client.table('debate_context').insert({
                    'room_id': session_id,
                    'session_number': 1,
                    'context_type': 'session_summary',  # Use existing enum value
                    'content': f"Moderation Action: {action_type} - {json.dumps(details)}",
                    'importance_score': 7
                }).execute()
            
            logger.debug(f"Added moderation action: {action_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add moderation action: {e}")
            return False
    
    async def get_conversation_history(self, session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieve recent conversation history."""
        if not self.is_available() or not session_id:
            return []
            
        try:
            if self.schema_type == 'new':
                # Use new schema
                response = self.client.table('conversation_turns') \
                    .select('speaker, content, turn_type, timestamp') \
                    .eq('session_id', session_id) \
                    .order('timestamp', desc=True) \
                    .limit(limit) \
                    .execute()
                
                return response.data
                
            else:  # legacy schema
                # Use legacy schema
                response = self.client.table('conversation_memory') \
                    .select('speaker_name, content_text, speaker_role, timestamp_start') \
                    .eq('room_id', session_id) \
                    .order('timestamp_start', desc=True) \
                    .limit(limit) \
                    .execute()
                
                # Convert to standard format
                history = []
                for item in response.data:
                    history.append({
                        'speaker': item['speaker_name'],
                        'content': item['content_text'],
                        'turn_type': item['speaker_role'],
                        'timestamp': item['timestamp_start']
                    })
                return history
                
        except Exception as e:
            logger.error(f"Failed to retrieve conversation history: {e}")
            return []
    
    async def get_participant_memories(self, session_id: str, participant: str) -> List[Dict[str, Any]]:
        """Get memories for a specific participant."""
        if not self.is_available() or not session_id:
            return []
            
        try:
            if self.schema_type == 'new':
                # Use new schema
                response = self.client.table('participant_memory') \
                    .select('memory_type, content, created_at') \
                    .eq('session_id', session_id) \
                    .eq('participant', participant) \
                    .order('created_at', desc=True) \
                    .execute()
                
                return response.data
                
            else:  # legacy schema
                # Use legacy schema
                personality_map = {
                    'socrates': 'socrates',
                    'aristotle': 'aristotle', 
                    'buddha': 'buddha',
                    'hermes': 'hermes',
                    'solon': 'solon'
                }
                
                personality = personality_map.get(participant.lower(), 'socrates')
                
                response = self.client.table('personality_memory') \
                    .select('memory_type, content, created_at') \
                    .eq('room_id', session_id) \
                    .eq('personality', personality) \
                    .order('created_at', desc=True) \
                    .execute()
                
                return response.data
                
        except Exception as e:
            logger.error(f"Failed to retrieve participant memories: {e}")
            return []
    
    async def end_session(self, session_id: str) -> bool:
        """Mark a session as ended."""
        if not self.is_available() or not session_id:
            return False
            
        try:
            if self.schema_type == 'new':
                # Use new schema
                self.client.table('debate_sessions') \
                    .update({'status': 'ended', 'ended_at': datetime.now(timezone.utc).isoformat()}) \
                    .eq('id', session_id) \
                    .execute()
                    
            else:  # legacy schema
                # Use legacy schema
                self.client.table('debate_rooms') \
                    .update({'status': 'completed'}) \
                    .eq('id', session_id) \
                    .execute()
            
            logger.info(f"Ended session: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to end session: {e}")
            return False

# Global instance
memory_manager = SupabaseMemoryManager() 