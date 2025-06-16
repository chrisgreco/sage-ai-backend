import asyncio
import logging
import time
from typing import Dict, List
from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli, llm
from livekit.agents.voice_assistant import VoiceAssistant
from livekit.plugins import openai, silero
from livekit import rtc
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConversationContext:
    def __init__(self):
        self.transcript = []
        self.agent_interventions = {}  # Track interventions by agent_id
        
    def add_user_message(self, user_id, message):
        self.transcript.append({
            "role": "user", 
            "user_id": user_id, 
            "content": message, 
            "timestamp": time.time()
        })
        logger.info(f"Added user message from {user_id}: {message[:50]}...")
        
    def add_agent_intervention(self, agent_id, message):
        self.transcript.append({
            "role": "agent", 
            "agent_id": agent_id, 
            "content": message, 
            "timestamp": time.time()
        })
        if agent_id not in self.agent_interventions:
            self.agent_interventions[agent_id] = []
        self.agent_interventions[agent_id].append(message)
        logger.info(f"Added agent intervention from {agent_id}: {message[:50]}...")
        
    def get_recent_context(self, window_size=10):
        return self.transcript[-window_size:] if len(self.transcript) > window_size else self.transcript
        
    def is_duplicate_message(self, agent_id, message, similarity_threshold=0.8):
        if agent_id in self.agent_interventions and self.agent_interventions[agent_id]:
            # Check if this would be a duplicate of any recent message from this agent
            for prev_message in self.agent_interventions[agent_id][-3:]:  # Check last 3 messages
                # Simple string comparison for now
                # In production, consider using semantic similarity
                if prev_message.lower() == message.lower():
                    return True
            
            # Check for high similarity with the last message
            last_message = self.agent_interventions[agent_id][-1]
            # Very basic similarity check - could be improved with NLP techniques
            if len(message) > 10 and message in last_message or last_message in message:
                return True
                
        return False

# Global session management
active_sessions = {}  # room_id -> ConversationContext

def get_or_create_session(room_id):
    if room_id not in active_sessions:
        active_sessions[room_id] = ConversationContext()
        logger.info(f"Created new conversation context for room {room_id}")
    return active_sessions[room_id]

class DebateAgent:
    def __init__(self, name: str, role: str, persona: str, instructions: str):
        self.name = name
        self.role = role
        self.persona = persona
        self.instructions = instructions
        self.active = True

class DebateModerationService:
    def __init__(self):
        self.agents = {
            "socrates": DebateAgent(
                "Socrates", 
                "Clarifier",
                "Ask clarifying questions when assumptions are made",
                "You are Socrates, an AI debate moderator. Ask clarifying questions when participants make assumptions or logical jumps. Only interject when clarity is needed. Keep questions brief and thought-provoking."
            ),
            "solon": DebateAgent(
                "Solon",
                "Rule Enforcer", 
                "Enforce debate rules and ensure fair turn-taking",
                "You are Solon, an AI debate moderator. Enforce debate rules like no interruptions, no personal attacks, and fair speaking time. Only speak when rules are violated. Be firm but respectful."
            ),
            "buddha": DebateAgent(
                "Buddha",
                "Peacekeeper",
                "Monitor tone and diffuse conflict",
                "You are Buddha, an AI debate moderator. Monitor emotional tone and intervene when discussions become heated or aggressive. Promote calm, respectful dialogue. Only speak when tone needs adjustment."
            ),
            "hermes": DebateAgent(
                "Hermes", 
                "Summarizer",
                "Provide summaries and logical transitions",
                "You are Hermes, an AI debate moderator. Summarize key points and provide logical transitions during natural breaks. Help structure the conversation. Only speak during appropriate pauses."
            ),
            "aristotle": DebateAgent(
                "Aristotle",
                "Fact-Checker", 
                "Request sources for factual claims",
                "You are Aristotle, an AI debate moderator. Listen for factual claims and request sources when evidence is lacking. Promote logical reasoning and evidence-based arguments. Only speak when facts need verification."
            )
        }
        self.current_agent = None
        self.transcript = []

    def get_active_agents(self) -> List[DebateAgent]:
        return [agent for agent in self.agents.values() if agent.active]

    def determine_appropriate_agent(self, conversation_context: str) -> DebateAgent:
        # Simple agent selection logic - in production this could be more sophisticated
        active_agents = self.get_active_agents()
        if not active_agents:
            return list(self.agents.values())[0]
        
        # For now, rotate through active agents
        # TODO: Implement smarter agent selection based on context
        import random
        return random.choice(active_agents)

    def get_moderation_instructions(self) -> str:
        active_agents = self.get_active_agents()
        agent_descriptions = "\n".join([
            f"- {agent.name} ({agent.role}): {agent.persona}"
            for agent in active_agents
        ])
        
        return f"""You are part of a multi-agent AI moderation system for live voice debates.

Active moderators:
{agent_descriptions}

Your role is to moderate the debate according to your assigned persona. Only speak when your specific moderation criteria are met. Keep interventions brief (1-2 sentences), polite, and focused on your role.

Current debate rules:
- No personal attacks
- Provide sources for factual claims  
- Respect speaking turns
- Stay on topic
- IMPORTANT: Never repeat yourself or say the same thing twice. Vary your wording and approach.

Listen carefully to the conversation and only interject when necessary according to your role."""

