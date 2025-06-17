# Use Python 3.9 slim image as base
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Set working directory to sage-ai-backend where the agent files are located
WORKDIR /app/sage-ai-backend

# Expose port
EXPOSE 8000

# Command to run the application - for web service use app.py, for background worker use multi_personality_agent.py
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"] 