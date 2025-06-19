#!/usr/bin/env python3
"""
Aristotle Agent - Individual AI personality for philosophical debates
"""

import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# LiveKit Agents imports
try:
    from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, cli, function_tool, RunContext
    from livekit.plugins import openai, silero
    from livekit.plugins.turn_detector import EnglishModel
    logger.info("✅ LiveKit Agents successfully imported")
except ImportError as e:
    logger.error(f"❌ LiveKit Agents import failed: {e}")
    sys.exit(1)

# Perplexity research integration
try:
    from perplexity_research import PerplexityResearcher
    PERPLEXITY_AVAILABLE = True
    logger.info("✅ Perplexity research module imported")
except ImportError as e:
    logger.warning(f"⚠️ Perplexity research module not available: {e}")
    PERPLEXITY_AVAILABLE = False

# Initialize Perplexity researcher
if PERPLEXITY_AVAILABLE:
    perplexity_researcher = PerplexityResearcher()
else:
    perplexity_researcher = None

@function_tool
async def research_fact(
    context: RunContext,
    claim: str,
) -> str:
    """Research and fact-check a claim using real-time sources. Use this when you need current data or want to verify statements."""
    
    if not PERPLEXITY_AVAILABLE or not perplexity_researcher:
        return "Research tools unavailable - providing analysis based on training data only."
    
    try:
        result = await perplexity_researcher.research_claim(claim)
        if result and result.answer:
            logger.info(f"🔍 Researched claim: {claim[:50]}... -> {result.answer[:100]}...")
            return f"According to current sources: {result.answer}"
        else:
            return "Unable to research this claim at the moment."
    except Exception as e:
        logger.error(f"Research failed: {e}")
        return "Research temporarily unavailable."

@function_tool  
async def verify_statistic(
    context: RunContext,
    statistic: str,
) -> str:
    """Verify specific statistics or numerical claims using current data sources."""
    
    if not PERPLEXITY_AVAILABLE or not perplexity_researcher:
        return "Statistical verification unavailable - cannot confirm current numbers."
    
    try:
        result = await perplexity_researcher.verify_statistics(statistic)
        if result and result.answer:
            logger.info(f"📊 Verified statistic: {statistic[:50]}... -> {result.answer[:100]}...")
            return f"Current data shows: {result.answer}"
        else:
            return "Unable to verify this statistic currently."
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return "Statistical verification temporarily unavailable."

# Aristotle personality configuration - ULTRA CONCISE WITH RESEARCH
ARISTOTLE_CONFIG = {
    "name": "Aristotle",
    "voice": "onyx",  # Changed to male voice
    "instructions": """You are Aristotle. Give 1 logical point (max 15 words) OR use research tools.

CRITICAL RULES:
- WAIT for complete silence before speaking
- If someone says "Socrates" - stay silent  
- 15 words maximum per response
- Use research_fact() or verify_statistic() when claims need checking
- Only ONE logical point per turn
- Analyze, then respond briefly"""
}

async def entrypoint(ctx: JobContext):
    """Aristotle agent entrypoint"""
    
    logger.info("🏛️ Aristotle joining the philosophical debate...")
    await ctx.connect()
    logger.info(f"✅ Aristotle connected to room: {ctx.room.name}")
    
    # Get debate topic from room metadata or job metadata
    debate_topic = "The impact of AI on society"  # Default topic
    
    if ctx.room.metadata:
        try:
            import json
            room_metadata = json.loads(ctx.room.metadata)
            debate_topic = room_metadata.get("debate_topic", debate_topic)
            logger.info(f"🎯 Room topic: {debate_topic}")
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"⚠️ Could not parse room metadata: {e}")
    
    # Check job metadata for agent-specific information
    if hasattr(ctx, 'job') and ctx.job.metadata:
        try:
            import json
            job_metadata = json.loads(ctx.job.metadata)
            role = job_metadata.get("role", "logical_analyst")
            agent_type = job_metadata.get("agent_type", "aristotle")
            job_topic = job_metadata.get("debate_topic")
            if job_topic:
                debate_topic = job_topic
            logger.info(f"🎭 Job role: {role}, Agent type: {agent_type}")
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"⚠️ Could not parse job metadata: {e}")
    
    logger.info(f"💭 Debate topic: {debate_topic}")
    
    # Create agent session with ADVANCED turn detection
    session = AgentSession(
        llm=openai.realtime.RealtimeModel(
            model="gpt-4o-realtime-preview-2024-12-17",
            voice=ARISTOTLE_CONFIG["voice"],
            temperature=0.7,
            speed=1.3  # 30% faster speech
        ),
        vad=silero.VAD.load(),
        turn_detector=EnglishModel.load(),  # Semantic turn detection
        min_endpointing_delay=1.2,  # Aristotle waits 1.2s minimum (longer than Socrates)
        max_endpointing_delay=4.5,
    )
    
    # Start session with research tools
    tools = [research_fact, verify_statistic] if PERPLEXITY_AVAILABLE else []
    
    await session.start(
        agent=Agent(
            instructions=ARISTOTLE_CONFIG["instructions"],
            tools=tools
        ),
        room=ctx.room
    )
    
    logger.info("✅ Aristotle is ready for logical analysis with research capabilities!")

def main():
    """Main function"""
    required_vars = ["LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "LIVEKIT_URL", "OPENAI_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"❌ Missing environment variables: {missing_vars}")
        sys.exit(1)
    
    # Check for Perplexity API key
    perplexity_key = os.getenv("PERPLEXITY_API_KEY")
    if perplexity_key:
        logger.info(f"✅ Perplexity API key found: {perplexity_key[:10]}...")
    else:
        logger.warning("⚠️ PERPLEXITY_API_KEY not found - research features will be limited")
    
    logger.info("🚀 Starting Aristotle (Logical Analyst) Agent...")
    
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="aristotle"  # Specific agent name for this worker
        )
    )

if __name__ == "__main__":
    main() 