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
from typing import Optional, Annotated, Dict, Any, List, Tuple, Callable, Set
from datetime import datetime
from contextlib import asynccontextmanager

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
        # Get persona from environment variable, default to Aristotle
        self.current_persona = os.getenv("MODERATOR_PERSONA", "Aristotle")

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
        """Fact-check a statement using LiveKit's LLM interface (no direct API calls!)"""
        try:
            # Use LiveKit's proper LLM interface - this is the correct way!
            fact_check_prompt = f"""
            Please fact-check the following statement and provide a brief, balanced analysis:
            
            Statement: "{statement}"
            
            Provide:
            1. Accuracy assessment (Accurate/Partially Accurate/Inaccurate/Unclear)
            2. Brief explanation (2-3 sentences max)
            3. Any important context or nuance
            
            Keep it concise and suitable for a live debate.
            """
            
            # Use context.llm (LiveKit's LLM) instead of direct API calls
            # This is the proper LiveKit way to do LLM calls from within tools
            response = await context.llm.agenerate(fact_check_prompt)
            fact_check_result = response.choices[0].message.content
            
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
    async def manage_speaking_time(
        self,
        context: RunContext,
        action: str,
        participant: Optional[str] = None
    ) -> str:
        """Manage speaking time and turn-taking in the debate"""
        try:
            if action == "get_status":
                return f"Current debate phase: {self.debate_phase}. Participants: {', '.join(self.participants) if self.participants else 'None yet'}"
            
            elif action == "give_turn":
                if participant:
                    return f"🎯 {participant}, you have the floor. Please share your thoughts on the current topic."
                else:
                    return "🎯 Who would like to speak next? Please raise your hand or say your name."
            
            elif action == "time_reminder":
                return "⏰ Let's keep our points concise to ensure everyone gets a chance to participate."
            
            elif action == "transition":
                return "🔄 Let's hear from someone who hasn't spoken recently. Anyone with a different perspective?"
            
            else:
                return "Available actions: get_status, give_turn, time_reminder, transition"
                
        except Exception as e:
            logger.error(f"Error in manage_speaking_time: {safe_binary_repr(str(e))}")
            return "I'll help manage speaking time as we continue the discussion."

    @function_tool
    async def summarize_discussion(
        self,
        context: RunContext,
        include_positions: bool = True
    ) -> str:
        """Provide a summary of the current discussion"""
        try:
            if not self.current_topic:
                return "No topic has been set for discussion yet."
            
            summary = f"📋 **Discussion Summary - Topic: {self.current_topic}**\n\n"
            
            if include_positions:
                summary += "**Key Points Raised:**\n"
                summary += "- [Points will be tracked as discussion progresses]\n\n"
            
            summary += "**Next Steps:**\n"
            summary += "- Continue with evidence-based arguments\n"
            summary += "- Address counterpoints respectfully\n"
            summary += "- Seek areas of common ground\n"
            
            return summary
            
        except Exception as e:
            logger.error(f"Error in summarize_discussion: {safe_binary_repr(str(e))}")
            return "I'll provide a summary as our discussion continues to develop."

    @function_tool
    async def suggest_topic_transition(
        self,
        context: RunContext,
        reason: str,
        suggested_direction: Optional[str] = None
    ) -> str:
        """Suggest transitioning to a new aspect of the topic or related topic"""
        try:
            if reason == "exhausted":
                return f"🔄 It seems we've explored this aspect thoroughly. {suggested_direction or 'Shall we consider a related angle or different perspective?'}"
            
            elif reason == "heated":
                return f"🕊️ I notice the discussion is getting intense. {suggested_direction or 'Perhaps we could step back and examine the underlying principles we both value?'}"
            
            elif reason == "stuck":
                return f"🤔 We seem to be at an impasse. {suggested_direction or 'Let me ask: what evidence might change your mind, or what common ground can we identify?'}"
            
            elif reason == "broaden":
                return f"🌐 {suggested_direction or 'Let us broaden our perspective. How might this issue affect different groups or contexts?'}"
            
            else:
                return f"🧭 Let's consider shifting our focus. {suggested_direction or 'What aspect would you like to explore next?'}"
                
        except Exception as e:
            logger.error(f"Error in suggest_topic_transition: {safe_binary_repr(str(e))}")
            return "Let's continue our thoughtful exploration of this topic."

    @function_tool
    async def switch_persona(self, context: RunContext, new_persona: str):
        """Switch to a new persona"""
        try:
            self.current_persona = new_persona
            logger.info(f"Switched to persona: {new_persona}")
            return f"Switched to persona: {new_persona}"
        except Exception as e:
            logger.error(f"Error switching persona: {safe_binary_repr(str(e))}")
            return "I'm unable to switch personas right now. Please try again later."

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
    """Main entrypoint with enhanced error handling and simplified LiveKit integration"""
    try:
        logger.info("Starting AI Debate Moderator Agent")
        
        await ctx.connect()
        
        # Create moderator instance first - it will get persona from environment variable
        moderator = DebateModerator()
        
        # Use the persona from the moderator instance
        persona = moderator.current_persona
        debate_topic = "General Discussion"  # Default fallback
        
        logger.info(f"🎭 Agent configured as: {persona}")
        logger.info(f"📋 Debate topic: {debate_topic}")
        
        # Get persona-specific instructions and greeting following LiveKit patterns
        persona_instructions = get_persona_instructions(persona)
        persona_greeting = get_persona_greeting(persona)
        
        # Create LiveKit agent session with built-in Perplexity support
        # This uses LiveKit's native Perplexity integration - no direct API calls!
        session = AgentSession(
            vad=silero.VAD.load(),
            stt=deepgram.STT(model="nova-3"),
            
            # Use LiveKit's built-in Perplexity support instead of OpenAI
            llm=openai.LLM.with_perplexity(
                model="llama-3.1-sonar-small-128k-online",  # Real-time search model
                api_key=os.getenv("PERPLEXITY_API_KEY"),
                temperature=0.7,
            ),
            
            tts=openai.TTS(voice="alloy"),
        )

        # Create agent with persona-specific instructions
        agent = Agent(
            instructions=persona_instructions,
            tools=[
                moderator.fact_check_statement,
                moderator.manage_speaking_time,
                moderator.summarize_discussion,
                moderator.suggest_topic_transition,
                moderator.switch_persona,  # Add persona switching tool
            ],
        )

        await session.start(agent=agent, room=ctx.room)
        
        # Generate persona-specific greeting
        await session.generate_reply(instructions=persona_greeting)

    except Exception as e:
        logger.error(f"❌ Agent failed to start: {e}")
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