#!/usr/bin/env python3

"""
Sage AI Debate Moderator Agent - Official LiveKit 1.0 Patterns
Follows exact patterns from https://docs.livekit.io/agents/quickstarts/voice-agent/
"""

import os
import json
import logging
from typing import Annotated
# Core LiveKit imports following official patterns
from livekit import agents
from livekit.agents import JobContext, RunContext, WorkerOptions, cli, function_tool
from livekit.plugins import deepgram, openai, silero, cartesia

# Environment variables are managed by Render directly - no need for dotenv
import os
import json
import logging
import httpx  # Added for Brave Search API calls

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Brave Search API configuration - API key managed by Render
BRAVE_API_URL = "https://api.search.brave.com/res/v1/web/search"
BRAVE_API_KEY = os.environ["BRAVE_API_KEY"]  # Render will inject this - no fallback

# Memory manager initialization
try:
    from supabase_memory_manager import SupabaseMemoryManager
    memory_manager = SupabaseMemoryManager()
    logger.info("✅ Supabase memory manager initialized successfully")
except ImportError:
    logger.warning("⚠️ Supabase memory manager not available - continuing without memory features")
    memory_manager = None
except Exception as e:
    logger.warning(f"⚠️ Memory manager initialization failed: {e}")
    memory_manager = None

# Global variables for agent state
current_persona = None
current_topic = None

def get_persona_instructions(persona: str, topic: str) -> str:
    """Generate persona-specific instructions based on the selected moderator"""
    
    base_instructions = f"""You are {persona}, a wise debate moderator for voice conversations.

CRITICAL: Start EVERY conversation with exactly this greeting:
"Hello, I'm {persona}. Today we'll be discussing {topic}. Go ahead with your opening arguments, and call upon me as needed."

Core principles:
- Keep responses SHORT (1-2 sentences max)
- Let participants lead - only intervene when needed
- Allow natural pauses in conversation"""

    persona_specific = {
        "Socrates": """
Socratic approach:
- Ask ONE thoughtful question, then let them think
- Sometimes just acknowledge: "That's worth reflecting on"
- Practice intellectual humility: "I'm not sure about that either"
- Don't question every response - balance with supportive comments""",

        "Aristotle": """
Aristotelian approach:
- Guide toward balanced, logical positions
- Point out logical fallacies briefly
- Encourage evidence-based reasoning
- Help find middle ground between extremes""",

        "Buddha": """
Buddhist approach:
- Focus on compassion and understanding
- Help find common ground between opposing views
- Encourage mindful listening
- Gently redirect away from personal attacks"""
    }

    return base_instructions + "\n" + persona_specific.get(persona, "")

# Function tools following official patterns
@function_tool()
async def moderate_discussion(ctx: RunContext, intervention_type: str, guidance: str) -> str:
    """
    Moderate the ongoing discussion with philosophical guidance.
    
    Args:
        intervention_type: Type of moderation needed (clarify, redirect, summarize, question)
        guidance: The specific guidance or question to offer
    """
    logger.info(f"🎭 {current_persona} moderating: {intervention_type}")
    
    # Store interaction in memory if available
    if memory_manager:
        try:
            await memory_manager.store_interaction(
                session_id=ctx.job.room.name,
                agent_name=current_persona,
                interaction_type="moderation",
                content=f"{intervention_type}: {guidance}",
                metadata={"topic": current_topic}
            )
        except Exception as e:
            logger.warning(f"Failed to store moderation in memory: {e}")
    
    return f"As {current_persona}, I offer this guidance: {guidance}"

