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
from dotenv import load_dotenv
from typing import Optional, Dict, Any, List
from datetime import datetime

# LiveKit imports
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
    function_tool,
    RunContext,
)
from livekit.plugins import openai, silero, deepgram
from livekit import rtc  # Add rtc import for better connection handling

from supabase_memory_manager import SupabaseMemoryManager

# Load environment variables first
load_dotenv()

# Configure logging with WebRTC-specific settings
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set more verbose logging for WebRTC debugging
logging.getLogger("livekit").setLevel(logging.DEBUG)
logging.getLogger("livekit.rtc").setLevel(logging.DEBUG)

# WebRTC Configuration for better connection stability
WEBRTC_CONFIG = {
    "ice_transport_policy": "all",  # Use both STUN and TURN servers
    "bundle_policy": "max-bundle",  # Bundle all media streams
    "rtcp_mux_policy": "require",   # Require RTCP multiplexing
    "ice_candidate_pool_size": 10,  # Pre-gather ICE candidates
}

# Connection retry configuration
CONNECTION_CONFIG = {
    "max_retries": 3,
    "retry_delay": 2.0,
    "connection_timeout": 30.0,
}

# Simple error handling following LiveKit patterns
def safe_binary_repr(data) -> str:
    """Safely represent data for logging without binary content"""
    if data is None:
        return "None"
    
    data_str = str(data)
    if len(data_str) > 500:  # Truncate very long strings
        return data_str[:500] + "... (truncated)"
    return data_str

# Removed unused ConversationState class and global variable

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
        """Fact-check a statement using LiveKit's LLM interface - provides quick, concise responses"""
        try:
            # Use LiveKit's proper LLM interface with Perplexity for real-time fact-checking
            fact_check_prompt = f"""
            Fact-check this statement and respond in exactly this format: "According to [source], actually [brief fact]" or "That's correct according to [source]"
            
            Statement: "{statement}"
            
            Keep response under 15 words. Be direct and cite the source.
            """
            
            # Use context.llm (LiveKit's LLM with Perplexity) for real-time fact-checking
            response = await context.llm.agenerate(fact_check_prompt)
            fact_check_result = response.choices[0].message.content
            
            # Store the fact-check (simplified for now)
            logger.info(f"Fact-check completed for speaker: {speaker}")
            
            logger.info(f"Fact-check completed for statement: {safe_binary_repr(statement[:50])}...")
            return fact_check_result
            
        except Exception as e:
            logger.error(f"Error in fact-checking: {safe_binary_repr(str(e))}")
            return "Unable to verify that right now."

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

def get_persona_instructions(persona: str) -> str:
    """Get persona-specific instructions for the agent."""
    persona_lower = persona.lower()
    
    if persona_lower == "socrates":
        return """You are Socrates, the ancient Greek philosopher, moderating a debate.

Your approach:
- ONLY speak when directly called by name or when users ask for your input
- Ask ONE brief, probing question at a time (1-2 sentences max)
- Use the Socratic method - guide people to discover truth through questioning
- When someone makes a claim, ask: "How do you know this?" or "What do you mean by...?"
- Stay quiet and let users debate - only intervene when specifically requested

Keep ALL responses under 20 words. Be concise and focused on asking the right questions."""
        
    elif persona_lower == "buddha":
        return """You are Buddha, the enlightened teacher, moderating a discussion.

Your approach:
- ONLY speak when directly called by name or when users ask for your input
- Promote compassion and understanding with brief, wise comments
- Help de-escalate conflicts with 1-2 calm sentences
- When tensions arise, offer brief redirection to common ground
- Stay quiet and let users discuss - only intervene when specifically requested

Keep ALL responses under 20 words. Speak with gentle wisdom and focus on harmony."""
        
    else:  # Aristotle (default)
        return """You are Aristotle, the systematic philosopher, moderating a debate.

Your approach:
- ONLY speak when directly called by name or when users ask for your input
- When fact-checking is requested, provide quick, evidence-based responses like "According to [source], actually [brief fact]"
- Point out logical fallacies briefly when asked
- Stay quiet and let users debate - only intervene when specifically requested
- Use your fact-checking tool when users ask to verify claims

Keep ALL responses under 20 words. Be logical, structured, and focused on evidence."""

