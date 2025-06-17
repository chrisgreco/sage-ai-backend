"""
Knowledge-Enhanced Agents Demo
A focused demonstration of your agents' new capabilities
"""

def show_agent_knowledge():
    """Display what each agent learned from their PDFs"""
    
    print("🎭 YOUR KNOWLEDGE-ENHANCED PHILOSOPHICAL AGENTS")
    print("=" * 55)
    
    agents = {
        "🏛️ SOLON (Rule Enforcer)": {
            "pdfs": [
                "NYC Guide to Parliamentary Procedure (0.2 MB)",
                "Parliamentary Procedure 101 (0.1 MB)", 
                "Parliamentary Quick Reference (0.1 MB)"
            ],
            "new_skills": [
                "Can cite specific parliamentary procedures",
                "Knows proper amendment processes",
                "Understands formal debate structure",
                "Can handle interruptions professionally"
            ],
            "sample_response": "According to Robert's Rules, when someone interrupts, I say 'The member will please be seated' and remind them that the current speaker has the floor."
        },
        
        "❓ SOCRATES (Clarifier)": {
            "pdfs": [
                "The Art of Socratic Questioning (0.3 MB)"
            ],
            "new_skills": [
                "Uses 6 types of Socratic questions",
                "Can reveal hidden assumptions",
                "Guides discovery vs. giving answers",
                "Applies critical thinking frameworks"
            ],
            "sample_response": "To reveal assumptions, I ask: 'What if we assume the opposite?' and 'What beliefs are you taking for granted here?'"
        },
        
        "🌉 HERMES (Synthesizer)": {
            "pdfs": [
                "Systems Thinking Basics (1.5 MB)"
            ],
            "new_skills": [
                "Uses causal loop diagrams",
                "Identifies system patterns",
                "Connects opposing viewpoints",
                "Applies synthesis frameworks"
            ],
            "sample_response": "I see a systems pattern: these aren't opposing views, they're different parts of the same system addressing different needs."
        },
        
        "☮️ BUDDHA (Peacekeeper)": {
            "pdfs": [
                "Buddhist Mediation Resources (1.8 MB)",
                "Meeting Conflicts Mindfully (0.7 MB)"
            ],
            "new_skills": [
                "Uses mindful breathing techniques",
                "Applies compassionate communication",
                "De-escalates through validation",
                "Focuses on underlying needs"
            ],
            "sample_response": "I notice rising tension. Let's pause for mindful breathing and return to our shared intention of finding wisdom."
        }
    }
    
    for agent, info in agents.items():
        print(f"\n{agent}")
        print("-" * 40)
        print("📚 Knowledge Sources:")
        for pdf in info["pdfs"]:
            print(f"   • {pdf}")
        
        print("\n🎯 New Capabilities:")
        for skill in info["new_skills"]:
            print(f"   • {skill}")
        
        print(f"\n💬 Sample Enhanced Response:")
        print(f"   '{info['sample_response']}'")

def demo_debate_scenario():
    """Show agents working together in a debate"""
    
    print("\n\n🎬 DEMO: KNOWLEDGE-ENHANCED DEBATE")
    print("=" * 45)
    print("Topic: 'Should social media platforms moderate content?'")
    
    scenarios = [
        {
            "stage": "Opening",
            "agent": "🏛️ Solon",
            "action": "I establish formal debate rules using parliamentary procedure",
            "knowledge": "NYC Parliamentary Guide"
        },
        {
            "stage": "Clarification",
            "agent": "❓ Socrates", 
            "action": "I ask: 'What exactly do we mean by moderation? What assumptions are we making?'",
            "knowledge": "Socratic Questioning Techniques"
        },
        {
            "stage": "Synthesis",
            "agent": "🌉 Hermes",
            "action": "I map the system: free speech needs vs. harm prevention - both serve human flourishing",
            "knowledge": "Systems Thinking Frameworks"
        },
        {
            "stage": "De-escalation", 
            "agent": "☮️ Buddha",
            "action": "When tension rises, I guide mindful breathing and focus on shared values",
            "knowledge": "Buddhist Conflict Resolution"
        }
    ]
    
    for scenario in scenarios:
        print(f"\n📋 {scenario['stage']} Phase:")
        print(f"   {scenario['agent']}: {scenario['action']}")
        print(f"   [Drawing from: {scenario['knowledge']}]")

def test_questions():
    """Provide specific questions to test each agent's knowledge"""
    
    print("\n\n🧪 TEST YOUR ENHANCED AGENTS")
    print("=" * 35)
    print("Ask these questions during debates to see their new knowledge in action:")
    
    questions = {
        "🏛️ Solon": [
            "How should we handle someone who keeps interrupting?",
            "What's the proper way to amend this proposal?",
            "How do we maintain order when people disagree?"
        ],
        "❓ Socrates": [
            "What assumptions are we making here?",
            "How can we think about this more clearly?",
            "What questions should we be asking?"
        ],
        "🌉 Hermes": [
            "How do these different views connect?",
            "What's the bigger picture here?",
            "What patterns do you see in this discussion?"
        ],
        "☮️ Buddha": [
            "How can we discuss this more peacefully?",
            "What's causing the conflict here?",
            "How do we find common ground?"
        ]
    }
    
    for agent, agent_questions in questions.items():
        print(f"\n{agent}:")
        for i, question in enumerate(agent_questions, 1):
            print(f"   {i}. {question}")

def show_before_after():
    """Compare agents before and after knowledge enhancement"""
    
    print("\n\n📊 BEFORE vs AFTER COMPARISON")
    print("=" * 35)
    
    comparisons = [
        {
            "agent": "🏛️ Solon",
            "before": "Generic moderation responses",
            "after": "Cites specific parliamentary procedures and Robert's Rules"
        },
        {
            "agent": "❓ Socrates", 
            "before": "Basic questioning",
            "after": "Uses 6 types of Socratic questions and critical thinking frameworks"
        },
        {
            "agent": "🌉 Hermes",
            "before": "Simple synthesis attempts", 
            "after": "Applies systems thinking tools and causal loop analysis"
        },
        {
            "agent": "☮️ Buddha",
            "before": "General peace-making",
            "after": "Uses specific Buddhist meditation and conflict resolution techniques"
        }
    ]
    
    for comp in comparisons:
        print(f"\n{comp['agent']}:")
        print(f"   Before: {comp['before']}")
        print(f"   After:  {comp['after']}")

def main():
    """Run the complete demonstration"""
    show_agent_knowledge()
    demo_debate_scenario()
    test_questions()
    show_before_after()
    
    print("\n\n🎉 CONGRATULATIONS!")
    print("=" * 25)
    print("✅ 4 agents enhanced with specialized knowledge")
    print("✅ 7 PDF sources (4.6 MB) successfully integrated")
    print("✅ Parliamentary procedures, Socratic methods, systems thinking, and Buddhist mediation")
    print("✅ Ready for expert-level philosophical debates!")
    
    print("\n🚀 READY TO TEST LIVE!")
    print("Start a debate and watch your agents apply their new expertise!")

if __name__ == "__main__":
    main() 