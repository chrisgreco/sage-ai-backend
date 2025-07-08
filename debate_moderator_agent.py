#!/usr/bin/env python3

"""
Sage AI Debate Moderator Agent - Official LiveKit 1.0 Patterns
Follows exact patterns from https://docs.livekit.io/agents/quickstarts/voice-agent/
"""

import os
import json
import logging
from typing import Annotated
from dotenv import load_dotenv

# Core LiveKit imports following official patterns
from livekit import agents
from livekit.agents import Agent, AgentSession, JobContext, RunContext, WorkerOptions, cli, function_tool
from livekit.plugins import deepgram, openai, silero

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger("sage-debate-moderator")

# Import memory manager with graceful fallback
try:
    from supabase_memory_manager import SupabaseMemoryManager
    memory_manager = SupabaseMemoryManager()
    logger.info("✅ Memory manager initialized successfully")
except Exception as e:
    logger.warning(f"⚠️ Memory manager initialization failed: {e}")
    memory_manager = None

# Global variables for agent state - MUST be set from room metadata
current_persona = None
current_topic = None

def get_persona_instructions(persona: str, topic: str) -> str:
    """Generate persona-specific instructions based on the selected moderator"""
    
    base_instructions = f"""You are {persona}, a concise debate moderator for voice conversations.

CRITICAL: Start EVERY conversation with exactly this greeting:
"Hello, I'm {persona}. Today we'll be discussing {topic}. Go ahead with your opening arguments, and call upon me as needed."

Key behaviors:
- Keep responses SHORT and SWEET (1-2 sentences max)
- Ask brief, pointed questions
- Guide discussion efficiently
- Use your philosophical approach but be concise
- Only speak when needed

Current topic: {topic}

"""
    
    persona_specific = {
        "Aristotle": """As Aristotle:
- Use logical reasoning and practical wisdom
- Ask brief questions about principles and virtue
- Guide toward balanced arguments
""",
        "Socrates": """As Socrates:
- Use short Socratic questions
- Challenge assumptions briefly
- Ask "What do you mean?" and "How do you know?"
""",
        "Buddha": """As Buddha:
- Focus on compassion and understanding
- Ask brief questions about attachment and suffering
- Guide toward mindful dialogue
"""
    }
    
    return base_instructions + persona_specific.get(persona, f"""As {persona}:
- Use your philosophical approach briefly
- Ask short, thoughtful questions
- Stay true to your character but be concise
""")

# Function tools following official patterns
@function_tool
async def moderate_discussion(
    context: RunContext,
    action: Annotated[str, "The moderation action to take: 'redirect', 'clarify', 'summarize', or 'question'"],
    content: Annotated[str, "The specific content or question for the moderation action"]
) -> str:
    """Moderate the debate discussion with specific actions"""
    try:
        logger.info(f"🎯 Moderating discussion: {action} - {content}")
        
        # Store moderation action in memory
        if memory_manager:
            await memory_manager.store_moderation_action(action, content, current_persona)
        
        return f"As {current_persona}, I will {action}: {content}"
        
    except Exception as e:
        logger.error(f"Error in moderate_discussion: {e}")
        return f"I'll help moderate this discussion as {current_persona}."

@function_tool
async def fact_check_statement(
    context: RunContext,
    statement: Annotated[str, "The statement to fact-check"]
) -> str:
    """Fact-check a statement using available knowledge"""
    try:
        logger.info(f"🔍 Fact-checking statement: {statement}")
        
        # Store the fact-check request in memory for context
        if memory_manager:
            await memory_manager.store_fact_check(statement, "fact-check-requested")
        
        return f"I'll fact-check this statement using available knowledge: {statement}"
        
    except Exception as e:
        logger.error(f"Error in fact_check_statement: {e}")
        return f"I'll verify this information: {statement}"

@function_tool
async def set_debate_topic(
    context: RunContext,
    topic: Annotated[str, "The new debate topic to set"]
) -> str:
    """Set a new topic for the debate discussion"""
    try:
        global current_topic
        current_topic = topic
        logger.info(f"📝 Setting debate topic: {topic}")
        
        # Store topic change in memory
        if memory_manager:
            await memory_manager.store_topic_change(topic, current_persona)
        
        return f"Perfect! I've set our debate topic to: {topic}. Let's explore this together."
        
    except Exception as e:
        logger.error(f"Error in set_debate_topic: {e}")
        return f"I'll guide our discussion on: {topic}"

