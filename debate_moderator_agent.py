#!/usr/bin/env python3

"""
Sage AI Debate Moderator Agent - Enhanced LiveKit Implementation with Error Handling
Handles debate moderation with comprehensive error handling based on Context7 LiveKit patterns
Updated: Added robust error handling framework
"""

import os
import sys
import asyncio
import logging
import json
import time
import threading
import signal
import functools
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import Optional, Annotated

from livekit import rtc
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
    function_tool,
    RunContext,
)
from livekit.agents.utils import http_context
from livekit.plugins import openai, silero

# Load environment variables first
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# LiveKit Agents imports with error handling
try:
    from livekit.agents import JobContext, WorkerOptions, cli, AgentSession, Agent, function_tool
    from livekit.plugins import openai, silero
    logger.info("✅ LiveKit Agents successfully imported")
except ImportError as e:
    logger.error(f"❌ Failed to import LiveKit Agents: {e}")
    sys.exit(1)

# Custom Error Classes for structured error handling
class AgentError(Exception):
    """Base exception for agent errors"""
    def __init__(self, message: str, error_code: str = None, context: dict = None):
        super().__init__(message)
        self.error_code = error_code
        self.context = context or {}
        self.timestamp = time.time()

class OpenAIAgentError(AgentError):
    """OpenAI-specific agent errors"""
    pass

class SessionError(AgentError):
    """LiveKit session errors"""
    pass

class ConfigurationError(AgentError):
    """Configuration and environment errors"""
    pass

