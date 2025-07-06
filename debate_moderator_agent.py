#!/usr/bin/env python3

"""
Sage AI Debate Moderator Agent - Enhanced with Memory and Context
Follows official LiveKit 1.0 patterns from the documentation
"""

import os
import asyncio
import logging
from typing import Optional, List, Dict, Any, Annotated
from datetime import datetime

# Core LiveKit imports following official patterns
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
    function_tool,
    RunContext,
)
from livekit.plugins import openai, silero, deepgram, cartesia

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import memory manager with graceful fallback
try:
    from supabase_memory_manager import SupabaseMemoryManager
    logger.info("✅ Supabase memory manager imported successfully")
except ImportError as e:
    logger.warning(f"⚠️ Supabase memory manager not available: {e}")
    SupabaseMemoryManager = None

# Global variables for agent state
CURRENT_PERSONA = "Aristotle"
CURRENT_TOPIC = "AI in society"
memory_manager = None

# Initialize memory manager globally
if SupabaseMemoryManager:
    try:
        memory_manager = SupabaseMemoryManager()
        logger.info("✅ Memory manager initialized successfully")
    except Exception as e:
        logger.warning(f"⚠️ Memory manager initialization failed: {e}")
        memory_manager = None

def get_prompt_for_persona(persona: str, topic: str) -> str:
    """Get dynamic system prompt for the specified persona"""
    base_prompt = f"""You are {persona}, moderating a debate about "{topic}".

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
- "What is the virtuous path here?"
- "Let us examine this through reason and evidence"
""",
        "Socrates": """As Socrates:
- Ask probing questions to reveal assumptions
- Use the Socratic method to guide discovery
- Challenge participants to think deeper
- "What do you mean by that?"
- "How do you know this to be true?"
""",
        "Buddha": """As Buddha:
- Focus on compassion and mindful consideration
- Guide toward understanding suffering and attachment
- Encourage middle way thinking
- "What attachment might be causing this view?"
- "How might we approach this with compassion?"
"""
    }
    
    return base_prompt + persona_specific.get(persona, f"""As {persona}:
- Use your philosophical approach to guide the discussion
- Ask thoughtful questions appropriate to your perspective
- Help participants think more deeply about the topic
- Stay true to your philosophical character and methods
""")

@function_tool
async def moderate_discussion(
    context: RunContext,
    action: Annotated[str, "The moderation action to take"],
    reason: Annotated[str, "Reason for the moderation"],
):
    """Moderate the discussion when needed"""
    try:
        logger.info(f"🛡️ Moderation action: {action} - {reason}")
        
        if memory_manager:
            try:
                await memory_manager.log_moderation_action(
                    session_id="current_session",
                    action=action,
                    reason=reason,
                    persona=CURRENT_PERSONA
                )
            except Exception as e:
                logger.warning(f"Failed to log moderation: {e}")
        
        return f"As {CURRENT_PERSONA}, I must {action}. {reason}"
    
    except Exception as e:
        logger.error(f"Error in moderate_discussion: {e}")
        return f"I apologize, but I encountered an issue while moderating. Let us continue with respect and understanding."

@function_tool
async def fact_check_statement(
    context: RunContext,
    statement: Annotated[str, "The statement to fact-check"],
    participant: Annotated[str, "Who made the statement"],
):
    """Fact-check a statement made during the debate"""
    try:
        logger.info(f"🔍 Fact-checking: {statement}")
        
        # In a real implementation, this would call a fact-checking API
        return f"Let me examine that claim, {participant}. While I cannot verify all facts in real-time, I encourage us to consider the sources and evidence for such statements."
    
    except Exception as e:
        logger.error(f"Error in fact_check_statement: {e}")
        return f"I apologize, but I cannot fact-check that statement right now. Let us proceed with careful consideration of our claims."

@function_tool
async def set_debate_topic(
    context: RunContext,
    new_topic: Annotated[str, "The new topic for debate"],
):
    """Change the debate topic"""
    try:
        global CURRENT_TOPIC
        logger.info(f"📝 Setting new debate topic: {new_topic}")
        CURRENT_TOPIC = new_topic
        
        if memory_manager:
            try:
                await memory_manager.update_session_topic("current_session", new_topic)
            except Exception as e:
                logger.warning(f"Failed to update topic: {e}")
        
        return f"Excellent! Let us now turn our attention to: {new_topic}"
    
    except Exception as e:
        logger.error(f"Error in set_debate_topic: {e}")
        return f"I apologize, but I encountered an issue changing the topic. Let us continue with our current discussion."

