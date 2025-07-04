#!/usr/bin/env python3

"""
Sage AI Debate Moderator Agent - Enhanced with Memory and Context
Receives topic and persona from environment variables passed by the backend
Integrates with Supabase for persistent memory and conversation context
"""

import os
import asyncio
import logging
import shutil
from typing import Optional, List, Dict, Any
from datetime import datetime

# Core LiveKit imports
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
    function_tool,
    RunContext,
    RoomInputOptions,
)
from livekit.plugins import openai, silero, deepgram, cartesia
from livekit.plugins.turn_detector.english import EnglishModel
from livekit import api, rtc

# Import memory manager
from supabase_memory_manager import SupabaseMemoryManager

# Environment variables are managed by Render directly - no need for dotenv
# Render automatically sets environment variables in the container runtime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AgentState:
    """Agent state constants for tracking current activity"""
    INITIALIZING = "initializing"
    LISTENING = "listening" 
    THINKING = "thinking"
    SPEAKING = "speaking"

class DebateModerator:
    """Enhanced debate moderator with persistent memory and context awareness"""
    
    def __init__(self, topic: str, persona: str, room_name: str, room: rtc.Room):
        self.topic = topic
        self.persona = persona
        self.room_name = room_name
        self.room = room
        self.session_id: Optional[str] = None
        self.conversation_count = 0
        self.current_state = AgentState.INITIALIZING
        
        # Initialize memory manager
        self.memory_manager = SupabaseMemoryManager()
        
        logger.info(f"🎯 Initialized {persona} moderator for topic: '{topic}' in room: {room_name}")
        
    async def set_agent_state(self, state: str):
        """Update agent state and broadcast to room"""
        self.current_state = state
        logger.info(f"🤖 Agent state: {state}")
        
        # Broadcast state to room participants
        try:
            await self.room.local_participant.publish_data(
                f'{{"type": "agent_state", "state": "{state}", "persona": "{self.persona}"}}',
                reliable=True
            )
        except Exception as e:
            logger.warning(f"Failed to broadcast agent state: {e}")
    
    async def store_conversation_turn(self, speaker: str, content: str, turn_type: str = "speech"):
        """Store conversation turn in memory system"""
        if self.session_id and self.memory_manager.is_available():
            success = await self.memory_manager.add_conversation_turn(
                self.session_id, speaker, content, turn_type
            )
            if success:
                logger.debug(f"💾 Stored conversation turn: {speaker}")
            else:
                logger.warning(f"Failed to store conversation turn: {speaker}")
    
    async def store_agent_memory(self, memory_type: str, content: str):
        """Store agent-specific memory (insights, decisions, etc.)"""
        if self.session_id and self.memory_manager.is_available():
            success = await self.memory_manager.add_participant_memory(
                self.session_id, f"AI-{self.persona}", memory_type, content
            )
            if success:
                logger.debug(f"💾 Stored agent memory: {memory_type}")

    async def initialize_session(self):
        """Initialize session with Supabase memory"""
        try:
            if self.memory_manager.is_available():
                self.session_id = await self.memory_manager.create_session(
                    room_name=self.room_name,
                    topic=self.topic,
                    persona=self.persona
                )
                
                if self.session_id:
                    logger.info(f"✅ Session created: {self.session_id}")
                    
                    # Store initial agent memory
                    await self.store_agent_memory(
                        "session_start",
                        f"Started debate session as {self.persona} moderator for topic: {self.topic}"
                    )
                else:
                    logger.warning("⚠️ Session creation failed, continuing without persistence")
            else:
                logger.info("💿 Memory manager not available, running without persistence")
                
        except Exception as e:
            logger.error(f"❌ Session initialization error: {e}")

    @function_tool
    async def set_debate_topic(
        self,
        context: RunContext,
        topic: str,
        context_info: Optional[str] = None
    ) -> str:
        """Set or update the debate topic"""
        try:
            await self.set_agent_state(AgentState.THINKING)
            
            self.topic = topic
            logger.info(f"📋 Topic updated to: {topic}")
            
            # Store topic change in memory
            await self.store_agent_memory(
                "topic_change", 
                f"Updated topic to: {topic}. Context: {context_info or 'None provided'}"
            )
            
            return f"Topic has been set to: '{topic}'. Let's begin our structured discussion."
            
        except Exception as e:
            logger.error(f"Error in set_debate_topic: {e}")
            return f"I acknowledge the topic '{topic}' but encountered an issue updating it."

    @function_tool
    async def moderate_discussion(
        self,
        context: RunContext,
        participant_statement: str,
        speaker_name: Optional[str] = None
    ) -> str:
        """Moderate the discussion with persona-specific approach"""
        try:
            await self.set_agent_state(AgentState.THINKING)
            
            self.conversation_count += 1
            speaker = speaker_name or f"Participant-{self.conversation_count}"
            
            logger.info(f"🎙️ Moderating statement from {speaker}")
            
            # Store the participant's statement
            await self.store_conversation_turn(speaker, participant_statement, "speech")
            
            # Store moderation action in memory
            if self.session_id and self.memory_manager.is_available():
                try:
                    await self.memory_manager.add_moderation_action(
                        self.session_id,
                        "statement_review",
                        {
                            "speaker": speaker,
                            "statement": participant_statement,
                            "persona": self.persona,
                            "topic": self.topic
                        }
                    )
                except Exception as e:
                    logger.error(f"Failed to store moderation action: {e}")
            
            response = f"Thank you, {speaker}. "
            
            # Persona-specific moderation approach
            if self.persona == "Socrates":
                response += "That's an interesting perspective. What led you to that conclusion?"
            elif self.persona == "Aristotle":
                response += "Let's examine the logic of that argument systematically."
            elif self.persona == "Buddha":
                response += "I hear your perspective with compassion. How might we find common ground here?"
            else:  # Fallback
                response += "Can you elaborate on that point with specific examples?"
            
            # Store our response
            await self.store_conversation_turn(f"AI-{self.persona}", response, "moderation")
            
            return response
            
        except Exception as e:
            logger.error(f"Error in moderate_discussion: {e}")
            return "I acknowledge your point. Please continue the discussion."

    @function_tool
    async def fact_check_statement(
        self,
        context: RunContext,
        claim: str,
        speaker: Optional[str] = None
    ) -> str:
        """Fact-check a statement with research if available"""
        try:
            await self.set_agent_state(AgentState.THINKING)
            
            logger.info(f"🔍 Fact-checking claim: {claim[:100]}...")
            
            # Store fact-check action in memory
            if self.session_id and self.memory_manager.is_available():
                try:
                    await self.memory_manager.add_moderation_action(
                        self.session_id,
                        "fact_check",
                        {
                            "claim": claim,
                            "speaker": speaker,
                            "persona": self.persona,
                            "topic": self.topic
                        }
                    )
                except Exception as e:
                    logger.error(f"Failed to store fact-check action: {e}")
            
            # Persona-specific fact-checking approach
            response = f"As {self.persona}, I'll examine this claim: '{claim}'"
            response += f"\n\nLet me provide some perspective on this statement in the context of our discussion about {self.topic}."
            
            # Store our fact-check response
            await self.store_conversation_turn(f"AI-{self.persona}", response, "fact_check")
            
            return response
            
        except Exception as e:
            logger.error(f"Error in fact_check_statement: {e}")
            return "I apologize, but I'm unable to fact-check that claim at the moment. Please continue the discussion."

    async def get_session_context(self) -> Dict[str, Any]:
        """Get current session context for debugging"""
        return {
            "session_id": self.session_id,
            "topic": self.topic,
            "persona": self.persona,
            "room_name": self.room_name,
            "conversation_count": self.conversation_count,
            "current_state": self.current_state,
            "memory_available": self.memory_manager.is_available()
        }

    async def get_conversation_summary(self) -> Optional[str]:
        """Get a summary of the conversation so far"""
        if not self.session_id or not self.memory_manager.is_available():
            return None
            
        try:
            history = await self.memory_manager.get_conversation_history(self.session_id, limit=10)
            if history:
                return f"Recent conversation: {len(history)} turns recorded"
            else:
                return "No conversation history found"
        except Exception as e:
            logger.error(f"Failed to get conversation summary: {e}")
            return None

    def get_prompt_for_persona(self, persona: str) -> str:
        """Get dynamic system prompt for the specified persona"""
        base_prompt = f"""You are {persona}, moderating a debate about "{self.topic}".

CRITICAL BEHAVIOR RULES:
- Only speak when directly asked a question by participants
- Only speak when discussion becomes hostile or unproductive  
- Only speak when participants explicitly request moderation
- Do NOT interrupt natural conversation flow
- You are a GUIDE, not a participant
- Keep ALL responses to 1-2 sentences maximum

"""
        
        persona_specific = {
            "Aristotle": """As Aristotle:
- Use logical reasoning and find the golden mean
- Ask one focused question to clarify logic
- Guide toward virtue ethics and practical wisdom
- Be systematic but extremely brief""",
            
            "Socrates": """As Socrates:  
- Ask one probing question to expose assumptions
- Admit what you don't know humbly
- Seek clarity and definitions
- Guide through gentle inquiry""",
            
            "Buddha": """As Buddha:
- Practice mindful, compassionate communication  
- Seek common ground and de-escalate conflicts
- Guide toward mutual understanding
- Use the middle way approach"""
        }
        
        return base_prompt + persona_specific.get(persona, persona_specific["Aristotle"])

    async def start(self, room: rtc.Room):
        """Start the moderator agent with Perplexity integration"""
        try:
            await self.set_agent_state(AgentState.INITIALIZING)
            logger.info(f"🚀 Starting {self.persona} moderator...")
            
            # Initialize session with memory
            await self.initialize_session()
            
            # Get dynamic persona prompt
            system_prompt = self.get_prompt_for_persona(self.persona)
            logger.info(f"🎭 Using persona prompt for {self.persona}")
            
            # Initialize the agent with Perplexity integration
            agent = Agent(
                llm=openai.LLM.with_perplexity(
                    model="llama-3.1-sonar-small-128k-online",  # Use online model for real-time info
                    api_key=os.getenv("PERPLEXITY_API_KEY"),
                    system_prompt=system_prompt,
                    web_search_options={
                        "search_context_size": "medium"  # Balance between cost and context
                    }
                ),
                tts=cartesia.TTS() if os.getenv("CARTESIA_API_KEY") else silero.TTS(),
                stt=deepgram.STT() if os.getenv("DEEPGRAM_API_KEY") else openai.STT(),
                turn_detector=EnglishModel(),
                room_input_options=RoomInputOptions(
                    auto_subscribe=True,
                    track_timeout=30.0,
                    silence_timeout=2.0
                )
            )
            
            # Set up agent event handlers for memory integration
            @agent.on("agent_speech_committed")
            async def on_agent_speech(agent_speech):
                """Store agent speech in memory"""
                await self.store_conversation_turn(
                    f"AI-{self.persona}", 
                    agent_speech.transcript, 
                    "agent_speech"
                )
                logger.debug(f"💾 Stored agent speech: {agent_speech.transcript[:50]}...")
            
            @agent.on("user_speech_committed") 
            async def on_user_speech(user_speech):
                """Store user speech in memory"""
                participant_name = getattr(user_speech, 'participant', {}).get('identity', 'Unknown')
                await self.store_conversation_turn(
                    participant_name,
                    user_speech.transcript,
                    "user_speech"
                )
                logger.debug(f"💾 Stored user speech from {participant_name}: {user_speech.transcript[:50]}...")
            
            # Start the agent session
            agent_session = AgentSession(room=room, agent=agent)
            await agent_session.start()
            
            await self.set_agent_state(AgentState.LISTENING)
            logger.info(f"✅ {self.persona} moderator is ready and listening")
            
        except Exception as e:
            logger.error(f"❌ Failed to start moderator: {e}")
            await self.set_agent_state(AgentState.INITIALIZING)
            raise

