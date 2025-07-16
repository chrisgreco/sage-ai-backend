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
from livekit.agents import (
    Agent,
    AgentSession, 
    JobContext,
    JobRequest,
    RunContext,
    WorkerOptions,
    cli,
    function_tool
)
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
BRAVE_API_KEY = os.environ.get("BRAVE_API_KEY")  # Render will inject this
if not BRAVE_API_KEY:
    logger.warning("⚠️ BRAVE_API_KEY not found - Brave Search functionality will be disabled")
    BRAVE_API_KEY = None

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

# Global state tracking
current_persona = None
current_topic = None
conversation_started = False  # Global conversation state

def get_persona_instructions(persona: str, topic: str) -> str:
    """Generate persona-specific instructions based on the selected moderator"""
    
    from datetime import datetime
    current_date = datetime.now().strftime("%B %d, %Y")
    
    # Check global conversation state
    global conversation_started
    
    # Conditional greeting based on conversation state
    greeting_instruction = ""
    if not conversation_started:
        greeting_instruction = f"""
CRITICAL: Start EVERY conversation with exactly this greeting:
"Hello, I'm {persona}. Today we'll be discussing {topic}. Go ahead with your opening arguments, and call upon me as needed."
"""
    else:
        greeting_instruction = """
IMPORTANT: The conversation has already started. Do NOT repeat the opening greeting. Continue the ongoing discussion naturally.
"""
    
    base_instructions = f"""You are {persona}, a wise debate moderator for voice conversations.

CURRENT CONTEXT: Today is {current_date}. You have access to real-time information through tools.

{greeting_instruction}

Core principles:
- Keep responses SHORT (1-2 sentences max)
- Let participants lead - only intervene when needed
- Allow natural pauses in conversation

IMPORTANT: When participants ask questions requiring real-time information, USE YOUR TOOLS:
- For any current events, facts, or real-time data - use brave_search immediately
- Share the information you find through your tools
- Don't refuse factual questions - that's what your tools are for!

Available tools:
- moderate_discussion: Provide philosophical guidance and redirect conversations
- brave_search: Search for real-time information and fact-check statements  
- set_debate_topic: Change the discussion topic when requested"""

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

# === Agent Class Definition ===
class DebateModerator(Agent):
    """Sage AI Debate Moderator Agent with persona-based behavior"""
    
    def __init__(self, persona: str, topic: str):
        self.persona = persona
        self.topic = topic
        
        # Get persona-specific instructions
        instructions = get_persona_instructions(persona, topic)
        
        super().__init__(
            instructions=instructions,
            tools=[moderate_discussion, brave_search, set_debate_topic],
        )
        
        logger.info(f"🎭 Created {persona} agent for topic: {topic}")
    
    async def say(self, message: str, allow_interruptions: bool = True):
        """Override say method to track conversation state"""
        # Mark conversation as started after any response
        global conversation_started
        if not conversation_started:
            conversation_started = True
            logger.info(f"🎬 {self.persona} conversation started globally - future agent instances will skip greeting")
        
        return await super().say(message, allow_interruptions)

# === Core Agent Functions ===
@function_tool()
async def moderate_discussion(ctx: RunContext, intervention_type: str, guidance: str) -> str:
    """
    Moderate the ongoing discussion with philosophical guidance.
    
    Args:
        intervention_type: Type of moderation needed (clarify, redirect, summarize, question)
        guidance: The specific guidance or question to offer
    """
    logger.info(f"🎭 {current_persona} moderating: {intervention_type}")
    
    # Store moderation action in memory if available
    if memory_manager:
        try:
            await memory_manager.store_moderation_action(
                action=intervention_type,
                content=guidance,
                persona=current_persona
            )
        except Exception as e:
            logger.warning(f"Failed to store moderation in memory: {e}")
    
    return f"As {current_persona}, I offer this guidance: {guidance}"

