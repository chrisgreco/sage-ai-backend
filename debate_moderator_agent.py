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
    from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, cli, function_tool
    from livekit.plugins import openai, silero
    from livekit.agents import UserStateChangedEvent, AgentStateChangedEvent
    from livekit import rtc  # For audio track handling
    logger.info("✅ LiveKit Agents successfully imported")
except ImportError as e:
    logger.error(f"❌ Failed to import LiveKit Agents: {e}")
    sys.exit(1)

# Check if knowledge system is available
KNOWLEDGE_AVAILABLE = False
try:
    import chromadb
    KNOWLEDGE_AVAILABLE = True
    logger.info("✅ Knowledge system available")
except ImportError:
    logger.warning("⚠️ ChromaDB not available - knowledge system disabled")

# Check if Perplexity is available
PERPLEXITY_AVAILABLE = bool(os.environ.get("PERPLEXITY_API_KEY"))
if PERPLEXITY_AVAILABLE:
    logger.info("✅ Perplexity research available")
else:
    logger.warning("⚠️ Perplexity API key not found - research features disabled")

def get_aristotle_knowledge_manager():
    """Get or create Aristotle's knowledge manager"""
    if not KNOWLEDGE_AVAILABLE:
        return None
    # Implementation would go here
    return None

async def get_agent_knowledge(agent_name, query, max_items=3):
    """Simple knowledge retrieval using file-based storage"""
    try:
        knowledge_file = f"knowledge/{agent_name}_knowledge.json"
        if os.path.exists(knowledge_file):
            with open(knowledge_file, 'r') as f:
                knowledge_data = json.load(f)
                # Simple search - in production, use vector similarity
                relevant_items = []
                for item in knowledge_data.get('items', []):
                    if any(word.lower() in item.get('content', '').lower() for word in query.split()):
                        relevant_items.append(item)
                        if len(relevant_items) >= max_items:
                            break
                return relevant_items
        return []
    except Exception as e:
        logger.error(f"Knowledge retrieval error: {e}")
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
    if not KNOWLEDGE_AVAILABLE:
        return {"knowledge": "Knowledge system not available", "sources": []}
        
    try:
        # Query parliamentary and facilitation knowledge
        knowledge_items = await get_agent_knowledge("aristotle", query, max_items=3)
        
        if knowledge_items:
            knowledge_text = "\n\n".join([
                f"Source: {item['source']}\n{item['content'][:400]}..." 
                for item in knowledge_items
            ])
            return {
                "knowledge": knowledge_text,
                "sources": [item['source'] for item in knowledge_items]
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
    """Fact-check statistical claims or verify information using Perplexity research
    
    Args:
        claim: The factual claim or statistic to verify
        source_requested: Whether the user specifically asked for fact-checking
    """
    if not PERPLEXITY_AVAILABLE:
        return {"fact_check": "Research system not available for fact-checking", "confidence": "low"}
        
    try:
        # Use LiveKit's Perplexity integration for research
        from livekit.plugins import openai
        import os
        
        # Get API key from environment
        api_key = os.environ.get("PERPLEXITY_API_KEY")
        if not api_key:
            raise ValueError("PERPLEXITY_API_KEY environment variable is required")
        
        # Create Perplexity LLM instance using LiveKit's proper integration
        perplexity_llm = openai.LLM.with_perplexity(
            model="sonar",
            temperature=0.2,  # Low temperature for factual accuracy
            api_key=api_key  # Explicitly pass the API key
        )
        
        # Format research prompt for fact-checking
        research_prompt = f"""As Aristotle, fact-check this claim with maximum brevity:

CLAIM: {claim}

Provide ONLY:
1. A direct correction in 1-2 sentences maximum
2. The accurate fact/statistic with current data
3. Authoritative source

Format: "Actually, [correct fact] according to [source]."

BE EXTREMELY CONCISE - no explanations or elaboration."""

        # Make the research request using LiveKit's Perplexity integration
        from livekit.agents.llm import ChatContext
        
        chat_ctx = ChatContext()
        chat_ctx.add_message(
            role="user", 
            content=research_prompt
        )
        
        stream = perplexity_llm.chat(chat_ctx=chat_ctx)
        
        # Collect the response from the stream
        response_chunks = []
        async for chunk in stream:
            if hasattr(chunk, 'delta') and chunk.delta and chunk.delta.content:
                response_chunks.append(chunk.delta.content)
        
        fact_check_result = ''.join(response_chunks) if response_chunks else "Unable to verify claim"
        
        return {
            "fact_check": fact_check_result,
            "confidence": "high",
            "source": "Perplexity AI with current data"
        }
        
    except Exception as e:
        logger.error(f"Fact-checking error: {e}")
        return {"error": f"Fact-checking failed: {str(e)}"}

@function_tool
async def research_live_data(context, query: str, research_type: str = "general"):
    """Access live research and current data using Perplexity AI
    
    Args:
        query: The research question or topic to investigate
        research_type: Type of research (general, statistical, current_events, etc.)
    """
    if not PERPLEXITY_AVAILABLE:
        return {"research": "Live research system not available", "confidence": "low"}
        
    try:
        # Format research prompt based on type
        if research_type == "statistical":
            research_prompt = f"""Provide current statistics and data for: {query}

Include:
1. Latest available statistics
2. Authoritative sources (government, academic, industry)
3. Date of data collection

BE CONCISE but thorough with sources."""
        elif research_type == "current_events":
            research_prompt = f"""Provide current information and recent developments on: {query}

Include:
1. Latest developments (within last 6 months)
2. Key facts and data
3. Reliable news sources

BE CURRENT and fact-focused."""
        else:
            research_prompt = f"""Provide comprehensive, current information on: {query}

Include:
1. Key facts and current data
2. Multiple authoritative sources
3. Recent developments if relevant

BE FACTUAL and well-sourced."""
        
        # Use LiveKit's Perplexity integration properly 
        # Create a standalone Perplexity LLM instance for research
        from livekit.plugins import openai
        from livekit.agents.llm import ChatContext
        import os
        
        # Get API key from environment
        api_key = os.environ.get("PERPLEXITY_API_KEY")
        if not api_key:
            raise ValueError("PERPLEXITY_API_KEY environment variable is required")
        
        perplexity_llm = openai.LLM.with_perplexity(
            model="sonar",
            temperature=0.3,
            api_key=api_key  # Explicitly pass the API key
        )
        
        # Make the research request
        chat_ctx = ChatContext()
        chat_ctx.add_message(
            role="user", 
            content=research_prompt
        )
        
        stream = perplexity_llm.chat(chat_ctx=chat_ctx)
        
        # Collect the response from the stream
        response_chunks = []
        async for chunk in stream:
            if hasattr(chunk, 'delta') and chunk.delta and chunk.delta.content:
                response_chunks.append(chunk.delta.content)
        
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
    # ENHANCED: Connect with auto_subscribe=True to hear all participants including other agents
    await ctx.connect(auto_subscribe=True)
    
    # ENHANCED: Set up audio track monitoring for inter-agent coordination
    audio_tracks = {}  # Track audio sources from other participants
    other_agents = set()  # Track other agent identities
    
    def on_track_subscribed(track, publication, participant):
        """Handle when we subscribe to an audio track from another participant"""
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
    
    # Initialize the moderator agent
    moderator = DebateModeratorAgent()
    
    # Configure LLM - use Perplexity when available for research capabilities
    if PERPLEXITY_AVAILABLE:
        try:
            research_llm = openai.LLM.with_perplexity(
                model="sonar",
                temperature=0.7  # Balanced for both personas
            )
            logger.info("✅ Using Perplexity LLM for Aristotle")
        except Exception as e:
            logger.warning(f"⚠️ Could not configure Perplexity, using realtime model: {e}")
            research_llm = openai.LLM(model="gpt-4o-realtime-preview", temperature=0.7)
    else:
        research_llm = openai.LLM(model="gpt-4o-realtime-preview", temperature=0.7)
    
    # Configure TTS
    tts = silero.TTS(
        model="v3_en",
        speaker="en_117"  # Clear, authoritative voice for Aristotle
    )
    
    # Create agent session
    agent_session = AgentSession(
        chat_ctx=openai.ChatContext(),
        fnc_ctx=openai.FunctionContext(),
        llm=research_llm,
        tts=tts
    )
    
    # Add function tools
    agent_session.fnc_ctx.add_function(get_debate_topic)
    agent_session.fnc_ctx.add_function(access_facilitation_knowledge)
    agent_session.fnc_ctx.add_function(suggest_process_intervention)
    agent_session.fnc_ctx.add_function(fact_check_claim)
    agent_session.fnc_ctx.add_function(research_live_data)
    agent_session.fnc_ctx.add_function(analyze_argument_structure)
    agent_session.fnc_ctx.add_function(detect_intervention_triggers)
    
    # Enhanced system prompt with coordination awareness
    system_prompt = f"""You are Aristotle, the logical analyst and debate moderator for the Sage AI system. You are participating in a debate about: "{debate_topic}"

COORDINATION AWARENESS:
- You are working WITH Socrates (the philosophical questioner) in the same room
- You can hear Socrates and should coordinate responses, not compete
- Let Socrates ask probing questions while you provide structure and analysis
- Don't repeat what Socrates just said - build on it or provide different perspective

CORE IDENTITY - ARISTOTLE:
- **Logical Structure**: You excel at organizing thoughts, identifying premises, and ensuring coherent argumentation
- **Analytical Precision**: You break down complex ideas into clear, logical components
- **Moderate Firmly**: You guide discussions with clear structure while remaining fair
- **Fact-Based**: You prioritize evidence, data, and logical consistency
- **Systematic Approach**: You help organize the debate flow and ensure all sides are heard

MODERATION STYLE:
- **Structure First**: "Let's organize this discussion around three key points..."
- **Logical Analysis**: "The argument structure here is... the premises are..."
- **Evidence Focus**: "What evidence supports this position?"
- **Fair Process**: Ensure balanced participation and logical progression
- **Synthesis**: Help synthesize different viewpoints into coherent frameworks

COMMUNICATION STYLE:
- **BE EXTREMELY CONCISE**: 1-2 sentences maximum unless asked for detail
- **IDENTIFY YOURSELF**: Start with "As Aristotle..." when speaking
- **COORDINATE WITH SOCRATES**: Don't interrupt or compete - complement his questioning
- **STRUCTURE RESPONSES**: Use clear, logical organization

AVAILABLE TOOLS:
- Access specialized knowledge about facilitation and parliamentary procedure
- Fact-check claims using live research
- Analyze argument structure using logical frameworks
- Suggest process interventions for challenging situations
- Detect when moderation intervention is needed

Remember: You work WITH Socrates as a team. He asks probing questions, you provide logical structure and analysis. Together you facilitate meaningful dialogue."""

    agent_session.chat_ctx.add_message(
        role="system",
        content=system_prompt
    )
    
    logger.info("🏛️ Aristotle (Debate Moderator) ready for philosophical discourse")
    logger.info(f"📋 Debate topic: {debate_topic}")
    logger.info(f"🎭 Agent role: {agent_role}")
    logger.info(f"🔊 Audio coordination enabled - can hear {len(audio_tracks)} participants")
    
    # User state change handler
    def on_user_state_changed(ev: UserStateChangedEvent):
        """Handle user speaking state changes for coordination"""
        if ev.state == "speaking":
            with conversation_state.conversation_lock:
                conversation_state.user_speaking = True
                logger.info("👤 User started speaking - agents will listen")
        elif ev.state == "not_speaking":
            with conversation_state.conversation_lock:
                conversation_state.user_speaking = False
                logger.info("👤 User stopped speaking - agents can respond")
    
    # Agent state change handler  
    def on_agent_state_changed(ev: AgentStateChangedEvent):
        """Handle agent state changes for coordination"""
        if ev.state == "speaking":
            logger.info(f"🎤 Agent started speaking: {ev.agent_participant.identity}")
        elif ev.state == "listening":
            logger.info(f"👂 Agent listening: {ev.agent_participant.identity}")
    
    # Register state change handlers
    agent_session.on("user_state_changed", on_user_state_changed)
    agent_session.on("agent_state_changed", on_agent_state_changed)
    
    # Start the agent session
    await agent_session.start(ctx.room)

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