import os
import logging
from dotenv import load_dotenv
from livekit.agents import WorkerOptions, cli, JobContext, Agent, AgentSession, ChatContext
from livekit.plugins import openai, silero

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables from .env file (if available)
load_dotenv()

# Set default environment variables if not already set
if not os.environ.get('LIVEKIT_URL'):
    os.environ['LIVEKIT_URL'] = 'wss://sage-2kpu4z1y.livekit.cloud'
if not os.environ.get('LIVEKIT_API_KEY'):
    os.environ['LIVEKIT_API_KEY'] = 'APIWQtUQUijqXVp'
if not os.environ.get('LIVEKIT_API_SECRET'):
    os.environ['LIVEKIT_API_SECRET'] = 'LDs7r35vqLLwR5vBPFg99hlPqE5y2EZ4sq7M90fAfEI'

# Get debate topic
debate_topic = os.environ.get("DEBATE_TOPIC", "The impact of artificial intelligence on society")

# The main entrypoint function that will be called for each job request
async def entrypoint(ctx: JobContext):
    try:
        # Get the room name if possible
        room_name = "unknown"
        if hasattr(ctx, 'job') and hasattr(ctx.job, 'room_name'):
            room_name = ctx.job.room_name
            
        logger.info(f"Starting debate moderator agent for room: {room_name}")
        logger.info(f"Using debate topic: {debate_topic}")
        
        # Connect to the room
        logger.info("Connecting to room...")
        await ctx.connect()
        
        # Now we can access ctx.room after connection
        logger.info(f"Connected to room: {ctx.room}")
        
        # Create initial chat context
        chat_ctx = ChatContext()
        chat_ctx.add_message(
            role="system", 
            content=f"You are SAGE, an AI debate moderator helping users with a discussion about: {debate_topic}. "
                    f"Your primary responsibilities include asking clarifying questions, enforcing debate rules, "
                    f"monitoring emotional tone, providing summaries, and requesting sources for factual claims."
        )
        
        # Create the agent
        debate_agent = Agent(
            chat_ctx=chat_ctx,
            instructions=f"""
You are SAGE, an AI debate moderator helping users with a discussion about: {debate_topic}

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
        )
        
        # Create the agent session
        logger.info("Creating agent session...")
        session = AgentSession(
            vad=silero.VAD.load(),
            stt=openai.STT(),
            llm=openai.LLM(
                model="gpt-4o-mini",
                temperature=0.8,
            ),
            tts=openai.TTS(voice="alloy"),
        )
        
        # Start the agent session
        logger.info("Starting agent session...")
        await session.start(
            room=ctx.room,
            agent=debate_agent,
        )
        
        # Initial greeting
        logger.info("Generating initial greeting...")
        await session.generate_reply(
            instructions="Introduce yourself as a debate moderator AI. Explain briefly that you can help facilitate productive discussions by keeping track of talking points, requesting sources for factual claims, and ensuring fair participation. Keep it brief and welcoming."
        )
        
        logger.info("SAGE debate moderation agent is active and ready")
        
        # Keep agent running until the job is done
        # The agent framework will automatically handle when to end the session
        await ctx.wait_until_done()
    except Exception as e:
        logger.error(f"Error in agent session: {e}", exc_info=True)
    finally:
        logger.info("Agent job completed")

# Entry point for the script
if __name__ == "__main__":
    # Display configuration info
    logger.info(f"Configuration:")
    logger.info(f"  LIVEKIT_URL: {os.environ.get('LIVEKIT_URL')}")
    logger.info(f"  LIVEKIT_API_KEY: {os.environ.get('LIVEKIT_API_KEY')}")
    if os.environ.get('LIVEKIT_API_SECRET'):
        logger.info(f"  LIVEKIT_API_SECRET: {os.environ.get('LIVEKIT_API_SECRET')[:5]}...")
    else:
        logger.info("  LIVEKIT_API_SECRET: not set")
    if os.environ.get('OPENAI_API_KEY'):
        logger.info(f"  OPENAI_API_KEY: {os.environ.get('OPENAI_API_KEY')[:5]}...")
    else:
        logger.info("  OPENAI_API_KEY: not set")
    logger.info(f"  Debate Topic: {debate_topic}")
    
    logger.info("Starting LiveKit debate moderation worker")
    
    # Configure worker options - keep it simple with just the entrypoint
    worker_options = WorkerOptions(
        entrypoint_fnc=entrypoint,
    )
    
    # Let the CLI handle the arguments and running the worker
    cli.run_app(worker_options) 