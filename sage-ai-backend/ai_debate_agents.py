#!/usr/bin/env python3

"""
Sage AI Multi-Agent Debate System
=================================

This module implements a sophisticated multi-agent AI debate system with 5 distinct AI personalities:
1. The Moderator - Guides the discussion and maintains order
2. The Expert - Provides in-depth knowledge and analysis  
3. The Challenger - Questions assumptions and plays devil's advocate
4. The Synthesizer - Finds common ground and summarizes insights
5. The Fact-Checker - Verifies claims and provides evidence

Each agent has:
- Unique voice personality using Cartesia TTS
- Specialized knowledge base and speaking patterns
- Intelligent conversation triggers based on context
- Real-time speech-to-text understanding via Deepgram
"""

import asyncio
import os
import logging
import json
import random
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from livekit.agents import (
    Agent,
    AgentSession, 
    JobContext,
    RunContext,
    WorkerOptions,
    cli,
    function_tool,
)
from livekit.plugins import deepgram, openai, silero, cartesia
from livekit import rtc

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class AgentPersonality:
    """Defines the personality traits and configuration for each AI agent"""
    name: str
    role: str
    voice_id: str  # Cartesia voice ID
    instructions: str
    knowledge_base: str
    speaking_triggers: List[str]
    interruption_threshold: float = 0.7  # How likely to interrupt (0-1)
    response_delay: float = 2.0  # Seconds to wait before responding
    personality_traits: Dict[str, Any] = None

class DebateContext:
    """Manages the state and context of the ongoing debate"""
    
    def __init__(self, topic: str):
        self.topic = topic
        self.debate_history: List[Dict] = []
        self.current_speaker: Optional[str] = None
        self.speaking_queue: List[str] = []
        self.key_points_raised: List[str] = []
        self.claims_to_verify: List[str] = []
        self.start_time = datetime.now()
        self.total_speaking_time: Dict[str, float] = {}
        
    def add_speech_event(self, agent_name: str, text: str, timestamp: datetime):
        """Record a speech event in the debate history"""
        event = {
            "agent": agent_name,
            "text": text,
            "timestamp": timestamp.isoformat(),
            "duration": 0  # Will be calculated when speech ends
        }
        self.debate_history.append(event)
        
    def should_agent_speak(self, agent_name: str, current_context: str) -> bool:
        """Determine if an agent should speak based on context and triggers"""
        personality = AGENT_PERSONALITIES[agent_name]
        
        # Check if any triggers are present in current context
        for trigger in personality.speaking_triggers:
            if trigger.lower() in current_context.lower():
                return random.random() < personality.interruption_threshold
                
        return False