# Agent class following official patterns
class SageDebateModerator(Agent):
    def __init__(self, persona: str, topic: str) -> None:
        super().__init__(
            instructions=get_persona_instructions(persona, topic),
            tools=[moderate_discussion, fact_check_statement, set_debate_topic],
        )

# Main entrypoint following exact official pattern
async def entrypoint(ctx: JobContext):
    """Main entry point for the LiveKit agent following official patterns"""
    
    try:
        logger.info("🚀 Starting Sage AI Debate Moderator Agent...")
        
        # Validate environment variables
        logger.info("🔍 Validating environment variables...")
        openai_key = os.getenv('OPENAI_API_KEY')
        deepgram_key = os.getenv('DEEPGRAM_API_KEY')
        
        logger.info(f"   OPENAI_API_KEY: {'✅ Found' if openai_key else '❌ Not found'}")
        logger.info(f"   DEEPGRAM_API_KEY: {'✅ Found' if deepgram_key else '❌ Not found'}")
        
        if not openai_key:
            logger.error("❌ OPENAI_API_KEY environment variable is required")
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        # Connect to room first (exact official pattern)
        logger.info("🔗 Connecting to LiveKit room...")
        await ctx.connect()
        logger.info("✅ Connected to room successfully")
        
        # CORRECT APPROACH: Read metadata from environment variables
        # For the LiveKit agent worker pattern, metadata comes from environment variables
        
        logger.info("🔍 Reading agent metadata from environment variables...")
        
        # Extract persona and topic from environment variables
        global current_persona, current_topic
        
        # Read from environment variables (set by backend)
        current_persona = os.getenv('DEBATE_PERSONA')
        current_topic = os.getenv('DEBATE_TOPIC')
        current_room = os.getenv('DEBATE_ROOM')
        
        # Log environment variable debugging
        logger.info(f"🔍 Environment variables:")
        logger.info(f"   DEBATE_PERSONA: {current_persona}")
        logger.info(f"   DEBATE_TOPIC: {current_topic}")
        logger.info(f"   DEBATE_ROOM: {current_room}")
        
        # If still no metadata, this indicates the backend is not setting environment variables
        if not current_persona or not current_topic:
            logger.error(f"❌ MISSING METADATA: persona={current_persona}, topic={current_topic}")
            logger.error("❌ This indicates the backend is not setting environment variables!")
            
            # Use emergency fallbacks but log the issue
            current_persona = current_persona or "Aristotle"
            current_topic = current_topic or "General Discussion"
            logger.warning(f"⚠️ Using emergency fallbacks: {current_persona}, {current_topic}")
        
        logger.info(f"🎭 Persona: {current_persona}")
        logger.info(f"📝 Topic: {current_topic}")
        logger.info(f"🏠 Room: {current_room}")
        
        # Create agent with persona-specific instructions and tools
        agent = SageDebateModerator(current_persona, current_topic)
        
        # Create session with OpenAI with deep male voice (onyx)
        logger.info("🧠 Creating AgentSession with OpenAI integration...")
        session = AgentSession(
            vad=silero.VAD.load(),
            stt=deepgram.STT(model="nova-2"),
            llm=openai.LLM(
                model="gpt-4o-mini",
                temperature=0.7,
            ),
            tts=openai.TTS(voice="onyx"),  # Deep, old-sounding male voice
        )
        
        logger.info("✅ AgentSession created successfully")
        
        # Start session with agent and room (exact official pattern)
        logger.info("▶️ Starting agent session...")
        await session.start(agent=agent, room=ctx.room)
        
        # Generate initial reply with exact greeting format
        initial_greeting = f"Hello, I'm {current_persona}. Today we'll be discussing {current_topic}. Go ahead with your opening arguments, and call upon me as needed."
        
        logger.info("💬 Generating initial greeting...")
        await session.generate_reply(instructions=initial_greeting)
        
        logger.info("🎉 Sage AI Debate Moderator Agent is now active!")
        
    except Exception as e:
        logger.error(f"❌ Error in entrypoint: {e}")
        raise

# CLI integration with agent registration for dispatch system
if __name__ == "__main__":
    cli.run_app(WorkerOptions(
        entrypoint_fnc=entrypoint,
        agent_name="sage-debate-moderator"  # Register with specific name for dispatch
    )) 