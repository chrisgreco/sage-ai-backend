"""
Enhanced LiveKit agent functionality with production-grade error handling,
session management, turn detection, and resource cleanup.
"""

import asyncio
import time
import signal
import threading
import os
from typing import Dict, Any, Optional, List, Callable
from contextlib import asynccontextmanager
from datetime import datetime

import aiohttp
from livekit import agents
from livekit.agents import AgentSession, Agent, JobContext

from .logging_config import agent_logger, performance_logger


class EnhancedErrorHandler:
    """Enhanced error handling with exponential backoff following Context7 patterns."""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay

    async def handle_api_call(self, 
                            api_func: Callable,
                            api_name: str,
                            *args,
                            **kwargs) -> Any:
        """Handle API calls with retry logic and proper error handling."""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                result = await api_func(*args, **kwargs)
                if attempt > 0:
                    agent_logger.info(f"API call succeeded after {attempt} retries",
                                    api_name=api_name,
                                    attempt=attempt)
                return result
                
            except asyncio.TimeoutError as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** attempt)
                    agent_logger.warning(f"API timeout, retrying in {delay}s",
                                       api_name=api_name,
                                       attempt=attempt,
                                       delay=delay)
                    await asyncio.sleep(delay)
                else:
                    agent_logger.error("API call failed after max retries",
                                     api_name=api_name,
                                     max_retries=self.max_retries,
                                     error="timeout")
            except aiohttp.ClientResponseError as e:
                last_exception = e
                if e.status >= 500 and attempt < self.max_retries:
                    delay = self.base_delay * (2 ** attempt)
                    agent_logger.warning(f"Server error {e.status}, retrying in {delay}s",
                                       api_name=api_name,
                                       attempt=attempt,
                                       status=e.status,
                                       delay=delay)
                    await asyncio.sleep(delay)
                else:
                    agent_logger.error("API call failed",
                                     api_name=api_name,
                                     status=e.status,
                                     error=str(e))
                    break
            except aiohttp.ClientConnectionError as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = self.base_delay * (2 ** attempt)
                    agent_logger.warning(f"Connection error, retrying in {delay}s",
                                       api_name=api_name,
                                       attempt=attempt,
                                       delay=delay)
                    await asyncio.sleep(delay)
                else:
                    agent_logger.error("Connection failed after max retries",
                                     api_name=api_name,
                                     max_retries=self.max_retries,
                                     error=str(e))
            except Exception as e:
                last_exception = e
                agent_logger.error("Unexpected API error",
                                 api_name=api_name,
                                 error=str(e),
                                 error_type=type(e).__name__)
                break
        
        # If we get here, all retries failed
        raise last_exception


class ConversationState:
    """Thread-safe conversation state management."""
    
    def __init__(self):
        self.lock = threading.Lock()
        self.active_speaker = None
        self.turn_queue = []
        self.session_data = {}
        self.error_count = 0
        self.last_activity = time.time()
        
    def claim_turn(self, speaker_id: str) -> bool:
        """Claim speaking turn for a participant."""
        with self.lock:
            if self.active_speaker is None:
                self.active_speaker = speaker_id
                self.last_activity = time.time()
                agent_logger.info("Turn claimed", 
                                speaker_id=speaker_id,
                                metric_type="turn_management")
                return True
            return False
    
    def release_turn(self, speaker_id: str) -> bool:
        """Release speaking turn."""
        with self.lock:
            if self.active_speaker == speaker_id:
                self.active_speaker = None
                self.last_activity = time.time()
                agent_logger.info("Turn released", 
                                speaker_id=speaker_id,
                                metric_type="turn_management")
                return True
            return False
    
    def update_session_data(self, key: str, value: Any):
        """Update session data in a thread-safe manner."""
        with self.lock:
            self.session_data[key] = value
            self.last_activity = time.time()
    
    def get_session_data(self, key: str, default=None):
        """Get session data in a thread-safe manner."""
        with self.lock:
            return self.session_data.get(key, default)
    
    def increment_error_count(self):
        """Increment error count for this session."""
        with self.lock:
            self.error_count += 1
            return self.error_count


