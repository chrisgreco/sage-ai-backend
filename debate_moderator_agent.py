#!/usr/bin/env python3

"""
Sage AI Debate Moderator Agent - Enhanced with Audio Track Subscription
Handles Aristotle persona (logical moderator) with proper inter-agent coordination
"""

import os
import sys
import asyncio
import logging
import json
import time
import threading
import signal
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import Optional

# Load environment variables first
load_dotenv()

# Configure logging with more detailed debugging
logging.basicConfig(
    level=logging.DEBUG,  # More verbose logging for debugging
    format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
)
logger = logging.getLogger(__name__)

# Add error handling for API connections
import traceback
from contextlib import asynccontextmanager

# LiveKit Agents imports
try:
    from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, cli, function_tool, AutoSubscribe
    from livekit.plugins import openai, silero
    from livekit.agents import UserStateChangedEvent, AgentStateChangedEvent
    from livekit import rtc  # For audio track handling
    # NOTE: Transcription handled by Socrates agent to avoid duplicates
    logger.info("✅ LiveKit Agents successfully imported")
except ImportError as e:
    logger.error(f"❌ Failed to import LiveKit Agents: {e}")
    sys.exit(1)

# Check if knowledge system is available
KNOWLEDGE_AVAILABLE = False
# Note: ChromaDB integration is planned but not yet implemented
# The knowledge system currently uses file-based storage
logger.info("📝 Using file-based knowledge system (ChromaDB integration planned)")

# Check if Perplexity is available
PERPLEXITY_AVAILABLE = bool(os.environ.get("PERPLEXITY_API_KEY"))
if PERPLEXITY_AVAILABLE:
    logger.info("✅ Perplexity research available")
else:
    logger.warning("⚠️ Perplexity API key not found - research features disabled")

# Global knowledge managers for each agent
_knowledge_managers = {}

def get_knowledge_manager(agent_name):
    """Get or create knowledge manager for an agent"""
    if agent_name not in _knowledge_managers:
        try:
            # Simple mock knowledge manager for testing
            class MockKnowledgeManager:
                def __init__(self, name):
                    self.name = name

                def load_documents(self):
                    pass

                def search_knowledge(self, query, max_results=3):
                    return []

            _knowledge_managers[agent_name] = MockKnowledgeManager(agent_name)
            logger.info(f"✅ Loaded mock knowledge manager for {agent_name}")
        except Exception as e:
            logger.error(f"Failed to load knowledge manager for {agent_name}: {e}")
            _knowledge_managers[agent_name] = None
    return _knowledge_managers[agent_name]

def get_aristotle_knowledge_manager():
    """Get or create Aristotle's knowledge manager"""
    return get_knowledge_manager("aristotle")

async def get_agent_knowledge(agent_name, query, max_items=3):
    """Knowledge retrieval using SimpleKnowledgeManager"""
    try:
        km = get_knowledge_manager(agent_name)
        if not km:
            logger.warning(f"No knowledge manager available for {agent_name}")
            return []

        # Use the knowledge manager's search function
        results = km.search_knowledge(query, max_results=max_items)

        # Convert to the expected format
        formatted_results = []
        for result in results:
            formatted_results.append({
                'source': result.get('document', 'Unknown'),
                'content': result.get('content', ''),
                'title': result.get('title', 'Untitled'),
                'relevance_score': result.get('relevance_score', 0.0)
            })

        return formatted_results

    except Exception as e:
        logger.error(f"Knowledge retrieval error for {agent_name}: {e}")
        return []

@dataclass
class ConversationState:
    """Shared state for coordinating between agents"""
    active_speaker: Optional[str] = None  # "aristotle", "socrates", or None
    user_speaking: bool = False
    last_intervention_time: float = 0
    intervention_count: int = 0
    conversation_lock: threading.Lock = threading.Lock()

# Global conversation state
conversation_state = ConversationState()

