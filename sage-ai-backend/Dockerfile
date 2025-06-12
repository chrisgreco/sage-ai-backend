FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies with verbose output
RUN pip install --no-cache-dir -v -r requirements.txt

# Verify installation of livekit-api package
RUN python -c "from livekit import api; print('Successfully imported LiveKit API')"

# Copy application code
COPY . .

# Expose port for web service
EXPOSE 8000

# Command to run the application using uvicorn
# The application will check SERVICE_MODE env var to determine mode
CMD ["python", "app.py"] 