class EnhancedAgentSession:
    """Enhanced agent session with production features."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.conversation_state = ConversationState()
        self.error_handler = EnhancedErrorHandler()
        self.resources = []  # Track resources for cleanup
        self.background_tasks = set()  # Track background tasks
        self.start_time = time.time()
        self.is_active = True
        
    async def __aenter__(self):
        """Async context manager entry."""
        performance_logger.log_session_event(
            event_type="session_start",
            session_id=self.session_id
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup."""
        await self.cleanup()
        
        duration = time.time() - self.start_time
        performance_logger.log_session_event(
            event_type="session_end",
            session_id=self.session_id,
            duration=duration,
            error_count=self.conversation_state.error_count
        )
    
    def add_resource(self, resource):
        """Add a resource to be cleaned up on session end."""
        self.resources.append(resource)
    
    def add_background_task(self, task: asyncio.Task):
        """Add a background task to be cancelled on session end."""
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)
    
    async def call_perplexity_api(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Call Perplexity API with enhanced error handling and safe logging."""
        # Validate message format before sending
        if not self._validate_perplexity_payload(payload):
            raise ValueError("Invalid Perplexity API payload format")
        
        # Safe logging of request payload (avoid logging large content)
        safe_payload_info = {
            "model": payload.get("model", "unknown"),
            "message_count": len(payload.get("messages", [])),
            "temperature": payload.get("temperature"),
            "max_tokens": payload.get("max_tokens")
        }
        agent_logger.debug("Making Perplexity API call", **safe_payload_info)
        
        async def _api_call():
            # Configure aiohttp session with proper cleanup to prevent unclosed session errors
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            connector = aiohttp.TCPConnector(
                limit=100, 
                limit_per_host=30,
                ttl_dns_cache=300,
                use_dns_cache=True,
                enable_cleanup_closed=True  # Critical: enables cleanup of closed connections
            )
            
            try:
                # Use proper async context manager - this prevents unclosed session errors
                async with aiohttp.ClientSession(
                    connector=connector,
                    timeout=timeout,
                    headers={
                        "User-Agent": "LiveKit-Agent/1.0"
                    }
                ) as session:
                    async with session.post(
                        "https://api.perplexity.ai/chat/completions",
                        json=payload,
                        headers={
                            "Authorization": f"Bearer {os.getenv('PERPLEXITY_API_KEY')}",
                            "Content-Type": "application/json"
                        }
                    ) as response:
                        response.raise_for_status()
                        result = await response.json()
                        
                        # Safe logging of response (avoid logging large content)
                        if result and "choices" in result:
                            content_length = len(result["choices"][0].get("message", {}).get("content", "")) if result["choices"] else 0
                            agent_logger.debug("Perplexity API response received", 
                                             status=response.status,
                                             choices_count=len(result["choices"]),
                                             content_length=content_length)
                        
                        return result
                        
            except aiohttp.ClientError as e:
                agent_logger.error("Perplexity API client error", error=str(e))
                raise
            except asyncio.TimeoutError as e:
                agent_logger.error("Perplexity API timeout", error=str(e))
                raise
            finally:
                # Ensure connector is properly closed to prevent unclosed connector warnings
                if not connector.closed:
                    await connector.close()
        
        return await self.error_handler.handle_api_call(
            _api_call,
            "perplexity_api"
        )
    
    def _validate_perplexity_payload(self, payload: Dict[str, Any]) -> bool:
        """Validate Perplexity API payload format."""
        if "messages" not in payload:
            return False
        
        messages = payload["messages"]
        if not messages:
            return False
        
        # Check last message has required role
        last_message = messages[-1]
        if last_message.get("role") not in ["user", "tool"]:
            agent_logger.error("Invalid message role in Perplexity payload",
                             last_role=last_message.get("role"),
                             required_roles=["user", "tool"])
            return False
        
        # Check message alternation
        for i in range(1, len(messages)):
            prev_role = messages[i-1].get("role")
            curr_role = messages[i].get("role")
            
            if prev_role == curr_role and curr_role in ["user", "assistant"]:
                agent_logger.error("Invalid message alternation in Perplexity payload",
                                 prev_role=prev_role,
                                 curr_role=curr_role,
                                 position=i)
                return False
        
        return True
    
    async def cleanup(self):
        """Clean up all resources and background tasks."""
        self.is_active = False
        
        # Cancel all background tasks
        for task in list(self.background_tasks):
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Close all resources
        for resource in self.resources:
            try:
                if hasattr(resource, 'close'):
                    if asyncio.iscoroutinefunction(resource.close):
                        await resource.close()
                    else:
                        resource.close()
                elif hasattr(resource, '__aexit__'):
                    await resource.__aexit__(None, None, None)
            except Exception as e:
                agent_logger.error("Error closing resource during cleanup",
                                 resource_type=type(resource).__name__,
                                 error=str(e))
        
        agent_logger.info("Session cleanup completed",
                        session_id=self.session_id,
                        resources_cleaned=len(self.resources),
                        tasks_cancelled=len(self.background_tasks))


class AgentManager:
    """Manages multiple agent sessions with graceful shutdown."""
    
    def __init__(self):
        self.sessions: Dict[str, EnhancedAgentSession] = {}
        self.shutdown_event = asyncio.Event()
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            agent_logger.info("Received shutdown signal", signal=signum)
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def create_session(self, session_id: str) -> EnhancedAgentSession:
        """Create a new enhanced agent session."""
        session = EnhancedAgentSession(session_id)
        self.sessions[session_id] = session
        
        agent_logger.info("Created new agent session",
                        session_id=session_id,
                        total_sessions=len(self.sessions))
        
        return session
    
    async def get_session(self, session_id: str) -> Optional[EnhancedAgentSession]:
        """Get an existing session."""
        return self.sessions.get(session_id)
    
    async def remove_session(self, session_id: str):
        """Remove and cleanup a session."""
        if session_id in self.sessions:
            session = self.sessions.pop(session_id)
            await session.cleanup()
            
            agent_logger.info("Removed agent session",
                            session_id=session_id,
                            remaining_sessions=len(self.sessions))
    
    async def shutdown(self):
        """Graceful shutdown of all sessions."""
        agent_logger.info("Starting graceful shutdown",
                        active_sessions=len(self.sessions))
        
        self.shutdown_event.set()
        
        # Cleanup all sessions
        cleanup_tasks = []
        for session_id, session in self.sessions.items():
            cleanup_tasks.append(session.cleanup())
        
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        self.sessions.clear()
        agent_logger.info("Graceful shutdown completed")


# Global agent manager instance
agent_manager = AgentManager()


@asynccontextmanager
async def get_enhanced_session(session_id: str):
    """Context manager for enhanced agent sessions."""
    session = await agent_manager.create_session(session_id)
    try:
        async with session:
            yield session
    finally:
        await agent_manager.remove_session(session_id)


class PerplexityClient:
    """Shared Perplexity API client with proper session management following Context7 patterns."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('PERPLEXITY_API_KEY')
        if not self.api_key:
            raise ValueError("Perplexity API key is required")
        
        self.session: Optional[aiohttp.ClientSession] = None
        self.error_handler = EnhancedErrorHandler()
        self._session_lock = asyncio.Lock()
        
    async def __aenter__(self):
        """Async context manager entry - create shared session."""
        await self._ensure_session()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup session."""
        await self.close()
    
    async def _ensure_session(self):
        """Ensure we have an active session, create if needed."""
        async with self._session_lock:
            if self.session is None or self.session.closed:
                # Following Context7 pattern for proper session management
                timeout = aiohttp.ClientTimeout(total=30, connect=10)
                connector = aiohttp.TCPConnector(
                    limit=10,  # Reduced connection pool size
                    limit_per_host=5,
                    ttl_dns_cache=300,
                    use_dns_cache=True,
                    enable_cleanup_closed=True
                )
                
                self.session = aiohttp.ClientSession(
                    connector=connector,
                    timeout=timeout,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "User-Agent": "LiveKit-Agent/1.0"
                    }
                )
                agent_logger.debug("Created new Perplexity session")

    async def call_api(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Call Perplexity API using shared session."""
        await self._ensure_session()
        
        # Validate payload
        if not self._validate_payload(payload):
            raise ValueError("Invalid Perplexity API payload format")
        
        # Safe logging
        safe_info = {
            "model": payload.get("model", "unknown"),
            "message_count": len(payload.get("messages", [])),
            "temperature": payload.get("temperature"),
            "max_tokens": payload.get("max_tokens")
        }
        agent_logger.debug("Making Perplexity API call", **safe_info)
        
        async def _api_call():
            async with self.session.post(
                "https://api.perplexity.ai/chat/completions",
                json=payload
            ) as response:
                response.raise_for_status()
                result = await response.json()
                
                # Safe response logging
                if result and "choices" in result:
                    content_length = len(result["choices"][0].get("message", {}).get("content", "")) if result["choices"] else 0
                    agent_logger.debug("Perplexity API response received", 
                                     status=response.status,
                                     choices_count=len(result["choices"]),
                                     content_length=content_length)
                
                return result
        
        return await self.error_handler.handle_api_call(
            _api_call,
            "perplexity_api"
        )
    
    def _validate_payload(self, payload: Dict[str, Any]) -> bool:
        """Validate Perplexity API payload format."""
        if "messages" not in payload:
            return False
        
        messages = payload["messages"]
        if not messages:
            return False
        
        # Check last message has required role
        last_message = messages[-1]
        if last_message.get("role") not in ["user", "tool"]:
            agent_logger.error("Invalid message role in Perplexity payload",
                             last_role=last_message.get("role"),
                             required_roles=["user", "tool"])
            return False
        
        return True
    
    async def close(self):
        """Close the session and cleanup resources."""
        if self.session and not self.session.closed:
            await self.session.close()
            agent_logger.debug("Closed Perplexity session")


class PerplexityLLM:
    """Simplified Perplexity LLM following Context7 patterns with shared client."""
    
    def __init__(self, 
                 model: str = "llama-3.1-sonar-small-128k-chat",
                 api_key: str = None,
                 temperature: float = 0.3):
        self.model = model
        self.temperature = temperature
        self._client: Optional[PerplexityClient] = None
        self._api_key = api_key
        
    async def _get_client(self) -> PerplexityClient:
        """Get or create shared client."""
        if self._client is None:
            self._client = PerplexityClient(api_key=self._api_key)
            await self._client._ensure_session()
        return self._client
    
    async def agenerate(self, prompt: str) -> Any:
        """Generate response using Perplexity API with shared client."""
        try:
            client = await self._get_client()
            
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": self.temperature,
                "max_tokens": 1000,
                "stream": False
            }
            
            result = await client.call_api(payload)
            
            # Mock response object for compatibility
            class MockMessage:
                def __init__(self, content):
                    self.content = content
            
            class MockChoice:
                def __init__(self, content):
                    self.message = MockMessage(content)
            
            class MockResponse:
                def __init__(self, content):
                    self.choices = [MockChoice(content)]
            
            if result and "choices" in result and result["choices"]:
                content = result["choices"][0]["message"]["content"]
                return MockResponse(content)
            else:
                agent_logger.warning("Empty response from Perplexity API")
                return MockResponse("I apologize, but I'm unable to provide a response at the moment.")
                
        except Exception as e:
            agent_logger.error(f"Error in Perplexity LLM generation: {str(e)}")
            # Return fallback response
            return MockResponse("I'm experiencing technical difficulties and cannot provide fact-checking at the moment.")
    
    async def close(self):
        """Close the client connection."""
        if self._client:
            await self._client.close()


