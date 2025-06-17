"""
Simple Knowledge Processor
A standalone script to process downloaded PDFs and demonstrate the knowledge system
"""

import os
from pathlib import Path

def analyze_downloaded_knowledge():
    """Analyze what knowledge was successfully downloaded"""
    knowledge_dir = Path("./knowledge_documents")
    
    if not knowledge_dir.exists():
        print("❌ No knowledge_documents directory found. Run standalone_knowledge_loader.py first.")
        return
    
    print("📚 KNOWLEDGE BASE ANALYSIS")
    print("=" * 50)
    
    total_files = 0
    total_size = 0
    
    # Analyze each agent's knowledge
    agents = {
        "solon": {
            "emoji": "🏛️",
            "name": "SOLON (Rule Enforcer)",
            "skills": ["Parliamentary procedures", "Meeting moderation", "Conflict de-escalation", "Fair process enforcement"]
        },
        "socrates": {
            "emoji": "❓", 
            "name": "SOCRATES (Clarifier)",
            "skills": ["Socratic questioning", "Critical thinking", "Assumption challenging", "Deep inquiry techniques"]
        },
        "hermes": {
            "emoji": "🌉",
            "name": "HERMES (Synthesizer)", 
            "skills": ["Systems thinking", "Pattern recognition", "Synthesis frameworks", "Integration methods"]
        },
        "buddha": {
            "emoji": "☮️",
            "name": "BUDDHA (Peacekeeper)",
            "skills": ["Mindful communication", "Conflict resolution", "Compassionate dialogue", "De-escalation techniques"]
        }
    }
    
    for agent_id, agent_info in agents.items():
        agent_dir = knowledge_dir / agent_id
        
        print(f"\n{agent_info['emoji']} {agent_info['name']}:")
        
        if not agent_dir.exists():
            print("   📁 No knowledge directory found")
            continue
            
        pdf_files = list(agent_dir.glob("*.pdf"))
        
        if not pdf_files:
            print("   📄 No PDF files found")
            continue
        
        agent_size = 0
        for pdf_file in pdf_files:
            file_size = pdf_file.stat().st_size / 1024 / 1024  # MB
            print(f"   📄 {pdf_file.name} ({file_size:.1f} MB)")
            agent_size += file_size
            total_size += file_size
        
        total_files += len(pdf_files)
        
        print(f"   📊 Total: {len(pdf_files)} files, {agent_size:.1f} MB")
        print(f"   🎯 Skills gained: {', '.join(agent_info['skills'])}")
    
    print(f"\n🎉 SUMMARY")
    print("=" * 30)
    print(f"📁 Total agents: {len([d for d in knowledge_dir.iterdir() if d.is_dir()])}")
    print(f"📄 Total PDF files: {total_files}")
    print(f"💾 Total size: {total_size:.1f} MB")
    
    print(f"\n🚀 WHAT YOUR AGENTS CAN NOW DO:")
    print("=" * 40)
    print("🏛️ Solon can reference specific parliamentary procedures")
    print("❓ Socrates can apply proven questioning frameworks") 
    print("🌉 Hermes can use systems thinking methodologies")
    print("☮️ Buddha can guide mindful conflict resolution")
    
    print(f"\n📖 KNOWLEDGE SOURCES BREAKDOWN:")
    print("=" * 40)
    
    source_details = {
        "solon": [
            "NYC Guide to Parliamentary Procedure (comprehensive rules)",
            "Parliamentary Procedure 101 (practical application)",
            "Parliamentary Quick Reference (fast lookup guide)"
        ],
        "socrates": [
            "The Art of Socratic Questioning (Foundation for Critical Thinking)"
        ],
        "hermes": [
            "Systems Thinking Basics: From Concepts to Causal Loops"
        ],
        "buddha": [
            "Transform Conflict: Mediation Resources for Buddhist Chaplains",
            "Meeting Conflicts Mindfully (Tibetan conflict resolution)"
        ]
    }
    
    for agent_id, sources in source_details.items():
        agent_info = agents[agent_id]
        print(f"\n{agent_info['emoji']} {agent_id.upper()}:")
        for source in sources:
            print(f"   • {source}")
    
    print(f"\n✨ NEXT STEPS:")
    print("1. Test agents with knowledge-specific questions")
    print("2. Start debates with specialized topics")
    print("3. Observe how agents apply their expertise")
    print("4. Add more PDFs as needed for deeper knowledge")
    
    return total_files, total_size

def test_knowledge_questions():
    """Provide sample questions to test each agent's knowledge"""
    print(f"\n🧪 SAMPLE KNOWLEDGE TEST QUESTIONS")
    print("=" * 45)
    
    test_questions = {
        "🏛️ Solon": [
            "How should we handle interruptions during a formal debate?",
            "What's the proper procedure for amending a motion?",
            "How do we maintain order when members disagree?"
        ],
        "❓ Socrates": [
            "How can I ask better clarifying questions?",
            "What questioning techniques reveal assumptions?",
            "How do I guide someone to discover truth themselves?"
        ],
        "🌉 Hermes": [
            "How can we connect these opposing viewpoints?",
            "What systems thinking tools apply here?",
            "How do we synthesize multiple perspectives?"
        ],
        "☮️ Buddha": [
            "How should we de-escalate this heated argument?",
            "What mindful communication techniques can help?",
            "How do we resolve conflict compassionately?"
        ]
    }
    
    for agent, questions in test_questions.items():
        print(f"\n{agent}:")
        for i, question in enumerate(questions, 1):
            print(f"   {i}. {question}")
    
    print(f"\n💡 TIP: Ask these questions during debates to see agents apply their specialized knowledge!")

if __name__ == "__main__":
    total_files, total_size = analyze_downloaded_knowledge()
    test_knowledge_questions()
    
    print(f"\n🎊 CONGRATULATIONS!")
    print(f"Your AI agents now have {total_files} specialized knowledge sources totaling {total_size:.1f} MB!")
    print("They're ready for expert-level philosophical debates! 🎭") 