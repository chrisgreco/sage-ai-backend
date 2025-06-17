# Use Python 3.9 slim image as base
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

<<<<<<< HEAD
# Copy the rest of the application
COPY . .
=======
# Copy the sage-ai-backend application
COPY sage-ai-backend/ ./sage-ai-backend/
>>>>>>> f9c00ce7acd928a1089fc02ab4cdf9e509bf5fc5

# Expose port
EXPOSE 8000

# Command to run the application
<<<<<<< HEAD
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"] 
=======
CMD ["uvicorn", "sage-ai-backend.app:app", "--host", "0.0.0.0", "--port", "8000"] 
>>>>>>> f9c00ce7acd928a1089fc02ab4cdf9e509bf5fc5
