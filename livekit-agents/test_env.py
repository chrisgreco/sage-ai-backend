import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Print environment variables
print("LIVEKIT_URL:", os.environ.get("LIVEKIT_URL"))
print("LIVEKIT_API_KEY:", os.environ.get("LIVEKIT_API_KEY"))
print("LIVEKIT_API_SECRET:", os.environ.get("LIVEKIT_API_SECRET"))
print("OPENAI_API_KEY:", os.environ.get("OPENAI_API_KEY")) 