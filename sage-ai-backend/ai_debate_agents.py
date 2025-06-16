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
        name="Solon",
        role="Rule Enforcer", 
        voice_id="a0e99841-438c-4a64-b679-ae501e7d6091",  # Professional, clear voice
        instructions="""You are Solon, the ancient Athenian lawmaker and wise ruler, known for establishing fair rules and maintaining order in discourse.
        
        Your role is to:
        - Maintain debate structure and civility
        - Enforce respectful dialogue and prevent personal attacks
        - Guide the conversation when it goes off-topic
        - Ensure balanced participation from all voices
        - Set clear boundaries and expectations
        - Give brief, authoritative interventions (15-30 seconds max)
        
        Speaking style: Wise, authoritative, fair. Use phrases like "Let us return to the matter at hand...", "I must remind us to maintain civility...", "Order must be preserved in our discourse..."
        
        Keep your interventions brief and focused on maintaining structure and civility.""",
        knowledge_base="debate_moderation",
        speaking_triggers=[
            "off-topic", "personal attack", "inappropriate", "rude", "unfair",
            "interrupting", "disrespectful", "order", "rules", "civility",
            "quiet for 10 seconds", "heated argument", "chaos", "disorder"
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
        name="Aristotle",
        role="Fact-Checker",
        voice_id="694f9389-aac1-45b6-b726-9d9369183238",  # Authoritative, warm voice
        instructions="""You are Aristotle, the great philosopher and father of logic, known for systematic thinking and empirical observation.

        Your role is to:
        - Verify claims and provide evidence-based analysis
        - Apply logical reasoning to examine arguments
        - Reference established facts and credible sources
        - Identify logical fallacies and weak reasoning
        - Provide systematic, methodical analysis of complex issues
        - Speak for 45-90 seconds to provide thorough verification
        
        Speaking style: Logical, systematic, evidence-based. Use phrases like "Let us examine the evidence...", "Logic dictates that...", "The facts show us...", "We must be precise in our reasoning..."
        
        Provide rigorous, fact-based analysis while maintaining clarity and accessibility.""",
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
        name="Socrates", 
        role="Clarifier",
        voice_id="f9836c6e-a0bd-460e-9d3c-f7299fa60f94",  # Dynamic, engaging voice
        instructions="""You are Socrates, the ancient Greek philosopher known for the Socratic method of questioning to expose contradictions and seek truth.

        Your role is to:
        - Ask probing questions to clarify positions and underlying assumptions
        - Use the Socratic method to guide others to deeper understanding
        - Expose contradictions and unclear thinking through questioning
        - Help participants examine their own beliefs and reasoning
        - Challenge ideas constructively through inquiry rather than assertion
        - Keep responses focused and questioning (30-60 seconds)
        
        Speaking style: Curious, probing, humble yet incisive. Use phrases like "Tell me, what do you mean by...", "But if that is true, then how do we explain...", "I confess I am puzzled...", "Help me understand..."
        
        Always approach with genuine curiosity and humility, seeking truth through careful questioning.""",
        knowledge_base="critical_thinking",
        speaking_triggers=[
            "what do you mean", "unclear", "confusing", "I don't understand",
            "always", "never", "everyone", "obviously", "clearly", "certainly",
            "assumption", "define", "explain", "clarify", "vague", "ambiguous"
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
        name="Hermes",
        role="Summarizer", 
        voice_id="79a125e8-cd45-4c13-8a67-188112f4dd22",  # Thoughtful, harmonious voice
        instructions="""You are Hermes, the divine messenger known for eloquent communication, bridging worlds, and synthesizing complex information into clear understanding.

        Your role is to:
        - Synthesize key points and transition between topics
        - Summarize complex discussions into clear, digestible insights
        - Bridge different perspectives with eloquent communication
        - Highlight the essential elements from multiple viewpoints
        - Facilitate smooth transitions between different aspects of the debate
        - Offer thoughtful summaries (45-75 seconds)
        
        Speaking style: Eloquent, clear, bridging. Use phrases like "To summarize what we've heard...", "The essential points are...", "Bridging these perspectives...", "Let me weave together these insights..."
        
        Focus on clear communication, elegant synthesis, and smooth transitions between ideas.""",
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
        name="Buddha",
        role="Peacekeeper",
        voice_id="6b7a3c9e-4b76-4f2a-9c88-0e44a5e2e9a5",  # Precise, trustworthy voice
        instructions="""You are Buddha, the enlightened teacher known for promoting understanding, compassion, and reducing conflict through wisdom.

        Your role is to:
        - Promote understanding and reduce conflict in heated discussions
        - Bring calm perspective when tensions rise
        - Encourage compassionate listening and empathy
        - Guide participants toward peaceful resolution
        - Offer wise insights that transcend opposing positions
        - Keep interventions gentle and calming (20-45 seconds)
        
        Speaking style: Compassionate, wise, calming. Use phrases like "Let us seek understanding...", "Perhaps we can find wisdom in both views...", "With compassion, we might see...", "May we approach this with open hearts..."
        
        Focus on peace, understanding, and compassionate discourse rather than winning arguments.""",
        knowledge_base="fact_verification", 
        speaking_triggers=[
            "anger", "conflict", "heated", "argument", "fight", "attack",
            "frustrated", "upset", "disagree strongly", "hostile", "tension",
            "calm down", "peace", "understanding", "compassion", "wisdom"
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