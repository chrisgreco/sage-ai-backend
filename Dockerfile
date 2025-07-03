# Dockerfile for LiveKit Debate Moderator Agent
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for LiveKit
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    portaudio19-dev \
    python3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY debate_moderator_agent.py .
COPY example.env .env

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check - simple process check since no HTTP server
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD pgrep -f "debate_moderator_agent.py" || exit 1

# Default command - run LiveKit agent
CMD ["python", "debate_moderator_agent.py", "start"] 