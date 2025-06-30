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
import aiohttp
import weakref
import functools
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import Optional, Set, Dict, List, Any, Callable
from enum import Enum

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

# Enhanced HTTP session management
_active_sessions: Set[aiohttp.ClientSession] = set()
_session_registry = weakref.WeakSet()

class HTTPSessionManager:
    """Context manager for HTTP sessions with automatic cleanup and resource leak detection"""
    
    def __init__(self, timeout: float = 30.0, max_connections: int = 10):
        self.timeout = timeout
        self.max_connections = max_connections
        self.session: Optional[aiohttp.ClientSession] = None
        self.created_at = time.time()
        
    async def __aenter__(self) -> aiohttp.ClientSession:
        """Create and return HTTP session"""
        try:
            connector = aiohttp.TCPConnector(
                limit=self.max_connections,
                limit_per_host=5,
                keepalive_timeout=30,
                enable_cleanup_closed=True
            )
            
            timeout = aiohttp.ClientTimeout(
                total=self.timeout,
                connect=10.0,
                sock_read=self.timeout,
                sock_connect=10.0
            )
            
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                trust_env=True
            )
            
            _active_sessions.add(self.session)
            _session_registry.add(self.session)
            
            logger.debug(f"✅ Created HTTP session (active: {len(_active_sessions)})")
            return self.session
            
        except Exception as e:
            logger.error(f"❌ Failed to create HTTP session: {e}")
            raise
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup HTTP session"""
        if self.session:
            try:
                # Remove from active sessions
                if self.session in _active_sessions:
                    _active_sessions.remove(self.session)
                
                # Close the session if not already closed
                if not self.session.closed:
                    await self.session.close()
                    
                # Small delay to ensure connections are properly closed
                await asyncio.sleep(0.1)
                
                session_lifetime = time.time() - self.created_at
                logger.debug(f"✅ Closed HTTP session after {session_lifetime:.1f}s (active: {len(_active_sessions)})")
                
            except Exception as e:
                logger.warning(f"⚠️ Error closing HTTP session: {e}")
            finally:
                self.session = None

async def get_http_session() -> aiohttp.ClientSession:
    """Get or create a properly managed HTTP session - DEPRECATED: Use HTTPSessionManager context manager instead"""
    logger.warning("⚠️ get_http_session() is deprecated. Use HTTPSessionManager context manager for better resource management.")
    
    session = aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=30),
        connector=aiohttp.TCPConnector(limit=10, limit_per_host=5, enable_cleanup_closed=True)
    )
    _active_sessions.add(session)
    _session_registry.add(session)
    return session

async def cleanup_http_sessions():
    """Clean up all active HTTP sessions"""
    logger.info(f"🧹 Cleaning up {len(_active_sessions)} HTTP sessions...")
    sessions_to_close = list(_active_sessions)
    _active_sessions.clear()
    
    cleanup_tasks = []
    for session in sessions_to_close:
        if not session.closed:
            cleanup_tasks.append(session.close())
    
    if cleanup_tasks:
        try:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            logger.info("✅ All HTTP sessions closed")
        except Exception as e:
            logger.warning(f"⚠️ Error during bulk session cleanup: {e}")
    
    # Wait for connections to fully close
    await asyncio.sleep(0.2)

async def check_resource_leaks():
    """Check for unclosed HTTP sessions and log warnings"""
    unclosed_sessions = [s for s in _session_registry if not s.closed]
    if unclosed_sessions:
        logger.warning(f"⚠️ Resource leak detected: {len(unclosed_sessions)} unclosed HTTP sessions")
        for i, session in enumerate(unclosed_sessions):
            logger.warning(f"  - Session {i+1}: connector={session.connector}")
    
    active_count = len(_active_sessions)
    registry_count = len(_session_registry)
    if active_count != registry_count:
        logger.warning(f"⚠️ Session count mismatch: active={active_count}, registry={registry_count}")

# LiveKit Agents imports
try:
    from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, cli, function_tool, AutoSubscribe
    from livekit.plugins import openai, silero
    from livekit.agents import UserStateChangedEvent, AgentStateChangedEvent
    from livekit import rtc  # For audio track handling
    from livekit.rtc import TrackKind
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
async def get_debate_topic():
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
async def access_facilitation_knowledge(query: str):
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
async def suggest_process_intervention(situation: str):
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
async def fact_check_claim(claim: str, source_requested: bool = False):
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
            research_results = await research_live_data(research_query, "fact_check")

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
async def research_live_data(query: str, research_type: str = "general"):
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

        # Use context manager for proper HTTP session management
        async with HTTPSessionManager(timeout=30.0) as session:
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
async def analyze_argument_structure(argument: str):
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
async def detect_intervention_triggers(conversation_snippet: str):
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

# Global variable to store original chat method for patching
original_llm_chat = None

# Perplexity wrapper to fix message formatting issues
def validate_perplexity_message_format(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Validate and fix Perplexity API message format with proper alternation rules.
    
    Ensures strict alternation: (optional system messages) → user/tool → assistant → user/tool → assistant...
    Fixes the error: 'After the (optional) system message(s), user or tool message(s) should alternate with assistant message(s)'
    """
    if not messages:
        return messages
    
    valid_roles = {"system", "user", "assistant", "tool"}
    corrected_messages = []
    
    # Phase 1: Collect and validate system messages at the start
    system_messages = []
    idx = 0
    while idx < len(messages) and messages[idx].get("role") == "system":
        msg = messages[idx].copy()
        if "content" not in msg or not msg["content"].strip():
            msg["content"] = "You are a helpful AI assistant."
            logger.warning(f"⚠️ Empty system message at index {idx}, added default content")
        system_messages.append(msg)
        idx += 1
    
    # Phase 2: Process non-system messages and enforce alternation
    remaining_messages = messages[idx:]
    
    if not remaining_messages:
        # Only system messages, add a default user message
        system_messages.append({
            "role": "user", 
            "content": "Please provide a helpful response."
        })
        logger.info("✅ Added default user message after system-only conversation")
        return system_messages
    
    # Rebuild conversation with proper alternation
    corrected_messages = system_messages.copy()
    expected_role = "user"  # After system messages, we expect user/tool first
    
    for i, msg in enumerate(remaining_messages):
        role = msg.get("role", "user")
        content = msg.get("content", "")
        
        # Validate role
        if role not in valid_roles:
            logger.warning(f"⚠️ Invalid role '{role}' at message {idx + i}, converting to 'user'")
            role = "user"
        
        # Validate content
        if not content or not content.strip():
            if role == "system":
                content = "You are a helpful AI assistant."
            elif role in ["user", "tool"]:
                content = "Please continue."
            else:  # assistant
                content = "I understand. How can I help you further?"
            logger.warning(f"⚠️ Empty content at message {idx + i}, added default content")
        
        # Enforce alternation
        if expected_role == "user" and role not in ["user", "tool"]:
            if role == "assistant":
                # Insert a user message before this assistant message
                corrected_messages.append({
                    "role": "user",
                    "content": "Please respond to the previous context."
                })
                logger.info(f"✅ Inserted user message before assistant message at position {len(corrected_messages)-1}")
                
                # Now add the assistant message
                corrected_messages.append({"role": "assistant", "content": content})
                expected_role = "user"
            else:
                # Convert other roles to user
                corrected_messages.append({"role": "user", "content": content})
                expected_role = "assistant"
                logger.info(f"✅ Converted role '{role}' to 'user' at position {len(corrected_messages)-1}")
                
        elif expected_role == "assistant" and role != "assistant":
            if role in ["user", "tool"]:
                # Insert an assistant message before this user/tool message
                corrected_messages.append({
                    "role": "assistant",
                    "content": "I understand your request. Let me help you with that."
                })
                logger.info(f"✅ Inserted assistant message before user/tool message at position {len(corrected_messages)-1}")
                
                # Now add the user/tool message
                corrected_messages.append({"role": role, "content": content})
                expected_role = "assistant"
            else:
                # Convert other roles to assistant
                corrected_messages.append({"role": "assistant", "content": content})
                expected_role = "user"
                logger.info(f"✅ Converted role '{role}' to 'assistant' at position {len(corrected_messages)-1}")
        else:
            # Role matches expectation
            corrected_messages.append({"role": role, "content": content})
            
            # Update expected role
            if role in ["user", "tool"]:
                expected_role = "assistant"
            elif role == "assistant":
                expected_role = "user"
    
    # Phase 3: Ensure conversation ends with user/tool message
    if corrected_messages and corrected_messages[-1]["role"] not in ["user", "tool"]:
        if corrected_messages[-1]["role"] == "assistant":
            # Good case - just add a follow-up user message
            corrected_messages.append({
                "role": "user",
                "content": "Please provide any additional information or clarification if needed."
            })
            logger.info("✅ Added follow-up user message to end conversation properly")
        else:
            # Should not happen after Phase 2, but just in case
            corrected_messages[-1]["role"] = "user"
            logger.info(f"✅ Converted final message to 'user' role")
    
    # Phase 4: Final validation
    alternation_valid = validate_message_alternation(corrected_messages)
    if not alternation_valid:
        logger.error("❌ Message alternation validation failed after correction - this should not happen!")
        # Fallback: create minimal valid conversation
        corrected_messages = [
            {"role": "system", "content": "You are a helpful AI assistant."},
            {"role": "user", "content": "Please provide a helpful response based on our conversation context."}
        ]
        logger.info("✅ Applied fallback minimal conversation structure")
    
    logger.info(f"✅ Message alternation validated and corrected: {len(messages)} → {len(corrected_messages)} messages")
    return corrected_messages

