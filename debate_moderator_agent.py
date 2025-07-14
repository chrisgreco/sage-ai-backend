#!/usr/bin/env python3

"""
Sage AI Debate Moderator Agent - Official LiveKit 1.0 Patterns
Follows exact patterns from https://docs.livekit.io/agents/quickstarts/voice-agent/
"""

import os
import json
import logging
from typing import Annotated
# Core LiveKit imports following official patterns
from livekit import agents
from livekit.agents import JobContext, RunContext, WorkerOptions, cli, function_tool
from livekit.plugins import deepgram, openai, silero, cartesia

# Environment variables are managed by Render directly - no need for dotenv
# load_dotenv() removed since Render sets environment variables

# Configure logging
logger = logging.getLogger("sage-debate-moderator")

# Import memory manager with graceful fallback
try:
    from supabase_memory_manager import SupabaseMemoryManager
    memory_manager = SupabaseMemoryManager()
    logger.info("✅ Supabase memory manager initialized successfully")
except ImportError:
    logger.warning("⚠️ Supabase memory manager not available - continuing without memory features")
    memory_manager = None
except Exception as e:
    logger.warning(f"⚠️ Memory manager initialization failed: {e}")
    memory_manager = None

# Global variables for agent state
current_persona = None
current_topic = None

def get_persona_instructions(persona: str, topic: str) -> str:
    """Generate persona-specific instructions based on the selected moderator"""
    
    base_instructions = f"""You are {persona}, a wise debate moderator for voice conversations.

CRITICAL: Start EVERY conversation with exactly this greeting:
"Hello, I'm {persona}. Today we'll be discussing {topic}. Go ahead with your opening arguments, and call upon me as needed."

Core principles:
- Keep responses SHORT (1-2 sentences max)
- Let participants lead - only intervene when needed
- Allow natural pauses in conversation"""

    persona_specific = {
        "Socrates": """
Socratic approach:
- Ask ONE thoughtful question, then let them think
- Sometimes just acknowledge: "That's worth reflecting on"
- Practice intellectual humility: "I'm not sure about that either"
- Don't question every response - balance with supportive comments""",

        "Aristotle": """
Aristotelian approach:
- Guide toward balanced, logical positions
- Point out logical fallacies briefly
- Encourage evidence-based reasoning
- Help find middle ground between extremes""",

        "Buddha": """
Buddhist approach:
- Focus on compassion and understanding
- Help find common ground between opposing views
- Encourage mindful listening
- Gently redirect away from personal attacks"""
    }

    return base_instructions + "\n" + persona_specific.get(persona, "")

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
        
        # OFFICIAL LIVEKIT PATTERN: Read metadata from ctx.job.metadata
        # According to official LiveKit documentation, job metadata is accessed via ctx.job.metadata
        
        logger.info("🔍 Reading agent metadata from job metadata (official LiveKit pattern)...")
        
        # Extract persona and topic from job metadata
        global current_persona, current_topic
        
        # Read from job metadata (official LiveKit pattern)
        job_metadata = {}
        
        logger.info(f"🔍 Job object: {ctx.job}")
        logger.info(f"🔍 Job metadata raw: {getattr(ctx.job, 'metadata', 'No metadata attribute')}")
        
        if hasattr(ctx.job, 'metadata') and ctx.job.metadata:
            try:
                # Job metadata is passed as JSON string according to docs
                if isinstance(ctx.job.metadata, str):
                    job_metadata = json.loads(ctx.job.metadata)
                else:
                    job_metadata = ctx.job.metadata
                logger.info(f"🎯 Job metadata parsed: {job_metadata}")
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Failed to parse job metadata: {e}")
                job_metadata = {}
        else:
            logger.warning("🎯 Job metadata: empty or missing")
        
        current_persona = job_metadata.get('persona')
        current_topic = job_metadata.get('topic')
        
        logger.info(f"🎭 Extracted persona from job metadata: {current_persona}")
        logger.info(f"💭 Extracted topic from job metadata: {current_topic}")
        
        # If still no metadata, this indicates the agent dispatch is not including metadata correctly
        if not current_persona or not current_topic:
            logger.error(f"❌ MISSING METADATA: persona={current_persona}, topic={current_topic}")
            logger.error(f"❌ Job metadata received: {job_metadata}")
            logger.error("❌ This indicates the backend agent dispatch is not including metadata correctly!")
            
            # Use emergency fallbacks but log the issue
            current_persona = current_persona or "Aristotle"
            current_topic = current_topic or "General Discussion"
            logger.warning(f"⚠️ Using emergency fallbacks: {current_persona}, {current_topic}")
        
        logger.info(f"🎭 Persona: {current_persona}")
        logger.info(f"📝 Topic: {current_topic}")
        logger.info(f"🔍 Full job metadata: {job_metadata}")
        
        # Create agent with persona-specific instructions and tools
        logger.info(f"🎭 Creating {current_persona} agent with topic: {current_topic}")
        
        # Configure Cartesia TTS (official implementation)
        logger.info("🎤 Configuring Cartesia TTS...")
        
        tts = cartesia.TTS(
            model="sonic-2-2025-03-07",  # Updated model that supports speed controls
            voice="a0e99841-438c-4a64-b679-ae501e7d6091",  # British Male (professional, deeper voice)
            speed=0.5,  # Much slower speed for deliberate, thoughtful speech
        )
        logger.info("✅ Using Cartesia TTS with slower British male voice")
        
        # Create Agent with tools and instructions (supports function tools)
        agent = agents.Agent(
            instructions=get_persona_instructions(current_persona, current_topic),
            tools=[moderate_discussion, fact_check_statement, set_debate_topic],
        )
        
        # Create AgentSession with Cartesia TTS (official pattern)
        session = agents.AgentSession(
            vad=silero.VAD.load(),
            stt=deepgram.STT(),
            llm=openai.LLM(model="gpt-4o-mini"),
            tts=tts,  # Use Cartesia TTS
        )
        
        logger.info("✅ Agent and AgentSession created successfully")
        
        # Start the session (official pattern)
        logger.info("▶️ Starting agent session...")
        await session.start(agent=agent, room=ctx.room)
        
        logger.info("🎉 Sage AI Debate Moderator Agent is now active and listening!")
        logger.info(f"🏠 Agent joined room: {ctx.room.name}")
        logger.info(f"👤 Agent participant identity: {current_persona}")  # Uses persona as identity
        
        # Send initial greeting (official pattern)
        initial_greeting = f"Hello, I'm {current_persona}. Today we'll be discussing {current_topic}. Go ahead with your opening arguments, and call upon me as needed."
        logger.info(f"🎤 Sending initial greeting: {initial_greeting}")
        await session.generate_reply(instructions=f"Say exactly: '{initial_greeting}'")
        
    except Exception as e:
        logger.error(f"❌ Error in entrypoint: {e}")
        raise

