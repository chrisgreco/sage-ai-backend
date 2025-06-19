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
    from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, cli
    from livekit.plugins import openai, silero
    logger.info("✅ LiveKit Agents successfully imported")
except ImportError as e:
    logger.error(f"❌ LiveKit Agents import failed: {e}")
    sys.exit(1)

# Aristotle personality configuration
ARISTOTLE_CONFIG = {
    "name": "Aristotle",
    "voice": "fable",  # Warm, expressive male voice
    "instructions": """You are Aristotle. Give ONE brief logical fact. That's it.
    
    RULES:
    - Listen to ALL participants (humans and Socrates)
    - Only speak when addressed as "Aristotle" or when clear analysis needed
    - If someone says "Socrates" - stay silent
    - WAIT for complete silence before speaking - never interrupt
    - ONE factual statement maximum - be direct
    - Maximum 15 words per response"""
}

async def entrypoint(ctx: JobContext):
    """Aristotle agent entrypoint"""
    
    logger.info("📚 Aristotle joining the philosophical debate...")
    await ctx.connect()
    logger.info(f"✅ Aristotle connected to room: {ctx.room.name}")
    
    # Get debate topic
    topic = os.getenv("DEBATE_TOPIC", "The impact of AI on society")
    logger.info(f"🔬 Analyzing topic: {topic}")
    
    # Create agent session with coordinated turn-taking
    session = AgentSession(
        llm=openai.realtime.RealtimeModel(
            model="gpt-4o-realtime-preview-2024-12-17",
            voice=ARISTOTLE_CONFIG["voice"],
            temperature=0.6,
            speed=1.3  # 30% faster speech
        ),
        vad=silero.VAD.load(),
        min_endpointing_delay=1.2,    # Slightly longer than Socrates to avoid collision
        max_endpointing_delay=4.5,    # Different timing pattern
    )
    
    # Start session
    await session.start(
        agent=Agent(instructions=ARISTOTLE_CONFIG["instructions"]),
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
    
    logger.info("🚀 Starting Aristotle Agent...")
    
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name="aristotle"  # Specific agent name for this worker
        )
    )

if __name__ == "__main__":
    main() 