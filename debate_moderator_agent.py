#!/usr/bin/env python3

"""
Sage AI Debate Moderator Agent - Simple LiveKit Implementation
Handles debate moderation with basic error handling
Updated: Fixed imports for LiveKit Agents 1.0 API compatibility
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# LiveKit Agents imports
try:
    from livekit.agents import JobContext, WorkerOptions, cli, llm, AgentSession, Agent
    from livekit.plugins import openai, silero
    from livekit.agents.llm import function_tool
    logger.info("✅ LiveKit Agents successfully imported")
except ImportError as e:
    logger.error(f"❌ Failed to import LiveKit Agents: {e}")
    sys.exit(1)

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
    """Simple debate moderator agent"""
    
    def __init__(self):
        self.name = "moderator"

    async def check_speaking_permission(self, session) -> bool:
        """Check if agent can speak"""
        with conversation_state.conversation_lock:
            if conversation_state.user_speaking:
                return False
            if conversation_state.active_speaker and conversation_state.active_speaker != self.name:
                return False
            return True

    async def claim_speaking_turn(self):
        """Claim speaking turn"""
        with conversation_state.conversation_lock:
            conversation_state.active_speaker = self.name

    async def release_speaking_turn(self):
        """Release speaking turn"""
        with conversation_state.conversation_lock:
            conversation_state.active_speaker = None

@function_tool
async def get_debate_topic():
    """Get the current debate topic"""
    topic = os.environ.get("DEBATE_TOPIC", "The impact of AI on society")
    logger.info(f"📋 Current debate topic: {topic}")
    return f"The current debate topic is: {topic}"

@function_tool
async def access_facilitation_knowledge(query: str):
    """Access debate facilitation knowledge"""
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

@function_tool
async def suggest_process_intervention(situation: str):
    """Suggest process interventions for debate management"""
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

@function_tool
async def fact_check_claim(claim: str, source_requested: bool = False):
    """Fact-check a claim made during the debate"""
    logger.info(f"🔍 Fact-checking claim: {claim}")
    
    # Simple fact-checking responses
    if source_requested:
        return f"I'd like to verify this claim: '{claim}'. Could you provide a source for this information so we can evaluate its credibility?"
    
    return f"This claim requires verification: '{claim}'. Let's examine the evidence supporting this statement. What sources inform this position?"

@function_tool
async def end_debate():
    """End the current debate session"""
    logger.info("🏁 Ending debate session")
    return "Thank you all for this engaging discussion. Let me provide a brief summary of the key points raised and conclude our session."

@function_tool
async def summarize_discussion():
    """Summarize the key points of the discussion"""
    logger.info("📝 Summarizing discussion")
    return "Let me summarize the main arguments and perspectives we've heard so far in this debate."

def get_persona_greeting(persona: str, topic: str) -> str:
    """Generate a greeting based on the persona and topic"""
    persona_lower = persona.lower()
    
    if persona_lower == "socrates":
        return f"Greetings, friends. I am Socrates. We gather to explore: {topic}. I know that I know nothing, so let us discover truth together through questions. What do you think you know about this topic?"
    elif persona_lower == "buddha":
        return f"Welcome, friends, to this discussion on: {topic}. I am Buddha. Let us approach this topic with compassion, mindfulness, and understanding for all perspectives."
    else:  # Aristotle (default)
        return f"Welcome to this debate on: {topic}. I am Aristotle. I will help ensure our discussion is grounded in evidence, logic, and sound reasoning. Let us begin with clear premises."

async def entrypoint(ctx: JobContext):
    """Main entry point for the LiveKit agent"""
    session = None
    try:
        logger.info("🚀 Starting Sage AI Debate Moderator Agent")
        
        # Connect to the room
        await ctx.connect()
        logger.info(f"✅ Connected to room: {ctx.room.name}")
        
        # Get moderator persona from room metadata
        moderator_persona = "Aristotle"  # Default
        topic = "General Discussion"  # Default
        
        if ctx.room.metadata:
            try:
                metadata = json.loads(ctx.room.metadata)
                moderator_persona = metadata.get("moderator", "Aristotle")
                topic = metadata.get("topic", "General Discussion")
                logger.info(f"📋 Room metadata - Persona: {moderator_persona}, Topic: {topic}")
            except json.JSONDecodeError:
                logger.warning("⚠️ Invalid room metadata JSON, using defaults")
        
        # Create persona-specific system prompt
        def get_persona_system_prompt(persona: str, topic: str) -> str:
            persona_lower = persona.lower()
            
            if persona_lower == "socrates":
                return f"""You are Socrates, the ancient Greek philosopher. You are moderating a debate on: {topic}.

Your approach:
- Ask probing questions to help participants examine their assumptions
- Use the Socratic method - guide people to discover truth through questioning
- Say "I know that I know nothing" - maintain intellectual humility
- Help participants clarify their thinking through gentle inquiry
- When someone makes a claim, ask: "How do you know this?" or "What do you mean by...?"

Keep responses concise and focused on asking the right questions."""
                
            elif persona_lower == "buddha":
                return f"""You are Buddha, the enlightened teacher. You are moderating a discussion on: {topic}.

Your approach:
- Promote compassion, understanding, and mindful dialogue
- Help de-escalate conflicts with wisdom and patience
- Guide participants toward deeper understanding and empathy
- When tensions arise, redirect to common ground and shared humanity
- Speak with gentle authority and profound insight

Keep responses calm, wise, and focused on harmony."""
                
            else:  # Aristotle (default)
                return f"""You are Aristotle, the systematic philosopher. You are moderating a debate on: {topic}.

Your approach:
- Ensure logical reasoning and evidence-based arguments
- Ask for sources and factual support when claims are made
- Help structure the debate with clear premises and conclusions
- Point out logical fallacies when they occur
- Guide toward rational, well-reasoned discourse

Keep responses logical, structured, and focused on evidence."""
        
        # Get system prompt for the selected persona
        system_prompt = get_persona_system_prompt(moderator_persona, topic)
        
        # Create the agent with persona-specific instructions
        agent = Agent(
            instructions=system_prompt,
            tools=[end_debate, summarize_discussion, fact_check_claim]
        )
        
        # Create agent session with OpenAI components
        session = AgentSession(
            vad=silero.VAD.load(),
            stt=openai.STT(),
            llm=openai.LLM(model="gpt-4o-mini"),
            tts=openai.TTS(voice="alloy")
        )
        
        # Start the session
        await session.start(agent=agent, room=ctx.room)
        
        # Generate initial greeting
        greeting = get_persona_greeting(moderator_persona, topic)
        await session.generate_reply(instructions=f"Say this greeting: {greeting}")
        
        logger.info(f"✅ {moderator_persona} agent started successfully for topic: {topic}")
        
        # Keep the session alive until the room is disconnected
        await session.wait_for_completion()
        
    except Exception as e:
        logger.error(f"❌ Failed to start agent: {e}")
        raise
    finally:
        # Ensure proper cleanup
        if session:
            try:
                await session.aclose()
                logger.info("✅ Agent session cleaned up successfully")
            except Exception as cleanup_error:
                logger.warning(f"⚠️ Error during session cleanup: {cleanup_error}")

def main():
    """Main entry point for the debate moderator agent"""
    cli.run_app(
        WorkerOptions(
            agent_name="moderator",
            entrypoint_fnc=entrypoint,
        )
    )

if __name__ == "__main__":
    main() 