# Request handler - use persona name as identity (what frontend expects)
async def handle_job_request(job_req: agents.JobRequest):
    """Handle incoming job requests with persona-based identity"""
    try:
        # Extract persona from job metadata
        job_metadata = {}
        if hasattr(job_req.job, 'metadata') and job_req.job.metadata:
            try:
                if isinstance(job_req.job.metadata, str):
                    job_metadata = json.loads(job_req.job.metadata)
                else:
                    job_metadata = job_req.job.metadata
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Failed to parse job metadata: {e}")
        
        # Get persona from metadata, default to Socrates
        persona = job_metadata.get('persona', 'Socrates')
        
        logger.info(f"🎭 Job request received for room: {job_req.room.name}")
        logger.info(f"🎭 Setting agent identity to: {persona}")
        
        # ✅ FIXED: Use persona name as identity (LiveKit best practice)
        # Frontend expects agent identity to match persona name exactly
        await job_req.accept(
            identity=persona,                    # ✅ "Socrates", "Aristotle", "Buddha"
            name=f"Sage AI - {persona}",         # Display name with persona
        )
        
        logger.info(f"✅ Agent accepted job with identity: {persona}")
        
    except Exception as e:
        logger.error(f"❌ Error handling job request: {e}")
        await job_req.reject()

# CLI integration with agent registration for dispatch system
if __name__ == "__main__":
    logger.info("🚀 Starting Sage AI Debate Moderator Agent...")
    logger.info(f"🔑 Environment check:")
    logger.info(f"   LIVEKIT_URL: {'✅ Set' if os.getenv('LIVEKIT_URL') else '❌ Missing'}")
    logger.info(f"   LIVEKIT_API_KEY: {'✅ Set' if os.getenv('LIVEKIT_API_KEY') else '❌ Missing'}")
    logger.info(f"   LIVEKIT_API_SECRET: {'✅ Set' if os.getenv('LIVEKIT_API_SECRET') else '❌ Missing'}")
    logger.info(f"   OPENAI_API_KEY: {'✅ Set' if os.getenv('OPENAI_API_KEY') else '❌ Missing'}")
    logger.info(f"   DEEPGRAM_API_KEY: {'✅ Set' if os.getenv('DEEPGRAM_API_KEY') else '❌ Missing'}")
    
    cli.run_app(WorkerOptions(
        entrypoint_fnc=entrypoint,
        request_fnc=handle_job_request,  # Custom job request handler
        agent_name="sage-debate-moderator",  # Register with specific name for dispatch
        # Configure worker permissions according to official LiveKit API
        permissions=agents.WorkerPermissions(
            can_publish=True,
            can_subscribe=True,
            can_publish_data=True,
            can_update_metadata=True,
        ),
    )) 