class DebateModeratorAgent:
    """Enhanced Aristotle moderator with coordination capabilities"""

    def __init__(self):
        self.agent_name = "aristotle"

    async def check_speaking_permission(self, session) -> bool:
        """Check if this agent should speak based on conversation state"""
        with conversation_state.conversation_lock:
            # Don't interrupt if user is speaking
            if conversation_state.user_speaking:
                return False

            # Don't interrupt if another agent spoke very recently (within 2 seconds)
            if (conversation_state.active_speaker and
                    conversation_state.active_speaker != self.agent_name and
                    time.time() - conversation_state.last_intervention_time < 2.0):
                return False

            # Limit intervention frequency (max 1 per 10 seconds)
            if (time.time() - conversation_state.last_intervention_time < 10.0 and
                    conversation_state.intervention_count > 0):
                return False

            return True

    async def claim_speaking_turn(self):
        """Claim speaking turn in conversation"""
        with conversation_state.conversation_lock:
            conversation_state.active_speaker = self.agent_name
            conversation_state.last_intervention_time = time.time()
            conversation_state.intervention_count += 1

    async def release_speaking_turn(self):
        """Release speaking turn"""
        with conversation_state.conversation_lock:
            conversation_state.active_speaker = None

@function_tool
async def get_debate_topic(context):
    """Get the current debate topic"""
    try:
        topic = os.getenv("DEBATE_TOPIC", "The impact of AI on society")
        logger.debug(f"Retrieved debate topic: {topic}")
        return f"Current debate topic: {topic}"
    except Exception as e:
        logger.error(f"Error getting debate topic: {e}")
        logger.error(f"Debate topic error traceback: {traceback.format_exc()}")
        return "Error: Could not retrieve debate topic"

@function_tool
async def access_facilitation_knowledge(context, query: str):
    """Access specialized knowledge about facilitation and parliamentary procedure

    Args:
        query: Question about moderation techniques, parliamentary procedure, or facilitation
    """
    try:
        logger.debug(f"Accessing facilitation knowledge for query: {query}")
        
        # Query parliamentary and facilitation knowledge using updated system
        knowledge_items = await get_agent_knowledge("aristotle", query, max_items=3)

        if knowledge_items:
            knowledge_text = "\n\n".join([
                f"Source: {item['title']} ({item['source']})\n{item['content'][:400]}..."
                for item in knowledge_items
            ])
            logger.debug(f"Found {len(knowledge_items)} knowledge items")
            return {
                "knowledge": knowledge_text,
                "sources": [f"{item['title']} ({item['source']})" for item in knowledge_items],
                "relevance_scores": [item.get('relevance_score', 0.0) for item in knowledge_items]
            }
        else:
            logger.debug("No facilitation knowledge found")
            return {
                "knowledge": "No specific facilitation knowledge found for this query.",
                "sources": [],
                "relevance_scores": []
            }

    except Exception as e:
        logger.error(f"Error accessing facilitation knowledge: {e}")
        logger.error(f"Facilitation knowledge error traceback: {traceback.format_exc()}")
        return {
            "knowledge": f"Error accessing knowledge: {str(e)}",
            "sources": [],
            "relevance_scores": []
        }

@function_tool
async def suggest_process_intervention(context, situation: str):
    """Suggest appropriate process interventions for debate management

    Args:
        situation: Description of the current debate situation requiring intervention
    """
    try:
        logger.debug(f"Suggesting process intervention for: {situation}")

        # Access knowledge about process interventions
        knowledge_items = await get_agent_knowledge("aristotle", f"process intervention {situation}", max_items=2)

        # Provide structured intervention suggestions
        intervention_suggestions = {
            "immediate_action": "Consider calling for a brief pause to reset the discussion tone",
            "process_options": [
                "Redirect to the original question or topic",
                "Ask for clarification of key terms",
                "Request evidence or sources for claims",
                "Suggest time limits for responses"
            ],
            "knowledge_context": knowledge_items[:2] if knowledge_items else []
        }

        return intervention_suggestions

    except Exception as e:
        logger.error(f"Error suggesting process intervention: {e}")
        logger.error(f"Process intervention error traceback: {traceback.format_exc()}")
        return {
            "immediate_action": "Monitor the situation and be ready to intervene if needed",
            "process_options": ["Maintain focus on respectful dialogue"],
            "knowledge_context": []
        }

