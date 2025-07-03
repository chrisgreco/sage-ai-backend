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

# Core LiveKit imports
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
    function_tool,
    RunContext,
)
from livekit.plugins import openai, silero, deepgram

# Import memory manager
from supabase_memory_manager import memory_manager

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DebateModerator:
    """Enhanced Debate Moderator with Memory and Context"""
    
    def __init__(self, topic: str, persona: str, room_name: str):
        self.topic = topic
        self.persona = persona
        self.room_name = room_name
        self.session_id: Optional[str] = None
        self.participants: List[str] = []
        self.conversation_count = 0
        
        logger.info(f"Initialized {persona} moderator for topic: '{topic}' in room: {room_name}")

    async def initialize_session(self):
        """Initialize debate session in memory system"""
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
        
        # Store in memory
        if self.session_id:
            await memory_manager.store_moderation_action(
                session_id=self.session_id,
                action_type="topic_change",
                details={"old_topic": old_topic, "new_topic": topic, "context": context_info}
            )
        
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
        self.conversation_count += 1
        
        # Store conversation turn
        if self.session_id and speaker_name:
            await memory_manager.store_conversation_turn(
                session_id=self.session_id,
                speaker=speaker_name,
                content=participant_statement,
                turn_type="speech"
            )
        
        # Get recent context for informed moderation
        recent_context = []
        if self.session_id:
            recent_conversation = await memory_manager.get_recent_conversation(self.session_id, limit=5)
            recent_context = [f"{turn['speaker']}: {turn['content']}" for turn in recent_conversation]
        
        # Persona-specific moderation approach
        persona_instructions = get_persona_instructions(self.persona)
        
        context_text = f"Topic: {self.topic}\n"
        if recent_context:
            context_text += f"Recent conversation:\n" + "\n".join(recent_context[-3:]) + "\n"
        context_text += f"Current statement: {participant_statement}\n"
        context_text += f"Respond as {self.persona} would, following these guidelines: {persona_instructions}"
        
        # Store moderation action
        if self.session_id:
            await memory_manager.store_moderation_action(
                session_id=self.session_id,
                action_type="moderation_response",
                details={
                    "speaker": speaker_name,
                    "statement": participant_statement,
                    "conversation_count": self.conversation_count
                }
            )
        
        return context_text

    @function_tool
    async def fact_check_statement(
        self,
        context: RunContext,
        claim: str,
        speaker: Optional[str] = None
    ) -> str:
        """Fact-check a statement using research capabilities"""
        
        # Store fact-check request
        if self.session_id:
            await memory_manager.store_moderation_action(
                session_id=self.session_id,
                action_type="fact_check",
                details={"claim": claim, "speaker": speaker}
            )
        
        fact_check_prompt = f"""
        As {self.persona}, I need to fact-check this claim made in our debate about '{self.topic}':
        
        Claim: "{claim}"
        Speaker: {speaker or 'Unknown'}
        
        Please verify this claim and provide:
        1. Whether the claim is accurate, partially accurate, or inaccurate
        2. Reliable sources or evidence
        3. Any important context or nuance
        4. How this relates to our debate topic
        
        Respond in the voice and style of {self.persona}.
        """
        
        return fact_check_prompt

    async def get_session_context(self) -> Dict[str, Any]:
        """Get comprehensive session context for AI reasoning"""
        if not self.session_id:
            return {"topic": self.topic, "persona": self.persona}
        
        return await memory_manager.get_debate_context(self.session_id)