def validate_message_alternation(messages: List[Dict[str, Any]]) -> bool:
    """Validate that messages follow proper alternation rules.
    
    Returns True if alternation is valid, False otherwise.
    """
    if not messages:
        return True
    
    # Skip system messages at the start
    idx = 0
    while idx < len(messages) and messages[idx].get("role") == "system":
        idx += 1
    
    if idx >= len(messages):
        # Only system messages - this is valid but should end with user
        return True
    
    # Check alternation pattern
    expected_role_type = "user"  # After system messages, expect user/tool first
    
    for i in range(idx, len(messages)):
        role = messages[i].get("role")
        
        if expected_role_type == "user":
            if role not in ["user", "tool"]:
                logger.debug(f"❌ Alternation violation at index {i}: expected user/tool, got '{role}'")
                return False
            expected_role_type = "assistant"
        else:  # expected_role_type == "assistant"
            if role != "assistant":
                logger.debug(f"❌ Alternation violation at index {i}: expected assistant, got '{role}'")
                return False
            expected_role_type = "user"
    
    # Final message should be user/tool for Perplexity API
    if messages and messages[-1].get("role") not in ["user", "tool"]:
        logger.debug(f"❌ Final message has role '{messages[-1].get('role')}', should be user/tool")
        return False
    
    return True

# Global async task exception handling
def log_async_exceptions(logger=None):
    """Decorator to catch and log exceptions in async tasks"""
    if logger is None:
        logger = logging.getLogger(__name__)
    
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except asyncio.CancelledError:
                # CancelledError should be re-raised to properly cancel tasks
                logger.debug(f"🚫 Task {func.__name__} cancelled")
                raise
            except Exception as e:
                logger.error(f"❌ Unhandled exception in async task {func.__name__}: {e}")
                logger.error(f"Exception traceback: {traceback.format_exc()}")
                
                # For critical inference tasks, trigger session recovery
                if 'inference' in func.__name__.lower() or 'recognize' in func.__name__.lower():
                    logger.error(f"🚨 Critical inference task {func.__name__} failed - triggering recovery")
                    if 'agent_session_recovery' in globals():
                        try:
                            await agent_session_recovery.handle_unrecoverable_error(e, f"async_task_{func.__name__}")
                        except Exception as recovery_error:
                            logger.error(f"❌ Session recovery also failed: {recovery_error}")
                
                # Don't re-raise for non-critical tasks to prevent cascade failures
                if 'monitor' in func.__name__.lower() or 'cleanup' in func.__name__.lower():
                    logger.warning(f"⚠️ Non-critical task {func.__name__} failed, continuing operation")
                    return None
                else:
                    raise
        return wrapper
    return decorator

# Additional session-level validation patch
original_agent_session_generate_reply = None