@function_tool()
async def brave_search(ctx: RunContext, query: str) -> str:
    """
    Search for real-time information and fact-check statements using Brave Search API.
    Can be used for weather, current events, or verifying claims made during debates.
    Returns the top 3 results as formatted sources for verification.
    
    Args:
        query: The search query or statement to fact-check (will be automatically cleaned)
    """
    if not BRAVE_API_KEY:
        logger.warning("⚠️ BRAVE_API_KEY not configured - search unavailable")
        return "Search is currently unavailable. Please verify information independently."
    
    # Clean up the query by removing opinion phrases and focusing on factual content
    cleaned_query = query.replace("I think", "").replace("I believe", "").replace("In my opinion", "").strip()
    
    # Enhance weather queries to get current conditions
    if "weather" in cleaned_query.lower():
        if "new york" in cleaned_query.lower() or "nyc" in cleaned_query.lower():
            cleaned_query = "current weather temperature New York City today"
        elif any(word in cleaned_query.lower() for word in ["temperature", "temp", "degrees"]):
            # Already has temperature terms
            cleaned_query = f"current {cleaned_query} today"
        else:
            cleaned_query = f"current weather {cleaned_query} today"
    
    search_query = cleaned_query if cleaned_query else query
    
    # Headers following Brave Search API best practices from Context7 documentation
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": BRAVE_API_KEY,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    params = {
        "q": search_query,
        "count": 3,  # Get top 3 results for concise fact-checking
        "safesearch": "moderate",  # Filter inappropriate content
        "search_lang": "en",  # English language results
        "country": "US"  # US-focused results
    }

    try:
        logger.info(f"🔍 Brave Search query: {search_query}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(BRAVE_API_URL, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            web_results = data.get("web", {}).get("results", [])

            # DEBUG: Log raw results to understand what we're getting
            logger.info(f"🔍 DEBUG: Brave Search returned {len(web_results)} results")
            for i, result in enumerate(web_results[:3]):
                title = result.get("title", "No title")
                url = result.get("url", "")
                description = result.get("description", "")
                logger.info(f"🔍 DEBUG Result {i+1}: {title}")
                logger.info(f"🔍 DEBUG URL {i+1}: {url}")
                logger.info(f"🔍 DEBUG Description {i+1}: {description[:100]}...")

            if not web_results:
                return f"No sources found for: {search_query}"

            # Format results for concise presentation, including descriptions for weather
            formatted_results = []
            for result in web_results:
                title = result.get("title", "No title")
                url = result.get("url", "")
                description = result.get("description", "")
                
                # For weather queries, include temperature from description if available
                temp_info = ""
                if "weather" in search_query.lower() and description:
                    # Extract temperature info from description
                    if "°" in description or "degrees" in description.lower():
                        # Find temperature mentions
                        import re
                        temp_matches = re.findall(r'\b\d+\s*°?[FfCc]?\b', description)
                        if temp_matches:
                            temp_info = f" - {temp_matches[0]}"
                
                # Truncate title if too long for voice
                if len(title) > 60:
                    title = title[:57] + "..."
                
                result_line = f"• {title}"
                if temp_info:
                    result_line += temp_info
                    
                formatted_results.append(result_line)
            
            result_text = "\n".join(formatted_results)
            
            # Store fact-check in memory if available
            if memory_manager:
                try:
                    await memory_manager.store_fact_check(
                        statement=search_query,
                        status=f"Verified with sources: {result_text}"
                    )
                except Exception as e:
                    logger.warning(f"Failed to store fact-check in memory: {e}")
            
            logger.info(f"✅ Brave Search returned {len(web_results)} results")
            return f"Based on current sources:\n{result_text}"

    except httpx.TimeoutException:
        logger.error("⏰ Brave Search request timed out")
        return "Search timed out. Please verify information independently."
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ Brave Search HTTP error: {e.response.status_code}")
        return "Search service temporarily unavailable."
    except Exception as e:
        logger.error(f"❌ Brave Search error: {e}")
        return f"Search failed: {str(e)}"

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
            await memory_manager.store_topic_change(
                topic=topic,
                persona=current_persona
            )
        except Exception as e:
            logger.warning(f"Failed to store topic change in memory: {e}")
    
    return f"Debate topic changed to: {topic}"

# Main entrypoint following exact official pattern
async def entrypoint(ctx: JobContext):
    """Main entrypoint for the Sage AI Debate Moderator Agent"""
    try:
        # Connect to the room
        await ctx.connect()
        logger.info(f"🔗 Connected to LiveKit room: {ctx.room.name}")
        
        # Get metadata from job context
        job_metadata = {}
        if hasattr(ctx.job, 'metadata') and ctx.job.metadata:
            try:
                if isinstance(ctx.job.metadata, str):
                    job_metadata = json.loads(ctx.job.metadata)
                else:
                    job_metadata = ctx.job.metadata
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Failed to parse job metadata: {e}")
        
        # Get persona and topic from metadata
        current_persona = job_metadata.get('persona', 'Socrates')
        current_topic = job_metadata.get('topic', 'philosophical discourse')
        
        logger.info(f"🎭 Initializing agent as: {current_persona}")
        logger.info(f"📝 Debate topic: {current_topic}")
        logger.info(f"🏠 Room: {ctx.room.name} (participants: {len(ctx.room.remote_participants)})")
        
        # Get the global memory manager (if available)
        global memory_manager
        
        # Configure the debate moderator agent
        agent = DebateModerator(persona=current_persona, topic=current_topic)
        
        # Debug: Check if Cartesia API key is available
        cartesia_key = os.environ.get('CARTESIA_API_KEY')
        logger.info(f"🔑 CARTESIA_API_KEY: {'✅ Available' if cartesia_key else '❌ Missing'}")
        
        tts = cartesia.TTS(
            model="sonic-2-2025-03-07",  # Updated model that supports speed controls
            voice="a0e99841-438c-4a64-b679-ae501e7d6091",  # British Male (professional, deeper voice)
            speed=0.8, # Added speed parameter
        )
        
        # Create the agent session with proper configuration
        session = AgentSession(
            vad=silero.VAD.load(),
            stt=deepgram.STT(model="nova-3"),
            llm=openai.LLM(model="gpt-4o-mini"),
            tts=tts,
        )
        
        # Start the persistent session
        await session.start(agent=agent, room=ctx.room)
        
        logger.info("🎉 Sage AI Debate Moderator Agent is now active and listening!")
        logger.info(f"🏠 Agent joined room: {ctx.room.name}")
        logger.info(f"👤 Agent participant identity: {current_persona}")
        
        # Send initial greeting ONLY once when agent first joins
        initial_greeting = f"Hello, I'm {current_persona}. Today we'll be discussing {current_topic}. Go ahead with your opening arguments, and call upon me as needed."
        logger.info(f"🎤 Sending initial greeting: {initial_greeting}")
        await session.say(initial_greeting)
        
    except Exception as e:
        logger.error(f"❌ Error in entrypoint: {e}")
        raise

# Request handler - use persona name as identity (what frontend expects)
async def handle_job_request(job_req: JobRequest):
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