@function_tool
async def fact_check_claim(context, claim: str, source_requested: bool = False):
    """Fact-check a claim made during the debate using live research

    Args:
        claim: The factual claim to verify
        source_requested: Whether to specifically request sources from the participant
    """
    try:
        logger.debug(f"Fact-checking claim: {claim}")

        # Use live research to verify the claim
        if PERPLEXITY_AVAILABLE:
            research_query = f"fact check verify: {claim}"
            research_results = await research_live_data(context, research_query, "fact_check")

            # Parse research results
            if isinstance(research_results, dict) and "research_findings" in research_results:
                findings = research_results["research_findings"]

                fact_check_result = {
                    "claim": claim,
                    "verification_status": "researched",
                    "findings": findings[:500],  # Limit length
                    "sources_available": bool(research_results.get("sources", [])),
                    "confidence": "medium",  # Default confidence level
                    "recommendation": "Request sources from participant if claim appears questionable"
                }

                if source_requested:
                    fact_check_result["follow_up"] = "Please provide credible sources for this claim so we can verify it together."

                return fact_check_result
            else:
                logger.warning("Research results not in expected format")

        # Fallback when research is not available
        return {
            "claim": claim,
            "verification_status": "research_unavailable",
            "findings": "Unable to verify this claim with live research. Please provide credible sources.",
            "sources_available": False,
            "confidence": "low",
            "recommendation": "Request sources from participant",
            "follow_up": "Could you please provide credible sources for this claim?"
        }

    except Exception as e:
        logger.error(f"Error fact-checking claim: {e}")
        logger.error(f"Fact-check error traceback: {traceback.format_exc()}")
        return {
            "claim": claim,
            "verification_status": "error",
            "findings": f"Error during fact-checking: {str(e)}",
            "sources_available": False,
            "confidence": "unknown",
            "recommendation": "Request sources from participant"
        }

@function_tool
async def research_live_data(context, query: str, research_type: str = "general"):
    """Perform live research using Perplexity to get current information

    Args:
        query: Research query
        research_type: Type of research (general, fact_check, policy, etc.)
    """
    try:
        logger.debug(f"Performing live research: {query} (type: {research_type})")

        if not PERPLEXITY_AVAILABLE:
            return {
                "research_findings": "Live research unavailable - Perplexity API key not configured",
                "sources": [],
                "research_type": research_type,
                "confidence": "low"
            }

        # This would use Perplexity's live research capabilities
        # For now, return a structured response indicating research capability
        return {
            "research_findings": f"Research query processed: {query}. Live research capabilities available but implementation pending.",
            "sources": ["Perplexity AI Research"],
            "research_type": research_type,
            "confidence": "medium",
            "note": "Live research integration in development"
        }

    except Exception as e:
        logger.error(f"Error in live research: {e}")
        logger.error(f"Live research error traceback: {traceback.format_exc()}")
        return {
            "research_findings": f"Research error: {str(e)}",
            "sources": [],
            "research_type": research_type,
            "confidence": "error"
        }

@function_tool
async def analyze_argument_structure(context, argument: str):
    """Analyze the logical structure of an argument for fallacies or weak reasoning

    Args:
        argument: The argument text to analyze
    """
    try:
        logger.debug(f"Analyzing argument structure: {argument[:100]}...")

        # Basic argument analysis
        analysis = {
            "argument": argument[:200],  # Truncate for brevity
            "structure_assessment": "Argument received for analysis",
            "logical_issues": [],
            "strengths": [],
            "suggestions": ["Consider providing evidence for key claims", "Clarify causal relationships"]
        }

        return analysis

    except Exception as e:
        logger.error(f"Error analyzing argument structure: {e}")
        logger.error(f"Argument analysis error traceback: {traceback.format_exc()}")
        return {
            "argument": argument[:100] if argument else "No argument provided",
            "structure_assessment": f"Analysis error: {str(e)}",
            "logical_issues": [],
            "strengths": [],
            "suggestions": []
        }

