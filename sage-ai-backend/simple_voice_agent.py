#!/usr/bin/env python3

"""
Simple LiveKit Voice Agent for Sage AI
======================================

This uses the much simpler OpenAI Realtime API approach that eliminates
the need for our complex audio bridge system. The Realtime API handles
all voice processing automatically.

Based on official LiveKit Agents documentation.
"""

import asyncio
import os
import logging
from dotenv import load_dotenv

# Core LiveKit Agents imports
from livekit.agents import (
    Agent,
    AgentSession, 
    JobContext,
    WorkerOptions,
    cli,
    function_tool,
)

# Simple imports - just OpenAI and Silero
from livekit.plugins import openai, silero

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Our AI debate personalities
class DebatePersonalities:
    SOCRATES = "You are Socrates, the ancient Greek philosopher. Ask probing questions to help users examine their beliefs and think more deeply. Use the Socratic method."
    
    ARISTOTLE = "You are Aristotle, the systematic philosopher. Provide logical analysis, categorize ideas, and offer practical wisdom based on empirical observation."
    
    BUDDHA = "You are Buddha, the enlightened teacher. Offer compassionate wisdom, help users find inner peace, and guide them toward mindful understanding."
    
    HERMES = "You are Hermes, the messenger god and synthesizer. Bridge different perspectives, summarize complex discussions, and facilitate communication between ideas."
    
    SOLON = "You are Solon, the wise lawgiver and moderator. Ensure fair discussion, maintain order, and guide conversations toward productive outcomes."

# Simple function tool for debate context
@function_tool
async def get_debate_context(
    context,
    topic: str,
):
    """Get context about the current debate topic."""
    return {
        "topic": topic,
        "participants": "Human participants and AI debate agents",
        "format": "Structured philosophical discussion",
        "goal": "Explore ideas deeply and reach better understanding"
    }

async def entrypoint(ctx: JobContext):
    """Main entry point for the voice agent."""
    await ctx.connect()
    
    # Get room metadata to determine which AI personality to use
    room_name = ctx.room.name or "demo"
    logger.info(f"🎭 Starting voice agent for room: {room_name}")
    
    # For demo, we'll use Socrates as the default
    # In production, you'd determine personality from room metadata
    personality = DebatePersonalities.SOCRATES
    
    # Create the agent with personality
    agent = Agent(
        instructions=personality,
        tools=[get_debate_context],
    )
    
    # Create session using OpenAI Realtime API - this handles everything!
    session = AgentSession(
        vad=silero.VAD.load(),  # Voice Activity Detection
        llm=openai.realtime.RealtimeModel(
            voice="alloy",  # OpenAI voice
            temperature=0.7,
            instructions=personality
        )
    )
    
    # Start the session - this connects to the room automatically
    await session.start(agent=agent, room=ctx.room)
    
    # Generate initial greeting
    await session.generate_reply(
        instructions=f"Greet the participants and introduce yourself. Ask what topic they'd like to explore in this philosophical discussion."
    )

if __name__ == "__main__":
    # Run with LiveKit CLI - supports 'dev', 'start', 'console' modes
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint)) 