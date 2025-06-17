# Use Python 3.9 slim image as base
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy everything
COPY . .

# Copy the agent file to root level for easy access
COPY sage-ai-backend/multi_personality_agent.py ./multi_personality_agent.py

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 8000

# Default command
CMD ["python", "app.py"] 