async def generate_agent_response(agent_id, context, instructions):
    """Generate a response using the LLM with full conversation context"""
    # Format the conversation history for the LLM
    messages = [
        {"role": "system", "content": instructions}
    ]
    
    # Add conversation history
    for entry in context:
        role = "assistant" if entry.get("role") == "agent" else "user"
        messages.append({"role": role, "content": entry.get("content", "")})
    
    # Call the LLM with the full conversation context
    try:
        response = await openai.ChatCompletion.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error generating agent response: {e}")
        return None

async def entrypoint(ctx: JobContext):
    logger.info("Starting SAGE debate moderation agent")
    
    # Initialize moderation service
    moderation_service = DebateModerationService()
    
    # Get or create conversation context for this room
    conversation_context = get_or_create_session(ctx.room.id)
    
    # Wait for participant to connect
    await ctx.wait_for_participant()
    logger.info("Participant connected to debate room")

    # Create voice assistant with OpenAI Realtime API
    assistant = VoiceAssistant(
        vad=silero.VAD.load(),
        stt=openai.STT(),
        llm=openai.LLM(
            model="gpt-4o-realtime-preview-2024-12-17",
            instructions=moderation_service.get_moderation_instructions(),
            temperature=0.8,
        ),
        tts=openai.TTS(voice="alloy"),
        chat_ctx=llm.ChatContext(),
    )

    # Handle chat context updates for agent coordination
    @assistant.on("function_calls_finished")
    def on_function_calls_finished(called_functions: list):
        logger.info(f"Function calls finished: {called_functions}")
        
    # Handle transcription results to update conversation context
    @assistant.on("transcription")
    def on_transcription(participant_id: str, transcript: str):
        if transcript and transcript.strip():
            conversation_context.add_user_message(participant_id, transcript)
            logger.info(f"Transcription from {participant_id}: {transcript}")
    
    # Handle agent responses to check for duplicates
    @assistant.on("before_tts")
    async def on_before_tts(text: str) -> str:
        # Determine which agent is speaking
        agent = moderation_service.determine_appropriate_agent(
            str(conversation_context.get_recent_context())
        )
        agent_id = agent.name
        
        # Check if this is a duplicate message
        if conversation_context.is_duplicate_message(agent_id, text):
            logger.info(f"Prevented duplicate message from {agent_id}: {text[:50]}...")
            
            # Try to generate an alternative response
            alternative_response = await generate_agent_response(
                agent_id,
                conversation_context.get_recent_context(),
                f"{agent.instructions}\n\nIMPORTANT: Your previous response was too similar to something you've already said. Please provide a completely different response that serves the same purpose."
            )
            
            if alternative_response and not conversation_context.is_duplicate_message(agent_id, alternative_response):
                conversation_context.add_agent_intervention(agent_id, alternative_response)
                return alternative_response
            else:
                # If we couldn't generate a non-duplicate alternative, skip this response
                return ""
        
        # Record non-duplicate intervention
        conversation_context.add_agent_intervention(agent_id, text)
        return text

    # Start the voice assistant
    assistant.start(ctx.room)
    
    # Listen for room events to coordinate agents
    @ctx.room.on("participant_connected")
    def on_participant_connected(participant: rtc.RemoteParticipant):
        logger.info(f"Participant connected: {participant.identity}")

    @ctx.room.on("participant_disconnected")  
    def on_participant_disconnected(participant: rtc.RemoteParticipant):
        logger.info(f"Participant disconnected: {participant.identity}")

    # Send periodic updates about moderation status
    async def send_moderation_status():
        while True:
            try:
                # Send status to frontend via data channel
                status_data = {
                    "type": "moderation_status",
                    "active_agents": [
                        {"name": agent.name, "role": agent.role, "active": agent.active}
                        for agent in moderation_service.agents.values()
                    ],
                    "transcript_length": len(conversation_context.transcript)
                }
                
                # Publish data to room
                await ctx.room.local_participant.publish_data(
                    json.dumps(status_data).encode(),
                    destination_identities=[]  # Send to all participants
                )
                
                await asyncio.sleep(5)  # Send status every 5 seconds
            except Exception as e:
                logger.error(f"Error sending moderation status: {e}")
                await asyncio.sleep(5)

    # Start status updates
    asyncio.create_task(send_moderation_status())
    
    logger.info("SAGE debate moderation agent is ready")

if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            # Allow agent to automatically subscribe to participant tracks
            auto_subscribe=AutoSubscribe.AUDIO_ONLY,
        )
    )