def get_persona_greeting(persona: str) -> str:
    """Get persona-specific greeting for the agent."""
    persona_lower = persona.lower()
    
    if persona_lower == "socrates":
        return "Give a brief greeting as Socrates in 10 words or less. Say you're here to help if called upon."
        
    elif persona_lower == "buddha":
        return "Give a brief greeting as Buddha in 10 words or less. Say you're here to help if called upon."
        
    else:  # Aristotle (default)
        return "Give a brief greeting as Aristotle in 10 words or less. Say you're here to help if called upon."

async def entrypoint(ctx: JobContext):
    """Main entrypoint with enhanced error handling and simplified LiveKit integration"""
    room_name = "unknown"
    persona = "Aristotle"
    debate_topic = "General Discussion"
    
    try:
        logger.info("🚀 AGENT STARTUP - Debate Moderator Agent Starting")
        
        # Get room name for error tracking
        try:
            room_name = ctx.room.name if hasattr(ctx, 'room') and hasattr(ctx.room, 'name') else "unknown"
            logger.info(f"📍 Room: {room_name}")
        except Exception as e:
            logger.warning(f"Could not get room name: {e}")
        
        # Connect to LiveKit room with enhanced WebRTC handling and retry logic
        connection_successful = False
        last_error = None
        
        for attempt in range(CONNECTION_CONFIG["max_retries"]):
            try:
                if attempt > 0:
                    logger.info(f"🔄 Connection attempt {attempt + 1}/{CONNECTION_CONFIG['max_retries']}")
                    await asyncio.sleep(CONNECTION_CONFIG["retry_delay"])
                else:
                    logger.info("🔌 Connecting to LiveKit room...")
                
                # Enhanced connection with WebRTC configuration
                await ctx.connect(
                    # Add connection options for better WebRTC stability
                    auto_subscribe=True,
                    # Enable adaptive stream for better connection reliability
                    adaptive_stream=True,
                )
                
                # Verify room connection is stable
                if ctx.room and ctx.room.connection_state == rtc.ConnectionState.CONNECTED:
                    logger.info("✅ Successfully connected to LiveKit room")
                    logger.info(f"📊 Room state: {ctx.room.connection_state}")
                    logger.info(f"👥 Current participants: {len(ctx.room.remote_participants)}")
                    connection_successful = True
                    break
                else:
                    logger.warning(f"⚠️ Room connection state: {ctx.room.connection_state if ctx.room else 'No room'}")
                    if attempt < CONNECTION_CONFIG["max_retries"] - 1:
                        logger.info("🔄 Will retry connection...")
                        continue
                    
            except Exception as connect_error:
                last_error = connect_error
                logger.warning(f"⚠️ Connection attempt {attempt + 1} failed: {type(connect_error).__name__}: {str(connect_error)}")
                
                # Log specific WebRTC connection details for debugging
                if "negotiation" in str(connect_error).lower():
                    logger.warning("🔧 WebRTC Negotiation Error - This may be due to network/firewall issues")
                elif "timeout" in str(connect_error).lower():
                    logger.warning("⏱️ Connection Timeout - Check network connectivity and LiveKit server status")
                elif "ice" in str(connect_error).lower():
                    logger.warning("🧊 ICE Connection Error - Network/NAT traversal issue")
                
                if attempt < CONNECTION_CONFIG["max_retries"] - 1:
                    logger.info(f"🔄 Retrying in {CONNECTION_CONFIG['retry_delay']} seconds...")
                else:
                    logger.error(f"❌ All {CONNECTION_CONFIG['max_retries']} connection attempts failed")
                    import traceback
                    logger.error(f"🔍 Final connection error traceback:\n{traceback.format_exc()}")
        
        if not connection_successful:
            logger.error("❌ ROOM CONNECTION FAILED after all retry attempts")
            if last_error:
                raise last_error
            else:
                raise Exception("Connection failed for unknown reason")
        
        # Get persona and topic from job metadata (Context7 compliant approach)
        try:
            logger.info("📋 Reading configuration from job metadata...")
            # Read from job metadata if available
            if hasattr(ctx, 'job') and hasattr(ctx.job, 'metadata') and ctx.job.metadata:
                # Parse JSON metadata (Context7 requirement)
                try:
                    if isinstance(ctx.job.metadata, str):
                        # Metadata is JSON string - parse it
                        metadata_dict = json.loads(ctx.job.metadata)
                        logger.info(f"📋 Parsed JSON metadata: {metadata_dict}")
                    else:
                        # Metadata is already a dict
                        metadata_dict = ctx.job.metadata
                        logger.info(f"📋 Direct metadata dict: {metadata_dict}")
                    
                    persona = metadata_dict.get("moderator_persona", "Aristotle")
                    debate_topic = metadata_dict.get("debate_topic", "General Discussion")
                    logger.info(f"✅ Job metadata found - Persona: {persona}, Topic: {debate_topic}")
                    
                except json.JSONDecodeError as json_error:
                    logger.error(f"❌ Error parsing metadata JSON: {json_error}")
                    logger.error(f"Raw metadata: {ctx.job.metadata}")
                    # Fall back to defaults
                    persona = "Aristotle"
                    debate_topic = "General Discussion"
                    logger.info(f"🎭 JSON parse failed, using defaults - Persona: {persona}, Topic: {debate_topic}")
            else:
                # Fallback to environment variables
                persona = os.getenv("MODERATOR_PERSONA", "Aristotle")
                debate_topic = os.getenv("DEBATE_TOPIC", "General Discussion")
                logger.info(f"⚠️  No job metadata, using environment variables - Persona: {persona}, Topic: {debate_topic}")
        except Exception as metadata_error:
            logger.warning(f"⚠️  Could not read job metadata: {type(metadata_error).__name__}: {str(metadata_error)}")
            persona = "Aristotle"
            debate_topic = "General Discussion"
            logger.info(f"🎭 Using defaults - Persona: {persona}, Topic: {debate_topic}")
        
        # Validate persona
        valid_personas = ["Socrates", "Aristotle", "Buddha"]
        if persona not in valid_personas:
            logger.warning(f"⚠️  Invalid persona '{persona}', defaulting to 'Aristotle'")
            persona = "Aristotle"
        
        # Create moderator instance with persona
        try:
            logger.info("🤖 Creating moderator instance...")
            moderator = DebateModerator()
            moderator.current_persona = persona
            logger.info(f"✅ Moderator created with persona: {persona}")
        except Exception as moderator_error:
            logger.error(f"❌ MODERATOR CREATION FAILED: {type(moderator_error).__name__}: {str(moderator_error)}")
            raise moderator_error
        
        logger.info(f"🎭 Agent configured as: {persona}")
        logger.info(f"📋 Debate topic: {debate_topic}")
        
        # Get persona-specific instructions and greeting following LiveKit patterns
        try:
            logger.info("📝 Generating persona-specific instructions...")
            persona_instructions = get_persona_instructions(persona)
            persona_greeting = get_persona_greeting(persona)
            logger.info("✅ Persona instructions and greeting prepared")
        except Exception as persona_error:
            logger.error(f"❌ PERSONA SETUP FAILED: {type(persona_error).__name__}: {str(persona_error)}")
            raise persona_error
        
        # Get environment variables
        logger.info("🔍 Checking environment variables...")
        
        # Create LiveKit agent session with built-in Perplexity support
        try:
            logger.info("🎧 Creating LiveKit agent session components...")
            
            # Load VAD
            try:
                vad = silero.VAD.load()
                logger.info("✅ VAD (Voice Activity Detection) loaded")
            except Exception as vad_error:
                logger.error(f"❌ VAD loading failed: {vad_error}")
                raise vad_error
            
            # Setup STT
            try:
                stt = deepgram.STT(model="nova-3")
                logger.info("✅ STT (Speech-to-Text) configured")
            except Exception as stt_error:
                logger.error(f"❌ STT setup failed: {stt_error}")
                raise stt_error
            
            # Setup LLM with Perplexity (Official LiveKit integration)
            try:
                logger.info("🧠 Setting up LLM with Perplexity integration...")
                
                # Perplexity requires PERPLEXITY_API_KEY environment variable
                perplexity_key = os.getenv("PERPLEXITY_API_KEY")
                if not perplexity_key or perplexity_key == "your-perplexity-key" or len(perplexity_key) < 20:
                    logger.error("❌ CRITICAL: PERPLEXITY_API_KEY not found or invalid in environment")
                    raise ValueError("Valid PERPLEXITY_API_KEY is required for Perplexity integration")
                
                # Allow model selection via environment variable for troubleshooting
                perplexity_model = os.getenv("PERPLEXITY_MODEL", "llama-3.1-sonar-small-128k-online")
                logger.info(f"🧠 Using Perplexity model: {perplexity_model}")
                logger.info(f"🔗 Perplexity API endpoint: https://api.perplexity.ai/")
                
                # Use proper Perplexity integration without base_url override
                llm = openai.LLM.with_perplexity(
                    model=perplexity_model,
                    api_key=perplexity_key,
                    temperature=0.7
                )
                
                # Verify connection to Perplexity API with a simple test query
                try:
                    logger.info("🔍 Testing Perplexity API connection...")
                    # Use proper chat method for testing
                    test_response = await llm.chat([{"role": "user", "content": "Hello"}])
                    if test_response and test_response.choices:
                        logger.info("✅ Perplexity API connection test successful")
                    else:
                        logger.warning("⚠️ Perplexity API connection test returned empty response")
                except Exception as test_error:
                    logger.warning(f"⚠️ Perplexity API connection test failed: {test_error}")
                    logger.warning("⚠️ Continuing despite test failure, but the agent may encounter issues")
                
                logger.info("✅ LLM with Perplexity integration configured")
            except Exception as llm_error:
                logger.error(f"❌ LLM setup failed: {type(llm_error).__name__}: {str(llm_error)}")
                raise llm_error
            
            # Setup TTS - Perplexity doesn't support TTS, use OpenAI TTS instead
            try:
                openai_key = os.getenv("OPENAI_API_KEY")
                if not openai_key or openai_key == "your-openai-key" or len(openai_key) < 20:
                    logger.error("❌ CRITICAL: OPENAI_API_KEY not found or invalid in environment (required for TTS)")
                    raise ValueError("Valid OPENAI_API_KEY is required for TTS functionality")
                
                logger.info("🗣️ Setting up TTS with OpenAI (Perplexity doesn't support TTS)...")
                tts = openai.TTS(
                    voice="alloy",
                    api_key=openai_key,  # Use OpenAI API key for TTS
                )
                logger.info("✅ TTS (Text-to-Speech) configured with OpenAI")
            except Exception as tts_error:
                logger.error(f"❌ TTS setup failed: {tts_error}")
                raise tts_error
            
            # Create session
            logger.info("🎬 Creating AgentSession...")
            session = AgentSession(
                vad=vad,
                stt=stt,
                llm=llm,
                tts=tts,
            )
            logger.info("✅ AgentSession created successfully")
            
        except Exception as session_error:
            logger.error(f"❌ SESSION CREATION FAILED: {type(session_error).__name__}: {str(session_error)}")
            import traceback
            logger.error(f"🔍 Session error traceback:\n{traceback.format_exc()}")
            raise session_error

        # Create agent with persona-specific instructions and tools
        try:
            logger.info("🛠️  Setting up agent tools...")
            tools = [
                moderator.fact_check_statement,
                moderator.manage_speaking_time,
                moderator.summarize_discussion,
                moderator.suggest_topic_transition,
                moderator.switch_persona,
            ]
            logger.info(f"✅ {len(tools)} tools prepared")
            
            logger.info("🤖 Creating Agent instance...")
            agent = Agent(
                instructions=persona_instructions,
                tools=tools,
            )
            logger.info("✅ Agent created successfully")
        except Exception as agent_error:
            logger.error(f"❌ AGENT CREATION FAILED: {type(agent_error).__name__}: {str(agent_error)}")
            raise agent_error

        # Start the session with proper resource management (Context7 pattern)
        try:
            logger.info("🚀 Starting agent session with proper resource management...")
            
            # Add connection state monitoring and participant event handlers
            def on_connection_state_changed(state: rtc.ConnectionState):
                logger.info(f"🔄 Connection state changed to: {state}")
                if state == rtc.ConnectionState.DISCONNECTED:
                    logger.warning("⚠️ Room disconnected - LiveKit will handle reconnection")
                elif state == rtc.ConnectionState.RECONNECTING:
                    logger.info("🔄 Reconnecting to room...")
                elif state == rtc.ConnectionState.CONNECTED:
                    logger.info("✅ Room reconnected successfully")
            
            def on_participant_connected(participant: rtc.RemoteParticipant):
                logger.info(f"👋 Participant joined: {participant.identity}")
                logger.info(f"👥 Total participants: {len(ctx.room.remote_participants)}")
            
            def on_participant_disconnected(participant: rtc.RemoteParticipant):
                logger.info(f"👋 Participant left: {participant.identity}")
                logger.info(f"👥 Total participants: {len(ctx.room.remote_participants)}")
            
            def on_track_published(publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
                logger.debug(f"📡 Track published by {participant.identity}: {publication.kind}")
            
            def on_track_unpublished(publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
                logger.debug(f"📡 Track unpublished by {participant.identity}: {publication.kind}")
            
            # Set up event monitoring
            if ctx.room:
                ctx.room.on("connection_state_changed", on_connection_state_changed)
                ctx.room.on("participant_connected", on_participant_connected)
                ctx.room.on("participant_disconnected", on_participant_disconnected)
                ctx.room.on("track_published", on_track_published)
                ctx.room.on("track_unpublished", on_track_unpublished)
            
            # Start the session directly without async context manager (Context7 best practice)
            await session.start(agent=agent, room=ctx.room)
            logger.info("✅ Agent session started successfully")
            
            # Verify session is active
            if hasattr(session, '_started') and session._started:
                logger.info("🎉 Agent session is confirmed active")
            else:
                logger.warning("⚠️ Agent session start status unclear")
            
            # Keep the session running - LiveKit will handle disconnection automatically
            logger.info("🎉 Agent is now active and ready for participants")
            
            # Generate initial greeting with retry logic
            try:
                await session.generate_reply(instructions=persona_greeting)
                logger.info("✅ Initial greeting sent")
            except Exception as greeting_error:
                logger.warning(f"⚠️ Could not send initial greeting: {greeting_error}")
                logger.info("🔄 Agent will greet participants when they join")
            
        except Exception as start_error:
            logger.error(f"❌ SESSION START FAILED: {type(start_error).__name__}: {str(start_error)}")
            
            # Log specific session start issues
            if "connection" in str(start_error).lower():
                logger.error("🔌 Session start failed due to connection issues")
            elif "timeout" in str(start_error).lower():
                logger.error("⏱️ Session start timed out")
            elif "permission" in str(start_error).lower():
                logger.error("🔐 Session start failed due to permission issues")
            
            import traceback
            logger.error(f"🔍 Session start error traceback:\n{traceback.format_exc()}")
            raise start_error
        
        logger.info(f"🎉 SUCCESS: {persona} moderator is ready in room {room_name}!")

    except Exception as general_error:
        logger.error(f"❌ CRITICAL AGENT FAILURE: {type(general_error).__name__}: {str(general_error)}")
        logger.error(f"📍 Room: {room_name}, Persona: {persona}, Topic: {debate_topic}")
        
        # Log full traceback for debugging
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"🔍 Full error traceback:\n{error_details}")
        
        # Check specific error types for better debugging
        if "api" in str(general_error).lower():
            logger.error("🔑 API ERROR: Check API keys and network connectivity")
        elif "timeout" in str(general_error).lower():
            logger.error("⏱️  TIMEOUT ERROR: Service took too long to respond")
        elif "connection" in str(general_error).lower():
            logger.error("🔌 CONNECTION ERROR: Network or service connectivity issue")
        elif "permission" in str(general_error).lower() or "unauthorized" in str(general_error).lower():
            logger.error("🔐 PERMISSION ERROR: Check API keys and access permissions")
        else:
            logger.error(f"🔍 UNKNOWN ERROR TYPE: {type(general_error).__name__}")
        
        raise general_error

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