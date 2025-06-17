"""
Process Downloaded Knowledge into Agent Knowledge Bases
This script takes all the downloaded PDFs and loads them into the vector databases
"""

import asyncio
import os
from pathlib import Path
from pdf_knowledge_loader import (
    load_moderation_guide,
    load_socratic_dialogue, 
    load_synthesis_guide,
    load_mindfulness_text
)

async def process_all_knowledge():
    """Process all downloaded PDFs into knowledge bases"""
    knowledge_dir = Path("./knowledge_documents")
    
    if not knowledge_dir.exists():
        print("❌ No knowledge_documents directory found. Run standalone_knowledge_loader.py first.")
        return
    
    print("🔧 PROCESSING PDFS INTO KNOWLEDGE BASES")
    print("=" * 50)
    
    results = {}
    
    # Process Solon's parliamentary procedures
    solon_dir = knowledge_dir / "solon"
    if solon_dir.exists():
        print("\n🏛️ SOLON (Rule Enforcer):")
        solon_count = 0
        for pdf_file in solon_dir.glob("*.pdf"):
            print(f"   📥 Processing: {pdf_file.name}")
            try:
                success = await load_moderation_guide(str(pdf_file), f"Parliamentary Guide: {pdf_file.stem}")
                if success:
                    solon_count += 1
                    print(f"   ✅ Loaded: {pdf_file.name}")
                else:
                    print(f"   ❌ Failed: {pdf_file.name}")
            except Exception as e:
                print(f"   ❌ Error with {pdf_file.name}: {e}")
        results["solon"] = solon_count
        print(f"   📊 Solon: {solon_count} sources loaded")
    
    # Process Socrates' questioning techniques
    socrates_dir = knowledge_dir / "socrates" 
    if socrates_dir.exists():
        print("\n❓ SOCRATES (Clarifier):")
        socrates_count = 0
        for pdf_file in socrates_dir.glob("*.pdf"):
            print(f"   📥 Processing: {pdf_file.name}")
            try:
                success = await load_socratic_dialogue(str(pdf_file), f"Socratic Method: {pdf_file.stem}")
                if success:
                    socrates_count += 1
                    print(f"   ✅ Loaded: {pdf_file.name}")
                else:
                    print(f"   ❌ Failed: {pdf_file.name}")
            except Exception as e:
                print(f"   ❌ Error with {pdf_file.name}: {e}")
        results["socrates"] = socrates_count
        print(f"   📊 Socrates: {socrates_count} sources loaded")
    
    # Process Hermes' systems thinking
    hermes_dir = knowledge_dir / "hermes"
    if hermes_dir.exists():
        print("\n🌉 HERMES (Synthesizer):")
        hermes_count = 0
        for pdf_file in hermes_dir.glob("*.pdf"):
            print(f"   📥 Processing: {pdf_file.name}")
            try:
                success = await load_synthesis_guide(str(pdf_file), f"Systems Thinking: {pdf_file.stem}")
                if success:
                    hermes_count += 1
                    print(f"   ✅ Loaded: {pdf_file.name}")
                else:
                    print(f"   ❌ Failed: {pdf_file.name}")
            except Exception as e:
                print(f"   ❌ Error with {pdf_file.name}: {e}")
        results["hermes"] = hermes_count
        print(f"   📊 Hermes: {hermes_count} sources loaded")
    
    # Process Buddha's mindfulness and conflict resolution
    buddha_dir = knowledge_dir / "buddha"
    if buddha_dir.exists():
        print("\n☮️ BUDDHA (Peacekeeper):")
        buddha_count = 0
        for pdf_file in buddha_dir.glob("*.pdf"):
            print(f"   📥 Processing: {pdf_file.name}")
            try:
                success = await load_mindfulness_text(str(pdf_file), f"Mindful Conflict Resolution: {pdf_file.stem}")
                if success:
                    buddha_count += 1
                    print(f"   ✅ Loaded: {pdf_file.name}")
                else:
                    print(f"   ❌ Failed: {pdf_file.name}")
            except Exception as e:
                print(f"   ❌ Error with {pdf_file.name}: {e}")
        results["buddha"] = buddha_count
        print(f"   📊 Buddha: {buddha_count} sources loaded")
    
    # Print final summary
    total_loaded = sum(results.values())
    print(f"\n🎉 KNOWLEDGE PROCESSING COMPLETE!")
    print("=" * 40)
    for agent, count in results.items():
        print(f"✅ {agent.title()}: {count} knowledge sources")
    print(f"🎯 Total: {total_loaded} knowledge sources loaded")
    
    print(f"\n🚀 AGENTS NOW HAVE SPECIALIZED KNOWLEDGE!")
    print("🏛️ Solon: Parliamentary procedures, meeting moderation")
    print("❓ Socrates: Socratic questioning, critical thinking")  
    print("🌉 Hermes: Systems thinking, synthesis frameworks")
    print("☮️ Buddha: Mindful communication, conflict resolution")
    
    return results

if __name__ == "__main__":
    asyncio.run(process_all_knowledge()) 