import asyncio
import logging
import os
import json
from typing import Dict, List
from dotenv import load_dotenv
from livekit.agents import JobContext, WorkerOptions, cli, AgentSession, ChatContext
from livekit.agents.voice import Agent
from livekit.plugins import openai, silero
from livekit import rtc

# Load environment variables from .env file
load_dotenv()

# Configure logging - set to DEBUG for more verbose output
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Show environment variables (with partial redaction for secrets)
logger.debug(f"Environment variables:")
logger.debug(f"LIVEKIT_URL: {os.environ.get('LIVEKIT_URL', 'not set')}")
logger.debug(f"LIVEKIT_API_KEY: {os.environ.get('LIVEKIT_API_KEY', 'not set')}")
if os.environ.get('LIVEKIT_API_SECRET'):
    logger.debug(f"LIVEKIT_API_SECRET: {os.environ.get('LIVEKIT_API_SECRET', 'not set')[:5]}...")
else:
    logger.debug("LIVEKIT_API_SECRET: not set")
if os.environ.get('OPENAI_API_KEY'):
    logger.debug(f"OPENAI_API_KEY: {os.environ.get('OPENAI_API_KEY', 'not set')[:10]}...")
else:
    logger.debug("OPENAI_API_KEY: not set")

class DebateModeratorAgent(Agent):
    def __init__(self, chat_ctx: ChatContext):
        super().__init__(
            chat_ctx=chat_ctx,
            instructions=self.get_moderation_instructions()
        )
        self.debate_topic = os.environ.get("DEBATE_TOPIC", "general discussion")
        self.transcript = []
        logger.debug(f"DebateModeratorAgent initialized with topic: {self.debate_topic}")
        
    def get_moderation_instructions(self) -> str:
        return f"""
You are SAGE, an AI debate moderator helping users with a discussion about: {self.debate_topic}

Your primary responsibilities:
1. Ask clarifying questions when participants make assumptions
2. Enforce debate rules (no interruptions, personal attacks, etc.)
3. Monitor emotional tone and diffuse conflicts
4. Provide summaries and transitions during natural pauses
5. Request sources for factual claims

Current debate rules:
- No personal attacks
- Provide sources for factual claims  
- Respect speaking turns
- Stay on topic

Be helpful, neutral, and concise in your responses. Only interject when necessary.
"""

async def entrypoint(ctx: JobContext):
    logger.info("Starting SAGE debate moderation agent")
    logger.debug(f"JobContext: room_name={ctx.room_name}, identity={ctx.identity}")
    
    # Log connection details
    logger.debug(f"Connecting to room with URL: {os.environ.get('LIVEKIT_URL')}")
    logger.debug(f"Using API key: {os.environ.get('LIVEKIT_API_KEY')}")
    
    try:
        # Connect to the room
        logger.debug("Attempting to connect to LiveKit room...")
        await ctx.connect()
        logger.info(f"Connected to room: {ctx.room_name}")
    except Exception as e:
        logger.error(f"Failed to connect to room: {e}", exc_info=True)
        raise
    
    # Initial context for the agent
    initial_ctx = ChatContext()
    initial_ctx.add_message(
        role="system", 
        content="You are a debate moderation AI designed to help facilitate productive discussions."
    )
    
    # Try to load debate topic from environment or job metadata
    debate_topic = os.environ.get("DEBATE_TOPIC", "general discussion")
    logger.debug(f"Initial debate topic from env: {debate_topic}")
    
    try:
        if ctx.job and ctx.job.metadata:
            metadata = json.loads(ctx.job.metadata)
            if "debate_topic" in metadata:
                debate_topic = metadata["debate_topic"]
                logger.info(f"Loaded debate topic from metadata: {debate_topic}")
    except Exception as e:
        logger.error(f"Error loading metadata: {e}")
    
    # Add debate topic to context
    initial_ctx.add_message(
        role="assistant",
        content=f"The current debate topic is: {debate_topic}"
    )
    
    # Create the agent session
    logger.debug("Creating agent session with OpenAI and Silero plugins")
    try:
        session = AgentSession(
            stt=openai.STT(),
            llm=openai.LLM(
                model="gpt-4o-realtime-preview-2024-12-17",
                temperature=0.8,
            ),
            tts=openai.TTS(voice="alloy"),
            vad=silero.VAD.load(),
        )
        logger.debug("Agent session created successfully")
    except Exception as e:
        logger.error(f"Failed to create agent session: {e}", exc_info=True)
        raise
    
    # Create our debate agent
    debate_agent = DebateModeratorAgent(chat_ctx=initial_ctx)
    
    # Start the agent session
    logger.debug("Starting agent session...")
    try:
        await session.start(
            room=ctx.room,
            agent=debate_agent,
        )
        logger.debug("Agent session started successfully")
    except Exception as e:
        logger.error(f"Failed to start agent session: {e}", exc_info=True)
        raise
    
    # Initial greeting
    logger.debug("Generating initial greeting...")
    try:
        await session.generate_reply(
            instructions="Introduce yourself as a debate moderator AI. Explain briefly that you can help facilitate productive discussions by keeping track of talking points, requesting sources for factual claims, and ensuring fair participation. Keep it brief and welcoming."
        )
        logger.debug("Initial greeting generated successfully")
    except Exception as e:
        logger.error(f"Failed to generate initial greeting: {e}", exc_info=True)
    
    logger.info("SAGE debate moderation agent is ready")

if __name__ == "__main__":
    # Let the CLI handle environment variables automatically
    logger.info("Starting LiveKit debate moderation agent")
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
        )
    )
