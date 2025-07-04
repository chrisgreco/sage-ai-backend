# Dockerfile for Sage AI Backend - Optimized Multi-Stage Build
# Stage 1: Build stage for dependencies
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install build dependencies in a single layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    portaudio19-dev \
    python3-dev \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/*

# Copy requirements for dependency installation
COPY requirements.txt .

# Install Python dependencies to user location for copying to final stage
RUN pip install --user --no-cache-dir --disable-pip-version-check -r requirements.txt

# Stage 2: Runtime stage - minimal and optimized
FROM python:3.11-slim as runtime

# Set working directory
WORKDIR /app

# Install only essential runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    portaudio19-dev \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/*

# Copy Python dependencies from builder stage
COPY --from=builder /root/.local /root/.local

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Copy application code (only what's needed)
COPY app.py .
COPY debate_moderator_agent.py .
COPY supabase_memory_manager.py .
COPY example.env .env

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Set environment variables for optimization
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Disable turn detection by default to save space and avoid model downloads
ENV ENABLE_TURN_DETECTION=false

# Health check for web service (lightweight)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Default command runs the web service
# Agent is launched separately as background service in render.yaml
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"] 