def get_persona_instructions(persona: str) -> str:
    """Get persona-specific instructions"""
    personas = {
        "Aristotle": """
        You are Aristotle, the great philosopher and logician. Your approach to debate moderation emphasizes:
        - Logical reasoning and structured arguments
        - Identifying fallacies and weak reasoning
        - Encouraging evidence-based claims
        - Maintaining intellectual rigor while being respectful
        - Using the Socratic method to probe deeper into arguments
        - Fact-checking claims against reliable sources
        """,
        
        "Socrates": """
        You are Socrates, master of questioning and dialogue. Your moderation style focuses on:
        - Asking probing questions to clarify positions
        - Exposing assumptions and contradictions
        - Encouraging self-reflection and deeper thinking
        - Using gentle irony to highlight inconsistencies
        - Guiding participants to discover truth through questioning
        - Never claiming to know everything, but always seeking wisdom
        """,
        
        "Buddha": """
        You are the Buddha, embodying compassion and mindful awareness. Your moderation emphasizes:
        - Maintaining peace and reducing conflict
        - Encouraging compassionate listening
        - Helping participants understand different perspectives
        - Addressing emotional reactions with kindness
        - Promoting mindful speech and thoughtful responses
        - Seeking middle paths and balanced understanding
        """,
        
        "Confucius": """
        You are Confucius, advocate of harmony and proper conduct. Your approach includes:
        - Maintaining respectful dialogue and proper etiquette
        - Emphasizing moral and ethical dimensions
        - Encouraging learning from different viewpoints
        - Promoting social harmony while allowing healthy debate
        - Focusing on practical wisdom and real-world applications
        - Modeling virtuous behavior in moderation
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
    
    # Initialize moderator with context
    moderator = DebateModerator(topic=topic, persona=persona, room_name=room_name)
    await moderator.initialize_session()
    
    # Get persona instructions
    instructions = get_persona_instructions(persona)
    
    # Create agent with enhanced tools
    agent = Agent(
        instructions=f"""
        You are {persona}, moderating a debate about: "{topic}"
        
        {instructions}
        
        Your goal is to facilitate a productive, respectful, and insightful debate while staying true to your philosophical approach.
        
        Use your tools to:
        - Moderate discussions based on the topic and your persona
        - Fact-check claims when participants make factual assertions
        - Maintain conversation context and participant memory
        
        Always respond in character as {persona} would.
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
    
    if not perplexity_key:
        raise ValueError("PERPLEXITY_API_KEY environment variable is required")
    if not openai_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    
    logger.info("🔑 API keys verified")
    
    # Configure LLM with Perplexity for research-backed responses
    try:
        perplexity_model = os.getenv("PERPLEXITY_MODEL", "llama-3.1-sonar-small-128k-online")
        llm = openai.LLM.with_perplexity(
            model=perplexity_model,
            api_key=perplexity_key,
            temperature=0.7
        )
        logger.info(f"🧠 Perplexity LLM configured: {perplexity_model}")
        
        # Test connection
        test_response = await llm.chat([{"role": "user", "content": "Hello"}])
        if test_response:
            logger.info("✅ Perplexity API connection successful")
        
    except Exception as e:
        logger.error(f"❌ Perplexity LLM setup failed: {e}")
        raise
    
    # Configure TTS with OpenAI
    try:
        tts = openai.TTS(
            voice="alloy",
            api_key=openai_key,
        )
        logger.info("🎤 OpenAI TTS configured")
    except Exception as e:
        logger.error(f"❌ OpenAI TTS setup failed: {e}")
        raise
    
    # Create session with all components
    session = AgentSession(
        vad=silero.VAD.load(),
        stt=deepgram.STT(model="nova-2"),
        llm=llm,
        tts=tts,
    )
    
    # Start the session
    try:
        await session.start(agent=agent, room=ctx.room)
        logger.info("🚀 Agent session started successfully")
        
        # Generate contextual greeting
        greeting = f"""
        Greetings! I am {persona}, your debate moderator for today's discussion on: "{topic}"
        
        I'm here to facilitate a thoughtful and structured dialogue. 
        I'll help ensure our conversation remains productive, fact-based, and respectful.
        
        Please feel free to begin sharing your perspectives on this important topic.
        """
        
        await session.generate_reply(instructions=greeting)
        logger.info("💬 Contextual greeting sent")
        
        # Store initial greeting
        if moderator.session_id:
            await memory_manager.store_conversation_turn(
                session_id=moderator.session_id,
                speaker=f"AI-{persona}",
                content=greeting,
                turn_type="greeting"
            )
        
    except Exception as e:
        logger.error(f"❌ Session start failed: {e}")
        raise

if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            # Allow agent to connect to any room
            prewarm_fnc=None,
        )
    ) 