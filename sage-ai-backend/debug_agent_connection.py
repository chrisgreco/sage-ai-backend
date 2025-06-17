#!/usr/bin/env python3

"""
Debug Agent Connection Issues
===========================

This script helps diagnose why AI agents aren't properly connecting to LiveKit rooms.
Run this to get detailed information about agent startup and connection issues.
"""

import os
import sys
import time
import logging
import subprocess
import asyncio
from dotenv import load_dotenv

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_environment():
    """Check if all required environment variables are set"""
    print("🔍 Checking Environment Variables...")
    
    required_vars = [
        "LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET",
        "OPENAI_API_KEY", "DEEPGRAM_API_KEY", "CARTESIA_API_KEY"
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {'*' * 8}...{value[-4:] if len(value) > 4 else '***'}")
        else:
            print(f"❌ {var}: NOT SET")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n⚠️  Missing environment variables: {', '.join(missing_vars)}")
        return False
    else:
        print("\n✅ All required environment variables are set")
        return True

def check_dependencies():
    """Check if required Python packages are installed"""
    print("\n🔍 Checking Python Dependencies...")
    
    required_packages = [
        ("livekit-agents", "livekit.agents"),
        ("livekit", "livekit"),
        ("openai", "openai"),
        ("python-dotenv", "dotenv"),
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn")
    ]
    
    missing_packages = []
    for package_name, import_name in required_packages:
        try:
            __import__(import_name)
            print(f"✅ {package_name}: Installed")
        except ImportError:
            print(f"❌ {package_name}: NOT INSTALLED")
            missing_packages.append(package_name)
    
    if missing_packages:
        print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
        print("Install with: pip install " + " ".join(missing_packages))
        return False
    else:
        print("\n✅ All required packages are installed")
        return True

def check_files():
    """Check if required files exist"""
    print("\n🔍 Checking Required Files...")
    
    required_files = [
        "multi_personality_agent.py",
        "app.py"
    ]
    
    missing_files = []
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file}: Found")
        else:
            print(f"❌ {file}: NOT FOUND")
            missing_files.append(file)
    
    if missing_files:
        print(f"\n⚠️  Missing files: {', '.join(missing_files)}")
        return False
    else:
        print("\n✅ All required files exist")
        return True

async def test_agent_startup():
    """Test agent startup with detailed logging"""
    print("\n🚀 Testing Agent Startup...")
    
    # Set up environment
    env = os.environ.copy()
    env.update({
        "ROOM_NAME": "debug-test-room",
        "DEBATE_TOPIC": "Test Topic for Debugging",
        "LIVEKIT_LOG_LEVEL": "debug"
    })
    
    try:
        print("Starting agent process...")
        process = subprocess.Popen([
            sys.executable, "-u", "multi_personality_agent.py"
        ], 
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        print(f"✅ Agent process started with PID: {process.pid}")
        
        # Monitor process for 15 seconds
        for i in range(15):
            if process.poll() is not None:
                print(f"❌ Process terminated after {i} seconds with return code: {process.returncode}")
                
                # Get stdout and stderr
                stdout, stderr = process.communicate()
                
                print("\n📄 STDOUT:")
                print(stdout[:1000] if stdout else "(empty)")
                
                print("\n📄 STDERR:")
                print(stderr[:1000] if stderr else "(empty)")
                
                return False
            
            print(f"⏳ Process running... ({i+1}/15 seconds)")
            await asyncio.sleep(1)
        
        print("✅ Process still running after 15 seconds")
        
        # Clean up
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        
        print("🧹 Process terminated cleanly")
        return True
        
    except Exception as e:
        print(f"❌ Failed to start agent process: {e}")
        return False

def test_livekit_connectivity():
    """Test LiveKit connectivity"""
    print("\n🔗 Testing LiveKit Connectivity...")
    
    try:
        # Try to import LiveKit
        from livekit import api
        
        # Try to connect to LiveKit
        livekit_api = api.LiveKitAPI(
            url=os.getenv("LIVEKIT_URL"),
            api_key=os.getenv("LIVEKIT_API_KEY"),
            api_secret=os.getenv("LIVEKIT_API_SECRET")
        )
        
        print("✅ LiveKit API client created successfully")
        return True
        
    except Exception as e:
        print(f"❌ LiveKit connectivity test failed: {e}")
        return False

async def run_comprehensive_diagnosis():
    """Run all diagnostic checks"""
    print("🔧 SAGE AI AGENT CONNECTION DIAGNOSTIC TOOL")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv()
    
    checks = [
        ("Environment Variables", check_environment),
        ("Python Dependencies", check_dependencies),
        ("Required Files", check_files),
        ("LiveKit Connectivity", test_livekit_connectivity),
    ]
    
    results = {}
    for check_name, check_func in checks:
        results[check_name] = check_func()
    
    # Test agent startup if other checks pass
    if all(results.values()):
        results["Agent Startup"] = await test_agent_startup()
    else:
        print("\n⚠️  Skipping agent startup test due to failed prerequisite checks")
        results["Agent Startup"] = False
    
    # Summary
    print("\n" + "=" * 50)
    print("🎯 DIAGNOSTIC SUMMARY")
    print("=" * 50)
    
    for check_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{check_name}: {status}")
    
    if all(results.values()):
        print("\n🎉 All checks passed! Agents should be connecting properly.")
        print("If you're still having issues, check the Render logs for more details.")
    else:
        print(f"\n⚠️  {sum(1 for x in results.values() if not x)} checks failed.")
        print("Please fix the failing checks and try again.")
    
    return all(results.values())

if __name__ == "__main__":
    asyncio.run(run_comprehensive_diagnosis()) 