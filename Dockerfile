# Dockerfile for Sage AI Backend - Web Service and LiveKit Agent
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for LiveKit and FastAPI
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    portaudio19-dev \
    python3-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .
COPY debate_moderator_agent.py .
COPY supabase_memory_manager.py .
COPY example.env .env

# Download required model files for LiveKit plugins
# This ensures models are available at runtime and improves startup time
RUN python debate_moderator_agent.py download-files || echo "Model download skipped (optional)"

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check for web service
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Default command runs the web service
# Agent is launched separately as background service in render.yaml
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"] 