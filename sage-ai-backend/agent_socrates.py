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
    logger.info("✅ LiveKit Agents successfully imported")
except ImportError as e:
    logger.error(f"❌ LiveKit Agents import failed: {e}")
    sys.exit(1)

# Socrates personality configuration
SOCRATES_CONFIG = {
    "name": "Socrates",
    "voice": "onyx",  # Deep, serious voice
    "instructions": """You are Socrates. Ask ONE brief question to challenge assumptions. That's it.
    
    RULES:
    - Listen to ALL participants (humans and Aristotle)
    - Only speak when addressed as "Socrates" or when appropriate
    - If someone says "Aristotle" - stay silent
    - WAIT for silence before speaking - never interrupt
    - ONE question maximum - be direct
    - Maximum 10 words per response"""
}

async def entrypoint(ctx: JobContext):
    """Socrates agent entrypoint"""
    
    logger.info("🧠 Socrates joining the philosophical debate...")
    await ctx.connect()
    logger.info(f"✅ Socrates connected to room: {ctx.room.name}")
    
    # Get debate topic
    topic = os.getenv("DEBATE_TOPIC", "The impact of AI on society")
    logger.info(f"💭 Debate topic: {topic}")
    
    # Create agent session with better turn-taking
    session = AgentSession(
        llm=openai.realtime.RealtimeModel(
            model="gpt-4o-realtime-preview-2024-12-17",
            voice=SOCRATES_CONFIG["voice"],
            temperature=0.8,
            speed=1.3  # 30% faster speech
        ),
        vad=silero.VAD.load(),
        min_endpointing_delay=1.0,    # Longer delay to prevent interruption  
        max_endpointing_delay=5.0,    # Increased max delay for better turn-taking
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