def patch_agent_session_generate_reply():
    """Patch AgentSession.generate_reply to validate chat context before LLM calls"""
    global original_agent_session_generate_reply
    
    try:
        from livekit.agents import AgentSession
        
        # Store original generate_reply method
        if original_agent_session_generate_reply is None:
            original_agent_session_generate_reply = AgentSession.generate_reply
        
        async def patched_generate_reply(self, *, instructions: str = None, user_input: str = None):
            """Patched generate_reply that validates chat context for Perplexity compatibility"""
            try:
                # Check if we're using Perplexity LLM
                is_perplexity = False
                if hasattr(self, 'llm') and hasattr(self.llm, '_client'):
                    client = self.llm._client
                    if hasattr(client, 'base_url'):
                        base_url_str = str(client.base_url).lower()
                        is_perplexity = 'perplexity' in base_url_str
                    if not is_perplexity and hasattr(client, '_api_key'):
                        api_key = str(client._api_key)[:8]
                        is_perplexity = api_key.startswith('pplx-')
                
                if is_perplexity:
                    logger.info("🔍 AgentSession using Perplexity - validating chat context")
                    
                    # Get current chat context if available
                    if hasattr(self, '_chat_ctx') and self._chat_ctx:
                        chat_ctx = self._chat_ctx
                        if hasattr(chat_ctx, 'messages') and chat_ctx.messages:
                            # Extract messages for validation
                            current_messages = []
                            for msg in chat_ctx.messages:
                                if hasattr(msg, 'role') and hasattr(msg, 'content'):
                                    current_messages.append({
                                        'role': msg.role,
                                        'content': msg.content
                                    })
                            
                            if current_messages:
                                logger.info(f"📝 Pre-generate_reply chat context: {len(current_messages)} messages")
                                
                                # Log current message sequence 
                                for i, msg in enumerate(current_messages):
                                    logger.debug(f"  [{i}] {msg.get('role', 'unknown')}: {msg.get('content', '')[:50]}...")
                                
                                # Validate alternation BEFORE adding new input
                                if not validate_message_alternation(current_messages):
                                    logger.warning(f"⚠️ Chat context has invalid alternation before generate_reply!")
                                
                                # Check if last message follows Perplexity rules
                                last_msg = current_messages[-1]
                                if last_msg.get('role') not in ['user', 'tool']:
                                    logger.warning(f"⚠️ Chat context ends with role '{last_msg.get('role')}' - may cause Perplexity error")
                                
                                # If adding user_input, simulate the final message sequence
                                if user_input:
                                    simulated_messages = current_messages + [{'role': 'user', 'content': user_input}]
                                    if not validate_message_alternation(simulated_messages):
                                        logger.error(f"❌ Adding user_input would create invalid alternation!")
                                        # Fix by adjusting current context
                                        logger.info("🔧 Attempting to fix chat context before adding user input")
                                        fixed_messages = validate_perplexity_message_format(current_messages)
                                        
                                        # Update the chat context with fixed messages
                                        if len(fixed_messages) != len(current_messages):
                                            logger.info(f"🔧 Fixed chat context: {len(current_messages)} → {len(fixed_messages)} messages")
                                            chat_ctx.messages.clear()
                                            for fixed_msg in fixed_messages:
                                                from livekit.agents import ChatMessage
                                                new_msg = ChatMessage.create(
                                                    text=fixed_msg['content'],
                                                    role=fixed_msg['role']
                                                )
                                                chat_ctx.messages.append(new_msg)
                
            except Exception as validation_error:
                logger.error(f"❌ Error in AgentSession validation: {validation_error}")
                logger.error(f"AgentSession validation error traceback: {traceback.format_exc()}")
                # Continue with original behavior if validation fails
            
            # Call original method
            return await original_agent_session_generate_reply(self, instructions=instructions, user_input=user_input)
        
        # Apply the patch
        AgentSession.generate_reply = patched_generate_reply
        logger.info("✅ Applied AgentSession.generate_reply validation patch")
        
    except Exception as patch_error:
        logger.error(f"❌ Failed to apply AgentSession validation patch: {patch_error}")
        logger.error(f"AgentSession patch error traceback: {traceback.format_exc()}")

# Monkey patch the OpenAI LLM to validate Perplexity messages
original_llm_chat = None

def patch_perplexity_llm_validation():
    """Patch LiveKit's OpenAI LLM to validate Perplexity message formats"""
    global original_llm_chat
    
    try:
        from livekit.plugins.openai.llm import LLM as OpenAILLM
        
        # Store original chat method
        if original_llm_chat is None:
            original_llm_chat = OpenAILLM.chat
        
        def patched_chat(self, **kwargs):
            """Patched chat method that validates message format for Perplexity"""
            try:
                # Check if this is a Perplexity LLM - multiple detection methods
                is_perplexity = False
                
                # Method 1: Check base_url
                if hasattr(self, '_client') and hasattr(self._client, 'base_url'):
                    base_url_str = str(self._client.base_url).lower()
                    is_perplexity = 'perplexity' in base_url_str
                    logger.debug(f"🔍 Perplexity detection via base_url: {base_url_str} -> {is_perplexity}")
                
                # Method 2: Check model name if available  
                if not is_perplexity and hasattr(self, '_opts'):
                    model_name = getattr(self._opts, 'model', '').lower()
                    is_perplexity = 'perplexity' in model_name or 'sonar' in model_name
                    logger.debug(f"🔍 Perplexity detection via model: {model_name} -> {is_perplexity}")
                
                # Method 3: Check API key pattern (starts with pplx-)
                if not is_perplexity and hasattr(self, '_client') and hasattr(self._client, '_api_key'):
                    api_key = str(self._client._api_key)[:8]  # Only log first 8 chars for security
                    is_perplexity = api_key.startswith('pplx-')
                    logger.debug(f"🔍 Perplexity detection via API key pattern: {api_key}... -> {is_perplexity}")
                
                if is_perplexity:
                    logger.info("🔧 Detected Perplexity API - applying message validation")
                
                if is_perplexity and 'chat_ctx' in kwargs:
                    chat_ctx = kwargs['chat_ctx']
                    if hasattr(chat_ctx, 'messages') and chat_ctx.messages:
                        # Extract messages for validation
                        original_messages = []
                        for msg in chat_ctx.messages:
                            if hasattr(msg, 'role') and hasattr(msg, 'content'):
                                original_messages.append({
                                    'role': msg.role,
                                    'content': msg.content
                                })
                        
                        if original_messages:
                            # Log original messages for debugging
                            logger.info(f"📝 Original messages before validation: {len(original_messages)} messages")
                            for i, msg in enumerate(original_messages):
                                logger.debug(f"  [{i}] {msg.get('role', 'unknown')}: {msg.get('content', '')[:100]}...")
                            
                            # Check if last message follows Perplexity rules
                            last_msg = original_messages[-1]
                            if last_msg.get('role') not in ['user', 'tool']:
                                logger.warning(f"⚠️ Last message has role '{last_msg.get('role')}' - Perplexity requires 'user' or 'tool'")
                            
                            # Validate and fix message format
                            validated_messages = validate_perplexity_message_format(original_messages)
                            logger.info(f"✅ Perplexity validation: {len(original_messages)} → {len(validated_messages)} messages")
                            
                            # Log validated messages for debugging
                            for i, msg in enumerate(validated_messages):
                                logger.debug(f"  Validated [{i}] {msg.get('role', 'unknown')}: {msg.get('content', '')[:100]}...")
                            
                            # Update the chat_ctx messages if validation made changes
                            if len(validated_messages) != len(original_messages) or validated_messages != original_messages:
                                logger.info(f"🔧 Fixed Perplexity message format: {len(original_messages)} → {len(validated_messages)} messages")
                                
                                # Clear existing messages and add validated ones
                                chat_ctx.messages.clear()
                                for validated_msg in validated_messages:
                                    # Create new message object with validated data
                                    from livekit.agents import ChatMessage
                                    new_msg = ChatMessage.create(
                                        text=validated_msg['content'],
                                        role=validated_msg['role']
                                    )
                                    chat_ctx.messages.append(new_msg)
                                    
                                logger.info(f"✅ Updated chat_ctx with {len(validated_messages)} validated messages")
                                
                                # Verify final message follows Perplexity rules
                                final_msg = validated_messages[-1]
                                if final_msg.get('role') in ['user', 'tool']:
                                    logger.info(f"✅ Final message role '{final_msg.get('role')}' is valid for Perplexity")
                                else:
                                    logger.error(f"❌ Final message role '{final_msg.get('role')}' is INVALID for Perplexity - this should not happen!")
                            else:
                                logger.debug("✅ No message validation changes needed")
                            
            except Exception as validation_error:
                logger.error(f"❌ Error during Perplexity message validation: {validation_error}")
                logger.error(f"Validation error traceback: {traceback.format_exc()}")
                # Continue with original behavior if validation fails
            
            # Call original method with potentially updated chat_ctx
            return original_llm_chat(self, **kwargs)
        
        # Apply the patch
        OpenAILLM.chat = patched_chat
        logger.info("✅ Applied enhanced Perplexity message format validation patch")
        
    except Exception as patch_error:
        logger.error(f"❌ Failed to apply Perplexity validation patch: {patch_error}")
        logger.error(f"Patch error traceback: {traceback.format_exc()}")

