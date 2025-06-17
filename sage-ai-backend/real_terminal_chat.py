#!/usr/bin/env python3

"""
Real AI Terminal Chat Interface for Sage AI Agents
=================================================

Actual AI-powered terminal interface using OpenAI API
with unique personalities for each philosopher agent.
"""

import asyncio
import logging
import sys
import os
import openai
from dotenv import load_dotenv

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

class RealAIChat:
    def __init__(self):
        self.client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.conversation_history = []
        
        self.agents = {
            "solon": {
                "name": "🏛️ Solon (Moderator)",
                "personality": """You are Solon, the ancient Greek lawmaker and moderator. You keep discussions structured and fair. You reference parliamentary procedure and ensure everyone gets heard. You speak with authority about governance and order. Keep responses concise but authoritative."""
            },
            "aristotle": {
                "name": "🧠 Aristotle (Fact-Checker)", 
                "personality": """You are Aristotle, the logical philosopher and fact-checker. You analyze claims empirically and provide evidence-based responses. You use phrases like 'from a logical standpoint' and 'the evidence suggests'. You correct misconceptions with facts. Be precise and analytical."""
            },
            "socrates": {
                "name": "❓ Socrates (Questioner)",
                "personality": """You are Socrates, master of questioning. You ask probing questions to help people examine their assumptions. Use the Socratic method - respond to statements with deeper questions. Ask 'But what do you mean by...?' and 'Have you considered...?' Challenge assumptions gently."""
            },
            "hermes": {
                "name": "🔄 Hermes (Synthesizer)",
                "personality": """You are Hermes, the messenger who synthesizes different perspectives. You find connections between ideas and help bridge different viewpoints. You use systems thinking and say things like 'I see connections between...' and 'From a systemic view...'. Be integrative."""
            },
            "buddha": {
                "name": "☮️ Buddha (Peacekeeper)",
                "personality": """You are Buddha, promoting mindful and compassionate dialogue. You help reduce tension and find common ground. You speak about the middle path, mindfulness, and compassion. When there's conflict, you guide toward harmony. Be wise and peaceful."""
            }
        }
        
    def display_welcome(self):
        print("\n" + "="*60)
        print("🎭 REAL AI MULTI-AGENT CHAT TERMINAL")
        print("="*60)
        print("Welcome! Chat with 5 real AI philosopher agents:")
        print()
        for agent_key, agent_data in self.agents.items():
            print(f"  {agent_data['name']}")
        print()
        print("💡 Type your message and press Enter")
        print("💡 Type 'quit' or 'exit' to leave")
        print("💡 Type 'help' for more commands")
        print("💡 Type 'history' to see conversation")
        print("="*60)
        print()
        
    async def get_agent_response(self, agent_key: str, user_input: str, context: str = ""):
        """Get a real AI response from a specific agent"""
        agent = self.agents[agent_key]
        
        # Build conversation context
        recent_history = "\n".join(self.conversation_history[-6:]) if self.conversation_history else ""
        
        prompt = f"""
{agent['personality']}

Recent conversation:
{recent_history}

User just said: "{user_input}"

Respond as {agent['name']} in character. Keep your response to 1-2 sentences max. Be conversational and specific to what the user said.
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": agent['personality']},
                    {"role": "user", "content": f"User said: '{user_input}'\n\nRespond in character as {agent['name']}. Keep it conversational and specific to their statement."}
                ],
                max_tokens=150,
                temperature=0.8
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error getting response from {agent_key}: {e}")
            return f"[{agent['name']} is thinking...]"
    
    async def get_multiple_responses(self, user_input: str):
        """Get responses from 2-3 random agents"""
        import random
        
        # Select 2-3 agents to respond
        responding_agents = random.sample(list(self.agents.keys()), random.randint(2, 3))
        
        # Get responses concurrently
        tasks = []
        for agent_key in responding_agents:
            task = self.get_agent_response(agent_key, user_input)
            tasks.append((agent_key, task))
        
        responses = []
        for agent_key, task in tasks:
            try:
                response = await task
                agent_name = self.agents[agent_key]['name']
                responses.append((agent_name, response))
            except Exception as e:
                logger.error(f"Error from {agent_key}: {e}")
        
        return responses
        
    async def start_chat(self):
        """Start the real AI chat interface"""
        # Check if OpenAI API key is available
        if not os.getenv('OPENAI_API_KEY'):
            print("❌ Error: OPENAI_API_KEY not found in environment variables.")
            print("Please set your OpenAI API key in the .env file.")
            return
            
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
                    print("  - 'history' to see conversation history")
                    print("  - 'clear' to clear the screen")
                    print()
                    continue
                    
                if user_input.lower() == 'agents':
                    print("\n🎭 ACTIVE AI AGENTS:")
                    for agent_key, agent_data in self.agents.items():
                        print(f"  {agent_data['name']}")
                    print()
                    continue
                    
                if user_input.lower() == 'history':
                    print("\n📖 CONVERSATION HISTORY:")
                    for line in self.conversation_history[-10:]:
                        print(f"  {line}")
                    print()
                    continue
                    
                if user_input.lower() == 'clear':
                    os.system('cls' if os.name == 'nt' else 'clear')
                    self.display_welcome()
                    continue
                
                # Add user input to history
                self.conversation_history.append(f"You: {user_input}")
                
                # Show user message
                print(f"\n💭 You said: '{user_input}'")
                print("\n🎭 AI Agent responses:")
                print("-" * 40)
                
                # Get real AI responses
                try:
                    responses = await self.get_multiple_responses(user_input)
                    
                    for agent_name, response in responses:
                        print(f"{agent_name}: {response}")
                        self.conversation_history.append(f"{agent_name}: {response}")
                        print()
                        
                except Exception as e:
                    print(f"❌ Error getting AI responses: {e}")
                    print("Please check your OpenAI API key and internet connection.")
                
        except KeyboardInterrupt:
            print("\n\n👋 Chat ended. Goodbye!")
        except Exception as e:
            print(f"\n❌ Error: {e}")

def main():
    """Main entry point"""
    chat = RealAIChat()
    asyncio.run(chat.start_chat())

if __name__ == "__main__":
    main() 