async def entrypoint(ctx: JobContext):
    """Enhanced entrypoint with topic and persona from room metadata"""
    
    # Connect to room first to access metadata
    await ctx.connect()
    logger.info("✅ Connected to LiveKit room")
    
    # Get context from environment variables (set by the backend)
    topic = os.getenv("DEBATE_TOPIC", "General Discussion")
    room_name = os.getenv("ROOM_NAME", ctx.room.name or "unknown")
    
    # Get persona from room metadata (dynamic per room)
    persona = "Aristotle"  # Default fallback
    if ctx.room and ctx.room.metadata:
        try:
            import json
            room_metadata = json.loads(ctx.room.metadata)
            persona = room_metadata.get("persona", "Aristotle")
            # Also get topic from metadata if available (more current than env var)
            if "topic" in room_metadata:
                topic = room_metadata["topic"]
            logger.info(f"📋 Got persona '{persona}' and topic '{topic}' from room metadata")
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Failed to parse room metadata: {e}, using defaults")
    else:
        logger.info(f"No room metadata found, using default persona: {persona}")
    
    logger.info(f"🎯 Starting {persona} moderator for topic: '{topic}' in room: {room_name}")
    
    # Initialize moderator with context including room reference
    moderator = DebateModerator(topic=topic, persona=persona, room_name=room_name, room=ctx.room)
    await moderator.start(ctx.room)

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint)) 