# Enhanced OpenAI API error handling
import openai
import random

class OpenAIErrorHandler:
    """Specialized error handler for OpenAI API interactions"""
    
    def __init__(self, max_retries: int = 5, base_delay: float = 1.0, circuit_breaker=None):
        self.max_retries = max_retries
        self.base_delay = base_delay
        # Use weak reference to avoid circular dependencies
        if circuit_breaker:
            import weakref
            self._circuit_breaker_ref = weakref.ref(circuit_breaker)
        else:
            self._circuit_breaker_ref = None
        
    def log_api_interaction(self, request_type: str, status_code: int = None, error: Exception = None, 
                           tokens_used: int = None, request_id: str = None):
        """Log OpenAI API interactions with structured data"""
        log_data = {
            "request_type": request_type,
            "status_code": status_code,
            "tokens_used": tokens_used,
            "request_id": request_id,
            "timestamp": time.time()
        }
        
        if error:
            log_data.update({
                "error_type": type(error).__name__,
                "error_message": str(error),
                "error_code": getattr(error, "code", None)
            })
            
        logger.info(f"📡 OpenAI API {request_type}", extra=log_data)
        
    async def handle_openai_error(self, error: Exception, attempt: int, context: str = "") -> tuple[bool, float, Optional[str]]:
        """
        Handle OpenAI API errors with specific retry logic
        
        Returns:
            (should_retry, delay_seconds, fallback_message)
        """
        error_type = type(error).__name__
        should_retry = False
        delay = 0.0
        fallback_message = None
        
        # Log the error with full context
        self.log_api_interaction(
            request_type=context,
            error=error,
            status_code=getattr(error, "status_code", None)
        )
        
        if isinstance(error, openai.APITimeoutError):
            # Timeout errors - retry with exponential backoff
            should_retry = attempt < self.max_retries
            delay = min(self.base_delay * (2 ** (attempt - 1)) + random.uniform(0, 1), 30)
            fallback_message = f"OpenAI API timeout (attempt {attempt}/{self.max_retries}). Retrying in {delay:.1f}s..."
            
        elif isinstance(error, openai.RateLimitError):
            # Rate limiting - respect retry-after header if present
            should_retry = attempt < self.max_retries
            retry_after = getattr(error, "retry_after", None)
            if retry_after:
                delay = float(retry_after) + random.uniform(0, 1)
            else:
                delay = min(self.base_delay * (2 ** attempt) + random.uniform(0, 3), 60)
            fallback_message = f"OpenAI API rate limited. Retrying in {delay:.1f}s..."
            
        elif isinstance(error, openai.AuthenticationError):
            # Authentication errors - don't retry, likely need new credentials
            should_retry = False
            fallback_message = "OpenAI API authentication failed. Please check API key configuration."
            
        elif isinstance(error, openai.PermissionDeniedError):
            # Permission errors - don't retry
            should_retry = False
            fallback_message = "OpenAI API permission denied. Please check API key permissions."
            
        elif isinstance(error, openai.BadRequestError):
            # Bad request - likely client error, don't retry
            should_retry = False
            error_detail = str(error)[:200]
            fallback_message = f"OpenAI API request error: {error_detail}. Please check request format."
            
        elif isinstance(error, openai.APIStatusError):
            status_code = error.status_code
            
            if status_code == 429:  # Rate limiting (backup check)
                should_retry = attempt < self.max_retries
                delay = min(self.base_delay * (2 ** attempt) + random.uniform(0, 3), 60)
                fallback_message = f"OpenAI API rate limited (HTTP 429). Retrying in {delay:.1f}s..."
                
            elif 500 <= status_code < 600:  # Server errors
                should_retry = attempt < self.max_retries
                delay = min(self.base_delay * (2 ** (attempt - 1)) + random.uniform(0, 2), 20)
                fallback_message = f"OpenAI API server error (HTTP {status_code}). Retrying in {delay:.1f}s..."
                
            elif status_code in [401, 403]:  # Auth errors
                should_retry = False
                fallback_message = f"OpenAI API authentication failed (HTTP {status_code}). Check API key."
                
            elif status_code == 400:  # Client errors
                should_retry = False
                fallback_message = f"OpenAI API client error (HTTP {status_code}). Check request format."
                
            else:
                # Unknown status code - try once more
                should_retry = attempt < min(2, self.max_retries)
                delay = self.base_delay + random.uniform(0, 1)
                fallback_message = f"OpenAI API unexpected status {status_code}. Retrying..."
                
        elif isinstance(error, openai.APIConnectionError):
            # Connection errors - retry with enhanced backoff and circuit breaker coordination
            should_retry = attempt < self.max_retries
            
            # Exponential backoff with jitter, but more aggressive for connection errors
            base_delay = min(2.0 * (1.5 ** (attempt - 1)), 30)  # Increased base delay
            jitter = random.uniform(0, base_delay * 0.3)  # 30% jitter
            delay = base_delay + jitter
            
            error_detail = str(error)[:100]
            fallback_message = f"OpenAI API connection error: {error_detail}. Retrying in {delay:.1f}s... (attempt {attempt}/{self.max_retries})"
            
            # Log additional connection error details
            logger.warning(f"🔌 Connection error details: {error}")
            if hasattr(error, '__cause__') and error.__cause__:
                logger.warning(f"🔌 Root cause: {error.__cause__}")
                
            # Check circuit breaker state for adaptive retry behavior
            if hasattr(self, '_circuit_breaker_ref'):
                cb = self._circuit_breaker_ref()
                if cb and cb.failure_count >= 3:  # If multiple failures, increase delay
                    delay = min(delay * 2, 60)
                    fallback_message = f"API connection issues detected. Extended retry in {delay:.1f}s... (attempt {attempt}/{self.max_retries})"
            
        else:
            # Unknown error type - minimal retry
            should_retry = attempt < min(2, self.max_retries)
            delay = self.base_delay + random.uniform(0, 1)
            fallback_message = f"Unknown OpenAI API error: {error_type}. Retrying..."
        
        if should_retry:
            logger.warning(f"🔄 {fallback_message}")
        else:
            logger.error(f"❌ OpenAI API error (final): {fallback_message}")
            
        return should_retry, delay, fallback_message
    
    async def retry_openai_operation(
        self, 
        operation: Callable, 
        context: str = "OpenAI operation",
        *args, 
        **kwargs
    ) -> Any:
        """
        Execute an OpenAI operation with specialized retry logic
        
        Args:
            operation: The async function to retry
            context: Description of the operation for logging
            *args, **kwargs: Arguments for the operation
            
        Returns:
            Result of the operation or raises the final error
        """
        last_error = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                result = await operation(*args, **kwargs)
                
                # Log successful operation
                self.log_api_interaction(
                    request_type=context,
                    status_code=200,
                    tokens_used=getattr(result, "usage", {}).get("total_tokens") if hasattr(result, "usage") else None
                )
                
                if attempt > 1:
                    logger.info(f"✅ OpenAI operation succeeded on attempt {attempt}")
                return result
                
            except Exception as error:
                last_error = error
                should_retry, delay, fallback_message = await self.handle_openai_error(error, attempt, context)
                
                if not should_retry:
                    break
                    
                if delay > 0:
                    await asyncio.sleep(delay)
        
        # All retries exhausted
        logger.error(f"❌ All retry attempts exhausted for OpenAI {context}")
        raise last_error

