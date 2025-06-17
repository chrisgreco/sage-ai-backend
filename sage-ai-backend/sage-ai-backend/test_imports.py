#!/usr/bin/env python
"""
Test script for LiveKit imports
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Try importing from livekit import api (correct)
try:
    from livekit import api
    print("SUCCESS: Imported from livekit import api")
    
    # Try creating a token
    token = api.AccessToken(
        api_key=os.getenv("LIVEKIT_API_KEY", "test-key"),
        api_secret=os.getenv("LIVEKIT_API_SECRET", "test-secret")
    ).with_identity("test-user").to_jwt()
    
    print(f"SUCCESS: Created token: {token[:20]}...")
    
except ImportError as e:
    print(f"ERROR: Could not import from livekit import api: {e}")

# Try importing from livekit.jwt import AccessToken (deprecated)
try:
    from livekit.jwt import AccessToken, VideoGrant
    print("WARNING: Imported from livekit.jwt import AccessToken - this is deprecated")
    
except ImportError as e:
    print(f"EXPECTED ERROR: Could not import from livekit.jwt: {e}") 