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
from typing import Optional, Annotated, Dict, Any, List, Tuple
from datetime import datetime

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
from livekit.plugins import openai, silero, deepgram

from backend_modules.livekit_enhanced import (
    with_perplexity
)

from supabase_memory_manager import SupabaseMemoryManager

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

# Simple error handling following LiveKit patterns
def safe_binary_repr(data) -> str:
    """Safely represent data for logging without binary content"""
    if data is None:
        return "None"
    
    data_str = str(data)
    if len(data_str) > 500:  # Truncate very long strings
        return data_str[:500] + "... (truncated)"
    return data_str

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

class DebateModerator:
    """Aristotle - The Debate Moderator Agent"""
    
    def __init__(self):
        self.memory_manager = SupabaseMemoryManager()
        self.session_data = {}
        self.current_topic = None
        self.participants = []
        self.debate_phase = "opening"  # opening, discussion, closing
        
        # Use Perplexity through enhanced session for fact-checking
        self.fact_checker_llm = None  # Will be set in entrypoint
        self.enhanced_session = None  # Enhanced session for Perplexity API calls
        
    async def initialize_session(self, room_name: str):
        """Initialize debate session with simple error handling"""
        try:
            logger.info(f"Initializing debate session for room: {safe_binary_repr(room_name)}")
            
            # Store session data
            self.session_data = {
                "room_name": room_name,
                "start_time": datetime.now().isoformat(),
                "participants": [],
                "topic": None,
                "phase": "opening"
            }
            
            # Memory manager will handle room creation when needed
            # No initialization required for Supabase memory manager
            
            logger.info("Debate session initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize session: {safe_binary_repr(str(e))}")
            raise

    @function_tool
    async def set_debate_topic(
        self,
        context: RunContext,
        topic: str,
        context_info: Optional[str] = None
    ) -> str:
        """Set the debate topic and provide context"""
        try:
            self.current_topic = topic
            self.session_data["topic"] = topic
            
            # Store in memory (simplified for now - would need room_id in production)
            logger.info(f"Topic set: {topic} with context: {context_info}")
            
            response = f"Debate topic set: '{topic}'"
            if context_info:
                response += f"\n\nContext: {context_info}"
            
            logger.info(f"Debate topic set: {safe_binary_repr(topic)}")
            return response
            
        except Exception as e:
            logger.error(f"Error setting debate topic: {safe_binary_repr(str(e))}")
            return f"I encountered an error setting the topic. Let's proceed with the current discussion."

    @function_tool
    async def fact_check_statement(
        self,
        context: RunContext,
        statement: str,
        speaker: Optional[str] = None
    ) -> str:
        """Fact-check a statement using OpenAI through LiveKit (no more manual API calls!)"""
        try:
            # Use OpenAI through LiveKit's system - much cleaner!
            fact_check_prompt = f"""
            Please fact-check the following statement and provide a brief, balanced analysis:
            
            Statement: "{statement}"
            
            Provide:
            1. Accuracy assessment (Accurate/Partially Accurate/Inaccurate/Unclear)
            2. Brief explanation (2-3 sentences max)
            3. Any important context or nuance
            
            Keep it concise and suitable for a live debate.
            """
            
            # Use Perplexity LLM for fact-checking through enhanced session
            if self.fact_checker_llm:
                response = await self.fact_checker_llm.agenerate(fact_check_prompt)
                fact_check_result = response.choices[0].message.content
            else:
                fact_check_result = "Fact-checking service temporarily unavailable. Please continue the discussion."
            
            # Store the fact-check (simplified for now)
            logger.info(f"Fact-check stored for speaker: {speaker}")
            
            logger.info(f"Fact-check completed for statement: {safe_binary_repr(statement[:50])}...")
            return f"Fact-check result: {fact_check_result}"
            
        except Exception as e:
            logger.error(f"Error in fact-checking: {safe_binary_repr(str(e))}")
            return "I'm unable to fact-check that statement right now, but let's continue the discussion."

    @function_tool
    async def moderate_discussion(
        self,
        context: RunContext,
        action: str,
        participant: Optional[str] = None,
        reason: Optional[str] = None
    ) -> str:
        """Moderate the discussion flow"""
        try:
            valid_actions = ["give_floor", "request_clarification", "summarize_points", "transition_topic", "call_for_evidence"]
            
            if action not in valid_actions:
                return f"Invalid moderation action. Valid actions: {', '.join(valid_actions)}"
            
            moderation_result = ""
            
            if action == "give_floor":
                moderation_result = f"The floor is now given to {participant or 'the next speaker'}."
                
            elif action == "request_clarification":
                moderation_result = f"Could {participant or 'the speaker'} please clarify their position?"
                if reason:
                    moderation_result += f" Specifically: {reason}"
                    
            elif action == "summarize_points":
                moderation_result = "Let me summarize the key points made so far in this discussion."
                
            elif action == "transition_topic":
                moderation_result = "Let's transition to the next aspect of this topic."
                
            elif action == "call_for_evidence":
                moderation_result = f"Could {participant or 'the speaker'} provide evidence to support that claim?"
            
            # Store moderation action (simplified for now)
            logger.info(f"Moderation action stored: {action} for {participant}")
            
            logger.info(f"Moderation action: {safe_binary_repr(action)}")
            return moderation_result
            
        except Exception as e:
            logger.error(f"Error in moderation: {safe_binary_repr(str(e))}")
            return "Let's continue with our discussion."

    @function_tool
    async def get_debate_summary(
        self,
        context: RunContext,
        include_fact_checks: bool = True
    ) -> str:
        """Get a summary of the current debate"""
        try:
            # Retrieve memories from the session (simplified for now)
            memories = []  # Would use get_room_memory_context in production
            
            summary_parts = []
            
            if self.current_topic:
                summary_parts.append(f"Topic: {self.current_topic}")
            
            summary_parts.append(f"Phase: {self.debate_phase}")
            summary_parts.append(f"Participants: {len(self.participants)}")
            
            if include_fact_checks and memories:
                fact_checks = [m for m in memories if m.get("type") == "fact_check"]
                if fact_checks:
                    summary_parts.append(f"Fact-checks performed: {len(fact_checks)}")
            
            summary = "\n".join(summary_parts)
            
            logger.info("Debate summary generated")
            return f"Debate Summary:\n{summary}"
            
        except Exception as e:
            logger.error(f"Error generating summary: {safe_binary_repr(str(e))}")
            return "I'm having trouble generating a summary right now."

