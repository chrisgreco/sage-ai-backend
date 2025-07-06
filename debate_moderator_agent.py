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
import time

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

# Environment variables are managed by Render directly - no need for dotenv
# Render automatically sets environment variables in the container runtime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DebateModerator:
    """AI Debate Moderator using different philosophical personas"""
    
    def __init__(self, topic: str, persona: str, room_name: str, room: rtc.Room):
        self.topic = topic
        self.persona = persona
        self.room_name = room_name
        self.room = room
        self.session_id = f"{room_name}_{int(time.time())}"
        self.conversation_count = 0
        self.current_state = "initializing"
        
        # Initialize memory manager with fallback
        try:
            # Try to import and initialize memory manager
            from supabase_memory_manager import SupabaseMemoryManager
            self.memory_manager = SupabaseMemoryManager()
        except Exception as e:
            logger.warning(f"Memory manager initialization failed: {e}")
            # Create a simple fallback memory manager
            self.memory_manager = None
        
        logger.info(f"🎯 Initialized {persona} moderator for topic: '{topic}' in room: {room_name}")
        
    async def set_agent_state(self, state: str):
        """Set agent state for tracking (using string instead of enum)"""
        try:
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
        except Exception as e:
            logger.error(f"Failed to set agent state: {e}")
    
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
            await self.set_agent_state("thinking")
            
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
            await self.set_agent_state("thinking")
            
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
            await self.set_agent_state("thinking")
            
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
- Respond naturally when participants speak to you
- Only interrupt if discussion becomes hostile or unproductive  
- Keep ALL responses to 1-2 sentences maximum
- Ask thoughtful questions to guide the discussion
- Stay in character as {persona}
- Be helpful and engaging while maintaining your philosophical approach

"""
        
        persona_specific = {
            "Aristotle": """As Aristotle:
- Use logical reasoning and find the golden mean
- Ask focused questions to clarify logic
- Guide toward virtue ethics and practical wisdom
- Be systematic but brief
- Help participants examine their arguments logically""",
            
            "Socrates": """As Socrates:  
- Ask probing questions to expose assumptions
- Admit what you don't know humbly
- Seek clarity and definitions
- Guide through gentle inquiry
- Help participants think more deeply""",
            
            "Buddha": """As Buddha:
- Practice mindful, compassionate communication  
- Seek common ground and de-escalate conflicts
- Guide toward mutual understanding
- Use the middle way approach
- Help participants find peace and understanding"""
        }
        
        return base_prompt + persona_specific.get(persona, persona_specific["Aristotle"])

    async def start(self):
        """Start the agent with proper LiveKit 1.0 pattern"""
        try:
            # Create agent with dynamic persona instructions
            agent = Agent(
                instructions=self.get_prompt_for_persona(self.persona),
                # Remove tools for now to simplify debugging
            )
            
            # Create session with Perplexity integration following 1.0 pattern
            session = AgentSession(
                vad=silero.VAD.load(),
                stt=deepgram.STT(model="nova-2"),
                llm=openai.LLM.with_perplexity(
                    model="sonar-pro",
                    api_key=None,  # Uses PERPLEXITY_API_KEY from env
                    base_url="https://api.perplexity.ai",
                    temperature=0.7,
                    parallel_tool_calls=False,
                    tool_choice="auto"
                ),
                tts=openai.TTS(voice="alloy"),
                turn_detection=EnglishModel(),
            )
            
            logger.info(f"🤖 Starting {self.persona} agent with Perplexity integration")
            
            # Start the session with the agent
            await session.start(agent=agent, room=self.room)
            
            # Initialize session memory
            await self.initialize_session()
            await self.set_agent_state("ready")
            
            # Don't generate initial reply - wait for user input to avoid Perplexity API message format issues
            # The agent will respond when users speak, following proper user->assistant message flow
            logger.info(f"✅ {self.persona} agent ready and waiting for participants")
            
        except Exception as e:
            logger.error(f"Failed to start agent: {e}")
            await self.set_agent_state("error")
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
    await moderator.start()

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint)) 