# Circuit Breaker Pattern for LLM API Protection
class CircuitBreakerState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

class LLMCircuitBreaker:
    """Circuit breaker to protect against repeated LLM API failures"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0, success_threshold: int = 3):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED
        
        # Statistics for monitoring
        self.total_requests = 0
        self.total_failures = 0
        self.state_change_times = []
        
    def record_success(self):
        """Record a successful operation"""
        self.total_requests += 1
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self._transition_to_closed()
        elif self.state == CircuitBreakerState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0
            
    def record_failure(self):
        """Record a failed operation"""
        self.total_requests += 1
        self.total_failures += 1
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitBreakerState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                self._transition_to_open()
        elif self.state == CircuitBreakerState.HALF_OPEN:
            # Failure in half-open state, go back to open
            self._transition_to_open()
            
    def can_attempt(self) -> tuple[bool, str]:
        """Check if an operation can be attempted
        
        Returns:
            (can_attempt, reason)
        """
        if self.state == CircuitBreakerState.CLOSED:
            return True, "Circuit closed - normal operation"
            
        elif self.state == CircuitBreakerState.OPEN:
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self._transition_to_half_open()
                return True, "Circuit half-open - testing recovery"
            else:
                remaining_time = self.recovery_timeout - (time.time() - self.last_failure_time)
                return False, f"Circuit open - {remaining_time:.1f}s until retry"
                
        elif self.state == CircuitBreakerState.HALF_OPEN:
            return True, "Circuit half-open - limited attempts"
            
        return False, "Circuit breaker error"
        
    def _transition_to_closed(self):
        """Transition to CLOSED state"""
        old_state = self.state
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self._log_state_change(old_state, self.state, "Sufficient successes achieved")
        
    def _transition_to_open(self):
        """Transition to OPEN state"""
        old_state = self.state
        self.state = CircuitBreakerState.OPEN
        self.success_count = 0
        self._log_state_change(old_state, self.state, f"Failure threshold exceeded ({self.failure_count}/{self.failure_threshold})")
        
    def _transition_to_half_open(self):
        """Transition to HALF_OPEN state"""
        old_state = self.state
        self.state = CircuitBreakerState.HALF_OPEN
        self.success_count = 0
        self._log_state_change(old_state, self.state, "Recovery timeout elapsed")
        
    def _log_state_change(self, old_state: CircuitBreakerState, new_state: CircuitBreakerState, reason: str):
        """Log circuit breaker state changes"""
        timestamp = time.time()
        self.state_change_times.append({
            "timestamp": timestamp,
            "old_state": old_state.value,
            "new_state": new_state.value,
            "reason": reason,
            "failure_count": self.failure_count,
            "total_failures": self.total_failures,
            "total_requests": self.total_requests
        })
        
        logger.warning(f"🔧 Circuit Breaker: {old_state.value} → {new_state.value} | {reason}")
        logger.info(f"📊 Circuit Breaker Stats: {self.total_failures}/{self.total_requests} failures, {self.failure_count} consecutive")
        
    def get_stats(self) -> dict:
        """Get circuit breaker statistics"""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "total_requests": self.total_requests,
            "total_failures": self.total_failures,
            "failure_rate": self.total_failures / max(self.total_requests, 1),
            "last_failure_time": self.last_failure_time,
            "state_changes": len(self.state_change_times)
        }

# Global circuit breaker instance
llm_circuit_breaker = LLMCircuitBreaker(failure_threshold=4, recovery_timeout=30.0)

# Global exception handler and session recovery
class AgentSessionRecovery:
    """Handles agent session recovery and graceful degradation"""
    
    def __init__(self, agent_session):
        self.agent_session = agent_session
        self.recovery_attempts = 0
        self.max_recovery_attempts = 3
        self.last_recovery_time = None
        self.recovery_cooldown = 60.0  # 1 minute between recovery attempts
        
    async def handle_unrecoverable_error(self, error: Exception, context: str = "unknown") -> bool:
        """Handle errors that could crash the session
        
        Returns:
            True if recovery was attempted, False if session should be abandoned
        """
        current_time = time.time()
        
        # Check if we're within recovery cooldown
        if (self.last_recovery_time and 
            current_time - self.last_recovery_time < self.recovery_cooldown):
            logger.error(f"🚫 Recovery cooldown active, not attempting recovery for: {error}")
            return False
            
        # Check if we've exceeded max recovery attempts
        if self.recovery_attempts >= self.max_recovery_attempts:
            logger.error(f"🚨 Max recovery attempts ({self.max_recovery_attempts}) exceeded, abandoning session")
            return False
            
        self.recovery_attempts += 1
        self.last_recovery_time = current_time
        
        logger.warning(f"🔄 Attempting session recovery #{self.recovery_attempts} for error: {error}")
        logger.warning(f"🔧 Recovery context: {context}")
        
        try:
            # Attempt to send a recovery message to users
            recovery_message = (
                f"I experienced a technical issue but I'm recovering. "
                f"Please give me a moment to restore normal functionality. "
                f"You can continue the conversation - I'll respond when ready."
            )
            
            await self.agent_session.say(recovery_message)
            logger.info(f"✅ Recovery message sent successfully")
            
            # Reset circuit breaker if it's in a bad state
            if llm_circuit_breaker.state != CircuitBreakerState.CLOSED:
                llm_circuit_breaker._transition_to_closed()
                logger.info(f"🔧 Reset circuit breaker to CLOSED state during recovery")
                
            return True
            
        except Exception as recovery_error:
            logger.error(f"❌ Recovery attempt failed: {recovery_error}")
            return False
    
    def get_recovery_stats(self) -> dict:
        """Get recovery statistics"""
        return {
            "recovery_attempts": self.recovery_attempts,
            "max_recovery_attempts": self.max_recovery_attempts,
            "last_recovery_time": self.last_recovery_time,
            "recovery_cooldown": self.recovery_cooldown
        }

# Global session recovery instance (will be initialized in entrypoint)
agent_session_recovery = None

async def safe_agent_operation(operation: Callable, context: str = "agent operation") -> bool:
    """Safely execute agent operations with session recovery
    
    Args:
        operation: The async function to execute
        context: Description of the operation for logging
        
    Returns:
        True if successful, False if failed but session is still viable
    """
    global agent_session_recovery
    
    try:
        await operation()
        return True
        
    except Exception as error:
        logger.error(f"❌ Agent operation failed: {error}")
        logger.error(f"🔧 Operation context: {context}")
        
        # Determine if this is a recoverable error
        is_recoverable = not isinstance(error, (
            KeyboardInterrupt,
            SystemExit,
            asyncio.CancelledError,
            RuntimeError,  # Usually indicates serious system issues
        ))
        
        if is_recoverable and agent_session_recovery:
            try:
                recovery_success = await agent_session_recovery.handle_unrecoverable_error(error, context)
                if recovery_success:
                    logger.info(f"✅ Session recovery successful for: {context}")
                    return False  # Operation failed but session is viable
                else:
                    logger.error(f"❌ Session recovery failed for: {context}")
                    return False
            except Exception as recovery_error:
                logger.error(f"💥 Recovery handler itself failed: {recovery_error}")
                return False
        else:
            logger.error(f"💥 Unrecoverable error in {context}: {error}")
            # For truly unrecoverable errors, we let them propagate
            raise
        
        return False

# Enhanced error wrapper for function tools
def resilient_function_tool(func):
    """Decorator to make function tools resilient to errors"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as error:
            logger.error(f"❌ Function tool '{func.__name__}' failed: {error}")
            logger.error(f"Function tool error traceback: {traceback.format_exc()}")
            
            # Return a safe error response instead of crashing
            return f"I apologize, but I encountered a technical issue while processing your request for {func.__name__}. Please try again or rephrase your request."
    
    return wrapper