# Define the 5 AI Agent Personalities
AGENT_PERSONALITIES = {
    "moderator": AgentPersonality(
        name="Dr. Alexandra Wright",
        role="Debate Moderator", 
        voice_id="a0e99841-438c-4a64-b679-ae501e7d6091",  # Professional, clear voice
        instructions="""You are Dr. Alexandra Wright, an experienced debate moderator with a PhD in Communication Studies. 
        
        Your role is to:
        - Guide the conversation and ensure balanced participation
        - Ask clarifying questions when discussions become unclear
        - Introduce new angles when the conversation stagnates
        - Summarize key points periodically
        - Maintain respectful discourse
        - Give brief, concise interventions (15-30 seconds max)
        
        Speaking style: Professional, neutral, encouraging. Use phrases like "That's an interesting point, let's explore...", "I'd like to hear more about...", "Let's ensure everyone has a chance to contribute..."
        
        Keep your interventions brief and focused on facilitation rather than adding content.""",
        knowledge_base="debate_moderation",
        speaking_triggers=[
            "unclear", "confusing", "what do you mean", "can you explain", 
            "I don't understand", "off-topic", "personal attack", "let's move on",
            "quiet for 10 seconds", "heated argument"
        ],
        interruption_threshold=0.9,
        response_delay=1.5,
        personality_traits={
            "intervention_style": "gentle_redirect",
            "max_speaking_time": 30,
            "priority_triggers": ["fairness", "clarity", "respect"]
        }
    ),
    
    "expert": AgentPersonality(
        name="Professor James Chen",
        role="Subject Matter Expert",
        voice_id="694f9389-aac1-45b6-b726-9d9369183238",  # Authoritative, warm voice
        instructions="""You are Professor James Chen, a distinguished academic with deep expertise across multiple fields including technology, economics, science, and social policy.

        Your role is to:
        - Provide in-depth analysis and factual information
        - Explain complex concepts in accessible ways
        - Draw connections between different domains of knowledge
        - Reference credible sources and studies when relevant
        - Build upon points raised by other participants with additional insights
        - Speak for 45-90 seconds to provide comprehensive explanations
        
        Speaking style: Thoughtful, measured, educational. Use phrases like "Research indicates...", "From an analytical perspective...", "It's important to consider...", "The data suggests..."
        
        Provide substantive, educational content while remaining engaging and accessible.""",
        knowledge_base="academic_research",
        speaking_triggers=[
            "research", "study", "data", "evidence", "how does", "why does", 
            "what is", "explain", "analysis", "expert opinion", "scientific",
            "academic", "peer-reviewed", "statistics", "empirical"
        ],
        interruption_threshold=0.6,
        response_delay=3.0,
        personality_traits={
            "explanation_depth": "comprehensive",
            "max_speaking_time": 90,
            "citation_frequency": "high"
        }
    ),
    
    "challenger": AgentPersonality(
        name="Sarah Rodriguez", 
        role="Critical Challenger",
        voice_id="f9836c6e-a0bd-460e-9d3c-f7299fa60f94",  # Dynamic, engaging voice
        instructions="""You are Sarah Rodriguez, a sharp-minded critical thinker who excels at identifying logical flaws, questioning assumptions, and presenting alternative viewpoints.

        Your role is to:
        - Question underlying assumptions in arguments
        - Present counterarguments and alternative perspectives  
        - Identify potential biases or logical fallacies
        - Play devil's advocate constructively
        - Challenge conventional wisdom with thought-provoking questions
        - Keep responses focused and punchy (30-60 seconds)
        
        Speaking style: Direct, questioning, intellectually provocative. Use phrases like "But what if...", "Have we considered...", "That assumes...", "Playing devil's advocate...", "Let me challenge that..."
        
        Be respectfully challenging while maintaining intellectual rigor and constructive discourse.""",
        knowledge_base="critical_thinking",
        speaking_triggers=[
            "always", "never", "everyone", "obviously", "clearly", "certainly",
            "assumption", "take for granted", "conventional wisdom", "status quo",
            "bias", "logical fallacy", "counterargument", "alternative"
        ],
        interruption_threshold=0.8,
        response_delay=1.8,
        personality_traits={
            "challenge_intensity": "moderate_high",
            "max_speaking_time": 60,
            "contrarian_tendency": 0.7
        }
    ),
    
    "synthesizer": AgentPersonality(
        name="Dr. Maya Patel",
        role="Insight Synthesizer", 
        voice_id="79a125e8-cd45-4c13-8a67-188112f4dd22",  # Thoughtful, harmonious voice
        instructions="""You are Dr. Maya Patel, a systems thinker who excels at finding common ground, identifying patterns, and synthesizing diverse viewpoints into coherent insights.

        Your role is to:
        - Identify common threads and shared principles across different viewpoints
        - Synthesize complex discussions into key insights
        - Propose framework approaches that integrate multiple perspectives
        - Highlight areas of consensus and productive disagreement
        - Bridge differences and find constructive middle ground
        - Offer thoughtful summaries (45-75 seconds)
        
        Speaking style: Integrative, thoughtful, diplomatic. Use phrases like "Building on both perspectives...", "What I'm hearing is...", "There seems to be agreement that...", "One way to reconcile these views..."
        
        Focus on connection-making and insight generation rather than taking sides.""",
        knowledge_base="systems_thinking",
        speaking_triggers=[
            "disagree", "conflict", "different views", "both sides", "common ground",
            "synthesis", "integrate", "combine", "bridge", "reconcile",
            "pattern", "framework", "holistic", "bigger picture"
        ],
        interruption_threshold=0.5,
        response_delay=4.0,
        personality_traits={
            "synthesis_style": "integrative",
            "max_speaking_time": 75,
            "consensus_seeking": 0.9
        }
    ),
    
    "fact_checker": AgentPersonality(
        name="Dr. Robert Kim",
        role="Fact-Checker & Evidence Analyst",
        voice_id="6b7a3c9e-4b76-4f2a-9c88-0e44a5e2e9a5",  # Precise, trustworthy voice
        instructions="""You are Dr. Robert Kim, a meticulous researcher and fact-checker with expertise in information verification, source evaluation, and evidence analysis.

        Your role is to:
        - Verify factual claims made during the discussion
        - Provide corrections when misinformation is shared
        - Cite reliable sources and recent data
        - Distinguish between facts, opinions, and interpretations
        - Flag when claims need additional evidence
        - Keep fact-checks concise and specific (20-45 seconds)
        
        Speaking style: Precise, evidence-based, helpful. Use phrases like "To verify that claim...", "The current data shows...", "According to reliable sources...", "That's partially correct, but...", "We should be careful about..."
        
        Focus on accuracy and evidence while being helpful rather than confrontational.""",
        knowledge_base="fact_verification", 
        speaking_triggers=[
            "percent", "study shows", "research proves", "statistics", "data",
            "fact", "evidence", "source", "according to", "reportedly",
            "misinformation", "false", "incorrect", "verify", "confirm"
        ],
        interruption_threshold=0.7,
        response_delay=2.5,
        personality_traits={
            "verification_rigor": "high", 
            "max_speaking_time": 45,
            "correction_style": "constructive"
        }
    )
}