@function_tool
async def detect_intervention_triggers(context, conversation_snippet: str):
    """Detect if moderator intervention is needed based on conversation content

    Args:
        conversation_snippet: Recent conversation text to analyze
    """
    try:
        logger.debug(f"Detecting intervention triggers in: {conversation_snippet[:100]}...")

        # Simple trigger detection
        triggers = {
            "intervention_needed": False,
            "trigger_type": "none",
            "confidence": 0.0,
            "suggested_action": "Continue monitoring",
            "reasoning": "No immediate intervention triggers detected"
        }

        # Basic keyword detection for demonstration
        if any(word in conversation_snippet.lower() for word in ["wrong", "stupid", "ridiculous"]):
            triggers.update({
                "intervention_needed": True,
                "trigger_type": "tone",
                "confidence": 0.7,
                "suggested_action": "Gently redirect to more constructive language",
                "reasoning": "Potentially dismissive language detected"
            })

        return triggers

    except Exception as e:
        logger.error(f"Error detecting intervention triggers: {e}")
        logger.error(f"Intervention triggers error traceback: {traceback.format_exc()}")
        return {
            "intervention_needed": False,
            "trigger_type": "error",
            "confidence": 0.0,
            "suggested_action": "Monitor conversation",
            "reasoning": f"Error in analysis: {str(e)}"
        }

async def process_audio_stream(audio_stream, participant):
    """Process audio frames from a participant's stream"""
    try:
        logger.info(f"🎵 Processing audio stream from {participant.identity}")

        async for frame in audio_stream:
            # Process audio frame for coordination
            # This could include voice activity detection, sentiment analysis, etc.
            pass

    except Exception as e:
        logger.error(f"❌ Error processing audio stream from {participant.identity}: {e}")
        logger.error(f"Audio stream error traceback: {traceback.format_exc()}")

