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
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import Optional

# Load environment variables first
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
    topic = os.getenv("DEBATE_TOPIC", "The impact of AI on society")
    return f"Current debate topic: {topic}"

@function_tool
async def access_facilitation_knowledge(context, query: str):
    """Access specialized knowledge about facilitation and parliamentary procedure

    Args:
        query: Question about moderation techniques, parliamentary procedure, or facilitation
    """
    try:
        # Query parliamentary and facilitation knowledge using updated system
        knowledge_items = await get_agent_knowledge("aristotle", query, max_items=3)

        if knowledge_items:
            knowledge_text = "\n\n".join([
                f"Source: {item['title']} ({item['source']})\n{item['content'][:400]}..."
                for item in knowledge_items
            ])
            return {
                "knowledge": knowledge_text,
                "sources": [f"{item['title']} ({item['source']})" for item in knowledge_items],
                "relevance_scores": [item.get('relevance_score', 0.0) for item in knowledge_items]
            }
        else:
            return {"knowledge": "No relevant facilitation knowledge found", "sources": []}

    except Exception as e:
        logger.error(f"Knowledge access error: {e}")
        return {"error": f"Knowledge access failed: {str(e)}"}

@function_tool
async def suggest_process_intervention(context, situation: str):
    """Suggest moderation techniques for challenging situations

    Args:
        situation: Description of the current discussion dynamic or challenge
    """
    interventions = {
        "dominating_speaker": ("Try: 'Thank you [Name]. Let's hear from someone who hasn't "
                               "spoken yet on this point.'"),
        "off_topic": ("Try: 'That's an interesting point. How does it connect to our main "
                      "question about [topic]?'"),
        "personal_attack": ("Try: 'Let's focus on the ideas rather than personal "
                            "characterizations. What specifically about that position concerns you?'"),
        "silence": "Try: 'I'm sensing some reflection time. [Name], what questions is this raising for you?'",
        "confusion": ("Try: 'Let me see if I can summarize what I'm hearing... "
                      "Does that capture the key points?'"),
        "polarization": ("Try: 'I'm hearing some different values here. Are there any shared "
                         "concerns we might build on?'")
    }

    # Simple keyword matching for demonstration
    for key, suggestion in interventions.items():
        if key.replace("_", " ") in situation.lower():
            return f"Moderation suggestion: {suggestion}"

    return ("Consider asking an open-ended question to refocus the conversation, "
            "or invite participation from a different perspective.")

@function_tool
async def fact_check_claim(context, claim: str, source_requested: bool = False):
    """Fact-check a claim using live research and current data

    Args:
        claim: The claim to be fact-checked
        source_requested: Whether to provide detailed source information
    """
    if not PERPLEXITY_AVAILABLE:
        return {"fact_check": "Live fact-checking system not available", "confidence": "low"}

    try:
        # Format fact-checking prompt
        research_prompt = f"""Fact-check this claim: {claim}

Please provide:
1. Whether the claim is TRUE, FALSE, PARTIALLY TRUE, or UNVERIFIABLE
2. Key evidence supporting or refuting the claim
3. Authoritative sources (if available)
4. Date of latest relevant information

BE FACTUAL and cite sources when possible."""

        # Use async context manager for proper resource cleanup
        async with openai.LLM.with_perplexity(
            model="sonar-pro",
            temperature=0.1
        ) as perplexity_llm:
            # Create chat context with correct import
            from livekit.plugins.openai.llm import ChatContext
            chat_ctx = ChatContext()
            chat_ctx.add_message(role="user", content=research_prompt)

            # Make the research request
            stream = perplexity_llm.chat(chat_ctx=chat_ctx)

            # Collect the response from the stream
            response_chunks = []
            async for chunk in stream:
                if hasattr(chunk, 'choices') and chunk.choices:
                    for choice in chunk.choices:
                        if hasattr(choice, 'delta') and choice.delta and choice.delta.content:
                            response_chunks.append(choice.delta.content)

            fact_check_result = ''.join(response_chunks) if response_chunks else "Unable to complete fact-check"

        return {
            "fact_check": fact_check_result,
            "confidence": "high",
            "source": "Perplexity AI with current data",
            "sources_provided": source_requested
        }

    except Exception as e:
        logger.error(f"Fact-check error: {e}")
        return {"error": f"Fact-checking failed: {str(e)}"}

