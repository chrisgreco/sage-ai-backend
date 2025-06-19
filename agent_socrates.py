#!/usr/bin/env python3
"""
Socrates Agent - Individual AI personality for philosophical debates
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

# Socrates personality configuration - ULTRA CONCISE
SOCRATES_CONFIG = {
    "name": "Socrates",
    "voice": "onyx",  # Deep, serious voice
    "instructions": """You are Socrates. Ask 1 question (max 10 words).

CRITICAL RULES:
- WAIT for complete silence before speaking
- If someone says "Aristotle" - stay silent
- 10 words maximum per response
- Only ask ONE question per turn
- Listen first, question second"""
}

def get_debate_topic_from_context(ctx: JobContext) -> str:
    """Extract debate topic from job context with comprehensive fallback"""
    
    default_topic = "The impact of AI on society"
    
    logger.info("🔍 Socrates checking for debate topic...")
    
    # Method 1: Check job metadata (primary method for agent dispatch)
    try:
        if hasattr(ctx, 'job') and ctx.job and hasattr(ctx.job, 'metadata') and ctx.job.metadata:
            logger.info(f"📋 Found job metadata: {ctx.job.metadata}")
            job_metadata = json.loads(ctx.job.metadata)
            topic = job_metadata.get("debate_topic")
            if topic:
                logger.info(f"✅ Socrates found topic from job metadata: {topic}")
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
                logger.info(f"✅ Socrates found topic from room metadata: {topic}")
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
                logger.info(f"✅ Socrates extracted topic from room name: {topic}")
                return topic
    except Exception as e:
        logger.error(f"❌ Failed to extract topic from room name: {e}")
    
    logger.warning(f"⚠️ Socrates falling back to default topic: {default_topic}")
    return default_topic

async def entrypoint(ctx: JobContext):
    """Socrates agent entrypoint"""
    
    logger.info("🧠 Socrates joining the philosophical debate...")
    await ctx.connect()
    logger.info(f"✅ Socrates connected to room: {ctx.room.name}")
    
    # Get debate topic using comprehensive method
    debate_topic = get_debate_topic_from_context(ctx)
    logger.info(f"🎯 SOCRATES FINAL TOPIC: {debate_topic}")
    
    # Create agent session with ADVANCED turn detection
    session = AgentSession(
        llm=openai.realtime.RealtimeModel(
            model="gpt-4o-realtime-preview-2024-12-17",
            voice=SOCRATES_CONFIG["voice"],
            temperature=0.7,
            speed=1.3  # 30% faster speech
        ),
        vad=silero.VAD.load(),
        turn_detector=EnglishModel.load(),  # Semantic turn detection
        min_endpointing_delay=1.0,  # Socrates waits 1.0s minimum
        max_endpointing_delay=4.0,
    )
    
    # Start session with dynamic instructions
    # Create dynamic instructions that include the actual debate topic
    dynamic_instructions = f"""{SOCRATES_CONFIG["instructions"]}

DEBATE TOPIC: "{debate_topic}"
Ask questions specifically about this topic."""
    
    await session.start(
        agent=Agent(instructions=dynamic_instructions),
        room=ctx.room
    )
    
    logger.info("✅ Socrates is ready for philosophical inquiry!")

def main():
    """Main function"""
    required_vars = ["LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "LIVEKIT_URL", "OPENAI_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"❌ Missing environment variables: {missing_vars}")
        sys.exit(1)
    
    logger.info("🚀 Starting Socrates (Inquisitive Challenger) Agent...")
    
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="socrates"  # Specific agent name for this worker
        )
    )

if __name__ == "__main__":
    main() 