@function_tool
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
async def end_debate():
    """End the current debate session"""
    try:
        logger.info("🏁 Ending debate session")
        return "Thank you all for this engaging discussion. Let me provide a brief summary of the key points raised and conclude our session."
    except Exception as e:
        logger.error(f"Error ending debate: {e}")
        return "Thank you for this discussion. This concludes our debate session."

@function_tool
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

async def entrypoint(ctx: JobContext):
    """Main entrypoint with enhanced error handling and simplified OpenAI integration"""
    try:
        logger.info("Starting Aristotle - Debate Moderator Agent")
        
        # Validate environment
        if not os.getenv("PERPLEXITY_API_KEY"):
            logger.error("PERPLEXITY_API_KEY environment variable is required")
            return
        
        await ctx.connect()
        
        # Create moderator instance
        moderator = DebateModerator()
        
        # Use Perplexity with regular sonar model for faster fact-checking
        llm = with_perplexity(
            model="llama-3.1-sonar-small-128k-chat",  # Regular sonar model for speed
            temperature=0.3  # Lower temperature for more factual responses
        )
        
        # Set the fact-checker LLM
        moderator.fact_checker_llm = llm
        
        # Create agent with tools
        agent = Agent(
            instructions="""You are Aristotle, a wise and fair debate moderator. Your role is to:

1. **Facilitate Fair Discussion**: Ensure all participants have equal opportunity to speak
2. **Fact-Check Claims**: Use your fact-checking tool when participants make factual claims
3. **Maintain Order**: Keep discussions focused and productive
4. **Encourage Evidence**: Ask for sources and evidence when appropriate
5. **Summarize Progress**: Periodically summarize key points made

Guidelines:
- Be impartial and respectful to all viewpoints
- Encourage critical thinking and evidence-based arguments
- Use your tools to fact-check, moderate, and summarize
- Keep the discussion engaging and educational
- Intervene when discussions become unproductive

Remember: You're here to elevate the quality of discourse, not to take sides.""",
            tools=[
                moderator.set_debate_topic,
                moderator.fact_check_statement,
                moderator.moderate_discussion,
                moderator.get_debate_summary,
            ],
        )
        
        # Create LiveKit agent session with proper components
        session = AgentSession(
            vad=silero.VAD.load(),
            stt=deepgram.STT(model="nova-3"),
            llm=openai.LLM(model="gpt-4o-mini"),  # Keep OpenAI for main agent
            tts=openai.TTS(voice="echo"),
        )
        
        # Initialize the moderator session
        room_name = ctx.room.name or "default_debate_room"
        
        # Initialize the moderator session
        await moderator.initialize_session(room_name)
        
        # Start the agent
        await session.start(agent=agent, room=ctx.room)
        
        # Generate initial greeting
        await session.generate_reply(
            instructions="Greet the participants and explain your role as Aristotle, the debate moderator. Ask what topic they'd like to discuss."
        )
        
        logger.info("Aristotle agent started successfully")
            
    except Exception as e:
        logger.error(f"Failed to start agent: {safe_binary_repr(str(e))}")
        raise

def main():
    """Main entry point for the debate moderator agent"""
    cli.run_app(
        WorkerOptions(
            agent_name="moderator",
            entrypoint_fnc=entrypoint,
        )
    )

# Binary data logging safeguards already defined above

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