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
            
            # Get persona instructions for response
            persona_instructions = get_persona_instructions(self.persona)
            
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
            persona_instructions = get_persona_instructions(self.persona)
            
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

def get_persona_instructions(persona: str) -> str:
    """Get detailed instructions for each persona"""
    personas = {
        "Aristotle": """
        You are Aristotle, the ancient Greek philosopher. Approach debates with:
        - Logical reasoning and systematic analysis
        - Focus on finding the golden mean between extremes
        - Use of syllogistic reasoning
        - Emphasis on virtue ethics and practical wisdom
        - Structured argumentation with clear premises and conclusions
        """,
        
        "Socrates": """
        You are Socrates, the classical Greek philosopher. Approach debates with:
        - Socratic questioning to expose assumptions
        - Humble acknowledgment of what you don't know
        - Focus on definitions and clarity of terms
        - Gentle but persistent inquiry
        - Helping participants examine their own beliefs
        """,
        
        "Buddha": """
        You are Buddha, the enlightened teacher. Approach debates with:
        - Mindful communication and compassionate understanding
        - Focus on reducing suffering and finding common ground
        - Emphasis on the middle way and balanced perspectives
        - Gentle guidance toward wisdom and mutual understanding
        - De-escalation of conflicts through mindful dialogue
        """
    }
    
    return personas.get(persona, personas["Aristotle"])

