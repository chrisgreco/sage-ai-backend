"""
Webhook endpoint for receiving Render log streams.
Provides real-time error monitoring and alerting capabilities.
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, List

import httpx
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from pydantic import BaseModel

from ..logging_config import agent_logger


class LogEvent(BaseModel):
    """Model for log events received from Render."""
    timestamp: str
    level: str
    message: str
    service: Optional[str] = None
    instance: Optional[str] = None
    source: Optional[str] = None


class AlertManager:
    """Manages alerting for critical errors and events."""
    
    def __init__(self):
        self.slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        self.email_webhook_url = os.getenv("EMAIL_WEBHOOK_URL")
        self.alert_threshold = int(os.getenv("ALERT_THRESHOLD", "5"))  # errors per minute
        self.error_counts = {}  # Track error frequency
        
    async def send_slack_alert(self, message: str, severity: str = "error"):
        """Send alert to Slack."""
        if not self.slack_webhook_url:
            agent_logger.warning("Slack webhook URL not configured")
            return
            
        color = {
            "error": "#ff0000",
            "warning": "#ffaa00", 
            "critical": "#800000"
        }.get(severity, "#ff0000")
        
        payload = {
            "attachments": [{
                "color": color,
                "title": f"🚨 LiveKit Agent Alert - {severity.upper()}",
                "text": message,
                "timestamp": datetime.utcnow().timestamp(),
                "fields": [
                    {
                        "title": "Service",
                        "value": "LiveKit Agent",
                        "short": True
                    },
                    {
                        "title": "Environment", 
                        "value": os.getenv("ENVIRONMENT", "production"),
                        "short": True
                    }
                ]
            }]
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.slack_webhook_url, json=payload)
                response.raise_for_status()
                agent_logger.info("Slack alert sent successfully", 
                                severity=severity, 
                                message=message)
        except Exception as e:
            agent_logger.error("Failed to send Slack alert", 
                             error=str(e), 
                             severity=severity)
    
    async def send_email_alert(self, subject: str, body: str):
        """Send email alert."""
        if not self.email_webhook_url:
            agent_logger.warning("Email webhook URL not configured")
            return
            
        payload = {
            "subject": f"[LiveKit Agent] {subject}",
            "body": body,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.email_webhook_url, json=payload)
                response.raise_for_status()
                agent_logger.info("Email alert sent successfully", subject=subject)
        except Exception as e:
            agent_logger.error("Failed to send email alert", 
                             error=str(e), 
                             subject=subject)
    
    def should_alert(self, error_type: str) -> bool:
        """Determine if we should send an alert based on error frequency."""
        now = datetime.utcnow()
        minute_key = now.strftime("%Y-%m-%d %H:%M")
        
        if error_type not in self.error_counts:
            self.error_counts[error_type] = {}
            
        # Clean up old entries (older than 5 minutes)
        cutoff_time = now.timestamp() - 300  # 5 minutes
        self.error_counts[error_type] = {
            k: v for k, v in self.error_counts[error_type].items() 
            if datetime.fromisoformat(k.replace(" ", "T")).timestamp() > cutoff_time
        }
        
        # Count errors in current minute
        current_count = self.error_counts[error_type].get(minute_key, 0)
        self.error_counts[error_type][minute_key] = current_count + 1
        
        return current_count >= self.alert_threshold
    
    async def process_error_log(self, log_event: LogEvent):
        """Process error logs and trigger alerts if needed."""
        error_patterns = {
            "api_error": ["APIStatusError", "APIConnectionError", "400 Bad Request"],
            "livekit_error": ["LiveKit", "agent", "session"],
            "perplexity_error": ["Perplexity", "message role", "user or tool"],
            "deployment_error": ["ResolutionImpossible", "dependency", "pip install"]
        }
        
        message_lower = log_event.message.lower()
        
        for error_type, patterns in error_patterns.items():
            if any(pattern.lower() in message_lower for pattern in patterns):
                if self.should_alert(error_type):
                    await self.send_alert_for_error_type(error_type, log_event)
                break
    
    async def send_alert_for_error_type(self, error_type: str, log_event: LogEvent):
        """Send appropriate alert based on error type."""
        severity = "critical" if error_type in ["deployment_error"] else "error"
        
        alert_message = f"""
**Error Type:** {error_type}
**Timestamp:** {log_event.timestamp}
**Service:** {log_event.service or 'Unknown'}
**Message:** {log_event.message}

**Action Required:** Please investigate immediately.
        """.strip()
        
        # Send both Slack and email for critical errors
        if severity == "critical":
            await asyncio.gather(
                self.send_slack_alert(alert_message, severity),
                self.send_email_alert(f"Critical Error: {error_type}", alert_message),
                return_exceptions=True
            )
        else:
            await self.send_slack_alert(alert_message, severity)


# Global alert manager instance
alert_manager = AlertManager()

# Create router
router = APIRouter(prefix="/api/logs", tags=["logging"])


@router.post("/webhook")
async def log_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Webhook endpoint for receiving Render log streams.
    Processes logs and triggers alerts for critical errors.
    """
    try:
        # Parse the incoming log event
        payload = await request.json()
        
        # Handle different log formats from Render
        if isinstance(payload, list):
            # Batch of log events
            log_events = [LogEvent(**event) for event in payload]
        else:
            # Single log event
            log_events = [LogEvent(**payload)]
        
        # Process each log event
        for log_event in log_events:
            agent_logger.info("Received log event from Render", 
                            level=log_event.level,
                            service=log_event.service,
                            message=log_event.message[:100])  # Truncate for logging
            
            # Process error logs in background
            if log_event.level in ["ERROR", "CRITICAL"]:
                background_tasks.add_task(
                    alert_manager.process_error_log, 
                    log_event
                )
        
        return {"status": "received", "processed": len(log_events)}
        
    except Exception as e:
        agent_logger.error("Failed to process log webhook", 
                         error=str(e), 
                         exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process logs")


@router.post("/test-alert")
async def test_alert(background_tasks: BackgroundTasks):
    """Test endpoint for alert functionality."""
    test_log = LogEvent(
        timestamp=datetime.utcnow().isoformat(),
        level="ERROR",
        message="Test error for alert system validation",
        service="livekit_agent"
    )
    
    background_tasks.add_task(alert_manager.process_error_log, test_log)
    return {"status": "test alert queued"}


@router.get("/health")
async def health_check():
    """Health check endpoint for the log webhook service."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "log_webhook",
        "alerts_configured": {
            "slack": bool(alert_manager.slack_webhook_url),
            "email": bool(alert_manager.email_webhook_url)
        }
    }


@router.get("/metrics")
async def get_metrics():
    """Get current error metrics and counts."""
    return {
        "error_counts": alert_manager.error_counts,
        "alert_threshold": alert_manager.alert_threshold,
        "timestamp": datetime.utcnow().isoformat()
    } 