@function_tool
async def research_live_data(context, query: str, research_type: str = "general"):
    """Research live data and current information using Perplexity

    Args:
        query: The research query
        research_type: Type of research (general, academic, news, technical)
    """
    if not PERPLEXITY_AVAILABLE:
        return {"research": "Live research system not available", "confidence": "low"}

    try:
        # Format research prompt based on type
        if research_type == "academic":
            research_prompt = (f"Research this topic with academic sources: {query}\n"
                               "Provide scholarly perspective with citations.")
        elif research_type == "news":
            research_prompt = (f"Find recent news and current developments about: {query}\n"
                               "Focus on latest events and trends.")
        elif research_type == "technical":
            research_prompt = (f"Provide technical analysis and expert insights on: {query}\n"
                               "Include technical details and specifications.")
        else:
            research_prompt = (f"Research comprehensive information about: {query}\n"
                               "Provide current, accurate information with sources.")

        # Use async context manager for proper resource cleanup
        async with openai.LLM.with_perplexity(
            model="sonar-pro",
            temperature=0.2
        ) as perplexity_llm:
            # Create chat context with correct import
            from livekit.plugins.openai.llm import ChatContext
            chat_ctx = ChatContext()
            chat_ctx.add_message(role="user", content=research_prompt)

            # Make the research request
            stream = perplexity_llm.chat(chat_ctx=chat_ctx)

            # Collect the response from the stream
            response_chunks = []
            async for chunk in stream:
                if hasattr(chunk, 'choices') and chunk.choices:
                    for choice in chunk.choices:
                        if hasattr(choice, 'delta') and choice.delta and choice.delta.content:
                            response_chunks.append(choice.delta.content)

            research_result = ''.join(response_chunks) if response_chunks else "Unable to complete research"

        return {
            "research": research_result,
            "confidence": "high",
            "source": "Perplexity AI with current data"
        }

    except Exception as e:
        logger.error(f"Research error: {e}")
        return {"error": f"Research failed: {str(e)}"}

@function_tool
async def analyze_argument_structure(context, argument: str):
    """Analyze the logical structure of an argument using Aristotelian logic

    Args:
        argument: The argument text to analyze
    """
    # Simple structural analysis - in production, use more sophisticated NLP
    analysis = {
        "premises": [],
        "conclusion": "",
        "logical_form": "unknown",
        "validity": "requires_evaluation"
    }

    # Basic pattern matching for demonstration
    sentences = argument.split('.')
    if len(sentences) >= 2:
        analysis["premises"] = sentences[:-1]
        analysis["conclusion"] = sentences[-1]
        analysis["logical_form"] = "syllogistic" if len(sentences) == 3 else "complex"

    return analysis

@function_tool
async def detect_intervention_triggers(context, conversation_snippet: str):
    """Detect when moderator intervention might be needed

    Args:
        conversation_snippet: Recent conversation text to analyze
    """
    triggers = {
        "personal_attack": ["you're wrong", "that's stupid", "you don't understand"],
        "off_topic": ["by the way", "speaking of", "that reminds me"],
        "domination": ["as I was saying", "let me finish", "you need to understand"],
        "confusion": ["I don't get it", "what do you mean", "that doesn't make sense"],
        "silence": ["...", "um", "well"]
    }

    detected = []
    snippet_lower = conversation_snippet.lower()

    for trigger_type, phrases in triggers.items():
        if any(phrase in snippet_lower for phrase in phrases):
            detected.append(trigger_type)

    if detected:
        return {
            "intervention_needed": True,
            "triggers": detected,
            "suggestion": f"Consider addressing: {', '.join(detected)}"
        }
    else:
        return {
            "intervention_needed": False,
            "triggers": [],
            "suggestion": "Conversation flowing well"
        }

async def process_audio_stream(audio_stream, participant):
    """Process audio frames from a participant's audio stream"""
    try:
        logger.info(f"🎵 Starting audio processing for {participant.identity}")
        async for audio_frame in audio_stream:
            # Log that we're receiving audio (but don't spam the logs)
            if hasattr(process_audio_stream, '_frame_count'):
                process_audio_stream._frame_count += 1
            else:
                process_audio_stream._frame_count = 1

            # Log every 100th frame to confirm audio is flowing
            if process_audio_stream._frame_count % 100 == 0:
                logger.debug(f"🎵 Received {process_audio_stream._frame_count} audio frames from {participant.identity}")

            # Here we could process the audio frame if needed
            # For now, the main purpose is to ensure the audio stream is properly subscribed
            # The actual speech processing is handled by the Agent framework's STT

    except Exception as e:
        logger.error(f"❌ Error processing audio stream from {participant.identity}: {e}")
    finally:
        logger.info(f"🎵 Audio processing ended for {participant.identity}")

