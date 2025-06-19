# 📚 AI Agent Knowledge Base Setup Guide

## Quick Start

### Option 1: Automatic Setup (Recommended)
Run this to automatically download and load knowledge for all agents:

```bash
cd sage-ai-backend
python auto_knowledge_loader.py
```

### Option 2: Individual Agent Setup
```python
# In Python
from auto_knowledge_loader import setup_single_agent
import asyncio

# Load knowledge for specific agent
asyncio.run(setup_single_agent("solon"))     # Parliamentary procedures
asyncio.run(setup_single_agent("socrates"))  # Socratic questioning
asyncio.run(setup_single_agent("hermes"))    # Systems thinking
asyncio.run(setup_single_agent("buddha"))    # Mindful conflict resolution
```

## What Gets Loaded

### 🏛️ **Solon (Rule Enforcer)**
- NYC Guide to Parliamentary Procedure (125 pages)
- Parliamentary Procedure 101 (practical guide)
- Parliamentary Procedure Quick Reference

**Skills gained:** Meeting moderation, conflict de-escalation, fair process enforcement

### ❓ **Socrates (Clarifier)** 
- The Art of Socratic Questioning (Foundation for Critical Thinking)

**Skills gained:** Deep questioning techniques, assumption challenging, critical thinking facilitation

### 🌉 **Hermes (Synthesizer)**
- Systems Thinking Tools: A User's Guide (87 pages)
- Systems Thinking Basics: From Concepts to Causal Loops

**Skills gained:** Connecting ideas, finding patterns, synthesis frameworks, integration methods

### ☮️ **Buddha (Peacekeeper)**
- Transform Conflict: Mediation Resources for Buddhist Chaplains
- Meeting Conflicts Mindfully

**Skills gained:** Compassionate communication, mindful de-escalation, peaceful conflict transformation

## Manual Additions (Optional)

For even richer knowledge bases, you can manually add these sources:

### Additional Socratic Sources:
- **The Socratic Temperament**: Visit http://www.socraticmethod.net/essays/ST_pdf_versions.html
- **Think with Socrates**: Search for this title on academic sites

### Additional Buddha Sources:
- **Buddhist Path to Transforming Conflict**: https://www.mangrovec.com/files/the-buddhist-path-to-transforming-conflict.pdf

## File Structure After Setup

```
sage-ai-backend/
├── knowledge_documents/
│   ├── solon/
│   │   ├── nyc_parliamentary_procedure.pdf
│   │   ├── parliamentary_procedure_101.pdf
│   │   └── parliamentary_cheat_sheet.pdf
│   ├── socrates/
│   │   └── socratic_questioning_guide.pdf
│   ├── hermes/
│   │   ├── systems_thinking_tools.pdf
│   │   └── systems_thinking_basics.pdf
│   └── buddha/
│       ├── buddhist_mediation_resources.pdf
│       └── meeting_conflicts_mindfully.pdf
└── knowledge_base/
    ├── solon_moderation_kb/
    ├── aristotle_logic_kb/
    ├── socrates_inquiry_kb/
    ├── hermes_synthesis_kb/
    └── buddha_compassion_kb/
```

## Testing Your Setup

After loading knowledge, test each agent:

```python
from knowledge_base_manager import KnowledgeBaseManager

kb = KnowledgeBaseManager()

# Test Solon's parliamentary knowledge
solon_context = await kb.get_context("solon", "How should we handle interruptions during debate?")

# Test Socrates' questioning techniques  
socrates_context = await kb.get_context("socrates", "How do I ask better questions?")

# Test Hermes' synthesis abilities
hermes_context = await kb.get_context("hermes", "How do I connect these opposing viewpoints?")

# Test Buddha's conflict resolution
buddha_context = await kb.get_context("buddha", "How should we de-escalate this heated argument?")
```

## Expected Results

- **Solon**: Will reference specific parliamentary procedures, proper meeting protocols
- **Socrates**: Will suggest specific questioning strategies, critical thinking frameworks  
- **Hermes**: Will apply systems thinking tools, synthesis methodologies
- **Buddha**: Will recommend mindful communication, compassionate conflict resolution

## Troubleshooting

**Q: Some PDFs fail to download?**
A: Check internet connection. Some sites require headers or have bot protection.

**Q: ChromaDB errors?**
A: Ensure ChromaDB is installed: `pip install chromadb`

**Q: Knowledge not retrieving properly?**
A: Check that your OpenAI API key is set for embeddings.

**Q: Want to add your own PDFs?**
A: Use the convenience functions in `pdf_knowledge_loader.py`:
```python
await load_moderation_guide("your_file.pdf", "Description")
``` 