# Global Error Handler Decorator
def agent_error_handler(func):
    """Decorator for comprehensive agent error handling based on Context7 patterns"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            # Check if it's an OpenAI-related error
            if hasattr(e, 'status_code'):
                if e.status_code == 404:
                    logger.error(f"OpenAI 404 in {func.__name__}: {e}")
                    raise OpenAIAgentError(
                        f"OpenAI endpoint not found: {e}", 
                        "OPENAI_404", 
                        {"function": func.__name__, "url": getattr(e, 'url', 'unknown')}
                    )
                elif e.status_code == 429:
                    logger.warning(f"OpenAI rate limit in {func.__name__}")
                    await asyncio.sleep(2)  # Exponential backoff
                    raise OpenAIAgentError(f"Rate limit exceeded: {e}", "RATE_LIMIT")
                elif e.status_code == 401:
                    logger.error(f"OpenAI authentication error in {func.__name__}")
                    raise OpenAIAgentError(f"Invalid API key: {e}", "AUTH_ERROR")
            
            # Handle general HTTP errors
            if "HTTPStatusError" in str(type(e).__name__):
                logger.error(f"HTTP Status error in {func.__name__}: {e}")
                raise OpenAIAgentError(f"HTTP error: {e}", "HTTP_ERROR")
            
            # Handle session-related errors
            if "session" in str(e).lower() or "AgentSession" in str(type(e).__name__):
                logger.error(f"Session error in {func.__name__}: {e}")
                raise SessionError(f"Session error: {e}", "SESSION_ERROR")
            
            # General error handling
            logger.error(f"Unexpected error in {func.__name__}: {e}")
            raise AgentError(f"Agent error: {e}", "GENERAL_ERROR", {"function": func.__name__})
    return wrapper

# Check for Perplexity availability
PERPLEXITY_AVAILABLE = False
try:
    if os.getenv("PERPLEXITY_API_KEY"):
        PERPLEXITY_AVAILABLE = True
        logger.info("✅ Perplexity API available")
    else:
        logger.info("ℹ️ Perplexity API key not found - using OpenAI only")
except Exception:
    logger.info("ℹ️ Perplexity not available - using OpenAI only")

@dataclass
class ConversationState:
    """Shared state for coordinating between agents"""
    active_speaker: Optional[str] = None
    user_speaking: bool = False
    last_intervention_time: float = 0
    intervention_count: int = 0
    conversation_lock: threading.Lock = threading.Lock()

# Global conversation state
conversation_state = ConversationState()

class DebateModeratorAgent:
    """Simple debate moderator agent with enhanced error handling"""
    
    def __init__(self):
        self.name = "moderator"

    @agent_error_handler
    async def check_speaking_permission(self, session) -> bool:
        """Check if agent can speak"""
        with conversation_state.conversation_lock:
            if conversation_state.user_speaking:
                return False
            if conversation_state.active_speaker and conversation_state.active_speaker != self.name:
                return False
            return True

    @agent_error_handler
    async def claim_speaking_turn(self):
        """Claim speaking turn"""
        with conversation_state.conversation_lock:
            conversation_state.active_speaker = self.name

    @agent_error_handler
    async def release_speaking_turn(self):
        """Release speaking turn"""
        with conversation_state.conversation_lock:
            conversation_state.active_speaker = None

@function_tool
@agent_error_handler
async def get_debate_topic():
    """Get the current debate topic"""
    try:
        topic = os.environ.get("DEBATE_TOPIC", "The impact of AI on society")
        logger.info(f"📋 Current debate topic: {topic}")
        return f"The current debate topic is: {topic}"
    except Exception as e:
        logger.error(f"Error getting debate topic: {e}")
        return "Unable to retrieve the current debate topic. Please try again."

@function_tool
@agent_error_handler
async def access_facilitation_knowledge(query: str):
    """Access debate facilitation knowledge"""
    try:
        logger.info(f"🧠 Accessing facilitation knowledge for: {query}")
        
        # Simple knowledge responses
        knowledge_responses = {
            "logical fallacy": "Common logical fallacies include ad hominem, straw man, false dichotomy, and appeal to authority. When you notice these, gently redirect the conversation to address the actual argument.",
            "debate structure": "A good debate follows: opening statements, main arguments with evidence, rebuttals, and closing summaries. Ensure each participant has equal time.",
            "moderation": "As a moderator, remain neutral, ensure fair participation, fact-check claims, and guide the conversation toward productive discourse.",
            "evidence": "Strong arguments require credible evidence. Ask for sources, verify claims, and distinguish between opinion and fact."
        }
        
        for key, response in knowledge_responses.items():
            if key in query.lower():
                return response
        
        return "I can help with debate structure, logical fallacies, moderation techniques, and evidence evaluation. What specific aspect would you like guidance on?"
    except Exception as e:
        logger.error(f"Error accessing facilitation knowledge: {e}")
        return "I'm temporarily unable to access that knowledge. Please rephrase your question."

@function_tool
@agent_error_handler
async def suggest_process_intervention(situation: str):
    """Suggest process interventions for debate management"""
    try:
        logger.info(f"🔧 Suggesting intervention for: {situation}")
        
        interventions = {
            "interruption": "Let's ensure everyone has a chance to complete their thoughts. Please hold questions until the speaker finishes.",
            "off-topic": "This is an interesting point, but let's return to our main topic. How does this relate to our current discussion?",
            "personal attack": "Let's focus on the ideas and arguments rather than personal characteristics. Can you rephrase that to address the position itself?",
            "repetition": "I notice we're revisiting this point. Let's either explore a new angle or move to the next aspect of the debate.",
            "dominance": "Thank you for your passion. Let's hear from others who haven't had a chance to contribute recently.",
            "confusion": "Let me help clarify the current state of our discussion and the key points raised so far."
        }
        
        for key, intervention in interventions.items():
            if key in situation.lower():
                return intervention
        
        return "Consider: pausing for clarification, summarizing key points, ensuring balanced participation, or refocusing on the topic."
    except Exception as e:
        logger.error(f"Error suggesting intervention: {e}")
        return "Let me help guide this discussion back to a productive path."

@function_tool
@agent_error_handler
async def fact_check_claim(claim: str, source_requested: bool = False):
    """Fact-check a claim made during the debate"""
    try:
        logger.info(f"🔍 Fact-checking claim: {claim}")
        
        # Simple fact-checking responses
        if source_requested:
            return f"I'd like to verify this claim: '{claim}'. Could you provide a source for this information so we can evaluate its credibility?"
        
        return f"This claim requires verification: '{claim}'. Let's examine the evidence supporting this statement. What sources inform this position?"
    except Exception as e:
        logger.error(f"Error fact-checking claim: {e}")
        return "Let's examine the evidence for this claim. What sources support this position?"

@function_tool
@agent_error_handler
async def end_debate():
    """End the current debate session"""
    try:
        logger.info("🏁 Ending debate session")
        return "Thank you all for this engaging discussion. Let me provide a brief summary of the key points raised and conclude our session."
    except Exception as e:
        logger.error(f"Error ending debate: {e}")
        return "Thank you for this discussion. This concludes our debate session."

@function_tool
@agent_error_handler
async def summarize_discussion():
    """Summarize the key points of the discussion"""
    try:
        logger.info("📝 Summarizing discussion")
        return "Let me summarize the main arguments and perspectives we've heard so far in this debate."
    except Exception as e:
        logger.error(f"Error summarizing discussion: {e}")
        return "Let me provide a summary of the key points discussed."

def get_persona_instructions(persona: str) -> str:
    """Get persona-specific instructions for the agent."""
    persona_lower = persona.lower()
    
    if persona_lower == "socrates":
        return """You are Socrates, the ancient Greek philosopher, moderating a debate.

