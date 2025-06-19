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
    "voice": "echo",
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
            role = job_metadata.get("role", "questioning_philosopher")
            agent_type = job_metadata.get("agent_type", "socrates")
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
            voice=SOCRATES_CONFIG["voice"],
            temperature=0.7,
            speed=1.3  # 30% faster speech
        ),
        vad=silero.VAD.load(),
        turn_detector=EnglishModel.load(),  # Semantic turn detection
        min_endpointing_delay=1.0,  # Socrates waits 1.0s minimum
        max_endpointing_delay=4.0,
    )
    
    # Start session
    await session.start(
        agent=Agent(instructions=SOCRATES_CONFIG["instructions"]),
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