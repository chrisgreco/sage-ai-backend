#!/usr/bin/env python3

"""
Terminal Chat Interface for Sage AI Agents
==========================================

Simple terminal interface to chat directly with the AI philosopher agents
without needing the web interface.
"""

import asyncio
import logging
import sys
import os
from dotenv import load_dotenv

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TerminalChat:
    def __init__(self):
        self.room_name = "terminal-chat"
        self.agents = {
            "solon": "🏛️ Solon (Moderator)",
            "aristotle": "🧠 Aristotle (Fact-Checker)", 
            "socrates": "❓ Socrates (Questioner)",
            "hermes": "🔄 Hermes (Synthesizer)",
            "buddha": "☮️ Buddha (Peacekeeper)"
        }
        
    def display_welcome(self):
        print("\n" + "="*60)
        print("🎭 SAGE AI MULTI-AGENT CHAT TERMINAL")
        print("="*60)
        print("Welcome! You can now chat with 5 AI philosopher agents:")
        print()
        for agent_name, display_name in self.agents.items():
            print(f"  {display_name}")
        print()
        print("💡 Type your message and press Enter")
        print("💡 Type 'quit' or 'exit' to leave")
        print("💡 Type 'help' for more commands")
        print("="*60)
        print()
        
    def simulate_agent_response(self, user_input: str):
        """Simulate AI agent responses for demonstration"""
        import random
        
        responses = {
            "solon": [
                f"🏛️ As moderator, I believe we should examine '{user_input}' through structured dialogue.",
                f"🏛️ Let us establish the parameters for discussing '{user_input}' fairly.",
                f"🏛️ I propose we address '{user_input}' using parliamentary procedure."
            ],
            "aristotle": [
                f"🧠 From a logical standpoint, '{user_input}' requires empirical analysis.",
                f"🧠 The facts suggest that '{user_input}' has multiple dimensions to consider.",
                f"🧠 Let me research the evidence regarding '{user_input}'..."
            ],
            "socrates": [
                f"❓ But what do you really mean by '{user_input}'? Can you define it more precisely?",
                f"❓ Have you considered the implications of '{user_input}'? What assumptions are we making?",
                f"❓ Why do you believe '{user_input}' is important? What led you to this question?"
            ],
            "hermes": [
                f"🔄 I see connections between '{user_input}' and several other concepts we should explore.",
                f"🔄 Let me synthesize the different perspectives on '{user_input}' we've heard.",
                f"🔄 The systemic view of '{user_input}' reveals interesting patterns."
            ],
            "buddha": [
                f"☮️ Let us approach '{user_input}' with mindfulness and compassion.",
                f"☮️ I sense some tension in this discussion of '{user_input}'. Perhaps we can find common ground.",
                f"☮️ The middle path regarding '{user_input}' may offer wisdom to all perspectives."
            ]
        }
        
        # Simulate 2-3 agents responding
        responding_agents = random.sample(list(self.agents.keys()), random.randint(2, 3))
        
        for agent in responding_agents:
            response = random.choice(responses[agent])
            print(f"{response}")
            print()
            
    async def start_chat(self):
        """Start the terminal chat interface"""
        self.display_welcome()
        
        try:
            while True:
                # Get user input
                user_input = input("🎯 You: ").strip()
                
                if not user_input:
                    continue
                    
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    print("\n👋 Goodbye! Thank you for chatting with the AI philosophers!")
                    break
                    
                if user_input.lower() == 'help':
                    print("\n📖 COMMANDS:")
                    print("  - Type any message to chat with the agents")
                    print("  - 'quit' or 'exit' to leave")
                    print("  - 'agents' to see who's available")
                    print("  - 'clear' to clear the screen")
                    print()
                    continue
                    
                if user_input.lower() == 'agents':
                    print("\n🎭 ACTIVE AGENTS:")
                    for agent_name, display_name in self.agents.items():
                        print(f"  {display_name}")
                    print()
                    continue
                    
                if user_input.lower() == 'clear':
                    os.system('cls' if os.name == 'nt' else 'clear')
                    self.display_welcome()
                    continue
                
                # Show user message
                print(f"\n💭 You said: '{user_input}'")
                print("\n🎭 Agent responses:")
                print("-" * 40)
                
                # Simulate agent responses
                self.simulate_agent_response(user_input)
                
        except KeyboardInterrupt:
            print("\n\n👋 Chat ended. Goodbye!")
        except Exception as e:
            print(f"\n❌ Error: {e}")

def main():
    """Main entry point"""
    chat = TerminalChat()
    asyncio.run(chat.start_chat())

if __name__ == "__main__":
    main() 