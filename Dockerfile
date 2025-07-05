# Dockerfile for Sage AI Backend - Simplified Single Stage Build
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
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/*

# Upgrade pip first
RUN pip install --upgrade pip

# Copy requirements and install Python dependencies
COPY requirements.txt .

# Install FastAPI first to ensure it's available
RUN pip install --no-cache-dir fastapi==0.104.1 uvicorn[standard]==0.24.0 pydantic==2.5.0

# Install remaining dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .
COPY debate_moderator_agent.py .
COPY supabase_memory_manager.py .
COPY test_imports.py .

# Copy knowledge documents for the AI agents
COPY knowledge_documents/ ./knowledge_documents/

# Test that all imports work
RUN python test_imports.py

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Set environment variables for optimization
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Health check for web service
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Default command runs the web service
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"] 