# Create global OpenAI error handler with circuit breaker coordination
openai_error_handler = OpenAIErrorHandler(max_retries=5, base_delay=1.0, circuit_breaker=llm_circuit_breaker)

async def safe_llm_generate_reply(agent_session, instructions: str, context: str = "generate_reply") -> bool:
    """
    Safely generate LLM reply with circuit breaker protection, error handling and retries
    
    Returns:
        True if successful, False if failed with fallback message sent
    """
    # Check circuit breaker state first
    can_attempt, reason = llm_circuit_breaker.can_attempt()
    if not can_attempt:
        logger.warning(f"🚫 Circuit breaker blocked LLM attempt: {reason}")
        try:
            fallback_msg = f"I'm currently experiencing technical difficulties and need a moment to recover. Please try again in a few seconds."
            await agent_session.say(fallback_msg)
            logger.info(f"✅ Sent circuit breaker fallback message")
            return False
        except Exception as fallback_error:
            logger.error(f"❌ Failed to send circuit breaker fallback message: {fallback_error}")
            return False
    
    async def _generate_reply():
        try:
            await agent_session.generate_reply(instructions=instructions)
            return True
        except Exception as generate_error:
            # Log the exact error details for debugging
            logger.error(f"❌ generate_reply failed: {type(generate_error).__name__}: {generate_error}")
            
            # Check if this is a Perplexity message format error
            error_str = str(generate_error).lower()
            if ('last message must have role user or tool' in error_str or 
                'invalid_message' in error_str or
                'message alternation' in error_str):
                logger.error(f"🔥 PERPLEXITY MESSAGE FORMAT ERROR DETECTED!")
                logger.error(f"Error details: {generate_error}")
                
                # This suggests our patch isn't working or isn't being applied correctly
                if hasattr(agent_session, 'llm') and hasattr(agent_session.llm, '_client'):
                    client = agent_session.llm._client
                    if hasattr(client, 'base_url'):
                        logger.error(f"LLM client base_url: {client.base_url}")
                    if hasattr(client, '_api_key'):
                        logger.error(f"LLM API key pattern: {str(client._api_key)[:8]}...")
                        
                logger.error(f"🚨 This error should have been prevented by our message validation patch!")
            
            raise  # Re-raise the error for the retry mechanism
    
    try:
        result = await openai_error_handler.retry_openai_operation(_generate_reply, context)
        
        # Record success with circuit breaker
        llm_circuit_breaker.record_success()
        logger.debug(f"✅ LLM operation successful, circuit breaker state: {llm_circuit_breaker.state.value}")
        
        return result
        
    except Exception as final_error:
        # Record failure with circuit breaker
        llm_circuit_breaker.record_failure()
        
        # Log detailed error information
        logger.error(f"❌ LLM operation failed after all retries: {final_error}")
        logger.error(f"📊 Circuit breaker stats: {llm_circuit_breaker.get_stats()}")
        
        # Send fallback message to user
        try:
            if llm_circuit_breaker.state == CircuitBreakerState.OPEN:
                fallback_msg = "I'm currently experiencing technical difficulties and need a moment to recover. Please try again shortly."
            else:
                fallback_msg = "I apologize, but I'm experiencing technical difficulties. Please try rephrasing your question or try again in a moment."
            
            await agent_session.say(fallback_msg)
            logger.warning(f"⚠️ Sent fallback message due to LLM failure: {final_error}")
            return False
        except Exception as fallback_error:
            logger.error(f"❌ Failed to send fallback message: {fallback_error}")
            return False

