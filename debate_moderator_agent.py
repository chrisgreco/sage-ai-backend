#!/usr/bin/env python3

"""
Sage AI Debate Moderator Agent - Enhanced with Memory and Context
Receives topic and persona from environment variables passed by the backend
Integrates with Supabase for persistent memory and conversation context
"""

import os
import asyncio
import logging
from dotenv import load_dotenv
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
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from livekit import api, rtc

# Import memory manager
from supabase_memory_manager import SupabaseMemoryManager

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize memory manager with error handling
try:
    memory_manager = SupabaseMemoryManager()
    logger.info("✅ Supabase memory manager initialized successfully")
except Exception as e:
    logger.warning(f"⚠️ Memory manager initialization failed: {e}")
    memory_manager = None

# Agent state constants matching frontend expectations
class AgentState:
    INITIALIZING = "initializing"
    LISTENING = "listening" 
    THINKING = "thinking"
    SPEAKING = "speaking"

class DebateModerator:
    """Enhanced Debate Moderator with Memory and Context"""
    
    def __init__(self, topic: str, persona: str, room_name: str, room: rtc.Room):
        self.topic = topic
        self.persona = persona
        self.room_name = room_name
        self.room = room
        self.session_id: Optional[str] = None
        self.participants: List[str] = []
        self.conversation_count = 0
        self.current_state = AgentState.INITIALIZING
        
        logger.info(f"Initialized {persona} moderator for topic: '{topic}' in room: {room_name}")

    async def set_agent_state(self, state: str):
        """Update agent state and broadcast to room participants"""
        self.current_state = state
        logger.info(f"Agent state changed to: {state}")
        
        try:
            import json
            
            # Update participant metadata with agent state
            metadata = {
                "agent_state": state,
                "persona": self.persona,
                "topic": self.topic,
                "participant_type": "agent"
            }
            await self.room.local_participant.update_metadata(json.dumps(metadata))
            
            # Also send state update via data message for immediate frontend feedback
            state_message = {
                "type": "agent_state_change",
                "state": state,
                "persona": self.persona,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.room.local_participant.publish_data(
                data=json.dumps(state_message).encode('utf-8'),
                reliable=True
            )
            
        except Exception as e:
            logger.error(f"Failed to update agent state: {e}")

    async def initialize_session(self):
        """Initialize debate session in memory system"""
        if not memory_manager:
            logger.warning("Memory manager not available, skipping session initialization")
            return
            
        try:
            self.session_id = await memory_manager.store_debate_session(
                room_name=self.room_name,
                topic=self.topic,
                persona=self.persona,
                participants=self.participants
            )
            if self.session_id:
                logger.info(f"Debate session {self.session_id} initialized in memory system")
                
                # Store initial context
                await memory_manager.store_moderation_action(
                    session_id=self.session_id,
                    action_type="session_start",
                    details={
                        "topic": self.topic,
                        "persona": self.persona,
                        "room_name": self.room_name
                    }
                )
            else:
                logger.warning("Failed to initialize session in memory system - continuing without memory")
        except Exception as e:
            logger.error(f"Failed to initialize session: {e}")

    @function_tool
    async def set_debate_topic(
        self,
        context: RunContext,
        topic: str,
        context_info: Optional[str] = None
    ) -> str:
        """Set or update the debate topic"""
        old_topic = self.topic
        self.topic = topic
        
        response = f"Debate topic updated from '{old_topic}' to '{topic}'"
        if context_info:
            response += f"\n\nAdditional context: {context_info}"
        
        # Store in memory if available
        if memory_manager and self.session_id:
            try:
                await memory_manager.store_moderation_action(
                    session_id=self.session_id,
                    action_type="topic_change",
                    details={"old_topic": old_topic, "new_topic": topic, "context": context_info}
                )
            except Exception as e:
                logger.error(f"Failed to store topic change: {e}")
        
        logger.info(f"Topic updated to: {topic}")
        return response

    @function_tool
    async def moderate_discussion(
        self,
        context: RunContext,
        participant_statement: str,
        speaker_name: Optional[str] = None
    ) -> str:
        """Moderate the discussion based on the current topic and persona"""
        try:
            # Set state to thinking
            await self.set_agent_state(AgentState.THINKING)
            
            self.conversation_count += 1
            
            # Store conversation turn if memory is available
            if memory_manager and self.session_id and speaker_name:
                try:
                    await memory_manager.store_conversation_turn(
                        session_id=self.session_id,
                        speaker=speaker_name,
                        content=participant_statement,
                        turn_type="speech"
                    )
                except Exception as e:
                    logger.error(f"Failed to store conversation turn: {e}")
            
            # Get recent context for informed moderation
            recent_context = []
            if memory_manager and self.session_id:
                try:
                    recent_conversation = await memory_manager.get_recent_conversation(self.session_id, limit=5)
                    recent_context = [f"{turn['speaker']}: {turn['content']}" for turn in recent_conversation]
                except Exception as e:
                    logger.error(f"Failed to get recent context: {e}")
            
            # Persona-specific moderation approach
            persona_instructions = get_persona_instructions(self.persona)
            
            context_text = f"Topic: {self.topic}\n"
            if recent_context:
                context_text += f"Recent conversation:\n" + "\n".join(recent_context[-3:]) + "\n"
            context_text += f"Current statement: {participant_statement}\n"
            context_text += f"Respond as {self.persona} would, following these guidelines: {persona_instructions}"
            
            # Store moderation action if memory is available
            if memory_manager and self.session_id:
                try:
                    await memory_manager.store_moderation_action(
                        session_id=self.session_id,
                        action_type="moderation_response",
                        details={
                            "speaker": speaker_name,
                            "statement": participant_statement,
                            "conversation_count": self.conversation_count
                        }
                    )
                except Exception as e:
                    logger.error(f"Failed to store moderation action: {e}")
            
            return f"As {self.persona}, I acknowledge your statement about {self.topic}. Let me provide some guidance on this perspective."
            
        except Exception as e:
            logger.error(f"Error in moderate_discussion: {e}")
            return f"I apologize, but I encountered an issue processing that statement. Please continue the discussion."

    @function_tool
    async def fact_check_statement(
        self,
        context: RunContext,
        claim: str,
        speaker: Optional[str] = None
    ) -> str:
        """Fact-check a specific claim made during the debate"""
        try:
            # Set state to thinking
            await self.set_agent_state(AgentState.THINKING)
            
            # Store fact-check request if memory is available
            if memory_manager and self.session_id:
                try:
                    await memory_manager.store_moderation_action(
                        session_id=self.session_id,
                        action_type="fact_check",
                        details={
                            "claim": claim,
                            "speaker": speaker,
                            "topic": self.topic
                        }
                    )
                except Exception as e:
                    logger.error(f"Failed to store fact-check action: {e}")
            
            # Persona-specific fact-checking approach
            persona_instructions = get_persona_instructions(self.persona)
            
            response = f"As {self.persona}, I'll examine this claim: '{claim}'"
            response += f"\n\nLet me provide some perspective on this statement in the context of our discussion about {self.topic}."
            
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
            "current_state": self.current_state
        }

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
        
        "Modern": """
        You are a modern debate moderator. Approach debates with:
        - Contemporary communication styles
        - Focus on evidence-based reasoning
        - Awareness of diverse perspectives
        - Structured time management
        - Emphasis on respectful dialogue and finding common ground
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
        # Last resort fallback
        stt = openai.STT(api_key=openai_key)
        logger.info("🎙️ Using OpenAI STT as fallback")
    
    # Configure VAD with error handling
    try:
        vad = silero.VAD.load()
        logger.info("🔊 Silero VAD loaded successfully")
    except Exception as e:
        logger.error(f"❌ VAD loading failed: {e}")
        # Continue without VAD - LiveKit can handle this
        vad = None
        logger.info("🔊 Continuing without VAD")
    
    # Create enhanced session with all recommended components
    try:
        session_kwargs = {
            'stt': stt,
            'llm': llm,
            'tts': tts,
            'turn_detection': MultilingualModel(),
        }
        
        # Only add VAD if it loaded successfully
        if vad:
            session_kwargs['vad'] = vad
            
        session = AgentSession(**session_kwargs)
        logger.info("🎧 Agent session components initialized")
    except Exception as e:
        logger.error(f"❌ Session initialization failed: {e}")
        raise
    
    # Add session event handlers for state management
    @session.on("agent_speech_committed")
    async def on_agent_speech_committed():
        """Called when agent finishes speaking"""
        logger.info("Agent finished speaking, returning to listening state")
        await moderator.set_agent_state(AgentState.LISTENING)

    @session.on("user_speech_committed")  
    async def on_user_speech_committed():
        """Called when user finishes speaking"""
        logger.info("User speech detected, agent is listening")
        await moderator.set_agent_state(AgentState.LISTENING)

    # Start the session with enhanced room input options
    try:
        await session.start(
            agent=agent, 
            room=ctx.room,
        )
        logger.info("🚀 Agent session started successfully")
        
        # Set agent state to listening after successful start
        await moderator.set_agent_state(AgentState.LISTENING)
        
        # Generate contextual greeting with error handling
        try:
            await moderator.set_agent_state(AgentState.SPEAKING)
            greeting = f"Greetings! I am {persona}, your debate moderator for today's discussion on: {topic}. I'm here to facilitate a thoughtful dialogue. Please feel free to share your perspectives."
            
            await session.generate_reply(instructions=greeting)
            logger.info("💬 Contextual greeting sent")
            
            # Store initial greeting if memory is available
            if memory_manager and moderator.session_id:
                try:
                    await memory_manager.store_conversation_turn(
                        session_id=moderator.session_id,
                        speaker=f"AI-{persona}",
                        content=greeting,
                        turn_type="greeting"
                    )
                except Exception as e:
                    logger.error(f"Failed to store greeting: {e}")
            
            # Return to listening state after greeting
            await moderator.set_agent_state(AgentState.LISTENING)
            
        except Exception as e:
            logger.error(f"❌ Greeting generation failed: {e}")
            # Continue without greeting - agent is still functional
            await moderator.set_agent_state(AgentState.LISTENING)
        
    except Exception as e:
        logger.error(f"❌ Session start failed: {e}")
        raise

if __name__ == "__main__":
    import sys
    
    # Handle download-files command for Docker optimization
    if len(sys.argv) > 1 and sys.argv[1] == "download-files":
        logger.info("📦 Pre-downloading model files...")
        try:
            # Pre-load models to speed up startup
            silero.VAD.load()
            logger.info("✅ Models downloaded successfully")
        except Exception as e:
            logger.warning(f"⚠️ Model download failed (optional): {e}")
        sys.exit(0)
    
    # Standard LiveKit Agents CLI pattern
    logger.info("🚀 Starting LiveKit Agent with CLI")
    
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=None,
            port=8081,
        )
    ) 