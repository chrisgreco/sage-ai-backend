# Use Python 3.9 slim image as base
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy the sage-ai-backend directory contents to the working directory
COPY . .

# Install dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 8000

# Default command
CMD ["python", "app.py"] 