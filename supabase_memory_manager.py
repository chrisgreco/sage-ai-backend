#!/usr/bin/env python3

"""
Supabase Memory Manager - Enhanced Memory System for LiveKit Agents
Provides conversation memory, participant memory, and session management with Supabase
Optimized schema for production deployment
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
    Uses optimized schema: debate_sessions, conversation_turns, participant_memory, moderation_actions
    """
    
    def __init__(self):
        """Initialize Supabase client with comprehensive error handling"""
        self.client: Optional[Client] = None
        self.is_connected = False
        
        # Environment variables are set by Render directly
        self.url = os.getenv('SUPABASE_URL')
        self.service_role_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        self.anon_key = os.getenv('SUPABASE_ANON_KEY')  # Fixed: was SUPABASE_KEY
        
        # Initialize connection
        self._initialize_connection()
    
    def _initialize_connection(self):
        """Initialize Supabase connection with proper error handling"""
        try:
            # Debug: Show what environment variables we're finding
            logger.info(f"🔍 Checking environment variables:")
            logger.info(f"   SUPABASE_URL: {'✅ Found' if self.url else '❌ Not found'}")
            logger.info(f"   SUPABASE_SERVICE_ROLE_KEY: {'✅ Found' if self.service_role_key else '❌ Not found'}")
            logger.info(f"   SUPABASE_ANON_KEY: {'✅ Found' if self.anon_key else '❌ Not found'}")
            
            if not self.url:
                logger.warning("SUPABASE_URL not found in environment variables")
                return
            
            # Prefer service role key for backend operations
            api_key = self.service_role_key or self.anon_key
            
            if not api_key:
                logger.warning("Supabase credentials not found. Required: SUPABASE_URL and either SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY")
                return
            
            logger.info(f"🔗 Connecting to Supabase at: {self.url}")
            
            # Create Supabase client
            self.client = create_client(self.url, api_key)
            
            # Test connection by querying the auth service
            try:
                # Simple test query to verify connection
                test_result = self.client.table('debate_sessions').select('id').limit(1).execute()
                self.is_connected = True
                logger.info("✅ Supabase connection established successfully")
                
            except Exception as test_error:
                logger.error(f"❌ Supabase connection test failed: {test_error}")
                logger.error("💡 Check that tables exist and RLS policies are configured")
                self.client = None
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize Supabase client: {e}")
            logger.info("💿 Memory features will be disabled. Agent will continue without persistent memory.")
    
    def is_available(self) -> bool:
        """Check if memory manager is available for use"""
        return self.client is not None and self.is_connected
    
    async def create_session(self, room_name: str, topic: str, persona: str) -> Optional[str]:
        """Create a new debate session and return session ID"""
        if not self.is_available():
            logger.warning("Memory manager not available for session creation")
            return None
            
        try:
            session_data = {
                'room_name': room_name,
                'topic': topic,
                'persona': persona,
                'participants': [],
                'status': 'active',
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            result = self.client.table('debate_sessions').insert(session_data).execute()
            
            if result.data and len(result.data) > 0:
                session_id = result.data[0]['id']
                logger.info(f"✅ Session created: {session_id}")
                return session_id
            else:
                logger.error("❌ Session creation failed: no data returned")
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to create session: {e}")
            return None
    
    async def add_conversation_turn(self, session_id: str, speaker: str, content: str, turn_type: str = "speech") -> bool:
        """Add a conversation turn to the session"""
        if not self.is_available():
            return False
            
        try:
            turn_data = {
                'session_id': session_id,
                'speaker': speaker,
                'content': content,
                'turn_type': turn_type,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            result = self.client.table('conversation_turns').insert(turn_data).execute()
            
            if result.data:
                logger.debug(f"💾 Conversation turn stored: {speaker} - {turn_type}")
                return True
            else:
                logger.warning(f"Failed to store conversation turn: {speaker}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to add conversation turn: {e}")
            return False
    
    async def add_participant_memory(self, session_id: str, participant: str, memory_type: str, content: str) -> bool:
        """Store participant-specific memory (insights, preferences, etc.)"""
        if not self.is_available():
            return False
            
        try:
            memory_data = {
                'session_id': session_id,
                'participant': participant,
                'memory_type': memory_type,
                'content': content,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            result = self.client.table('participant_memory').insert(memory_data).execute()
            
            if result.data:
                logger.debug(f"💾 Participant memory stored: {participant} - {memory_type}")
                return True
            else:
                logger.warning(f"Failed to store participant memory: {participant}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to add participant memory: {e}")
            return False
    
    async def add_moderation_action(self, session_id: str, action_type: str, details: Dict[str, Any]) -> bool:
        """Store moderation actions (fact-checks, interventions, etc.)"""
        if not self.is_available():
            return False
            
        try:
            action_data = {
                'session_id': session_id,
                'action_type': action_type,
                'details': json.dumps(details),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            result = self.client.table('moderation_actions').insert(action_data).execute()
            
            if result.data:
                logger.debug(f"💾 Moderation action stored: {action_type}")
                return True
            else:
                logger.warning(f"Failed to store moderation action: {action_type}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to add moderation action: {e}")
            return False
    
    async def get_conversation_history(self, session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get conversation history for a session"""
        if not self.is_available():
            return []
            
        try:
            result = self.client.table('conversation_turns').select('*').eq('session_id', session_id).order('timestamp', desc=False).limit(limit).execute()
            
            if result.data:
                logger.debug(f"📖 Retrieved {len(result.data)} conversation turns")
                return result.data
            else:
                logger.debug("No conversation history found")
                return []
                
        except Exception as e:
            logger.error(f"❌ Failed to get conversation history: {e}")
            return []
    
    async def get_participant_memories(self, session_id: str, participant: str) -> List[Dict[str, Any]]:
        """Get memories for a specific participant"""
        if not self.is_available():
            return []
            
        try:
            result = self.client.table('participant_memory').select('*').eq('session_id', session_id).eq('participant', participant).order('created_at', desc=False).execute()
            
            if result.data:
                logger.debug(f"🧠 Retrieved {len(result.data)} memories for {participant}")
                return result.data
            else:
                logger.debug(f"No memories found for {participant}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Failed to get participant memories: {e}")
            return []
    
    async def update_session_status(self, session_id: str, status: str) -> bool:
        """Update session status (active, paused, ended)"""
        if not self.is_available():
            return False
            
        try:
            update_data = {'status': status}
            if status == 'ended':
                update_data['ended_at'] = datetime.now(timezone.utc).isoformat()
            
            result = self.client.table('debate_sessions').update(update_data).eq('id', session_id).execute()
            
            if result.data:
                logger.info(f"📊 Session {session_id} status updated to: {status}")
                return True
            else:
                logger.warning(f"Failed to update session status: {session_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to update session status: {e}")
            return False
    
    async def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get basic session information"""
        if not self.is_available():
            return None
            
        try:
            result = self.client.table('debate_sessions').select('*').eq('id', session_id).execute()
            
            if result.data and len(result.data) > 0:
                logger.debug(f"📋 Retrieved session info: {session_id}")
                return result.data[0]
            else:
                logger.warning(f"Session not found: {session_id}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to get session info: {e}")
            return None

    # Additional convenience methods for agent function tools
    async def store_moderation_action(self, action: str, content: str, persona: str) -> bool:
        """Store a moderation action from the agent function tools"""
        if not self.is_available():
            return False
            
        try:
            # For now, we'll store without a specific session_id since we don't have session management yet
            # In a full implementation, you'd want to track the current session
            action_data = {
                'session_id': None,  # Would need to be set when session management is implemented
                'action_type': action,
                'details': json.dumps({
                    'content': content,
                    'persona': persona,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # For now, just log the action since we don't have session context
            logger.info(f"💾 Moderation action: {persona} - {action} - {content}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to store moderation action: {e}")
            return False

    async def store_fact_check(self, statement: str, status: str) -> bool:
        """Store a fact-check request from the agent function tools"""
        if not self.is_available():
            return False
            
        try:
            # Log the fact-check request
            logger.info(f"🔍 Fact-check request: {statement} - {status}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to store fact-check: {e}")
            return False

    async def store_topic_change(self, topic: str, persona: str) -> bool:
        """Store a topic change from the agent function tools"""
        if not self.is_available():
            return False
            
        try:
            # Log the topic change
            logger.info(f"📝 Topic change: {persona} set topic to '{topic}'")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to store topic change: {e}")
            return False

# Global instance
memory_manager = SupabaseMemoryManager() 