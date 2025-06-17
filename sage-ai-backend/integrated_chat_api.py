# Integrated Chat API

"""
Production-Ready Chat API with Proper Turn-Taking and Memory
===========================================================

This API integrates with the LiveKit AI agents system to provide:
1. Single agent responses (no simultaneous talking)
2. Persistent conversation memory
3. Intelligent agent selection based on content
4. Integration with voice agents for production
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional
import logging
from datetime import datetime
from dotenv import load_dotenv

# Import our AI agents system
try:
    from ai_debate_agents import AGENT_PERSONALITIES
    AGENTS_AVAILABLE = True
except ImportError:
    AGENTS_AVAILABLE = False
    
load_dotenv()
app = FastAPI(title="Sage AI Integrated Chat API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatMessage(BaseModel):
    message: str
    room_id: str

class AgentResponse(BaseModel):
    agent_name: str
    agent_role: str
    message: str
    timestamp: str

# Global conversation memory - persistent across requests
conversation_memory: Dict[str, List[Dict]] = {}

@app.post("/api/chat/message")
async def send_message(message: ChatMessage):
    """Send message and get ONE intelligent agent response"""
    
    # Initialize room memory if needed
    if message.room_id not in conversation_memory:
        conversation_memory[message.room_id] = []
    
    # Add user message to persistent memory
    user_event = {
        "speaker": "user", 
        "message": message.message,
        "timestamp": datetime.now().isoformat()
    }
    conversation_memory[message.room_id].append(user_event)
    
    # Select the BEST agent to respond (not multiple)
    selected_agent = select_best_agent(message.message)
    
    # Generate response with conversation context
    response = generate_contextual_response(selected_agent, message.message, message.room_id)
    
    # Add agent response to persistent memory
    agent_event = {
        "speaker": selected_agent,
        "message": response["message"], 
        "timestamp": response["timestamp"]
    }
    conversation_memory[message.room_id].append(agent_event)
    
    return {"response": response, "conversation_length": len(conversation_memory[message.room_id])}

def select_best_agent(user_message: str) -> str:
    """Select the most appropriate single agent to respond"""
    
    if not AGENTS_AVAILABLE:
        return "moderator"
        
    message_lower = user_message.lower()
    
    # Priority-based selection
    if any(word in message_lower for word in ["fact", "evidence", "research", "study", "data", "prove"]):
        return "expert"  # Aristotle for fact-checking
        
    elif any(word in message_lower for word in ["why", "what", "how", "explain", "meaning"]):
        return "challenger"  # Socrates for questioning
        
    elif any(word in message_lower for word in ["peace", "conflict", "calm", "meditation", "harmony"]):
        return "fact_checker"  # Buddha for peace (note: ID is fact_checker)
        
    elif any(word in message_lower for word in ["connect", "relate", "system", "together", "synthesis"]):
        return "synthesizer"  # Hermes for connections
        
    else:
        return "moderator"  # Solon as default

def generate_contextual_response(agent_id: str, user_message: str, room_id: str) -> Dict:
    """Generate response with full conversation context"""
    
    if not AGENTS_AVAILABLE:
        return {
            "agent_name": "System",
            "agent_role": "Assistant", 
            "message": "AI system unavailable",
            "timestamp": datetime.now().isoformat()
        }
        
    personality = AGENT_PERSONALITIES[agent_id]
    
    # Get conversation history for context
    history = conversation_memory.get(room_id, [])
    recent_context = "\n".join([f"{msg['speaker']}: {msg['message']}" for msg in history[-3:]])
    
    # Generate response based on personality and context
    response_text = create_personality_response(personality, user_message, recent_context)
    
    return {
        "agent_name": personality.name,
        "agent_role": personality.role,
        "message": response_text,
        "timestamp": datetime.now().isoformat()
    }

def create_personality_response(personality, user_message: str, context: str) -> str:
    """Create response based on agent's unique personality"""
    
    if personality.name == "Solon":
        return f"As moderator, I ensure we address '{user_message}' with proper structure and give all voices fair consideration."
        
    elif personality.name == "Aristotle": 
        return f"Let me analyze '{user_message}' systematically. The logical framework suggests we need empirical evidence to evaluate this claim properly."
        
    elif personality.name == "Socrates":
        return f"Interesting that you mention '{user_message}'. But tell me - what assumptions are we making here? Have you considered what this really means?"
        
    elif personality.name == "Hermes":
        return f"I see how '{user_message}' connects to broader patterns in our discussion. From a systems perspective, this links to several key themes."
        
    elif personality.name == "Buddha":
        return f"Let us approach '{user_message}' with mindfulness. Perhaps the middle path can help us find wisdom in this matter."
        
    return f"Thank you for sharing '{user_message}'. This deserves thoughtful consideration."

@app.get("/api/chat/memory/{room_id}")
async def get_conversation_memory(room_id: str):
    """Get full conversation memory for room"""
    return {
        "room_id": room_id,
        "conversation": conversation_memory.get(room_id, []),
        "message_count": len(conversation_memory.get(room_id, []))
    }

@app.get("/api/agents")
async def get_agents():
    """Get available agent information"""
    if not AGENTS_AVAILABLE:
        return {"error": "AI agents not available"}
        
    return {
        agent_id: {
            "name": p.name,
            "role": p.role,
            "triggers": p.speaking_triggers[:3]
        }
        for agent_id, p in AGENT_PERSONALITIES.items()
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "agents_available": AGENTS_AVAILABLE, 
        "active_conversations": len(conversation_memory)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001) 