async def entrypoint(ctx: JobContext):
    """Main entry point for the LiveKit agent following official patterns"""
    
    try:
        # Validate environment variables first
        logger.info("🔍 Validating environment variables...")
        perplexity_key = os.getenv('PERPLEXITY_API_KEY')
        openai_key = os.getenv('OPENAI_API_KEY')
        
        logger.info(f"   PERPLEXITY_API_KEY: {'✅ Found' if perplexity_key else '❌ Not found'}")
        logger.info(f"   OPENAI_API_KEY: {'✅ Found' if openai_key else '❌ Not found'}")
        
        if not perplexity_key:
            logger.error("❌ PERPLEXITY_API_KEY environment variable is required for LLM.with_perplexity()")
            raise ValueError("PERPLEXITY_API_KEY environment variable is required")
            
        # Connect to the room first (official pattern)
        logger.info("🔗 Connecting to LiveKit room...")
        await ctx.connect()
        logger.info("✅ Successfully connected to LiveKit room")
        
        # Now we can access the actual room object and its metadata
        room = ctx.room
        room_metadata = {}
        
        # Safely get metadata if available
        if hasattr(room, 'metadata') and room.metadata:
            try:
                import json
                room_metadata = json.loads(room.metadata) if isinstance(room.metadata, str) else room.metadata
                logger.info(f"📋 Room metadata loaded: {room_metadata}")
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Failed to parse room metadata: {e}, using defaults")
                room_metadata = {}
        
        # Extract persona and topic from room metadata or use defaults
        global CURRENT_PERSONA, CURRENT_TOPIC
        CURRENT_PERSONA = room_metadata.get('persona', 'Aristotle')
        CURRENT_TOPIC = room_metadata.get('topic', 'AI in society')
        
        logger.info(f"🎭 Starting {CURRENT_PERSONA} moderator for topic: {CURRENT_TOPIC}")
        
        # Create the debate moderator agent with function tools (official pattern)
        agent = Agent(
            instructions=get_prompt_for_persona(CURRENT_PERSONA, CURRENT_TOPIC),
            tools=[moderate_discussion, fact_check_statement, set_debate_topic]
        )
        
        # Create session with OpenAI (temporarily while Perplexity integration is fixed)
        session = AgentSession(
            vad=silero.VAD.load(),
            stt=deepgram.STT(model="nova-2"),
            llm=openai.LLM(
                model="gpt-4o-mini",
                temperature=0.7,
            ),
            tts=openai.TTS(voice="alloy"),
        )
        logger.info("✅ AgentSession created successfully")
        
        # Start the session with the agent and room (official pattern)
        logger.info("🚀 Starting agent session...")
        await session.start(agent=agent, room=room)
        logger.info("✅ Agent session started successfully")
        
        # Generate initial greeting (official pattern)
        logger.info("👋 Generating initial greeting...")
        await session.generate_reply(
            instructions="Greet the participants and introduce yourself as the debate moderator. Briefly explain your role and invite them to begin the discussion."
        )
        logger.info("✅ Initial greeting generated successfully")
        
        # Keep the session alive
        logger.info("🔄 Agent is now active and ready for participants")
        
    except Exception as e:
        logger.error(f"❌ Critical error in entrypoint: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error details: {str(e)}")
        
        # Try to handle gracefully
        try:
            if 'session' in locals():
                logger.info("🛑 Attempting graceful session cleanup...")
                # Session cleanup would go here if needed
        except Exception as cleanup_error:
            logger.error(f"❌ Error during cleanup: {cleanup_error}")
        
        # Re-raise the exception so LiveKit can handle it
        raise

if __name__ == "__main__":
    try:
        logger.info("🎬 Starting LiveKit Debate Moderator Agent...")
        cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
    except Exception as e:
        logger.error(f"❌ Failed to start agent: {e}")
        raise 