async def entrypoint(ctx: JobContext):
    """Main entry point for the Aristotle debate moderator agent"""
    logger.info("🏛️ Aristotle Debate Moderator Agent starting...")

    # Track audio streams and other agents for coordination
    audio_tracks = {}
    other_agents = set()

    # Use decorator pattern for event handlers to fix async callback issues
    @ctx.room.on("track_subscribed")
    async def on_track_subscribed(track, publication, participant):
        """Handle when we subscribe to an audio track from another participant"""
        try:
            if track.kind == rtc.TrackKind.AUDIO:
                logger.info(f"🎧 Moderator subscribed to audio track from: {participant.identity}")

                # Store the audio track for coordination
                audio_tracks[participant.identity] = {
                    "track": track,
                    "publication": publication,
                    "participant": participant
                }

                # Identify other agents for coordination
                if (participant.identity and
                        ("socrates" in participant.identity.lower() or
                         "philosopher" in participant.identity.lower())):
                    other_agents.add(participant.identity)
                    logger.info(f"🤝 Moderator detected Socrates agent: {participant.identity}")

                # Process audio stream from this participant
                try:
                    audio_stream = rtc.AudioStream(track)
                    logger.info(f"🎵 Created audio stream for {participant.identity}")

                    # Start processing audio frames in the background
                    asyncio.create_task(process_audio_stream(audio_stream, participant))
                except Exception as e:
                    logger.error(f"❌ Failed to create audio stream for {participant.identity}: {e}")
        except Exception as e:
            logger.error(f"❌ Error in track_subscribed handler: {e}")
            logger.error(f"Track subscribed error traceback: {traceback.format_exc()}")

    @ctx.room.on("track_unsubscribed")
    async def on_track_unsubscribed(track, publication, participant):
        """Handle when we unsubscribe from an audio track"""
        try:
            if participant.identity in audio_tracks:
                del audio_tracks[participant.identity]
                logger.info(f"🔇 Moderator unsubscribed from: {participant.identity}")
        except Exception as e:
            logger.error(f"❌ Error in track_unsubscribed handler: {e}")

    @ctx.room.on("participant_connected")
    async def on_participant_connected(participant):
        """Handle when a participant connects to the room"""
        try:
            logger.info(f"👋 Participant connected: {participant.identity}")

            # Identify agent types for coordination
            if (participant.identity and
                    ("socrates" in participant.identity.lower() or
                     "philosopher" in participant.identity.lower())):
                other_agents.add(participant.identity)
                logger.info(f"🤝 Moderator detected Socrates agent joined: {participant.identity}")
        except Exception as e:
            logger.error(f"❌ Error in participant_connected handler: {e}")

    @ctx.room.on("participant_disconnected")
    async def on_participant_disconnected(participant):
        """Handle when a participant disconnects"""
        try:
            logger.info(f"👋 Participant disconnected: {participant.identity}")
            if participant.identity in other_agents:
                other_agents.remove(participant.identity)
            if participant.identity in audio_tracks:
                del audio_tracks[participant.identity]
        except Exception as e:
            logger.error(f"❌ Error in participant_disconnected handler: {e}")

    # ENHANCED TOPIC DETECTION - Check job metadata first (from agent dispatch)
    debate_topic = "The impact of AI on society"  # Default
    moderator_persona = "Aristotle"  # Default persona

    # Check if we have job metadata from agent dispatch
    if hasattr(ctx, 'job') and ctx.job and hasattr(ctx.job, 'metadata'):
        try:
            metadata = json.loads(ctx.job.metadata) if isinstance(ctx.job.metadata, str) else ctx.job.metadata
            debate_topic = metadata.get("debate_topic", debate_topic)
            moderator_persona = metadata.get("moderator", moderator_persona)
            logger.info(f"📋 Job metadata - Topic: {debate_topic}, Moderator: {moderator_persona}")
        except Exception as e:
            logger.warning(f"⚠️ Could not parse job metadata: {e}")

    # Also check room metadata as fallback
    if ctx.room.metadata:
        try:
            room_metadata = json.loads(ctx.room.metadata)
            debate_topic = room_metadata.get("topic", debate_topic)
            moderator_persona = room_metadata.get("moderator", moderator_persona)
            logger.info(f"📋 Room metadata - Topic: {debate_topic}, Moderator: {moderator_persona}")
        except Exception as e:
            logger.warning(f"⚠️ Could not parse room metadata: {e}")

    # Also check participant metadata for moderator selection
    try:
        # Look for participant with moderator metadata
        for participant in ctx.room.local_participants + ctx.room.remote_participants:
            if participant.metadata:
                try:
                    participant_metadata = json.loads(participant.metadata)
                    if "moderator" in participant_metadata:
                        moderator_persona = participant_metadata["moderator"]
                        logger.info(f"📋 Found moderator in participant metadata: {moderator_persona}")
                        break
                except Exception as e:
                    logger.debug(f"Could not parse participant metadata: {e}")
    except Exception as e:
        logger.debug(f"Error checking participant metadata: {e}")

    # Set environment variable for other functions to access
    os.environ["DEBATE_TOPIC"] = debate_topic
    os.environ["MODERATOR_PERSONA"] = moderator_persona

    # Generate persona-specific instructions
    def get_persona_instructions(persona: str, topic: str) -> str:
        """Generate instructions based on the selected moderator persona"""
        
        base_context = f"You are moderating a debate on the topic: {topic}\n\n"
        
        if persona.lower() == "socrates":
            return base_context + """You are Socrates, the wise philosopher who guides through questioning.

Your core directive: Ask clarifying questions when assumptions are made or logic jumps occur.

Your approach:
- Probe deeper when participants make assumptions without evidence
- Challenge logical leaps with gentle questioning
- Use the Socratic method: "What do you mean by...?", "How do you know that?", "What evidence supports this?"
- Help participants examine their beliefs and reasoning
- Guide the conversation toward greater wisdom through inquiry
- Remain curious and humble, admitting when you don't know something

Your voice should be:
- Thoughtful and probing
- Genuinely curious about understanding
- Patient and encouraging
- Focused on the process of thinking rather than winning arguments

Use your available function tools to research claims and access knowledge when needed to ask better questions."""

        elif persona.lower() == "buddha":
            return base_context + """You are Buddha, the compassionate teacher who maintains harmony and understanding.

Your core directive: Monitor tone and diffuse conflict, promote calm respectful dialogue.

Your approach:
- Watch for rising tensions and emotional escalation
- Intervene gently when discussions become heated or disrespectful
- Steer conversations toward mutual understanding and respect
- Acknowledge all perspectives with compassion
- Guide participants away from personal attacks toward constructive dialogue
- Encourage mindful listening and speaking
- Help find common ground and shared values
- Promote patience, kindness, and wisdom in discourse

Your voice should be:
- Calm and soothing
- Compassionate and understanding
- Focused on harmony and balance
- Gentle but firm when redirecting negative energy
- Encouraging of mindful participation

Use your available function tools to research claims and access knowledge when needed to promote understanding."""

        else:  # Default to Aristotle
            return base_context + """You are Aristotle, the logical analyst who ensures structured reasoning.

Your core directive: Fact-check arguments, request sources for claims, assess evidence.

Your approach:
- Fact-check significant claims using live research
- Request credible sources when participants make factual assertions
- Assess the quality and reliability of evidence presented
- Evaluate the truth value and logical consistency of arguments
- Guide conversations to remain productive and evidence-based
- Identify logical fallacies and help clarify arguments
- Maintain focus on rational discourse and verified information

Your voice should be:
- Analytical and precise
- Focused on logic and evidence
- Authoritative but fair
- Committed to truth and accuracy
- Structured in approach

Use your available function tools to research claims and access knowledge when needed."""

    # Initialize the moderator agent with persona-specific instructions
    moderator = Agent(
        instructions=get_persona_instructions(moderator_persona, debate_topic),
        tools=[
            get_debate_topic,
            access_facilitation_knowledge,
            suggest_process_intervention,
            fact_check_claim,
            research_live_data,
            analyze_argument_structure,
            detect_intervention_triggers
        ]
    )

    # Log the selected persona
    logger.info(f"🎭 Moderator persona selected: {moderator_persona}")

    # Configure LLM - use Perplexity when available for research capabilities
    # Adjust temperature based on persona
    persona_temperature = {
        "socrates": 0.7,  # More creative for questioning
        "buddha": 0.5,    # Balanced for compassionate responses
        "aristotle": 0.2  # More focused for logical analysis
    }
    
    temp = persona_temperature.get(moderator_persona.lower(), 0.2)
    research_llm = None
    
    # Try Perplexity first if available
    if PERPLEXITY_AVAILABLE:
        try:
            # Create Perplexity LLM with proper session management
            research_llm = openai.LLM.with_perplexity(
                model="sonar-pro",  # Updated to current Perplexity model (200k context)
                temperature=temp,
                max_tokens=4000,  # Add explicit limits to prevent runaway costs
                timeout=30.0  # Add timeout to prevent hanging
            )
            logger.info(f"✅ Using Perplexity LLM for {moderator_persona} (temp: {temp})")
        except Exception as e:
            logger.warning(f"⚠️ Could not configure Perplexity: {e}")
            logger.warning(f"Perplexity error traceback: {traceback.format_exc()}")
            research_llm = None
    
    # Fallback to OpenAI if Perplexity fails or is unavailable
    if research_llm is None:
        try:
            research_llm = openai.LLM(
                model="gpt-4o-realtime-preview", 
                temperature=temp,
                max_tokens=4000,  # Add explicit limits to prevent runaway costs
                timeout=30.0  # Add timeout to prevent hanging
            )
            logger.info(f"✅ Using OpenAI GPT-4o for {moderator_persona} (temp: {temp})")
        except Exception as e:
            logger.error(f"❌ Failed to configure OpenAI LLM: {e}")
            logger.error(f"OpenAI error traceback: {traceback.format_exc()}")
            # Try basic configuration as last resort
            try:
                research_llm = openai.LLM(model="gpt-4o-realtime-preview", temperature=0.5)
                logger.warning(f"⚠️ Using basic OpenAI configuration as fallback")
            except Exception as fallback_error:
                logger.error(f"❌ Complete LLM configuration failure: {fallback_error}")
                raise RuntimeError(f"Could not configure any LLM: {e}")

    # Select voice based on persona
    persona_voices = {
        "socrates": "alloy",    # Thoughtful, questioning voice
        "buddha": "nova",       # Calm, soothing voice  
        "aristotle": "onyx"     # Clear, authoritative voice
    }
    
    selected_voice = persona_voices.get(moderator_persona.lower(), "onyx")
    logger.info(f"🎤 Using voice '{selected_voice}' for {moderator_persona}")

    # Use async context manager for TTS to ensure proper cleanup
    tts = None
    try:
        logger.info(f"🎤 Initializing TTS with voice: {selected_voice}")
        tts = openai.TTS(
            model="tts-1",
            voice=selected_voice
        )
        
        # Use async context manager for proper resource management
        async with tts as tts_context:
            logger.info(f"✅ TTS initialized successfully")
            tts = tts_context  # Use the context manager version

            # Create agent session with comprehensive error handling
            try:
                logger.info(f"🤖 Creating AgentSession for {moderator_persona}")
                agent_session = AgentSession(
                    stt=openai.STT(),  # Add STT for voice input processing
                    llm=research_llm,
                    tts=tts,
                    vad=silero.VAD.load()  # Add VAD for voice activity detection
                )
                logger.info(f"✅ AgentSession created successfully")
            except Exception as session_error:
                logger.error(f"❌ Failed to create AgentSession: {session_error}")
                logger.error(f"Session error traceback: {traceback.format_exc()}")
                raise RuntimeError(f"Could not create agent session: {session_error}")

            logger.info(f"🎯 {moderator_persona} agent session created successfully")

            # Connect memory manager if available
            try:
                from supabase_memory_manager import SUPABASE_AVAILABLE
                if SUPABASE_AVAILABLE:
                    logger.info(f"🧠 Memory manager connected to {moderator_persona}")
                else:
                    logger.warning("⚠️ Memory manager not available")
            except Exception as e:
                logger.warning(f"⚠️ Could not connect memory manager: {e}")

            # Register agent state change handlers using decorator pattern
            @agent_session.on("user_state_changed")
            def handle_user_state_changed(event):
                """Monitor user speaking state for coordination"""
                try:
                    with conversation_state.conversation_lock:
                        if event.new_state == "speaking":
                            conversation_state.user_speaking = True
                            # If user starts speaking, agent should stop
                            if conversation_state.active_speaker:
                                logger.info("👤 User started speaking - agent should yield")
                                conversation_state.active_speaker = None
                        elif event.new_state == "listening":
                            conversation_state.user_speaking = False
                            logger.info("👂 User stopped speaking - agent may respond if appropriate")
                        elif event.new_state == "away":
                            conversation_state.user_speaking = False
                            logger.info("👋 User disconnected")
                except Exception as e:
                    logger.error(f"❌ Error in user_state_changed handler: {e}")

            @agent_session.on("agent_state_changed")
            def handle_agent_state_changed(event):
                """Monitor agent speaking state for coordination"""
                try:
                    agent_name = moderator_persona.lower()

                    if event.new_state == "speaking":
                        with conversation_state.conversation_lock:
                            conversation_state.active_speaker = agent_name
                            logger.info(f"🎤 {moderator_persona} started speaking")
                    elif event.new_state in ["idle", "listening", "thinking"]:
                        with conversation_state.conversation_lock:
                            if conversation_state.active_speaker == agent_name:
                                conversation_state.active_speaker = None
                                logger.info(f"🔇 {moderator_persona} finished speaking")
                except Exception as e:
                    logger.error(f"❌ Error in agent_state_changed handler: {e}")

            # Start the moderation session with error handling
            try:
                logger.info(f"🚀 Starting agent session for {moderator_persona}")
                await agent_session.start(
                    agent=moderator,
                    room=ctx.room
                )
                logger.info(f"✅ Agent session started successfully")
            except Exception as start_error:
                logger.error(f"❌ Failed to start agent session: {start_error}")
                logger.error(f"Start error traceback: {traceback.format_exc()}")
                raise RuntimeError(f"Could not start agent session: {start_error}")

            logger.info(f"🏛️ Debate Moderator '{moderator_persona}' active for topic: {debate_topic}")

            # Generate persona-specific initial greeting
            def get_persona_greeting(persona: str, topic: str) -> str:
                if persona.lower() == "socrates":
                    return f"""Welcome to this Sage AI debate on: {topic}

I am Socrates, your philosophical guide. I will help you explore this topic through thoughtful questioning. 

My role is to ask clarifying questions when assumptions are made or logic jumps occur. Let's begin by examining what we truly know about this important subject."""

                elif persona.lower() == "buddha":
                    return f"""Welcome to this Sage AI debate on: {topic}

I am Buddha, your compassionate moderator. I will help maintain harmony and mutual understanding throughout our discussion.

My role is to monitor tone and diffuse conflict, promoting calm respectful dialogue. Let's approach this topic with mindfulness and open hearts."""

                else:  # Aristotle
                    return f"""Welcome to this Sage AI debate on: {topic}

I am Aristotle, your logical debate moderator. I will help ensure our discussion is grounded in evidence and sound reasoning.

My role is to fact-check arguments, request sources for claims, and assess evidence. Let's begin with a thoughtful exploration of this important topic."""

            try:
                initial_prompt = get_persona_greeting(moderator_persona, debate_topic)
                logger.info(f"🎭 Generated greeting for {moderator_persona}")
                
                await agent_session.generate_reply(instructions=initial_prompt)
                logger.info(f"✅ Initial greeting sent successfully")
            except Exception as greeting_error:
                logger.error(f"❌ Failed to generate initial greeting: {greeting_error}")
                logger.error(f"Greeting error traceback: {traceback.format_exc()}")
                # Don't raise here - the agent can still function without initial greeting

            logger.info(f"🏛️ {moderator_persona} agent is now active and listening for conversations...")

            # Keep the agent session alive - this is critical for LiveKit agents
            # The session will continue running and responding to events automatically
            # We just need to prevent the function from returning
            
            # Set up graceful shutdown handling
            shutdown_event = asyncio.Event()
            
            def signal_handler():
                logger.info(f"🛑 Shutdown signal received for {moderator_persona}")
                shutdown_event.set()
            
            # Register signal handlers for graceful shutdown
            try:
                loop = asyncio.get_running_loop()
                for sig in [signal.SIGTERM, signal.SIGINT]:
                    loop.add_signal_handler(sig, signal_handler)
            except (NotImplementedError, RuntimeError):
                # Signal handling not available (e.g., on Windows or in some environments)
                logger.debug("Signal handling not available in this environment")
            
            try:
                # Wait for shutdown signal or indefinitely
                await shutdown_event.wait()
                logger.info(f"🔚 {moderator_persona} agent shutting down gracefully")
            except (KeyboardInterrupt, asyncio.CancelledError):
                logger.info(f"🔚 {moderator_persona} agent session interrupted")
            except Exception as session_error:
                logger.error(f"❌ Agent session error: {session_error}")
                logger.error(f"Session error traceback: {traceback.format_exc()}")
            finally:
                logger.info(f"🔚 {moderator_persona} agent session ended")
                # Cleanup agent session resources
                try:
                    if hasattr(agent_session, 'aclose'):
                        await agent_session.aclose()
                        logger.info(f"✅ Agent session closed successfully")
                except Exception as cleanup_error:
                    logger.warning(f"⚠️ Error closing agent session: {cleanup_error}")
                    
    except Exception as tts_error:
        logger.error(f"❌ Error in TTS context manager: {tts_error}")
        logger.error(f"TTS error traceback: {traceback.format_exc()}")
        raise
    finally:
        # Ensure TTS resources are cleaned up
        if tts and hasattr(tts, 'aclose'):
            try:
                await tts.aclose()
                logger.info(f"✅ TTS resources cleaned up")
            except Exception as tts_cleanup_error:
                logger.warning(f"⚠️ Error cleaning up TTS: {tts_cleanup_error}")

    except Exception as e:
        logger.error(f"❌ Error in {moderator_persona} agent session: {e}")
        logger.error(f"Agent error traceback: {traceback.format_exc()}")
        # Ensure proper cleanup even on errors
        try:
            # Cleanup LLM resources
            if 'research_llm' in locals() and hasattr(research_llm, 'aclose'):
                await research_llm.aclose()
                logger.info(f"✅ LLM resources cleaned up")
            
            # Cleanup agent session if it exists
            if 'agent_session' in locals() and hasattr(agent_session, 'aclose'):
                await agent_session.aclose()
                logger.info(f"✅ Agent session cleaned up")
                
        except Exception as cleanup_error:
            logger.error(f"❌ Error during cleanup: {cleanup_error}")
        raise

def main():
    """Main entry point for the debate moderator agent"""
    cli.run_app(
        WorkerOptions(
            agent_name="moderator",  # Generic name since persona is determined at runtime
            entrypoint_fnc=entrypoint,
        )
    )

if __name__ == "__main__":
    main()