class MultiAgentDebateSystem:
    """Main system orchestrating the multi-agent debate"""
    
    def __init__(self, room: rtc.Room, topic: str):
        self.room = room
        self.debate_context = DebateContext(topic)
        self.agents: Dict[str, Agent] = {}
        self.agent_sessions: Dict[str, AgentSession] = {}
        self.active_speakers: set = set()
        self.is_initialized = False
        
    async def initialize_agents(self):
        """Initialize all AI agents with their personalities and voices"""
        logger.info("Initializing multi-agent debate system...")
        
        for agent_id, personality in AGENT_PERSONALITIES.items():
            # Create agent with personality-specific configuration
            agent = Agent(
                instructions=personality.instructions,
                tools=[
                    self.get_debate_status_tool(),
                    self.request_speaking_turn_tool(), 
                    self.add_key_point_tool(),
                    self.flag_claim_for_verification_tool() if agent_id == "fact_checker" else None
                ]
            )
            
            # Create agent session with Cartesia TTS and Deepgram STT
            session = AgentSession(
                vad=silero.VAD.load(),
                stt=deepgram.STT(
                    model="nova-2", 
                    language="en",
                    interim_results=True
                ),
                llm=openai.LLM(
                    model="gpt-4o-mini",
                    temperature=0.7 if agent_id != "fact_checker" else 0.3
                ),
                tts=cartesia.TTS(
                    voice_id=personality.voice_id,
                    model_id="sonic-2",
                    experimental_controls={
                        "speed": "normal",
                        "emotion": self.get_voice_emotion_for_agent(agent_id)
                    }
                )
            )
            
            self.agents[agent_id] = agent
            self.agent_sessions[agent_id] = session
            
        self.is_initialized = True
        logger.info("All agents initialized successfully!")
        
    def get_voice_emotion_for_agent(self, agent_id: str) -> List[str]:
        """Get appropriate voice emotions for each agent type"""
        emotions = {
            "moderator": ["professional:medium", "calm:medium"],
            "expert": ["thoughtful:medium", "authoritative:low"], 
            "challenger": ["engaging:medium", "curious:high"],
            "synthesizer": ["warm:medium", "understanding:medium"],
            "fact_checker": ["precise:medium", "trustworthy:high"]
        }
        return emotions.get(agent_id, ["neutral:medium"])
        
    @function_tool
    async def get_debate_status_tool(self, context: RunContext) -> Dict[str, Any]:
        """Tool for agents to get current debate status and context"""
        return {
            "topic": self.debate_context.topic,
            "current_speaker": self.debate_context.current_speaker,
            "recent_points": self.debate_context.key_points_raised[-5:],
            "debate_duration": str(datetime.now() - self.debate_context.start_time),
            "speaking_time_balance": self.debate_context.total_speaking_time
        }
        
    @function_tool 
    async def request_speaking_turn_tool(self, context: RunContext, agent_name: str, urgency: str = "normal") -> bool:
        """Tool for agents to request a speaking turn"""
        if urgency == "high" or len(self.debate_context.speaking_queue) < 2:
            if agent_name not in self.debate_context.speaking_queue:
                self.debate_context.speaking_queue.append(agent_name)
            return True
        return False
        
    @function_tool
    async def add_key_point_tool(self, context: RunContext, point: str, category: str = "general") -> bool:
        """Tool for agents to flag important points raised"""
        self.debate_context.key_points_raised.append({
            "point": point,
            "category": category,
            "timestamp": datetime.now().isoformat()
        })
        return True
        
    @function_tool
    async def flag_claim_for_verification_tool(self, context: RunContext, claim: str, speaker: str) -> bool:
        """Tool for fact-checker to flag claims needing verification"""
        self.debate_context.claims_to_verify.append({
            "claim": claim,
            "speaker": speaker,
            "flagged_at": datetime.now().isoformat(),
            "status": "pending"
        })
        return True
        
    async def start_debate_session(self):
        """Start the main debate session with all agents"""
        if not self.is_initialized:
            await self.initialize_agents()
            
        logger.info(f"Starting debate session on topic: {self.debate_context.topic}")
        
        # Start all agent sessions
        for agent_id, session in self.agent_sessions.items():
            agent = self.agents[agent_id]
            await session.start(agent=agent, room=self.room)
            
        # Have moderator introduce the topic
        moderator_session = self.agent_sessions["moderator"]
        await moderator_session.generate_reply(
            instructions=f"""Introduce today's debate topic: "{self.debate_context.topic}". 
            Welcome the participants and set the stage for a thoughtful, evidence-based discussion. 
            Mention that we have experts from various perspectives who will share insights. 
            Keep it brief (30 seconds) and engaging."""
        )
        
        # Start the conversation monitoring loop
        await self.monitor_conversation()
        
    async def monitor_conversation(self):
        """Monitor the conversation and orchestrate agent participation"""
        logger.info("Starting conversation monitoring...")
        
        last_activity_time = datetime.now()
        silence_threshold = 8.0  # seconds of silence before moderator intervenes
        
        while True:
            try:
                await asyncio.sleep(1.0)  # Check every second
                
                current_time = datetime.now()
                silence_duration = (current_time - last_activity_time).total_seconds()
                
                # Check if we need moderator intervention due to silence
                if silence_duration > silence_threshold and not self.active_speakers:
                    await self.trigger_moderator_intervention("silence")
                    last_activity_time = current_time
                    
                # Process speaking queue
                if self.debate_context.speaking_queue and not self.active_speakers:
                    next_speaker = self.debate_context.speaking_queue.pop(0)
                    await self.activate_agent_speech(next_speaker)
                    last_activity_time = current_time
                    
                # Check for natural conversation triggers
                await self.check_conversation_triggers()
                
            except Exception as e:
                logger.error(f"Error in conversation monitoring: {e}")
                await asyncio.sleep(5.0)
                
    async def trigger_moderator_intervention(self, reason: str):
        """Trigger moderator to intervene when needed"""
        moderator_session = self.agent_sessions["moderator"]
        
        interventions = {
            "silence": "The conversation seems to have paused. Let's explore another angle of this topic. What other perspectives should we consider?",
            "imbalance": "I'd like to ensure we're hearing from all viewpoints. Let's invite some additional perspectives on this point.",
            "clarification": "I think it would be helpful to clarify some of the points raised. Could we break down the key arguments so far?",
            "summary": "Let me pause here to summarize the key insights we've gathered and see what questions remain to explore."
        }
        
        instruction = interventions.get(reason, interventions["silence"])
        await moderator_session.generate_reply(instructions=instruction)
        
    async def activate_agent_speech(self, agent_id: str):
        """Activate a specific agent to speak"""
        if agent_id not in self.agent_sessions:
            return
            
        personality = AGENT_PERSONALITIES[agent_id]
        session = self.agent_sessions[agent_id]
        
        self.active_speakers.add(agent_id)
        self.debate_context.current_speaker = agent_id
        
        # Generate contextual response based on recent conversation
        recent_context = self.get_recent_conversation_context()
        
        context_instruction = f"""
        Based on the recent conversation about {self.debate_context.topic}, 
        provide your perspective as {personality.name}, the {personality.role}.
        
        Recent context: {recent_context}
        
        Remember your role: {personality.instructions}
        
        Keep your response to approximately {personality.personality_traits.get('max_speaking_time', 60)} seconds.
        """
        
        try:
            await session.generate_reply(instructions=context_instruction)
        except Exception as e:
            logger.error(f"Error generating speech for {agent_id}: {e}")
        finally:
            self.active_speakers.discard(agent_id)
            if self.debate_context.current_speaker == agent_id:
                self.debate_context.current_speaker = None
                
    def get_recent_conversation_context(self) -> str:
        """Get recent conversation context for agent responses"""
        if not self.debate_context.debate_history:
            return f"This is the opening of our debate on {self.debate_context.topic}"
            
        recent_events = self.debate_context.debate_history[-3:]  # Last 3 speech events
        context_summary = []
        
        for event in recent_events:
            agent_role = next((p.role for p in AGENT_PERSONALITIES.values() if p.name == event['agent']), event['agent'])
            context_summary.append(f"{agent_role}: {event['text'][:100]}...")
            
        return " | ".join(context_summary)
        
    async def check_conversation_triggers(self):
        """Check if any agents should be triggered to speak based on conversation content"""
        if not self.debate_context.debate_history or self.active_speakers:
            return
            
        recent_text = self.debate_context.debate_history[-1]['text'].lower()
        
        for agent_id, personality in AGENT_PERSONALITIES.items():
            if (agent_id not in self.active_speakers and 
                agent_id not in self.debate_context.speaking_queue and
                self.debate_context.should_agent_speak(agent_id, recent_text)):
                
                # Add some randomness to avoid overly predictable responses
                if random.random() < 0.6:  # 60% chance to actually trigger
                    await asyncio.sleep(personality.response_delay)
                    self.debate_context.speaking_queue.append(agent_id)

