#!/usr/bin/env python3

"""
Sage AI Debate Moderator Agent - Enhanced with Memory and Context
Follows exact official LiveKit 1.0 patterns from the documentation
"""

import os
import asyncio
import logging
import json
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
    memory_manager = SupabaseMemoryManager()
    logger.info("✅ Memory manager initialized successfully")
except Exception as e:
    logger.warning(f"⚠️ Memory manager initialization failed: {e}")
    memory_manager = None

# Global variables for agent state (following official patterns)
current_persona = "Aristotle"
current_topic = "General Discussion"

def get_persona_prompt(persona: str) -> str:
    """Generate persona-specific prompt based on the selected moderator"""
    
    base_prompt = f"""You are {persona}, acting as a debate moderator for voice conversations. 
Your role is to:
- Guide meaningful philosophical discussions
- Ask thought-provoking questions
- Help participants explore different perspectives
- Maintain respectful dialogue
- Use your unique philosophical approach

Current topic: {current_topic}

"""
    
    persona_specific = {
        "Aristotle": """As Aristotle:
- Use logical reasoning and systematic analysis
- Ask questions that reveal underlying principles
- Guide discussions toward practical wisdom (phronesis)
- Help participants find the "golden mean" in their arguments
- Focus on virtue ethics and character development
""",
        "Socrates": """As Socrates:
- Use the Socratic method of questioning
- Challenge assumptions through inquiry
- Ask "What do you mean by..." and "How do you know..." questions
- Guide participants to discover contradictions in their thinking
- Emphasize that true wisdom comes from knowing what you don't know
""",
        "Buddha": """As Buddha:
- Focus on reducing suffering and finding peace
- Ask questions about attachment and desire
- Guide discussions toward compassion and understanding
- Help participants see interconnectedness
- Emphasize mindfulness and present-moment awareness
"""
    }
    
    return base_prompt + persona_specific.get(persona, f"""As {persona}:
- Use your philosophical approach to guide the discussion
- Ask thoughtful questions appropriate to your perspective
- Help participants think more deeply about the topic
- Stay true to your philosophical character and methods
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
async def fact_check_statement(statement: Annotated[str, "The statement to fact-check"]) -> str:
    """Fact-check a statement using real-time search capabilities"""
    try:
        logger.info(f"🔍 Fact-checking statement: {statement}")
        
        # Store the fact-check request in memory for context
        if memory_manager:
            await memory_manager.store_fact_check(statement, "fact-check-requested")
        
        # Let the LLM handle fact-checking through OpenAI's knowledge base
        return f"I'll fact-check this statement using current information: {statement}"
        
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

# Main entrypoint following exact official pattern
async def entrypoint(ctx: JobContext):
    """Main entry point for the LiveKit agent following official patterns"""
    
    try:
        logger.info("🚀 Starting Sage AI Debate Moderator Agent...")
        
        # Validate environment variables
        logger.info("🔍 Validating environment variables...")
        openai_key = os.getenv('OPENAI_API_KEY')
        
        logger.info(f"   OPENAI_API_KEY: {'✅ Found' if openai_key else '❌ Not found'}")
        
        if not openai_key:
            logger.error("❌ OPENAI_API_KEY environment variable is required for OpenAI LLM")
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        # Connect to room first (official pattern)
        logger.info("🔗 Connecting to LiveKit room...")
        await ctx.connect()
        logger.info("✅ Connected to room successfully")
        
        # Get room metadata safely
        room = ctx.room
        room_metadata = {}
        
        if hasattr(room, 'metadata') and room.metadata:
            try:
                room_metadata = json.loads(room.metadata) if isinstance(room.metadata, str) else room.metadata
                logger.info(f"📋 Room metadata: {room_metadata}")
            except (json.JSONDecodeError, TypeError):
                logger.warning("Failed to parse room metadata, using defaults")
                room_metadata = {}
        
        # Extract persona and topic from room metadata
        global current_persona, current_topic
        current_persona = room_metadata.get('persona', 'Aristotle')
        current_topic = room_metadata.get('topic', 'General Discussion')
        
        logger.info(f"🎭 Persona: {current_persona}")
        logger.info(f"📝 Topic: {current_topic}")
        
        # Create agent with instructions and tools (exact official pattern)
        agent = Agent(
            instructions=get_persona_prompt(current_persona),
            tools=[moderate_discussion, fact_check_statement, set_debate_topic],
        )
        
        # Create session with OpenAI (temporarily while Perplexity integration is fixed)
        logger.info("🧠 Creating AgentSession with OpenAI integration...")
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
        
        # Start session with agent and room (exact official pattern)
        logger.info("▶️ Starting agent session...")
        await session.start(agent=agent, room=ctx.room)
        
        # Generate initial reply (exact official pattern)
        initial_greeting = f"Hello! I'm {current_persona}, and I'll be moderating our discussion on {current_topic}. How would you like to begin exploring this topic together?"
        
        logger.info("💬 Generating initial greeting...")
        await session.generate_reply(instructions=initial_greeting)
        
        logger.info("🎉 Sage AI Debate Moderator Agent is now active!")
        
    except Exception as e:
        logger.error(f"❌ Error in entrypoint: {e}")
        raise

# CLI integration (exact official pattern)
if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint)) 