@function_tool()
async def brave_search(ctx: RunContext, query: str) -> str:
    """
    Use the Brave Search API to get real-time search results for fact-checking.
    Returns the top 3 results as title + URL pairs for verification.
    
    Args:
        query: The search query to fact-check
    """
    if not BRAVE_API_KEY:
        logger.warning("⚠️ BRAVE_API_KEY not configured - fact-checking unavailable")
        return "Fact-checking is currently unavailable. Please verify information independently."
    
    # Headers following Brave Search API best practices from Context7 documentation
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": BRAVE_API_KEY,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    params = {
        "q": query,
        "count": 3,  # Get top 3 results for concise fact-checking
        "safesearch": "moderate",  # Filter inappropriate content
        "search_lang": "en",  # English language results
        "country": "US"  # US-focused results
    }

    try:
        logger.info(f"🔍 Brave Search fact-check query: {query}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(BRAVE_API_URL, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            web_results = data.get("web", {}).get("results", [])

            if not web_results:
                return f"No verification sources found for: {query}"

            # Format results for concise presentation
            formatted_results = []
            for result in web_results:
                title = result.get("title", "No title")
                url = result.get("url", "")
                # Truncate title if too long for voice
                if len(title) > 60:
                    title = title[:57] + "..."
                formatted_results.append(f"• {title}")
            
            result_text = "\n".join(formatted_results)
            
            # Store fact-check in memory if available
            if memory_manager:
                try:
                    await memory_manager.store_interaction(
                        session_id=ctx.job.room.name,
                        agent_name=current_persona,
                        interaction_type="fact_check",
                        content=f"Query: {query}\nResults: {result_text}",
                        metadata={"topic": current_topic, "source": "brave_search"}
                    )
                except Exception as e:
                    logger.warning(f"Failed to store fact-check in memory: {e}")
            
            logger.info(f"✅ Brave Search returned {len(web_results)} results")
            return f"Based on current sources:\n{result_text}"

    except httpx.TimeoutException:
        logger.error("⏰ Brave Search request timed out")
        return "Fact-checking timed out. Please verify information independently."
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ Brave Search HTTP error: {e.response.status_code}")
        return "Fact-checking service temporarily unavailable."
    except Exception as e:
        logger.error(f"❌ Brave Search error: {e}")
        return f"Fact-checking failed: {str(e)}"

@function_tool()
async def fact_check_statement(ctx: RunContext, statement: str) -> str:
    """
    Fact-check a specific statement made during the debate using Brave Search.
    
    Args:
        statement: The statement to fact-check
    """
    logger.info(f"🔍 Fact-checking statement: {statement}")
    
    # Create a focused search query from the statement
    # Remove common debate phrases and focus on factual claims
    search_query = statement.replace("I think", "").replace("I believe", "").replace("In my opinion", "").strip()
    
    # Use brave_search to get verification
    search_result = await brave_search(ctx, search_query)
    
    return f"Fact-checking '{statement[:50]}...': {search_result}"

@function_tool()
async def set_debate_topic(ctx: RunContext, topic: str) -> str:
    """
    Set or change the current debate topic.
    
    Args:
        topic: The new topic for discussion
    """
    global current_topic
    current_topic = topic
    logger.info(f"📝 Topic set to: {topic}")
    
    # Store topic change in memory if available
    if memory_manager:
        try:
            await memory_manager.store_interaction(
                session_id=ctx.job.room.name,
                agent_name=current_persona,
                interaction_type="topic_change",
                content=topic,
                metadata={"previous_topic": current_topic}
            )
        except Exception as e:
            logger.warning(f"Failed to store topic change in memory: {e}")
    
    return f"I'll guide our discussion on: {topic}"

# Main entrypoint following exact official pattern
async def entrypoint(ctx: JobContext):
    """Main agent entrypoint - follows official LiveKit pattern exactly"""
    try:
        logger.info("🚀 Sage AI Debate Moderator starting...")
        
        # Extract metadata from job context (official pattern)
        global current_persona, current_topic
        
        job_metadata = {}
        if hasattr(ctx.job, 'metadata') and ctx.job.metadata:
            try:
                if isinstance(ctx.job.metadata, str):
                    job_metadata = json.loads(ctx.job.metadata)
                else:
                    job_metadata = ctx.job.metadata
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Failed to parse job metadata: {e}")
        
        # Set persona and topic from metadata with defaults
        current_persona = job_metadata.get('persona', 'Socrates')
        current_topic = job_metadata.get('topic', 'Philosophy and Ethics')
        
        logger.info(f"🎭 Persona: {current_persona}")
        logger.info(f"📝 Topic: {current_topic}")
        
        # Create agent with persona-specific instructions and tools
        logger.info(f"🎭 Creating {current_persona} agent with topic: {current_topic}")
        
        # Configure Cartesia TTS (official implementation)
        logger.info("🎤 Configuring Cartesia TTS...")
        
        # Debug: Check if Cartesia API key is available
            cartesia_key = os.environ.get('CARTESIA_API_KEY')
    logger.info(f"🔑 CARTESIA_API_KEY: {'✅ Available' if cartesia_key else '❌ Missing'}")
        
        tts = cartesia.TTS(
            model="sonic-2-2025-03-07",  # Updated model that supports speed controls
            voice="a0e99841-438c-4a64-b679-ae501e7d6091",  # British Male (professional, deeper voice)
            speed=0.8, # Added speed parameter
        )
        logger.info("✅ Using Cartesia TTS with British male voice")
        logger.info(f"🎛️ TTS Configuration: model=sonic-2-2025-03-07, voice=a0e99841-438c-4a64-b679-ae501e7d6091, speed=0.8")
        
        # Create Agent with tools and instructions (supports function tools)
        agent = agents.Agent(
            instructions=get_persona_instructions(current_persona, current_topic),
            tools=[moderate_discussion, brave_search, fact_check_statement, set_debate_topic],
        )
        
        # Create AgentSession with Cartesia TTS (official pattern)
        session = agents.AgentSession(
            vad=silero.VAD.load(),
            stt=deepgram.STT(),
            llm=openai.LLM(model="gpt-4o-mini"),
            tts=tts,  # Use Cartesia TTS
        )
        
        logger.info("✅ Agent and AgentSession created successfully")
        
        # Start the session (official pattern)
        logger.info("▶️ Starting agent session...")
        await session.start(agent=agent, room=ctx.room)
        
        logger.info("🎉 Sage AI Debate Moderator Agent is now active and listening!")
        logger.info(f"🏠 Agent joined room: {ctx.room.name}")
        logger.info(f"👤 Agent participant identity: {current_persona}")  # Uses persona as identity
        
        # Send initial greeting (official pattern)
        initial_greeting = f"Hello, I'm {current_persona}. Today we'll be discussing {current_topic}. Go ahead with your opening arguments, and call upon me as needed."
        logger.info(f"🎤 Sending initial greeting: {initial_greeting}")
        await session.generate_reply(instructions=f"Say exactly: '{initial_greeting}'")
        
    except Exception as e:
        logger.error(f"❌ Error in entrypoint: {e}")
        raise

# Request handler - use persona name as identity (what frontend expects)
async def handle_job_request(job_req: agents.JobRequest):
    """Handle incoming job requests with persona-based identity"""
    try:
        # Extract persona from job metadata
        job_metadata = {}
        if hasattr(job_req.job, 'metadata') and job_req.job.metadata:
            try:
                if isinstance(job_req.job.metadata, str):
                    job_metadata = json.loads(job_req.job.metadata)
                else:
                    job_metadata = job_req.job.metadata
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Failed to parse job metadata: {e}")
        
        # Get persona from metadata, default to Socrates
        persona = job_metadata.get('persona', 'Socrates')
        
        logger.info(f"🎭 Job request received for room: {job_req.room.name}")
        logger.info(f"🎭 Setting agent identity to: {persona}")
        
        # ✅ FIXED: Use persona name as identity (LiveKit best practice)
        # Frontend expects agent identity to match persona name exactly
        await job_req.accept(
            identity=persona,                    # ✅ "Socrates", "Aristotle", "Buddha"
            name=f"Sage AI - {persona}",         # Display name with persona
        )
        
        logger.info(f"✅ Agent accepted job with identity: {persona}")
        
    except Exception as e:
        logger.error(f"❌ Error handling job request: {e}")
        await job_req.reject()

# CLI integration with agent registration for dispatch system
if __name__ == "__main__":
    logger.info("🚀 Starting Sage AI Debate Moderator Agent...")
    logger.info(f"🔑 Environment check:")
    logger.info(f"   LIVEKIT_URL: {'✅ Set' if os.getenv('LIVEKIT_URL') else '❌ Missing'}")
    logger.info(f"   LIVEKIT_API_KEY: {'✅ Set' if os.getenv('LIVEKIT_API_KEY') else '❌ Missing'}")
    logger.info(f"   LIVEKIT_API_SECRET: {'✅ Set' if os.getenv('LIVEKIT_API_SECRET') else '❌ Missing'}")
    logger.info(f"   OPENAI_API_KEY: {'✅ Set' if os.getenv('OPENAI_API_KEY') else '❌ Missing'}")
    logger.info(f"   DEEPGRAM_API_KEY: {'✅ Set' if os.getenv('DEEPGRAM_API_KEY') else '❌ Missing'}")
    logger.info(f"   BRAVE_API_KEY: {'✅ Set' if os.getenv('BRAVE_API_KEY') else '❌ Missing'}")
    
    cli.run_app(WorkerOptions(
        entrypoint_fnc=entrypoint,
        request_fnc=handle_job_request,  # Custom job request handler
        agent_name="sage-debate-moderator",  # Register with specific name for dispatch
        # Configure worker permissions according to official LiveKit API
    )) 