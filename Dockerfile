# Use Python 3.9 slim image as base
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the sage-ai-backend application
COPY sage-ai-backend/ ./sage-ai-backend/

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "sage-ai-backend.app:app", "--host", "0.0.0.0", "--port", "8000"] 