async def entrypoint(ctx: JobContext):
    """Enhanced entrypoint with topic and persona from environment"""
    
    # Get context from environment variables (set by the backend)
    topic = os.getenv("DEBATE_TOPIC", "General Discussion")
    persona = os.getenv("MODERATOR_PERSONA", "Aristotle") 
    room_name = os.getenv("ROOM_NAME", ctx.room.name or "unknown")
    
    logger.info(f"🎯 Starting {persona} moderator for topic: '{topic}' in room: {room_name}")
    
    # Connect to room first
    await ctx.connect()
    logger.info("✅ Connected to LiveKit room")
    
    # Initialize moderator with context including room reference
    moderator = DebateModerator(topic=topic, persona=persona, room_name=room_name, room=ctx.room)
    await moderator.initialize_session()
    
    # Set initial agent state
    await moderator.set_agent_state(AgentState.INITIALIZING)
    
    # Get persona instructions
    instructions = get_persona_instructions(persona)
    
    # Create agent with enhanced tools
    agent = Agent(
        instructions=f"""
        You are {persona}, moderating a debate about: "{topic}"
        
        {instructions}
        
        CRITICAL: Keep ALL responses SHORT and TO THE POINT (1-2 sentences maximum).
        Be precise, not verbose. Quality over quantity.
        
        Use your tools to:
        - Moderate discussions with brief, targeted interventions
        - Fact-check claims with specific sources: "According to [source], the data shows..."
        - Ask concise questions to guide the discussion
        
        Always respond in character as {persona} would, but BRIEFLY.
        """,
        tools=[
            moderator.set_debate_topic,
            moderator.moderate_discussion,
            moderator.fact_check_statement,
        ],
    )
    
    # Verify API keys
    perplexity_key = os.getenv("PERPLEXITY_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    deepgram_key = os.getenv("DEEPGRAM_API_KEY")
    
    if not openai_key:
        logger.error("❌ OPENAI_API_KEY environment variable is required")
        raise ValueError("OPENAI_API_KEY environment variable is required")
    
    logger.info("🔑 API keys verified")
    
    # Check available disk space
    try:
        total, used, free = shutil.disk_usage("/")
        free_gb = free // (1024**3)
        logger.info(f"💾 Available disk space: {free_gb}GB")
        
        # If less than 1GB free, disable model downloads
        if free_gb < 1:
            logger.warning(f"⚠️ Low disk space ({free_gb}GB), disabling advanced models to prevent crashes")
            os.environ["ENABLE_TURN_DETECTION"] = "false"
            # Could also disable VAD here if needed
    except Exception as e:
        logger.warning(f"Could not check disk space: {e}")
    
    # Configure LLM - Use Perplexity if available, fallback to OpenAI
    try:
        if perplexity_key:
            perplexity_model = "sonar"  # Current recommended Perplexity model
            llm = openai.LLM.with_perplexity(
                model=perplexity_model,
                api_key=perplexity_key,
                temperature=0.7
            )
            logger.info(f"🧠 Perplexity LLM configured: {perplexity_model}")
        else:
            # Fallback to OpenAI
            llm = openai.LLM(
                model="gpt-4o-mini",
                api_key=openai_key,
                temperature=0.7
            )
            logger.info("🧠 OpenAI LLM configured (fallback)")
        
    except Exception as e:
        logger.error(f"❌ LLM setup failed: {e}")
        # Last resort fallback
        llm = openai.LLM(
            model="gpt-4o-mini",
            api_key=openai_key,
            temperature=0.7
        )
        logger.info("🧠 Using OpenAI LLM as last resort")
    
    # Configure TTS with Cartesia for better voice quality (fallback to OpenAI)
    try:
        cartesia_key = os.getenv("CARTESIA_API_KEY")
        if cartesia_key:
            tts = cartesia.TTS(
                model="sonic-2", 
                voice="f786b574-daa5-4673-aa0c-cbe3e8534c02",  # Default voice
                api_key=cartesia_key
            )
            logger.info("🎤 Cartesia TTS configured (premium)")
        else:
            # Fallback to OpenAI TTS
            tts = openai.TTS(
                voice="alloy",
                api_key=openai_key,
            )
            logger.info("🎤 OpenAI TTS configured (fallback)")
    except Exception as e:
        logger.error(f"❌ TTS setup failed: {e}")
        # Fallback to OpenAI TTS
        tts = openai.TTS(
            voice="alloy",
            api_key=openai_key,
        )
        logger.info("🎤 Using OpenAI TTS as fallback")
    
    # Configure STT with proper fallbacks
    try:
        if deepgram_key:
            stt = deepgram.STT(model="nova-2", api_key=deepgram_key)
            logger.info("🎙️ Deepgram STT configured")
        else:
            # Fallback to OpenAI STT
            stt = openai.STT(api_key=openai_key)
            logger.info("🎙️ OpenAI STT configured (fallback)")
    except Exception as e:
        logger.error(f"❌ STT setup failed: {e}")
        # Final fallback to OpenAI STT
        stt = openai.STT(api_key=openai_key)
        logger.info("🎙️ Using OpenAI STT as fallback")
    
    # Configure turn detector - Use English model for efficiency
    try:
        turn_detector = EnglishModel()
        logger.info("🎯 English turn detector configured")
    except Exception as e:
        logger.error(f"❌ Turn detector setup failed: {e}")
        turn_detector = None
        logger.warning("⚠️ Continuing without turn detector")
        
    # Create agent session with enhanced memory integration
    session = AgentSession(
        llm=llm,
        tts=tts,
        stt=stt,
        vad=silero.VAD.load(activation_threshold=0.6),
        turn_detector=turn_detector,
        min_endpointing_delay=0.8,  # Slightly longer for better turn detection
        max_endpointing_delay=2.5,  # Reasonable max
    )
    
    # Enhanced event handlers for automatic memory storage
    @session.on("agent_speech_committed")
    async def on_agent_speech_committed(speech):
        """Store agent speech in memory automatically"""
        try:
            if speech.text and speech.text.strip():
                await moderator.store_conversation_turn(
                    f"AI-{moderator.persona}", 
                    speech.text, 
                    "speech"
                )
                logger.debug(f"💾 Stored agent speech: {speech.text[:50]}...")
        except Exception as e:
            logger.error(f"Failed to store agent speech: {e}")
    
    @session.on("user_speech_committed")  
    async def on_user_speech_committed(speech):
        """Store user speech in memory automatically"""
        try:
            if speech.text and speech.text.strip():
                # Use participant identity if available, otherwise generic
                speaker_name = getattr(speech, 'participant', None)
                if speaker_name:
                    speaker = f"User-{speaker_name.identity}"
                else:
                    speaker = f"User-{moderator.conversation_count + 1}"
                
                await moderator.store_conversation_turn(
                    speaker, 
                    speech.text, 
                    "speech"
                )
                logger.debug(f"💾 Stored user speech: {speech.text[:50]}...")
        except Exception as e:
            logger.error(f"Failed to store user speech: {e}")
    
    # Start the session
    await session.start(agent=agent, room=ctx.room)
    
    # Initial greeting with persona context
    await moderator.set_agent_state(AgentState.SPEAKING)
    
    greeting = f"""Hello! I'm {persona}, and I'll be moderating our discussion about {topic}. 
    
    I'm here to facilitate a thoughtful exchange of ideas. Please feel free to share your thoughts, and I'll help guide our conversation."""
    
    # Store the initial greeting
    await moderator.store_conversation_turn(f"AI-{persona}", greeting, "greeting")
    
    # Generate the greeting reply
    await session.generate_reply(instructions=f"Greet participants as {persona} and invite them to begin discussing {topic}. Be warm but brief.")
    
    logger.info(f"🎤 {persona} moderator is ready and listening...")
    await moderator.set_agent_state(AgentState.LISTENING)

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint)) 