# Global shared client instance
_global_perplexity_client: Optional[PerplexityClient] = None

@asynccontextmanager
async def get_perplexity_client():
    """Get shared Perplexity client instance following Context7 patterns."""
    global _global_perplexity_client
    
    if _global_perplexity_client is None:
        _global_perplexity_client = PerplexityClient()
    
    try:
        async with _global_perplexity_client as client:
            yield client
    finally:
        # Client will be cleaned up by its own context manager
        pass


def with_perplexity(
    *,
    model: str = "llama-3.1-sonar-small-128k-chat",
    api_key: str = None,
    temperature: float = 0.3
) -> PerplexityLLM:
    """Create PerplexityLLM instance with proper resource management."""
    return PerplexityLLM(
        model=model,
        api_key=api_key,
        temperature=temperature
    )


# Cleanup function for global resources
async def cleanup_global_resources():
    """Cleanup global resources on shutdown."""
    global _global_perplexity_client
    if _global_perplexity_client:
        await _global_perplexity_client.close()
        _global_perplexity_client = None


# Setup signal handlers for cleanup
def _setup_cleanup_handlers():
    """Setup signal handlers for graceful cleanup."""
    def signal_handler(signum, frame):
        agent_logger.info("Received shutdown signal, cleaning up resources", signal=signum)
        asyncio.create_task(cleanup_global_resources())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

_setup_cleanup_handlers() 