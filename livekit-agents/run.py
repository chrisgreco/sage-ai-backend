#!/usr/bin/env python3
import os
import sys
import argparse
import subprocess
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_args():
    parser = argparse.ArgumentParser(description='LiveKit Debate Moderator Launcher')
    parser.add_argument('mode', choices=['agent', 'client', 'both'], 
                        help='Run the agent, test client, or both')
    parser.add_argument('--livekit-url', default='wss://sage-2kpu4z1y.livekit.cloud',
                        help='LiveKit server URL')
    parser.add_argument('--livekit-api-key', default='APIWQtUQUijqXVp',
                        help='LiveKit API key')
    parser.add_argument('--livekit-api-secret', default='LDs7r35vqLLwR5vBPFg99hlPqE5y2EZ4sq7M90fAfEI',
                        help='LiveKit API secret')
    parser.add_argument('--openai-api-key', default=os.environ.get('OPENAI_API_KEY'),
                        help='OpenAI API key')
    parser.add_argument('--debate-topic', default='The impact of artificial intelligence on society',
                        help='Debate topic')
    parser.add_argument('--room-name', default='test-debate-room',
                        help='Room name to join')
    parser.add_argument('--identity', default='test-user',
                        help='User identity')
    return parser.parse_args()

def run_agent(args):
    """Run the LiveKit agent"""
    logger.info("Starting debate moderator agent...")
    
    # Prepare command
    cmd = [
        sys.executable, 'run_agent.py',
        '--livekit-url', args.livekit_url,
        '--livekit-api-key', args.livekit_api_key,
        '--livekit-api-secret', args.livekit_api_secret,
        '--debate-topic', args.debate_topic
    ]
    
    # Add OpenAI API key if provided
    if args.openai_api_key:
        cmd.extend(['--openai-api-key', args.openai_api_key])
    
    logger.info(f"Running command: {' '.join(cmd)}")
    
    # Run the command with output displayed
    try:
        # Use stdout and stderr so we can see the output
        return subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            universal_newlines=True,
            bufsize=1
        )
    except Exception as e:
        logger.error(f"Error starting agent: {e}")
        return None

def run_client(args):
    """Run the LiveKit test client"""
    logger.info("Starting test client...")
    
    # Prepare command
    cmd = [
        sys.executable, 'test_agent.py',
        '--livekit-url', args.livekit_url,
        '--livekit-api-key', args.livekit_api_key,
        '--livekit-api-secret', args.livekit_api_secret,
        '--room-name', args.room_name,
        '--identity', args.identity
    ]
    
    # Run the command
    try:
        subprocess.run(cmd)
    except Exception as e:
        logger.error(f"Error running test client: {e}")

def main():
    """Main function"""
    args = parse_args()
    
    # Check for OpenAI API key
    if not args.openai_api_key and args.mode in ['agent', 'both']:
        logger.warning("No OpenAI API key provided. The agent will not work properly without it.")
        answer = input("Do you want to continue anyway? (y/n): ")
        if answer.lower() != 'y':
            logger.info("Exiting...")
            sys.exit(0)
    
    # Run the agent and/or client
    agent_process = None
    
    try:
        if args.mode in ['agent', 'both']:
            agent_process = run_agent(args)
            if not agent_process:
                logger.error("Failed to start the agent. Exiting...")
                sys.exit(1)
            
            # Start a thread to read and print the output
            import threading
            
            def read_output(process):
                while True:
                    # Read stdout
                    output = process.stdout.readline()
                    if output:
                        print(f"[AGENT STDOUT] {output.strip()}")
                    
                    # Read stderr
                    error = process.stderr.readline()
                    if error:
                        print(f"[AGENT STDERR] {error.strip()}")
                    
                    # Check if process is still running
                    if process.poll() is not None:
                        # Process has terminated
                        # Read any remaining output
                        for line in process.stdout:
                            print(f"[AGENT STDOUT] {line.strip()}")
                        for line in process.stderr:
                            print(f"[AGENT STDERR] {line.strip()}")
                        break
            
            # Start the output reader thread
            output_thread = threading.Thread(target=read_output, args=(agent_process,))
            output_thread.daemon = True  # Thread will exit when main thread exits
            output_thread.start()
        
        if args.mode in ['client', 'both']:
            if args.mode == 'both':
                # Give the agent time to start up and connect
                logger.info("Waiting for agent to start...")
                import time
                time.sleep(5)
            
            run_client(args)
    
    finally:
        # Clean up
        if agent_process:
            logger.info("Stopping agent...")
            agent_process.terminate()
            try:
                agent_process.wait(timeout=5)  # Wait up to 5 seconds for process to terminate
            except subprocess.TimeoutExpired:
                logger.warning("Agent process did not terminate gracefully, forcing...")
                agent_process.kill()
                agent_process.wait()
            logger.info("Agent stopped")

if __name__ == "__main__":
    main() 