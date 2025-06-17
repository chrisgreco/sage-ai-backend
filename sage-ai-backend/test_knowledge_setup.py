"""
Test script to verify knowledge base setup for all agents
"""

import asyncio
import logging
from knowledge_base_manager import KnowledgeBaseManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_agent_knowledge(agent_name: str, test_query: str):
    """Test knowledge retrieval for a specific agent"""
    try:
        kb = KnowledgeBaseManager()
        context = await kb.get_context(agent_name, test_query)
        
        print(f"\n🎭 {agent_name.upper()} TEST")
        print("=" * 40)
        print(f"Query: {test_query}")
        print(f"Knowledge Retrieved: {len(context)} characters")
        
        if context:
            # Show first 200 characters of retrieved knowledge
            preview = context[:200] + "..." if len(context) > 200 else context
            print(f"Preview: {preview}")
            return True
        else:
            print("❌ No knowledge retrieved")
            return False
            
    except Exception as e:
        print(f"❌ Error testing {agent_name}: {e}")
        return False

async def test_all_agents():
    """Test knowledge retrieval for all agents"""
    
    test_cases = [
        ("solon", "How should we handle interruptions during a debate?"),
        ("aristotle", "How do I verify the accuracy of statistical claims?"),
        ("socrates", "What are effective questioning techniques for deeper understanding?"),
        ("hermes", "How do I synthesize opposing viewpoints into a coherent framework?"),
        ("buddha", "What are mindful approaches to de-escalating heated conflicts?")
    ]
    
    print("🧠 TESTING AI AGENT KNOWLEDGE BASES")
    print("=" * 50)
    
    results = {}
    for agent_name, query in test_cases:
        success = await test_agent_knowledge(agent_name, query)
        results[agent_name] = success
    
    # Summary
    print("\n📊 TEST RESULTS SUMMARY")
    print("=" * 30)
    
    total_passed = sum(results.values())
    total_tests = len(results)
    
    for agent, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{agent.title():<10}: {status}")
    
    print(f"\nOverall: {total_passed}/{total_tests} agents have working knowledge bases")
    
    if total_passed == total_tests:
        print("🎉 All knowledge bases are working correctly!")
    else:
        print("⚠️  Some knowledge bases need setup. Run auto_knowledge_loader.py")
    
    return results

async def demonstrate_enhanced_responses():
    """Show how agents respond with vs without knowledge"""
    
    print("\n🔬 DEMONSTRATION: Enhanced vs Basic Responses")
    print("=" * 55)
    
    kb = KnowledgeBaseManager()
    
    # Test query for Solon
    query = "Someone keeps interrupting the speaker. How should I handle this?"
    
    # Get enhanced response with knowledge
    enhanced_context = await kb.get_context("solon", query)
    
    print(f"Query: {query}")
    print(f"\n📚 WITH KNOWLEDGE BASE ({len(enhanced_context)} chars of context):")
    
    if enhanced_context:
        # Extract key guidance from the knowledge
        if "parliamentary" in enhanced_context.lower():
            print("✅ Found parliamentary procedure guidance")
        if "interruption" in enhanced_context.lower():
            print("✅ Found specific interruption handling protocols")
        if "chair" in enhanced_context.lower():
            print("✅ Found chairperson/moderator instructions")
            
        preview = enhanced_context[:300] + "..." if len(enhanced_context) > 300 else enhanced_context
        print(f"Knowledge preview: {preview}")
    else:
        print("❌ No relevant knowledge found")
    
    print(f"\n💡 WITHOUT KNOWLEDGE BASE:")
    print("Agent would only use general AI training - less specific, less authoritative")

if __name__ == "__main__":
    print("Starting knowledge base tests...\n")
    
    # Run the tests
    asyncio.run(test_all_agents())
    
    print("\n" + "="*60)
    
    # Run demonstration
    asyncio.run(demonstrate_enhanced_responses()) 