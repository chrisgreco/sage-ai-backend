"""
Structured logging configuration for Render log streams integration.
Provides JSON-formatted logging with proper error handling and monitoring capabilities.
"""

import logging
import sys
import json
import time
from typing import Dict, Any, Optional
from datetime import datetime


class JsonFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": record.thread,
            "process": record.process,
        }
        
        # Add exception information if present
        if record.exc_info:
            log_record["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info)
            }
        
        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_record.update(record.extra_fields)
            
        return json.dumps(log_record, ensure_ascii=False)


class LiveKitAgentLogger:
    """Enhanced logger for LiveKit agent applications with production-grade features."""
    
    def __init__(self, name: str = "livekit_agent", level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.setup_logger(level)
        
    def setup_logger(self, level: str):
        """Setup structured JSON logging for production."""
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Create console handler with JSON formatter
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        
        # Set log level
        log_level = getattr(logging, level.upper(), logging.INFO)
        self.logger.setLevel(log_level)
        handler.setLevel(log_level)
        
        self.logger.addHandler(handler)
        
        # Prevent propagation to root logger
        self.logger.propagate = False
        
    def log_with_context(self, level: str, message: str, **context):
        """Log with additional context fields."""
        extra_fields = {
            "service": "livekit_agent",
            "environment": "production",
            **context
        }
        
        # Create a custom log record with extra fields
        record = self.logger.makeRecord(
            self.logger.name,
            getattr(logging, level.upper()),
            __file__,
            0,
            message,
            (),
            None
        )
        record.extra_fields = extra_fields
        self.logger.handle(record)
        
    def info(self, message: str, **context):
        """Log info message with context."""
        self.log_with_context("INFO", message, **context)
        
    def warning(self, message: str, **context):
        """Log warning message with context."""
        self.log_with_context("WARNING", message, **context)
        
    def error(self, message: str, **context):
        """Log error message with context."""
        self.log_with_context("ERROR", message, **context)
        
    def critical(self, message: str, **context):
        """Log critical message with context."""
        self.log_with_context("CRITICAL", message, **context)
        
    def debug(self, message: str, **context):
        """Log debug message with context."""
        self.log_with_context("DEBUG", message, **context)


class PerformanceLogger:
    """Logger for performance metrics and monitoring."""
    
    def __init__(self, logger: LiveKitAgentLogger):
        self.logger = logger
        
    def log_api_call(self, 
                     api_name: str, 
                     duration: float, 
                     status_code: Optional[int] = None,
                     error: Optional[str] = None,
                     **context):
        """Log API call performance metrics."""
        self.logger.info(
            f"API call completed: {api_name}",
            api_name=api_name,
            duration_ms=round(duration * 1000, 2),
            status_code=status_code,
            error=error,
            metric_type="api_call",
            **context
        )
        
    def log_session_event(self, 
                         event_type: str, 
                         session_id: str,
                         duration: Optional[float] = None,
                         **context):
        """Log session lifecycle events."""
        self.logger.info(
            f"Session event: {event_type}",
            event_type=event_type,
            session_id=session_id,
            duration_ms=round(duration * 1000, 2) if duration else None,
            metric_type="session_event",
            **context
        )
        
    def log_agent_state(self, 
                       state: str, 
                       session_id: str,
                       previous_state: Optional[str] = None,
                       **context):
        """Log agent state changes."""
        self.logger.info(
            f"Agent state changed: {previous_state} -> {state}",
            current_state=state,
            previous_state=previous_state,
            session_id=session_id,
            metric_type="agent_state",
            **context
        )


# Global logger instances
agent_logger = LiveKitAgentLogger()
performance_logger = PerformanceLogger(agent_logger)


def get_logger(name: str = "livekit_agent") -> LiveKitAgentLogger:
    """Get a configured logger instance."""
    return LiveKitAgentLogger(name)


def setup_global_logging(level: str = "INFO"):
    """Setup global logging configuration."""
    global agent_logger
    agent_logger = LiveKitAgentLogger("livekit_agent", level)
    
    # Setup Python's root logger to also use JSON formatting
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        root_logger.addHandler(handler)
        root_logger.setLevel(getattr(logging, level.upper(), logging.INFO)) 