# Main entrypoint function for LiveKit agents framework
async def entrypoint(ctx: JobContext):
    """Main entrypoint for the multi-agent debate system"""
    logger.info("Starting Sage AI Multi-Agent Debate System...")
    
    await ctx.connect()
    
    # Get debate topic from room metadata or environment variables
    room_name = ctx.room.name
    topic = os.getenv("DEBATE_TOPIC", "The future of artificial intelligence in society")
    
    # Try to extract topic from room name if available
    if room_name and "topic=" in room_name:
        try:
            topic = room_name.split("topic=")[1].replace("_", " ")
        except:
            pass
    
    logger.info(f"🎯 Initializing debate on topic: {topic}")
    logger.info(f"🏛️ Room: {room_name}")
    
    # Initialize the multi-agent system
    debate_system = MultiAgentDebateSystem(ctx.room, topic)
    
    try:
        await debate_system.start_debate_session()
    except Exception as e:
        logger.error(f"Error in debate session: {e}")
        raise

if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check if this is being called with room argument
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "start":
        # Handle the start command with room argument
        if "--room" in sys.argv:
            room_idx = sys.argv.index("--room")
            if room_idx + 1 < len(sys.argv):
                room_name = sys.argv[room_idx + 1]
                os.environ["ROOM_NAME"] = room_name
                logger.info(f"🎯 Starting agents for room: {room_name}")
    
    # Required environment variables check
    required_vars = [
        "LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET",
        "OPENAI_API_KEY", "DEEPGRAM_API_KEY", "CARTESIA_API_KEY"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        exit(1)
    
    logger.info("🚀 All environment variables configured!")
    logger.info("🎭 Starting multi-agent AI debate system...")
    
    # Run the agent
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_connections=5,  # Pre-warm for multiple agents
        )
    ) 