async def entrypoint(ctx: JobContext):
    """Debate Moderator agent entrypoint - only joins rooms marked for sage debates"""

    logger.info("🏛️ Sage AI Debate Moderator checking room metadata...")
    # ENHANCED: Connect with auto_subscribe to hear all participants including other agents
    await ctx.connect(auto_subscribe=AutoSubscribe.SUBSCRIBE_ALL)

    # ENHANCED: Set up audio track monitoring for inter-agent coordination
    audio_tracks = {}  # Track audio sources from other participants
    other_agents = set()  # Track other agent identities

    # NOTE: Transcription is handled by Socrates agent to avoid duplicates

    def on_track_subscribed(track, publication, participant):
        """Handle when we subscribe to an audio track from another participant"""
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

                # Start processing audio frames in the background (use create_task for async)
                asyncio.create_task(process_audio_stream(audio_stream, participant))
            except Exception as e:
                logger.error(f"❌ Failed to create audio stream for {participant.identity}: {e}")

    def on_track_unsubscribed(track, publication, participant):
        """Handle when we unsubscribe from an audio track"""
        if participant.identity in audio_tracks:
            del audio_tracks[participant.identity]
            logger.info(f"🔇 Moderator unsubscribed from: {participant.identity}")

    def on_participant_connected(participant):
        """Handle when a participant connects to the room"""
        logger.info(f"👋 Participant connected: {participant.identity}")

        # Identify agent types for coordination
        if (participant.identity and
                ("socrates" in participant.identity.lower() or
                 "philosopher" in participant.identity.lower())):
            other_agents.add(participant.identity)
            logger.info(f"🤝 Moderator detected Socrates agent joined: {participant.identity}")

    def on_participant_disconnected(participant):
        """Handle when a participant disconnects"""
        logger.info(f"👋 Participant disconnected: {participant.identity}")
        if participant.identity in other_agents:
            other_agents.remove(participant.identity)
        if participant.identity in audio_tracks:
            del audio_tracks[participant.identity]

    # Register event handlers for audio coordination
    ctx.room.on("track_subscribed", on_track_subscribed)
    ctx.room.on("track_unsubscribed", on_track_unsubscribed)
    ctx.room.on("participant_connected", on_participant_connected)
    ctx.room.on("participant_disconnected", on_participant_disconnected)

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
        "aristotle": 0.2  # Lower for analytical precision
    }
    
    temp = persona_temperature.get(moderator_persona.lower(), 0.5)
    
    if PERPLEXITY_AVAILABLE:
        try:
            research_llm = openai.LLM.with_perplexity(
                model="sonar-pro",  # Updated to current Perplexity model (200k context)
                temperature=temp
            )
            logger.info(f"✅ Using Perplexity LLM for {moderator_persona} (temp: {temp})")
        except Exception as e:
            logger.warning(f"⚠️ Could not configure Perplexity, using realtime model: {e}")
            research_llm = openai.LLM(model="gpt-4o-realtime-preview", temperature=temp)
    else:
        research_llm = openai.LLM(model="gpt-4o-realtime-preview", temperature=temp)

    # Select voice based on persona
    persona_voices = {
        "socrates": "alloy",    # Thoughtful, questioning voice
        "buddha": "nova",       # Calm, soothing voice  
        "aristotle": "onyx"     # Clear, authoritative voice
    }
    
    selected_voice = persona_voices.get(moderator_persona.lower(), "onyx")
    logger.info(f"🎤 Using voice '{selected_voice}' for {moderator_persona}")

    # Use async context manager for TTS to ensure proper cleanup
    try:
        async with openai.TTS(
            model="tts-1",
            voice=selected_voice
        ) as tts:

            # Create agent session with correct LiveKit 1.0 pattern
            agent_session = AgentSession(
                stt=openai.STT(),  # Add STT for voice input processing
                llm=research_llm,
                tts=tts,
                vad=silero.VAD.load()  # Add VAD for voice activity detection
            )

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

            @agent_session.on("agent_state_changed")
            def handle_agent_state_changed(event):
                """Monitor agent speaking state for coordination"""
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

            # Start the moderation session
            await agent_session.start(
                agent=moderator,
                room=ctx.room
            )

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

            initial_prompt = get_persona_greeting(moderator_persona, debate_topic)

            await agent_session.generate_reply(instructions=initial_prompt)

            logger.info(f"🏛️ {moderator_persona} agent is now active and listening for conversations...")

            # Keep the agent session alive - this is critical for LiveKit agents
            # The session will continue running and responding to events automatically
            # We just need to prevent the function from returning
            try:
                # Wait indefinitely - the agent will handle events and responses
                while True:
                    await asyncio.sleep(1.0)
            except (KeyboardInterrupt, asyncio.CancelledError):
                logger.info(f"🔚 {moderator_persona} agent session interrupted")
            except Exception as session_error:
                logger.error(f"❌ Agent session error: {session_error}")
            finally:
                logger.info(f"🔚 {moderator_persona} agent session ended")

    except Exception as e:
        logger.error(f"❌ Error in {moderator_persona} agent session: {e}")
        # Ensure proper cleanup even on errors
        if 'research_llm' in locals() and hasattr(research_llm, 'aclose'):
            try:
                await research_llm.aclose()
            except Exception as cleanup_error:
                logger.error(f"Error during LLM cleanup: {cleanup_error}")
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
