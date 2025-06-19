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
    "voice": "alloy",
    "instructions": """You are Aristotle, the systematic philosopher and scientist. Your role is to 
    provide factual analysis, logical reasoning, and evidence-based arguments. You excel at categorizing 
    ideas and finding practical solutions. Focus on empirical evidence, logical structure, and real-world 
    applications. Provide clear, well-reasoned responses.
    
    You are participating in a multi-agent philosophical debate. Listen to other participants and 
    respond with your characteristic analytical approach. Build upon others' ideas with logic and evidence."""
}

async def entrypoint(ctx: JobContext):
    """Aristotle agent entrypoint"""
    
    logger.info("📚 Aristotle joining the philosophical debate...")
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
    
    logger.info(f"🔬 Analyzing topic: {debate_topic}")
    
    # Create agent session
    session = AgentSession(
        llm=openai.realtime.RealtimeModel(
            model="gpt-4o-realtime-preview-2024-12-17",
            voice=ARISTOTLE_CONFIG["voice"],
            temperature=0.6
        ),
        vad=silero.VAD.load(),
        min_endpointing_delay=0.5,
        max_endpointing_delay=3.0,
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