async def entrypoint(ctx: JobContext):
    """Main entry point for the Aristotle debate moderator agent"""
    logger.info("🏛️ Debate Moderator Agent starting... (v2.0 - Fixed Async Callbacks)")
    
    # Apply message format validation patches early
    logger.info("🔧 Applying AgentSession and LLM validation patches...")
    patch_agent_session_generate_reply()
    patch_perplexity_llm_validation()

    # Track audio streams and other agents for coordination
    audio_tracks = {}
    other_agents = set()
    
    # Set up connection timeouts and limits
    connection_timeout = 30.0
    max_retries = 3

    # Use synchronous event handlers with asyncio.create_task for async operations
    @ctx.room.on("track_subscribed")
    def on_track_subscribed(track, publication, participant):
        """Handle when we subscribe to an audio track from another participant"""
        @log_async_exceptions(logger)
        async def handle_track_subscribed():
            try:
                if track.kind == TrackKind.AUDIO:
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

                        # Start processing audio frames in the background with exception handling
                        protected_process_audio = log_async_exceptions(logger)(process_audio_stream)
                        asyncio.create_task(protected_process_audio(audio_stream, participant))
                    except Exception as e:
                        logger.error(f"❌ Failed to create audio stream for {participant.identity}: {e}")
            except Exception as e:
                logger.error(f"❌ Error in track_subscribed handler: {e}")
                logger.error(f"Track subscribed error traceback: {traceback.format_exc()}")
        
        # Create task for async operations
        asyncio.create_task(handle_track_subscribed())

    @ctx.room.on("track_unsubscribed")
    def on_track_unsubscribed(track, publication, participant):
        """Handle when we unsubscribe from an audio track"""
        @log_async_exceptions(logger)
        async def handle_track_unsubscribed():
            try:
                if participant.identity in audio_tracks:
                    del audio_tracks[participant.identity]
                    logger.info(f"🔇 Moderator unsubscribed from: {participant.identity}")
            except Exception as e:
                logger.error(f"❌ Error in track_unsubscribed handler: {e}")
        
        # Create task for async operations
        asyncio.create_task(handle_track_unsubscribed())

    @ctx.room.on("participant_connected")
    def on_participant_connected(participant):
        """Handle when a participant connects to the room"""
        @log_async_exceptions(logger)
        async def handle_participant_connected():
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
        
        # Create task for async operations
        asyncio.create_task(handle_participant_connected())

    @ctx.room.on("participant_disconnected")
    def on_participant_disconnected(participant):
        """Handle when a participant disconnects"""
        @log_async_exceptions(logger)
        async def handle_participant_disconnected():
            try:
                logger.info(f"👋 Participant disconnected: {participant.identity}")
                if participant.identity in other_agents:
                    other_agents.remove(participant.identity)
                if participant.identity in audio_tracks:
                    del audio_tracks[participant.identity]
            except Exception as e:
                logger.error(f"❌ Error in participant_disconnected handler: {e}")
        
        # Create task for async operations
        asyncio.create_task(handle_participant_disconnected())

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
    
    # Enhanced LLM configuration with proper timeout and error handling
    llm_config = {
        "temperature": temp,
        "request_timeout": 30.0,  # 30 second timeout for completions
        "max_retries": 0,  # We handle retries manually through our error handler
    }
    
    # Try Perplexity first if available
    if PERPLEXITY_AVAILABLE:
        try:
            # Create Perplexity LLM with proper session management and timeouts
            research_llm = openai.LLM.with_perplexity(
                model="sonar-pro",  # Updated to current Perplexity model (200k context)
                **llm_config
            )
            logger.info(f"✅ Using Perplexity LLM for {moderator_persona} (temp: {temp}, timeout: 30s)")
        except Exception as e:
            logger.warning(f"⚠️ Could not configure Perplexity: {e}")
            logger.warning(f"Perplexity error traceback: {traceback.format_exc()}")
            research_llm = None
    
    # Fallback to OpenAI if Perplexity fails or is unavailable
    if research_llm is None:
        try:
            research_llm = openai.LLM(
                model="gpt-4o-realtime-preview", 
                **llm_config
            )
            logger.info(f"✅ Using OpenAI GPT-4o for {moderator_persona} (temp: {temp}, timeout: 30s)")
        except Exception as e:
            logger.error(f"❌ Failed to configure OpenAI LLM: {e}")
            logger.error(f"OpenAI error traceback: {traceback.format_exc()}")
            # Try basic configuration as last resort
            try:
                research_llm = openai.LLM(
                    model="gpt-4o-realtime-preview", 
                    temperature=temp,
                    request_timeout=30.0
                )
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

            # Initialize session recovery handler
            global agent_session_recovery
            agent_session_recovery = AgentSessionRecovery(agent_session)
            logger.info(f"✅ Session recovery handler initialized")

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
                
                await safe_llm_generate_reply(agent_session, initial_prompt)
                logger.info(f"✅ Initial greeting sent successfully")
            except Exception as greeting_error:
                logger.error(f"❌ Failed to generate initial greeting: {greeting_error}")
                logger.error(f"Greeting error traceback: {traceback.format_exc()}")
                # Don't raise here - the agent can still function without initial greeting

            logger.info(f"🏛️ {moderator_persona} agent is now active and listening for conversations...")

            # Keep the agent session alive - this is critical for LiveKit agents
            # The session will continue running and responding to events automatically
            # We just need to prevent the function from returning
            
            # Start background monitoring task for resource leaks and circuit breaker health
            @log_async_exceptions(logger)
            async def monitor_resources():
                """Periodically check for resource leaks and circuit breaker health"""
                while not shutdown_event.is_set():
                    try:
                        await asyncio.sleep(60)  # Check every minute
                        
                        # Check for resource leaks
                        await check_resource_leaks()
                        
                        # Log circuit breaker statistics
                        cb_stats = llm_circuit_breaker.get_stats()
                        if cb_stats["total_requests"] > 0:
                            logger.info(f"🔧 Circuit Breaker Health Check:")
                            logger.info(f"   State: {cb_stats['state']}")
                            logger.info(f"   Failure Rate: {cb_stats['failure_rate']:.2%} ({cb_stats['total_failures']}/{cb_stats['total_requests']})")
                            logger.info(f"   Consecutive Failures: {cb_stats['failure_count']}")
                            logger.info(f"   State Changes: {cb_stats['state_changes']}")
                            
                            # Alert on high failure rates
                            if cb_stats['failure_rate'] > 0.5:
                                logger.warning(f"⚠️ High LLM failure rate detected: {cb_stats['failure_rate']:.2%}")
                            
                            # Alert if circuit is open for extended periods
                            if cb_stats['state'] == 'OPEN' and cb_stats['last_failure_time']:
                                time_open = time.time() - cb_stats['last_failure_time']
                                if time_open > 300:  # 5 minutes
                                    logger.error(f"🚨 Circuit breaker has been OPEN for {time_open/60:.1f} minutes")
                        
                        # Log session recovery statistics
                        if agent_session_recovery:
                            recovery_stats = agent_session_recovery.get_recovery_stats()
                            if recovery_stats['recovery_attempts'] > 0:
                                logger.info(f"🔄 Session Recovery Health Check:")
                                logger.info(f"   Recovery Attempts: {recovery_stats['recovery_attempts']}/{recovery_stats['max_recovery_attempts']}")
                                logger.info(f"   Last Recovery: {recovery_stats['last_recovery_time']}")
                                
                                # Alert if recovery attempts are high
                                if recovery_stats['recovery_attempts'] >= recovery_stats['max_recovery_attempts']:
                                    logger.error(f"🚨 Session recovery limit reached: {recovery_stats['recovery_attempts']}/{recovery_stats['max_recovery_attempts']}")
                                elif recovery_stats['recovery_attempts'] > 1:
                                    logger.warning(f"⚠️ Multiple recovery attempts: {recovery_stats['recovery_attempts']}")
                        
                    except asyncio.CancelledError:
                        break
                    except Exception as e:
                        logger.warning(f"⚠️ Error in resource monitoring: {e}")
            
            # Set up graceful shutdown handling
            shutdown_event = asyncio.Event()
            monitor_task = asyncio.create_task(monitor_resources())
            
            def signal_handler():
                logger.info(f"🛑 Shutdown signal received for {moderator_persona}")
                shutdown_event.set()
                if monitor_task and not monitor_task.done():
                    monitor_task.cancel()
            
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
                logger.info(f"🔚 {moderator_persona} agent session cleanup starting...")
                
                # Comprehensive resource cleanup
                cleanup_tasks = []
                
                # 1. Clean up agent session
                if hasattr(agent_session, 'aclose'):
                    async def cleanup_agent_session():
                        try:
                            # Cancel monitoring task
                            if monitor_task and not monitor_task.done():
                                monitor_task.cancel()
                                try:
                                    await monitor_task
                                except asyncio.CancelledError:
                                    pass
                            
                            await agent_session.aclose()
                            logger.info(f"✅ Agent session closed successfully")
                        except Exception as cleanup_error:
                            logger.warning(f"⚠️ Error closing agent session: {cleanup_error}")
                    cleanup_tasks.append(cleanup_agent_session())
                
                # 2. Clean up room connection
                if hasattr(ctx.room, 'disconnect'):
                    async def cleanup_room():
                        try:
                            await ctx.room.disconnect()
                            logger.info(f"✅ Room disconnected successfully")
                        except Exception as cleanup_error:
                            logger.warning(f"⚠️ Error disconnecting from room: {cleanup_error}")
                    cleanup_tasks.append(cleanup_room())
                
                # 3. Clean up HTTP sessions
                cleanup_tasks.append(cleanup_http_sessions())
                
                # 4. Clean up LLM resources
                if 'research_llm' in locals() and hasattr(research_llm, 'aclose'):
                    async def cleanup_llm():
                        try:
                            await research_llm.aclose()
                            logger.info(f"✅ LLM resources cleaned up")
                        except Exception as cleanup_error:
                            logger.warning(f"⚠️ Error cleaning up LLM: {cleanup_error}")
                    cleanup_tasks.append(cleanup_llm())
                
                # Execute all cleanup tasks
                if cleanup_tasks:
                    try:
                        await asyncio.gather(*cleanup_tasks, return_exceptions=True)
                        logger.info(f"✅ All resources cleaned up for {moderator_persona}")
                    except Exception as final_cleanup_error:
                        logger.error(f"❌ Error in final cleanup: {final_cleanup_error}")
                
                logger.info(f"🔚 {moderator_persona} agent session ended")
                    
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

