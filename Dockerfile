# syntax=docker/dockerfile:1
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for audio processing and compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    portaudio19-dev \
    python3-dev \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install wheel
RUN pip install --upgrade pip wheel

# Copy requirements file first for better layer caching
COPY requirements.txt .

# Install Python dependencies with cache mount for better performance
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .
COPY debate_moderator_agent.py .
COPY supabase_memory_manager.py .

# Copy knowledge documents for the AI agents
COPY knowledge_documents/ ./knowledge_documents/

# Download turn-detector model files using LiveKit agents CLI
# This is the correct way according to LiveKit documentation
RUN python debate_moderator_agent.py download-files

# Expose port 8000 for the FastAPI backend
EXPOSE 8000

# Health check for the backend service
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command runs the FastAPI backend
# The agent is launched dynamically by the backend when rooms are created
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"] 