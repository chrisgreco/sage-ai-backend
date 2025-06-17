#!/usr/bin/env python3
"""
Quick test script to verify agent launching works correctly
"""

import os
import sys
import subprocess
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_agent_launch():
    """Test if the agent can be launched with the start command"""
    
    print("🧪 Testing Agent Launch")
    print("=" * 50)
    
    # Check required environment variables
    required_vars = ["LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "LIVEKIT_URL", "OPENAI_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {missing_vars}")
        return False
    
    print("✅ All required environment variables found")
    
    # Set test room environment
    env = os.environ.copy()
    env.update({
        "ROOM_NAME": "test-room-123",
        "DEBATE_TOPIC": "Test Topic for Agent Launch"
    })
    
    print("🚀 Launching agent with 'start' command...")
    print(f"Command: python multi_personality_agent.py start")
    
    try:
        # Launch the agent
        process = subprocess.Popen([
            sys.executable, "-u", "multi_personality_agent.py", "start"
        ], 
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
        )
        
        print(f"✅ Agent process launched with PID {process.pid}")
        
        # Monitor for first few seconds
        for i in range(10):
            if process.poll() is not None:
                print(f"❌ Process terminated early with return code: {process.returncode}")
                
                # Get output
                stdout, stderr = process.communicate()
                if stdout:
                    print("\n📄 STDOUT:")
                    print(stdout)
                if stderr:
                    print("\n❌ STDERR:")
                    print(stderr)
                
                return False
            
            print(f"⏱️  Process still running after {i+1} seconds...")
            time.sleep(1)
        
        print("✅ Agent appears to be running successfully!")
        
        # Terminate the test process
        print("🛑 Terminating test process...")
        process.terminate()
        
        # Wait for termination and get final output
        try:
            stdout, stderr = process.communicate(timeout=5)
            if stdout:
                print("\n📄 Final STDOUT:")
                print(stdout[-500:])  # Last 500 chars
        except subprocess.TimeoutExpired:
            process.kill()
            print("⚠️ Process killed due to timeout")
        
        return True
        
    except FileNotFoundError:
        print("❌ multi_personality_agent.py not found")
        return False
    except Exception as e:
        print(f"❌ Error launching agent: {e}")
        return False

if __name__ == "__main__":
    print("Testing Sage AI Agent Launch")
    success = test_agent_launch()
    
    if success:
        print("\n🎉 Test PASSED - Agent can be launched successfully!")
    else:
        print("\n💥 Test FAILED - Agent launch has issues")
    
    sys.exit(0 if success else 1) 