async def global_cleanup():
    """Global cleanup function to ensure all resources are properly closed"""
    logger.info("🧹 Performing global cleanup...")
    try:
        # Check for resource leaks before cleanup
        await check_resource_leaks()
        
        # Clean up HTTP sessions
        await cleanup_http_sessions()
        
        # Final resource leak check
        await check_resource_leaks()
        
        logger.info("✅ Global cleanup completed")
    except Exception as e:
        logger.error(f"❌ Error in global cleanup: {e}")

def setup_global_cleanup():
    """Set up global cleanup handlers"""
    import atexit
    
    def sync_cleanup():
        """Synchronous cleanup wrapper for atexit"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create a new task for cleanup
                loop.create_task(global_cleanup())
            else:
                # Run cleanup in new loop
                asyncio.run(global_cleanup())
        except Exception as e:
            logger.error(f"❌ Error in sync cleanup: {e}")
    
    atexit.register(sync_cleanup)
    logger.info("✅ Global cleanup handlers registered")

def main():
    """Main entry point for the debate moderator agent"""
    # Set up global cleanup
    setup_global_cleanup()
    
    cli.run_app(
        WorkerOptions(
            agent_name="moderator",  # Generic name since persona is determined at runtime
            entrypoint_fnc=entrypoint,
        )
    )

if __name__ == "__main__":
    main()
