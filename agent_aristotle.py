#!/usr/bin/env python3
"""
Aristotle Agent - Individual AI personality for philosophical debates
"""

import os
import sys
import asyncio
import logging
import json
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
    from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, cli
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

# Aristotle personality configuration - ULTRA CONCISE
ARISTOTLE_CONFIG = {
    "name": "Aristotle",
    "voice": "fable",  # Warm, expressive voice
    "instructions": """You are Aristotle. Make 1 logical point (max 15 words).

CRITICAL RULES:
- WAIT for complete silence before speaking
- If someone says "Socrates" - stay silent
- 15 words maximum per response
- Only make ONE logical point per turn
- Think first, then respond with logic"""
}

def get_debate_topic_from_context(ctx: JobContext) -> str:
    """Extract debate topic from job context with comprehensive fallback"""
    
    default_topic = "The impact of AI on society"
    
    logger.info("🔍 Aristotle checking for debate topic...")
    
    # Method 1: Check job metadata (primary method for agent dispatch)
    try:
        if hasattr(ctx, 'job') and ctx.job and hasattr(ctx.job, 'metadata') and ctx.job.metadata:
            logger.info(f"📋 Found job metadata: {ctx.job.metadata}")
            job_metadata = json.loads(ctx.job.metadata)
            topic = job_metadata.get("debate_topic")
            if topic:
                logger.info(f"✅ Aristotle found topic from job metadata: {topic}")
                return topic
            else:
                logger.warning("⚠️ No 'debate_topic' key in job metadata")
        else:
            logger.info("📭 No job metadata available")
    except (json.JSONDecodeError, Exception) as e:
        logger.error(f"❌ Failed to parse job metadata: {e}")
    
    # Method 2: Check room metadata (fallback)
    try:
        if ctx.room and ctx.room.metadata:
            logger.info(f"🏠 Found room metadata: {ctx.room.metadata}")
            room_metadata = json.loads(ctx.room.metadata)
            topic = room_metadata.get("debate_topic")
            if topic:
                logger.info(f"✅ Aristotle found topic from room metadata: {topic}")
                return topic
            else:
                logger.warning("⚠️ No 'debate_topic' key in room metadata")
        else:
            logger.info("🏠 No room metadata available")
    except (json.JSONDecodeError, Exception) as e:
        logger.error(f"❌ Failed to parse room metadata: {e}")
    
    # Method 3: Check room name for topic hints (additional fallback)
    try:
        if ctx.room and ctx.room.name:
            room_name = ctx.room.name
            logger.info(f"🏷️ Room name: {room_name}")
            
            # Extract topic from room name if it follows pattern like "debate-topic-name"
            if room_name.startswith("debate-") and len(room_name.split("-")) > 1:
                # Convert room name back to topic
                topic_parts = room_name.replace("debate-", "").split("-")
                topic = " ".join(word.capitalize() for word in topic_parts)
                logger.info(f"✅ Aristotle extracted topic from room name: {topic}")
                return topic
    except Exception as e:
        logger.error(f"❌ Failed to extract topic from room name: {e}")
    
    logger.warning(f"⚠️ Aristotle falling back to default topic: {default_topic}")
    return default_topic

async def entrypoint(ctx: JobContext):
    """Aristotle agent entrypoint"""
    
    logger.info("🏛️ Aristotle joining the philosophical debate...")
    await ctx.connect()
    logger.info(f"✅ Aristotle connected to room: {ctx.room.name}")
    
    # Get debate topic using comprehensive method
    debate_topic = get_debate_topic_from_context(ctx)
    logger.info(f"🎯 ARISTOTLE FINAL TOPIC: {debate_topic}")
    
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
        min_endpointing_delay=1.2,  # Aristotle waits 1.2s minimum (different from Socrates)
        max_endpointing_delay=4.0,
    )
    
    # Start session with dynamic instructions
    # Create dynamic instructions that include the actual debate topic
    dynamic_instructions = f"""{ARISTOTLE_CONFIG["instructions"]}

DEBATE TOPIC: "{debate_topic}"
Make logical points specifically about this topic."""
    
    await session.start(
        agent=Agent(instructions=dynamic_instructions),
        room=ctx.room
    )
    
    logger.info("✅ Aristotle is ready for logical analysis!")

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