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
from typing import Optional, Dict, List

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
    # NOTE: Transcription handled by Socrates agent to avoid duplicates
    from livekit import rtc  # For audio track handling
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
            from simple_knowledge_manager import SimpleKnowledgeManager
            _knowledge_managers[agent_name] = SimpleKnowledgeManager(agent_name)
            _knowledge_managers[agent_name].load_documents()
            logger.info(f"✅ Loaded knowledge manager for {agent_name}")
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
        "dominating_speaker": "Try: 'Thank you [Name]. Let's hear from someone who hasn't spoken yet on this point.'",
        "off_topic": "Try: 'That's an interesting point. How does it connect to our main question about [topic]?'",
        "personal_attack": "Try: 'Let's focus on the ideas rather than personal characterizations. What specifically about that position concerns you?'",
        "silence": "Try: 'I'm sensing some reflection time. [Name], what questions is this raising for you?'",
        "confusion": "Try: 'Let me see if I can summarize what I'm hearing... Does that capture the key points?'",
        "polarization": "Try: 'I'm hearing some different values here. Are there any shared concerns we might build on?'"
    }
    
    # Simple keyword matching for demonstration
    for key, suggestion in interventions.items():
        if key.replace("_", " ") in situation.lower():
            return f"Moderation suggestion: {suggestion}"
    
    return "Consider asking an open-ended question to refocus the conversation, or invite participation from a different perspective."

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
            research_prompt = f"Research this topic with academic sources: {query}\nProvide scholarly perspective with citations."
        elif research_type == "news":
            research_prompt = f"Find recent news and current developments about: {query}\nFocus on latest events and trends."
        elif research_type == "technical":
            research_prompt = f"Provide technical analysis and expert insights on: {query}\nInclude technical details and specifications."
        else:
            research_prompt = f"Research comprehensive information about: {query}\nProvide current, accurate information with sources."

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
        from livekit import rtc  # Import within function scope
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            logger.info(f"🎧 Aristotle subscribed to audio track from: {participant.identity}")
            
            # Store the audio track for coordination
            audio_tracks[participant.identity] = {
                "track": track,
                "publication": publication,
                "participant": participant
            }
            
            # Identify other agents for coordination
            if participant.identity and ("socrates" in participant.identity.lower() or "philosopher" in participant.identity.lower()):
                other_agents.add(participant.identity)
                logger.info(f"🤝 Aristotle detected Socrates agent: {participant.identity}")
    
    def on_track_unsubscribed(track, publication, participant):
        """Handle when we unsubscribe from an audio track"""
        if participant.identity in audio_tracks:
            del audio_tracks[participant.identity]
            logger.info(f"🔇 Aristotle unsubscribed from: {participant.identity}")
    
    def on_participant_connected(participant):
        """Handle when a participant connects to the room"""
        logger.info(f"👋 Participant connected: {participant.identity}")
        
        # Identify agent types for coordination
        if participant.identity and ("socrates" in participant.identity.lower() or "philosopher" in participant.identity.lower()):
            other_agents.add(participant.identity)
            logger.info(f"🤝 Aristotle detected Socrates agent joined: {participant.identity}")
    
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
    agent_role = "logical_analyst"  # Default
    
    # Check if we have job metadata from agent dispatch
    if hasattr(ctx, 'job') and ctx.job and hasattr(ctx.job, 'metadata'):
        try:
            metadata = json.loads(ctx.job.metadata) if isinstance(ctx.job.metadata, str) else ctx.job.metadata
            debate_topic = metadata.get("debate_topic", debate_topic)
            agent_role = metadata.get("role", agent_role)
            logger.info(f"📋 Job metadata - Topic: {debate_topic}, Role: {agent_role}")
        except Exception as e:
            logger.warning(f"⚠️ Could not parse job metadata: {e}")
    
    # Also check room metadata as fallback
    if ctx.room.metadata:
        try:
            room_metadata = json.loads(ctx.room.metadata)
            debate_topic = room_metadata.get("topic", debate_topic)
            agent_role = room_metadata.get("moderator_role", agent_role)
            logger.info(f"📋 Room metadata - Topic: {debate_topic}, Role: {agent_role}")
        except Exception as e:
            logger.warning(f"⚠️ Could not parse room metadata: {e}")
    
    # Set environment variable for other functions to access
    os.environ["DEBATE_TOPIC"] = debate_topic
    
    # Initialize the moderator agent with function tools - correct LiveKit 1.0 pattern
    moderator = Agent(
        instructions=f"""You are Aristotle, a logical debate moderator for the topic: {debate_topic}
        
You will:
- Ensure structured reasoning and evidence-based discussion
- Fact-check claims when needed using live research
- Guide conversations to remain productive  
- Identify logical fallacies and help clarify arguments
- Coordinate with Socrates (philosophical questioner) agent

Use your available function tools to research claims and access knowledge when needed.""",
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
    
    # Configure LLM - use Perplexity when available for research capabilities
    if PERPLEXITY_AVAILABLE:
        try:
            research_llm = openai.LLM.with_perplexity(
                model="sonar-pro",  # Updated to current Perplexity model (200k context)
                temperature=0.2  # Lower temperature for analytical precision
            )
            logger.info("✅ Using Perplexity LLM for Aristotle")
        except Exception as e:
            logger.warning(f"⚠️ Could not configure Perplexity, using realtime model: {e}")
            research_llm = openai.LLM(model="gpt-4o-realtime-preview", temperature=0.7)
    else:
        research_llm = openai.LLM(model="gpt-4o-realtime-preview", temperature=0.7)
    
    # Use async context manager for TTS to ensure proper cleanup
    try:
        async with openai.TTS(
            model="tts-1",
            voice="onyx"  # Clear, authoritative voice for Aristotle
        ) as tts:
            
            # Create agent session with correct LiveKit 1.0 pattern
            agent_session = AgentSession(
                stt=openai.STT(),  # Add STT for voice input processing
                llm=research_llm,
                tts=tts,
                vad=silero.VAD.load()  # Add VAD for voice activity detection
            )
            
            logger.info("🎯 Aristotle agent session created successfully")
            
            # Connect memory manager if available
            try:
                from supabase_memory_manager import memory_manager, SUPABASE_AVAILABLE
                if SUPABASE_AVAILABLE:
                    logger.info("🧠 Memory manager connected to Aristotle")
                else:
                    logger.warning("⚠️ Memory manager not available")
            except Exception as e:
                logger.warning(f"⚠️ Could not connect memory manager: {e}")
            
            # Set up conversation state monitoring
            def on_user_state_changed(ev: UserStateChangedEvent):
                """Monitor user speaking state for coordination"""
                with conversation_state.conversation_lock:
                    if ev.new_state == "speaking":
                        conversation_state.user_speaking = True
                        # If user starts speaking, both agents should stop
                        if conversation_state.active_speaker:
                            logger.info("👤 User started speaking - agents should yield")
                            conversation_state.active_speaker = None
                    elif ev.new_state == "listening":
                        conversation_state.user_speaking = False
                        logger.info("👂 User stopped speaking - agents may respond if appropriate")
                    elif ev.new_state == "away":
                        conversation_state.user_speaking = False
                        logger.info("👋 User disconnected")

            def on_agent_state_changed(ev: AgentStateChangedEvent):
                """Monitor agent speaking state for coordination"""
                agent_name = "aristotle"
                
                if ev.new_state == "speaking":
                    with conversation_state.conversation_lock:
                        conversation_state.active_speaker = agent_name
                        logger.info(f"🎤 {agent_name.capitalize()} started speaking")
                elif ev.new_state in ["idle", "listening", "thinking"]:
                    with conversation_state.conversation_lock:
                        if conversation_state.active_speaker == agent_name:
                            conversation_state.active_speaker = None
                            logger.info(f"🔇 {agent_name.capitalize()} finished speaking")
            
            # Register agent state change handlers
            agent_session.on("user_state_changed", on_user_state_changed)
            agent_session.on("agent_state_changed", on_agent_state_changed)
            
            # Start the moderation session
            await agent_session.start(
                agent=moderator,
                room=ctx.room
            )
            
            logger.info(f"🏛️ Debate Moderator 'Aristotle' active for topic: {debate_topic}")
            
            # Initial greeting and topic introduction
            initial_prompt = f"""Welcome to this Sage AI debate on: {debate_topic}

I am Aristotle, your logical debate moderator. I will:
- Ensure structured reasoning and evidence-based discussion
- Fact-check claims when needed
- Guide the conversation to remain productive
- Identify logical fallacies and help clarify arguments

Let's begin with a thoughtful exploration of this important topic."""

            await agent_session.generate_reply(instructions=initial_prompt)
            
            logger.info("🏛️ Aristotle agent is now active and listening for conversations...")
            
            # Keep the agent session alive - this is critical for LiveKit agents
            # The session will continue running and responding to events automatically
            # We just need to prevent the function from returning
            try:
                # Wait indefinitely - the agent will handle events and responses
                while True:
                    await asyncio.sleep(1.0)
            except (KeyboardInterrupt, asyncio.CancelledError):
                logger.info("🔚 Aristotle agent session interrupted")
            except Exception as session_error:
                logger.error(f"❌ Agent session error: {session_error}")
            finally:
                logger.info("🔚 Aristotle agent session ended")

    except Exception as e:
        logger.error(f"❌ Error in Aristotle agent session: {e}")
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
            agent_name="aristotle",
            entrypoint_fnc=entrypoint,
        )
    )

if __name__ == "__main__":
    main() 