Your approach:
- Ask probing questions to help participants examine their assumptions
- Use the Socratic method - guide people to discover truth through questioning
- Say "I know that I know nothing" - maintain intellectual humility
- Help participants clarify their thinking through gentle inquiry
- When someone makes a claim, ask: "How do you know this?" or "What do you mean by...?"

Keep responses concise and focused on asking the right questions."""
        
    elif persona_lower == "buddha":
        return """You are Buddha, the enlightened teacher, moderating a discussion.

Your approach:
- Promote compassion, understanding, and mindful dialogue
- Help de-escalate conflicts with wisdom and patience
- Guide participants toward deeper understanding and empathy
- When tensions arise, redirect to common ground and shared humanity
- Speak with gentle authority and profound insight

Keep responses calm, wise, and focused on harmony."""
        
    else:  # Aristotle (default)
        return """You are Aristotle, the systematic philosopher, moderating a debate.

Your approach:
- Ensure logical reasoning and evidence-based arguments
- Ask for sources and factual support when claims are made
- Help structure the debate with clear premises and conclusions
- Point out logical fallacies when they occur
- Guide toward rational, well-reasoned discourse

Keep responses logical, structured, and focused on evidence."""

def get_persona_greeting(persona: str) -> str:
    """Get persona-specific greeting for the agent."""
    persona_lower = persona.lower()
    
    if persona_lower == "socrates":
        return "Greet the participants as Socrates. Welcome them to the discussion and ask them what they hope to discover through dialogue today."
        
    elif persona_lower == "buddha":
        return "Greet the participants as Buddha. Welcome them with compassion and invite them to share their thoughts mindfully."
        
    else:  # Aristotle (default)
        return "Greet the participants as Aristotle. Welcome them to the debate and ask them to present their arguments with logic and evidence."

@agent_error_handler
async def entrypoint(ctx: JobContext):
    """Enhanced main entry point for the LiveKit agent with comprehensive error handling"""
    session = None
    try:
        logger.info("🚀 Starting Sage AI Debate Moderator Agent with Enhanced Error Handling")
        
        # Validate environment first - Check for Perplexity API key
        perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
        if not perplexity_api_key:
            raise ConfigurationError("PERPLEXITY_API_KEY environment variable is required", "MISSING_PERPLEXITY_KEY")
        logger.info("✅ Perplexity API key validated")
        
        # Fallback to OpenAI if needed (for STT/TTS)
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            logger.warning("⚠️ OpenAI API key not found - using Perplexity for all operations")
            # Use Perplexity for everything if no OpenAI key
            openai_api_key = None
        
        # Connect to the room
        await ctx.connect()
        logger.info("Connected to room %s", ctx.room.name)
        
        # Get persona from room metadata with enhanced error handling
        persona = "socrates"  # default
        try:
            if ctx.room.metadata:
                metadata_dict = json.loads(ctx.room.metadata)
                persona = metadata_dict.get("persona", "socrates")
            logger.info("Using persona: %s", persona)
        except (json.JSONDecodeError, AttributeError, TypeError) as e:
            logger.warning(f"Could not parse room metadata, using default persona 'socrates': {e}")
            
        # Create enhanced session with Perplexity integration using newest model
        from backend_modules.livekit_enhanced import EnhancedAgentSession
        
        # Create enhanced session for Perplexity API calls with proper lifecycle management
        session_id = f"debate_{ctx.room.name}_{int(time.time())}"
        
        # Use the enhanced session context manager for proper cleanup
        from backend_modules.livekit_enhanced import get_enhanced_session
        
        async with get_enhanced_session(session_id) as enhanced_session:
            # Create a custom LLM wrapper that uses Perplexity API with safe logging and proper session management
            class PerplexityLLMWrapper:
                def __init__(self, enhanced_session, model="sonar-deep-research"):
                    self.enhanced_session = enhanced_session
                    self.model = model
                    self._session = None
                    
                async def __aenter__(self):
                    """Async context manager entry"""
                    return self
                    
                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    """Async context manager exit with proper cleanup"""
                    await self.aclose()
                    
                async def aclose(self):
                    """Properly close any resources"""
                    if self._session and not self._session.closed:
                        await self._session.close()
                        self._session = None
                    
                async def agenerate(self, messages, **kwargs):
                    """Generate response using Perplexity API with newest model and safe logging"""
                    try:
                        # Safe logging of input messages (avoid logging large content)
                        message_info = {
                            "message_count": len(messages),
                            "model": self.model,
                            "total_input_length": sum(len(str(msg.get("content", ""))) for msg in messages)
                        }
                        logger.debug(f"🤖 Generating response with Perplexity: {safe_binary_repr(message_info)}")
                        
                        # Convert messages to Perplexity format
                        perplexity_payload = {
                            "model": self.model,  # Use newest Sonar Deep Research model
                            "messages": [{"role": msg.get("role", "user"), "content": msg.get("content", "")} for msg in messages],
                            "temperature": kwargs.get("temperature", 0.7),
                            "max_tokens": kwargs.get("max_tokens", 1000)
                        }
                        
                        response = await self.enhanced_session.call_perplexity_api(perplexity_payload)
                        
                        # Extract content from response with safe logging
                        if response and "choices" in response and len(response["choices"]) > 0:
                            content = response["choices"][0].get("message", {}).get("content", "")
                            logger.debug(f"✅ Perplexity response generated: {len(content)} chars")
                            return content
                        else:
                            logger.warning("Invalid Perplexity API response format")
                            return "I apologize, but I'm having trouble processing that request right now."
                            
                    except Exception as e:
                        logger.error(f"Perplexity API call failed: {safe_binary_repr(str(e))}")
                        return "I apologize, but I'm experiencing technical difficulties. Please try again."
            
            # Create the custom Perplexity LLM
            perplexity_llm = PerplexityLLMWrapper(enhanced_session, "sonar-deep-research")
            
            # Create agent with persona-specific instructions and tools
            agent = Agent(
                instructions=get_persona_instructions(persona),
                tools=[
                    get_debate_topic,
                    access_facilitation_knowledge,
                    suggest_process_intervention,
                    fact_check_claim,
                    end_debate,
                    summarize_discussion,
                ],
            )
            
            # Create standard LiveKit session with our custom LLM
            session = AgentSession(
                vad=silero.VAD.load(),
                stt=openai.STT() if openai_api_key else None,
                llm=perplexity_llm,  # Use our custom Perplexity wrapper
                tts=openai.TTS(voice="echo") if openai_api_key else None,
            )
            
            # Start the session with error handling
            try:
                await session.start(agent=agent, room=ctx.room)
                logger.info("✅ Agent session started successfully")
            except Exception as e:
                logger.error(f"Failed to start agent session: {e}")
                raise SessionError(f"Session start failed: {e}", "SESSION_START_ERROR")
            
            # Generate initial greeting with error handling
            try:
                greeting = get_persona_greeting(persona)
                await session.generate_reply(instructions=greeting)
                logger.info("✅ Initial greeting generated successfully")
            except Exception as e:
                logger.warning(f"Failed to generate initial greeting: {e}")
                # Continue without greeting rather than failing
            
            # Get topic for logging
            topic = os.environ.get("DEBATE_TOPIC", "The impact of AI on society")
            logger.info(f"✅ {persona} agent started successfully for topic: {topic}")
            
            # Session will run until the room is disconnected
            # No need to wait for completion - session.start() handles the lifecycle
        
    except ConfigurationError as e:
        logger.error(f"❌ Configuration error: {e}")
        raise
    except SessionError as e:
        logger.error(f"❌ Session error: {e}")
        raise
    except OpenAIAgentError as e:
        logger.error(f"❌ OpenAI error: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error starting agent: {e}")
        raise AgentError(f"Agent startup failed: {e}", "STARTUP_ERROR")
    finally:
        # Ensure proper cleanup of session resources
        if session:
            try:
                await session.aclose()
                logger.info("🧹 Session cleanup completed")
            except Exception as cleanup_error:
                logger.warning(f"⚠️ Session cleanup warning: {cleanup_error}")

def main():
    """Main entry point for the debate moderator agent"""
    cli.run_app(
        WorkerOptions(
            agent_name="moderator",
            entrypoint_fnc=entrypoint,
        )
    )

# Binary data logging safeguards
def safe_binary_repr(data) -> str:
    """Return a safe representation of potentially binary data for logging."""
    if isinstance(data, (bytes, bytearray)):
        return f"<binary data: {len(data)} bytes>"
    elif isinstance(data, str) and len(data) > 1000:
        # Truncate very long strings that might be binary data encoded as strings
        return f"<large string: {len(data)} chars, preview: {data[:100]}...>"
    elif isinstance(data, dict):
        # Handle large JSON responses
        if len(str(data)) > 2000:
            return f"<large dict: {len(data)} keys, {len(str(data))} chars>"
        return data
    return data

def setup_logging_filters():
    """Setup logging filters to prevent binary data and large HTTP responses from being logged."""
    
    class BinaryDataFilter(logging.Filter):
        """Filter to prevent binary data and large HTTP responses from being logged."""
        
        def filter(self, record):
            # Convert the log message to string safely
            try:
                msg = str(record.getMessage())
                
                # Filter out very long messages that might contain binary data
                if len(msg) > 5000:
                    record.msg = f"<filtered large log message: {len(msg)} chars>"
                    record.args = ()
                    return True
                
                # Filter out potential binary data patterns
                if any(pattern in msg.lower() for pattern in [
                    'x00', 'x01', 'x02', 'x03', 'x04', 'x05',  # Common binary patterns
                    'riff', 'wav', 'mp3', 'ogg',  # Audio format headers
                    'content-encoding', 'gzip', 'deflate',  # Compressed content
                    'multipart/form-data'  # Form data that might contain binary
                ]):
                    record.msg = f"<filtered binary/media content: {len(msg)} chars>"
                    record.args = ()
                    return True
                    
                return True
                
            except Exception:
                # If we can't process the message, allow it through
                return True
    
    # Apply filter to all relevant loggers
    binary_filter = BinaryDataFilter()
    
    # Add filter to root logger
    logging.getLogger().addFilter(binary_filter)
    
    # Add filter to common HTTP libraries that might log large responses
    for logger_name in [
        'aiohttp',
        'aiohttp.client',
        'aiohttp.access',
        'httpx',
        'urllib3',
        'openai',
        'livekit'
    ]:
        try:
            logger = logging.getLogger(logger_name)
            logger.addFilter(binary_filter)
            # Also set level to INFO to reduce debug output
            logger.setLevel(logging.INFO)
        except Exception:
            pass  # Logger might not exist

# Configure logging with binary data protection
setup_logging_filters()

if __name__ == "__main__":
    main() 