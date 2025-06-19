#!/usr/bin/env python3
"""
Socrates Agent - Individual AI personality for philosophical debates
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

async def entrypoint(ctx: JobContext):
    """Socrates agent entrypoint"""
    
    logger.info("🧠 Socrates joining the philosophical debate...")
    await ctx.connect()
    logger.info(f"✅ Socrates connected to room: {ctx.room.name}")
    
    # Get debate topic from room metadata or job metadata
    debate_topic = "The impact of AI on society"  # Default topic
    
    # First check room metadata
    if ctx.room.metadata:
        try:
            import json
            room_metadata = json.loads(ctx.room.metadata)
            debate_topic = room_metadata.get("debate_topic", debate_topic)
            logger.info(f"🎯 Room topic from metadata: {debate_topic}")
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"⚠️ Could not parse room metadata: {e}")
    else:
        logger.info("📝 No room metadata available")
    
    # Check job metadata for agent-specific information (THIS IS WHERE THE TOPIC SHOULD COME FROM)
    if hasattr(ctx, 'job') and ctx.job and hasattr(ctx.job, 'metadata') and ctx.job.metadata:
        try:
            import json
            job_metadata = json.loads(ctx.job.metadata)
            role = job_metadata.get("role", "questioning_philosopher")
            agent_type = job_metadata.get("agent_type", "socrates")
            job_topic = job_metadata.get("debate_topic")
            
            logger.info(f"🎭 Job metadata found:")
            logger.info(f"   Role: {role}")
            logger.info(f"   Agent type: {agent_type}")
            logger.info(f"   Job topic: {job_topic}")
            
            if job_topic:
                debate_topic = job_topic
                logger.info(f"✅ Using topic from job metadata: {debate_topic}")
            else:
                logger.warning("⚠️ No debate_topic in job metadata!")
                
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"❌ Could not parse job metadata: {e}")
    else:
        logger.warning("⚠️ No job metadata available - this is the problem!")
        if hasattr(ctx, 'job'):
            if ctx.job:
                logger.info(f"   ctx.job exists: {type(ctx.job)}")
                if hasattr(ctx.job, 'metadata'):
                    logger.info(f"   ctx.job.metadata: {ctx.job.metadata}")
                else:
                    logger.info("   ctx.job has no metadata attribute")
            else:
                logger.info("   ctx.job is None")
        else:
            logger.info("   ctx has no job attribute")
    
    logger.info(f"🔬 FINAL TOPIC: {debate_topic}")
    
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